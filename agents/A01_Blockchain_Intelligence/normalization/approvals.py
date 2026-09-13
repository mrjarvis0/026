"""
CIE-OS
A01 Blockchain Intelligence Agent

Module:
    normalization.approvals

Purpose:
    Turn a captured batch of event logs into stored-ready approval records,
    binding each to the block that emitted it.

Design goals:
    - Decoding delegated to ``blockchain.security.approval_risk``; this layer
      maps, binds to a block, and counts the remainder
    - Undecoded approvals counted, never silently dropped
    - Block linkage required, so an approval cannot outlive its block
    - Same refusal discipline as :mod:`normalization.logs`
    - Pure: no chain access, no contract calls

Notes:
    This module is the sibling of :mod:`normalization.logs`. A block's log
    batch carries transfers and approvals side by side; ``normalize_logs``
    files the transfers and counts the approvals as undecoded, and this files
    the approvals. Running both over the same payload is deliberate -- the two
    are different facts with different shapes, and folding an approval into
    transfer flow inflates every total it touches.

    **Every approval is bound to its own block hash**, taken from the log
    rather than from the caller. Storage cascades approvals from the block row,
    so a reorg withdrawal removes them with the block that carried them; binding
    to height instead would leave a grant attached to a height whose block was
    abandoned -- a live-looking approval on a chain that no longer exists.

    A decoded approval that arrives without a readable block hash is refused
    rather than stored under a guessed one, for the same reason
    ``normalize_logs`` refuses a transfer without linkage: a grant that survives
    a reorg it should not is worse than one that was never filed.
"""

from __future__ import annotations

import logging

from dataclasses import dataclass
from typing import Any

from blockchain.security.approval_risk import (
    ApprovalRefusal,
    DecodedApproval,
    decode_approval,
)
from config.security.validation import ValidationIssue

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StoredApproval:
    """
    One decoded approval and the block hash that binds it to storage.

    The decoder reads a grant's fields but not its block hash -- a log carries
    the hash in ``blockHash``, which is metadata about where the log sits, not
    part of the event. This pairs the two so a repository has the linkage it
    needs to cascade the grant away when its block is withdrawn.
    """

    approval: DecodedApproval
    block_hash: str


@dataclass(frozen=True, slots=True)
class ApprovalActivity:
    """
    What a log batch held in the way of approvals, ready to store.

    ``undecoded`` counts approval-shaped logs that could not be read, not every
    non-approval log in the batch. A rising count for one contract is the same
    signal a rising transfer-refusal rate is: a non-standard implementation, or
    occasionally something shaped to confuse a decoder.
    """

    chain: str
    approvals: tuple[StoredApproval, ...] = ()
    undecoded: int = 0
    source_record_id: str = ""

    @property
    def empty(self) -> bool:
        return not self.approvals

    def as_dict(self) -> dict[str, Any]:
        return {
            "chain": self.chain,
            "approvals": len(self.approvals),
            "undecoded": self.undecoded,
            "source_record_id": self.source_record_id,
        }


def normalize_approvals(
    payload: Any,
    *,
    chain: str,
    source_record_id: str = "",
) -> tuple[ApprovalActivity | None, tuple[ValidationIssue, ...]]:
    """
    Map a batch of logs onto stored-ready approvals.

    Each approval takes its block hash from its own log, so a batch spanning
    heights files each grant under the block that emitted it -- which is what
    lets a reorg withdrawal cascade them away.

    Returns ``(None, issues)`` only when the batch itself is unusable. An
    individual approval that cannot be read, or one with no block linkage, is
    counted or refused without costing the rest of the batch.
    """
    if not isinstance(payload, list):
        return None, (
            ValidationIssue(
                field="logs",
                message=f"expected a list, got {type(payload).__name__}",
            ),
        )

    records: list[StoredApproval] = []
    issues: list[ValidationIssue] = []
    undecoded = 0

    # One pass over the payload: decode each log and pair the successful ones
    # with the block hash carried alongside them. The earlier ``by_index`` build
    # scanned every log in the batch (transfers included) and then keyed the
    # lookup on ``(tx_hash, log_index or 0)`` -- collapsing missing indices to
    # zero and silently mis-binding block hashes when two logs shared the key.
    # Pairing at the point of decode removes both costs and both collisions.
    for log in payload:
        outcome = decode_approval(log, chain=chain)
        if isinstance(outcome, ApprovalRefusal):
            # ``recognised`` is the decoder's distinction between a malformed
            # approval and a log that is not an approval at all; only the former
            # counts against the batch.
            if outcome.recognised:
                undecoded += 1
            continue

        # An approval without a log index cannot be uniquely keyed under
        # ``chain:tx_hash:log_index``; storing two such grants from the same tx
        # would collide on the primary key and ``ON CONFLICT DO NOTHING`` would
        # silently drop the second. Refuse here so the operator sees the count.
        if outcome.log_index is None:
            issues.append(
                ValidationIssue(
                    field="log.logIndex",
                    message="absent; an approval without a log index cannot be "
                    "uniquely keyed and would collide with any sibling in the "
                    "same tx",
                )
            )
            continue

        block_hash = str(log.get("blockHash", "") or "").lower()
        if not block_hash:
            issues.append(
                ValidationIssue(
                    field=f"log[{outcome.log_index}].blockHash",
                    message="absent; an approval without block linkage would "
                    "survive a reorg that withdrew its block",
                )
            )
            continue

        records.append(StoredApproval(approval=outcome, block_hash=block_hash))

    activity = ApprovalActivity(
        chain=chain,
        approvals=tuple(records),
        undecoded=undecoded,
        source_record_id=source_record_id,
    )

    if issues:
        logger.warning(
            "%s: %d decoded approval(s) could not be filed", chain, len(issues)
        )

    return activity, tuple(issues)


__all__ = ["ApprovalActivity", "StoredApproval", "normalize_approvals"]
