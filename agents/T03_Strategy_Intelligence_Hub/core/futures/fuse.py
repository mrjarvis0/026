"""Signal fusion engine — SCALPER.md component #5.

Combines:
    1. Scanner consensus   (how many of the 8 strategies agree → strength & direction)
    2. MTF alignment       (+1 all TFs up, -1 all down, 0 chop → if chop, STAND ASIDE)
    3. Next-candle P(up)   (calibrated model → extra edge)
    4. Sentiment (optional) (Fear & Greed / news, small weight — experimental)

Output: FusedSignal with a final (direction, confidence) and explicit "stand aside" flag.

Fusion logic from SCALPER.md:
    direction, confidence = fuse(
        scanner_consensus,   # from core.scan
        mtf_alignment,       # from core.futures.mtf
        p_up,                # from core.futures.predict
        sentiment (optional),
    )
    # trade only when:
    #   TFs aligned (not chop)  AND
    #   |p_up − 0.5| > edge_threshold  AND
    #   confidence high enough

Constitution §0 — fusion never averages confidence.  The weakest input's
confidence becomes the floor.  Conflicting signals are preserved (not silenced).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ScannerConsensus:
    """Output of core.scan.consensus()."""
    long: int
    short: int
    flat: int
    err: int
    net: int
    bias: str       # 'LONG' | 'SHORT' | 'NEUTRAL'
    total: int

    @classmethod
    def from_dict(cls, d: dict) -> "ScannerConsensus":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})

    @property
    def direction(self) -> int:
        return 1 if self.bias == "LONG" else (-1 if self.bias == "SHORT" else 0)

    @property
    def strength(self) -> float:
        """Fraction of active agents agreeing (0.0–1.0); erring agents ignored."""
        active = self.long + self.short + self.flat
        agree = max(self.long, self.short)
        return round(agree / active, 3) if active > 0 else 0.0


@dataclass
class FusedSignal:
    """The final fused signal the scalper acts on."""

    direction: int              # +1 long, -1 short, 0 flat/stand-aside
    confidence: float           # 0.0–1.0; minimum of all contributing inputs
    stand_aside: bool           # True = do NOT trade (chop, weak edge, conflict)
    reason: str                 # human-readable reason for the decision

    # Contributing inputs (preserved for provenance — §4 conflict rule)
    scanner_direction: int = 0
    scanner_strength: float = 0.0
    mtf_alignment: int = 0
    mtf_confidence: float = 0.0
    p_up: float = 0.5
    p_up_edge: float = 0.0
    sentiment_score: float = 0.0    # -1..+1; 0 = not provided
    raw: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        if self.stand_aside:
            return f"STAND ASIDE — {self.reason}"
        dir_str = {1: "LONG", -1: "SHORT", 0: "FLAT"}[self.direction]
        return (f"{dir_str} (conf={self.confidence:.0%})  scanner={self.scanner_direction:+d}"
                f"  mtf={self.mtf_alignment:+d}  p_up={self.p_up:.3f}  — {self.reason}")


# ---------------------------------------------------------------------------
# Weights (tunable via ScalperAgent config.yaml `fuse:` section)
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS = {
    "scanner": 0.35,        # 8-strategy consensus weight
    "mtf": 0.40,            # MTF alignment weight (highest — regime is king)
    "predict": 0.20,        # next-candle probability weight
    "sentiment": 0.05,      # Fear & Greed / news (small; experimental)
}

DEFAULT_THRESHOLDS = {
    "min_confidence": 0.55,         # overall fused confidence to take a trade
    "min_scanner_strength": 0.50,   # at least 50 % of strategies must agree
    "min_p_up_edge": 0.02,          # |p_up − 0.5| >= 0.02 (i.e. >= 52 %)
    "min_oos_accuracy": 0.52,       # don't use the model below this accuracy
    "require_mtf_aligned": True,    # if True, chop (alignment=0) = stand aside
}


# ---------------------------------------------------------------------------
# Fusion
# ---------------------------------------------------------------------------

class SignalFuser:
    """Fuse scanner + MTF + predictor + sentiment into a single FusedSignal."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        thresholds: dict[str, Any] | None = None,
    ) -> None:
        self.w = {**DEFAULT_WEIGHTS, **(weights or {})}
        self.t = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        # Normalise weights so they sum to 1.0
        total_w = sum(self.w.values())
        self.w = {k: v / total_w for k, v in self.w.items()}

    def fuse(
        self,
        scanner: ScannerConsensus,
        mtf_alignment: int,
        mtf_confidence: float,
        p_up: float = 0.5,
        p_up_oos_accuracy: float = 0.0,
        sentiment_score: float = 0.0,   # -1 (fear) .. +1 (greed); 0 = not provided
    ) -> FusedSignal:
        """Produce a FusedSignal from the four inputs.

        Constitution §4 fusion rules:
        - Weakest confidence is the floor (never average it away)
        - Conflicts are recorded, not resolved
        - Result is a hypothesis; the execution gate (RiskEngine) decides sizing
        """
        reasons: list[str] = []
        conflicts: list[str] = []

        # --- GATE 1: MTF chop check (highest priority) -----------------------
        if self.t["require_mtf_aligned"] and mtf_alignment == 0:
            return FusedSignal(
                direction=0, confidence=0.0, stand_aside=True,
                reason="MTF chop: alignment=0 — stand aside",
                scanner_direction=scanner.direction,
                scanner_strength=scanner.strength,
                mtf_alignment=mtf_alignment,
                mtf_confidence=mtf_confidence,
                p_up=p_up,
                p_up_edge=abs(p_up - 0.5),
                sentiment_score=sentiment_score,
            )

        # --- GATE 2: Scanner strength ----------------------------------------
        if scanner.strength < self.t["min_scanner_strength"]:
            reasons.append(f"scanner weak ({scanner.strength:.0%} agree)")

        # --- GATE 3: Predict edge --------------------------------------------
        p_up_edge = abs(p_up - 0.5)
        use_predict = p_up_oos_accuracy >= self.t["min_oos_accuracy"]
        if use_predict and p_up_edge < self.t["min_p_up_edge"]:
            reasons.append(f"predict edge thin ({p_up_edge:.3f} < {self.t['min_p_up_edge']})")

        # --- Directional votes (weighted) ------------------------------------
        scanner_score = scanner.direction * scanner.strength * self.w["scanner"]
        mtf_score = mtf_alignment * mtf_confidence * self.w["mtf"]
        predict_vote = (1 if p_up > 0.5 else -1) if use_predict else 0
        predict_score = predict_vote * p_up_edge * self.w["predict"] if use_predict else 0.0
        sentiment_vote = 1 if sentiment_score > 0.1 else (-1 if sentiment_score < -0.1 else 0)
        sentiment_score_w = sentiment_vote * abs(sentiment_score) * self.w["sentiment"] if sentiment_vote != 0 else 0.0

        total_score = scanner_score + mtf_score + predict_score + sentiment_score_w

        # --- Conflict detection ----------------------------------------------
        directions = {
            "scanner": scanner.direction,
            "mtf": mtf_alignment,
        }
        if use_predict:
            directions["predict"] = predict_vote
        if sentiment_vote != 0:
            directions["sentiment"] = sentiment_vote

        active = {k: v for k, v in directions.items() if v != 0}
        if len(set(active.values())) > 1:
            conflict_str = ", ".join(f"{k}={v:+d}" for k, v in active.items())
            conflicts.append(f"CONFLICT [{conflict_str}]")

        # --- Final direction from weighted score ----------------------------
        final_direction = 1 if total_score > 0.02 else (-1 if total_score < -0.02 else 0)

        # --- Confidence: minimum of contributing inputs (§4 — never average) --
        confidences: list[float] = [mtf_confidence]
        if scanner.total > 0:
            confidences.append(scanner.strength)
        if use_predict:
            confidences.append(min(p_up_edge * 4, 1.0))    # scale edge 0-0.5 → 0-1
        min_conf = min(confidences)

        # --- Final gate: overall confidence threshold ------------------------
        stand_aside = False
        if reasons:
            stand_aside = True
        elif final_direction == 0:
            stand_aside = True
            reasons.append("conflicting/flat weighted score")
        elif min_conf < self.t["min_confidence"]:
            stand_aside = True
            reasons.append(f"overall confidence {min_conf:.0%} < threshold {self.t['min_confidence']:.0%}")

        reason_str = "; ".join(reasons + conflicts) or "all gates clear"

        return FusedSignal(
            direction=0 if stand_aside else final_direction,
            confidence=round(min_conf, 3),
            stand_aside=stand_aside,
            reason=reason_str,
            scanner_direction=scanner.direction,
            scanner_strength=scanner.strength,
            mtf_alignment=mtf_alignment,
            mtf_confidence=mtf_confidence,
            p_up=p_up,
            p_up_edge=round(p_up_edge, 4),
            sentiment_score=sentiment_score,
            raw={
                "total_score": round(total_score, 4),
                "scanner_score": round(scanner_score, 4),
                "mtf_score": round(mtf_score, 4),
                "predict_score": round(predict_score, 4),
                "conflicts": conflicts,
            },
        )
