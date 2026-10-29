"""The event envelope: schemas, validation, canonical form (design spec section 6).

An event is a plain JSON-able dict. ``validate_event`` is the single gate every event passes
before it is stored: evidence standard (confidence <= ceiling, evidence for any claim), maturity
labels, UTC timestamps, producer authorization, and a size cap. Events carry facts, never
commands. Imports nothing above this layer (stdlib + yaml only).
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import yaml

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "config" / "events"
MATURITY_ORDER = {"implemented": 0, "validated": 1}
MAX_ENVELOPE_BYTES = 65536

_TYPE_RE = re.compile(r"^[a-z0-9]+(\.[a-z0-9_]+){2,3}$")
_REQUIRED_TOP = ("event_id", "type", "schema_version", "source", "subject", "observed_at",
                 "trace_id", "coverage", "evidence", "untrusted", "data")
_INSTRUCTION_KEYS = {"action", "command", "tool"}   # an untrusted payload must not look like orders


class EnvelopeError(ValueError):
    pass


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


_KINDS = {
    "str": lambda v: isinstance(v, str),
    "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": _is_number,
    "bool": lambda v: isinstance(v, bool),
    "list": lambda v: isinstance(v, list),
    "dict": lambda v: isinstance(v, dict),
    "any": lambda v: True,
}


def load_schemas(directory: Path | None = None) -> dict[str, dict]:
    """type -> {schema_version, platform, required, optional} from ``config/events/*.yaml``."""
    schemas: dict[str, dict] = {}
    for path in sorted((directory or SCHEMA_DIR).glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        data = raw.get("data") or {}
        schemas[raw["type"]] = {
            "schema_version": int(raw["schema_version"]),
            "platform": bool(raw.get("platform", False)),
            "required": dict(data.get("required") or {}),
            "optional": dict(data.get("optional") or {}),
        }
    return schemas


def canonical_json(event: dict) -> str:
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def type_matches(pattern: str, type_: str) -> bool:
    return type_.startswith(pattern[:-1]) if pattern.endswith(".*") else pattern == type_


def passes_maturity(event: dict, minimum: str) -> bool:
    """Plain facts (no detector) always pass; detector events need at least ``minimum``."""
    detector = event.get("detector")
    if not detector:
        return True
    return MATURITY_ORDER[detector["maturity"]] >= MATURITY_ORDER[minimum]


def make_event_id(*parts: str) -> str:
    return "evt_" + hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _aware(value, name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise EnvelopeError(f"{name}: not an ISO-8601 timestamp") from None
    if parsed.tzinfo is None:
        raise EnvelopeError(f"{name}: timestamp must be timezone-aware (UTC)")
    return parsed


def _produces(manifest: dict) -> set[str]:
    return {p["type"] if isinstance(p, dict) else str(p) for p in (manifest.get("produces") or [])}


def validate_event(event: dict, schemas: dict[str, dict], manifests: dict[str, dict]) -> None:
    missing = [k for k in _REQUIRED_TOP if k not in event]
    if missing:
        raise EnvelopeError("missing field(s): " + ", ".join(missing))
    if len(canonical_json(event).encode("utf-8")) > MAX_ENVELOPE_BYTES:
        raise EnvelopeError(f"envelope too large (> {MAX_ENVELOPE_BYTES} bytes)")

    type_ = event["type"]
    schema = schemas.get(type_)
    if not _TYPE_RE.match(str(type_)) or schema is None:
        raise EnvelopeError(f"unregistered type {type_!r}")
    if event["schema_version"] != schema["schema_version"]:
        raise EnvelopeError(f"{type_}: schema_version {event['schema_version']} != {schema['schema_version']}")

    source = event["source"]
    if schema["platform"]:
        if source != "SYS":
            raise EnvelopeError(f"{type_} is a platform type: only source 'SYS' may publish it")
    elif type_ not in _produces(manifests.get(source) or {}):
        raise EnvelopeError(f"source {source!r} does not declare that it produces {type_!r}")

    _aware(event["observed_at"], "observed_at")
    for name in ("event_time", "known_at"):
        if event.get(name) is not None:
            _aware(event[name], name)
    window = event.get("event_window")
    if window is not None:
        if _aware(window["from"], "event_window.from") > _aware(window["to"], "event_window.to"):
            raise EnvelopeError("event_window: 'from' is after 'to'")

    detector, confidence = event.get("detector"), event.get("confidence")
    if detector is not None:
        if detector.get("maturity") not in MATURITY_ORDER:
            raise EnvelopeError(f"detector.maturity must be one of {sorted(MATURITY_ORDER)}")
    if confidence is not None:
        if not _is_number(confidence) or not 0 <= confidence <= 1:
            raise EnvelopeError("confidence must be a number in [0, 1] or null")
        ceiling = (detector or {}).get("ceiling")
        if ceiling is not None and confidence > ceiling:
            raise EnvelopeError(f"confidence {confidence} exceeds the detector ceiling {ceiling}")

    evidence = event["evidence"]
    if not isinstance(evidence, list):
        raise EnvelopeError("evidence must be a list")
    if (detector is not None or confidence is not None) and not evidence:
        raise EnvelopeError("a claim needs evidence: evidence is empty")
    for item in evidence:
        _aware(item.get("retrieved_at"), "evidence.retrieved_at")

    data = event["data"]
    if not isinstance(data, dict):
        raise EnvelopeError("data must be an object")
    for name, kind in schema["required"].items():
        if name not in data:
            raise EnvelopeError(f"data missing required field {name!r}")
        if kind != "any" and (data[name] is None or not _KINDS[kind](data[name])):
            raise EnvelopeError(f"data.{name} must be {kind}")
    for name, kind in schema["optional"].items():
        if data.get(name) is not None and not _KINDS[kind](data[name]):
            raise EnvelopeError(f"data.{name} must be {kind}")
    if event["untrusted"] and _INSTRUCTION_KEYS & {k.lower() for k in data}:
        raise EnvelopeError("untrusted data must not carry an instruction-like key")
