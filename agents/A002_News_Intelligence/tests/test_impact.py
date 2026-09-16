"""
CIE-OS
A002 News Intelligence Agent

Phase 4 tests — market impact, history correlation, prediction (offline).
Run directly:
    python agents/A002_News_Intelligence/tests/test_impact.py
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from agents.A002_News_Intelligence.core.models import Entity, NormalizedItem
from agents.A002_News_Intelligence.intelligence.history import (
    classify_category,
    expected_impact,
    find_similar_events,
    fomo_bucket,
)
from agents.A002_News_Intelligence.intelligence.impact import (
    _price_at,
    compute_measured_impact,
    price_after,
    price_before,
    returns_at_horizons,
    severity_label,
)
from agents.A002_News_Intelligence.intelligence.narrative import Narrative
from agents.A002_News_Intelligence.intelligence.predict import (
    predict_asset,
    _assess_risk_factors,
    _detect_regime,
)

PASS = 0
FAIL = 0


def check(label: str, ok: bool) -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [OK] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}")


def make_candles(base: float = 100.0, hours: int = 120, step: float = 0.0, start: datetime | None = None) -> list[dict]:
    """Synthetic hourly candles ending at `start` (default: now)."""

    end = start or datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    candles = []
    for i in range(hours):
        close = base + step * i
        candles.append(
            {
                "open_time": (end - timedelta(hours=hours - i)).isoformat(),
                "open": close - step,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": 1000.0,
            }
        )
    return candles


def crash_series(t0: datetime, hours: int = 48, start_close: float | None = None, drop_per_hour: float = 0.2) -> list[dict]:
    """Candles after t0 with declining closes and high volume.
    
    If start_close is None, uses 95.0 as default.
    """
    if start_close is None:
        start_close = 95.0
    
    return [
        {"open_time": (t0 + timedelta(hours=i)).isoformat(),
         "open": start_close + drop_per_hour * (i - 1),
         "high": start_close + 1,
         "low": start_close - 1,
         "close": start_close - i * drop_per_hour,
         "volume": 5000.0}
        for i in range(hours)
    ]


def narrative_with(claim: str, first_seen: datetime, fomo: float = 40.0, confidence: float = 0.6,
                   status: str = "unconfirmed", coord: float = 0.0) -> Narrative:
    item = NormalizedItem(source="rss_a", source_key="k", title=claim, content="", published_at=first_seen)
    item.entities = [Entity(type="crypto", symbol="BTC", name="Bitcoin", context=None)]
    n = Narrative(claim_text=claim, items=[item], first_seen=first_seen, last_seen=first_seen)
    n.fomo_score = fomo
    n.confidence = confidence
    n.epistemic_status = status
    n.coordination_score = coord
    return n


def test_categories() -> None:
    print("categories:")
    check("regulatory", classify_category("SEC files lawsuit against exchange") == "regulatory")
    check("hack", classify_category("Exchange hacked, funds drained") == "hack")
    check("delisting", classify_category("XYZ token faces delisting from exchange") == "delisting")
    check("etf", classify_category("SEC approves spot Bitcoin ETF") == "etf")
    check("earnings", classify_category("Apple Q2 revenue beats estimates") == "earnings")
    check("macro", classify_category("Fed cuts interest rates") == "macro")
    check("fraud", classify_category("Pump and dump scheme uncovered") == "fraud")
    check("general", classify_category("Coinbase launches new feature") == "general")
    check("fomo bucket", fomo_bucket(0) == 0 and fomo_bucket(95) == 4)
    print()


def test_impact_measurement() -> None:
    print("impact measurement:")
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    t0 = now - timedelta(hours=30)
    # flat 100 until t0, then crash: 100 -> 95 -> declining
    base = make_candles(100.0, 30, start=t0)
    crash = crash_series(t0)
    series = base + crash
    measured = compute_measured_impact(series, t0)
    ret_1h = measured["returns"].get(1)
    check("crash returns negative", ret_1h is not None and ret_1h < -0.1)
    check("returns keyed by horizons", set(measured["returns"]) == {1, 6, 24})
    check("volume surge detected", measured["volume_surge"] is not None and measured["volume_surge"] > 1.0)
    check("severity not unknown", measured["severity"] in ("mild", "moderate", "severe"))

    base_price = price_before(series, t0, 1)
    after = price_after(series, t0, 6)
    check("price before", abs(base_price - 100) < 1e-9)
    check("price after lower", after is not None and after < base_price)

    # mild case: no move
    flat = make_candles(50.0, 100)
    mild = compute_measured_impact(flat, now - timedelta(hours=50))
    check("flat severity mild/unknown", mild["severity"] in ("mild", "unknown"))
    check("flat return near zero", abs(mild["returns"].get(1) or 0) < 0.5)
    print()


def test_history() -> None:
    print("history:")
    events = [
        {"asset": "BTC", "category": "regulatory", "fomo_score": 70, "measured_return": -4.2,
         "epistemic_status": "confirmed_true"},
        {"asset": "BTC", "category": "regulatory", "fomo_score": 65, "measured_return": -7.1,
         "epistemic_status": "likely_true"},
        {"asset": "BTC", "category": "regulatory", "fomo_score": 80, "measured_return": -3.8,
         "epistemic_status": "confirmed_true"},
        {"asset": "ETH", "category": "hack", "fomo_score": 90, "measured_return": -12.0,
         "epistemic_status": "confirmed_true"},
        {"asset": "BTC", "category": "partnership", "fomo_score": 40, "measured_return": 3.1,
         "epistemic_status": "unconfirmed"},
    ]
    similar = find_similar_events(events, "regulatory", 75, "BTC", k=3)
    check("top matches regulatory", all(e["category"] == "regulatory" for e, _ in similar))
    check("same asset preferred", all(e["asset"] == "BTC" for e, _ in similar))
    check("top3 returned", len(similar) == 3)

    analog = expected_impact(similar, "BTC")
    check("analog present", analog is not None)
    check("mean negative (regulatory == down)", analog["mean"] < 0)
    check("range brackets mean", analog["low"] <= analog["mean"] <= analog["high"])
    check("confidence in range", 0 < analog["confidence"] <= 0.85)

    none_analog = expected_impact([])
    check("no history -> None", none_analog is None)
    print()


def test_price_at() -> None:
    print("price at:")
    t1 = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
    t2 = datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC)
    t3 = datetime(2023, 1, 1, 14, 0, 0, tzinfo=UTC)

    candles = [
        {"open_time": t1.isoformat(), "close": 100.0},
        {"open_time": t2.isoformat(), "close": 110.0},
        {"open_time": t3.isoformat(), "close": 120.0},
    ]

    # exact match
    check("exact match t2", _price_at(candles, t2) == 110.0)

    # between t1 and t2 -> should return t1's close
    t_between = datetime(2023, 1, 1, 12, 30, 0, tzinfo=UTC)
    check("between match", _price_at(candles, t_between) == 100.0)

    # after all candles -> should return t3's close
    t_after = datetime(2023, 1, 1, 15, 0, 0, tzinfo=UTC)
    check("after match", _price_at(candles, t_after) == 120.0)

    # before all candles -> should return None
    t_before = datetime(2023, 1, 1, 11, 0, 0, tzinfo=UTC)
    check("before match", _price_at(candles, t_before) is None)

    # empty candles
    check("empty match", _price_at([], t1) is None)
    print()


def test_detect_regime() -> None:
    print("detect regime:")
    check("None -> normal", _detect_regime(None, 0, {}) == "normal")
    check("> 5.0 -> crisis", _detect_regime(5.1, 0, {}) == "crisis")
    check("> 2.0 -> high_vol", _detect_regime(2.1, 0, {}) == "high_vol")
    check("< 0.5 -> low_vol", _detect_regime(0.4, 0, {}) == "low_vol")
    check("between 0.5 and 2.0 -> normal", _detect_regime(1.0, 0, {}) == "normal")
    print()


def test_predict_asset_enhanced() -> None:
    print("predict_asset enhanced metrics:")
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    t0 = now - timedelta(hours=30)

    # create high volatility candles to trigger regime changes and jumps
    # base candles end exactly at t0. make_candles(start=t0) actually ends at t0.
    # The previous code made base end at t0, so volatile crash should start at t0
    base = make_candles(100.0, 100, start=t0)

    # create a very sudden, massive drop to trigger tail risk and jumps
    # starting from t0 moving forward
    volatile_crash = [
        {"open_time": (t0 + timedelta(hours=1)).isoformat(), "open": 100.0, "high": 100.0, "low": 90.0, "close": 90.0, "volume": 10000.0},
        {"open_time": (t0 + timedelta(hours=2)).isoformat(), "open": 90.0, "high": 90.0, "low": 80.0, "close": 82.0, "volume": 15000.0},
        {"open_time": (t0 + timedelta(hours=3)).isoformat(), "open": 82.0, "high": 85.0, "low": 75.0, "close": 78.0, "volume": 12000.0},
    ]
    candles = base + volatile_crash

    narrative = narrative_with("Massive hack drains exchange", t0, fomo=90, confidence=0.8, status="confirmed_true")
    history = [
        {"asset": "BTC", "category": "hack", "fomo_score": 85, "measured_return": -15.0, "epistemic_status": "confirmed_true"}
    ]

    pred = predict_asset("BTC", narrative, candles, history)

    check("asset and category matched", pred.asset == "BTC" and pred.category == "hack")
    check("realized vol calculated", pred.realized_vol_pct is not None and pred.realized_vol_pct > 0)
    check("jump detected", pred.jump_count > 0 and len(pred.jumps) > 0)
    check("tail risk (var_95) populated", pred.var_95_pct is not None)
    check("regime is high_vol or crisis", pred.regime in ("high_vol", "crisis"))
    check("risk factors include jump/tail warnings", any("jump" in r.lower() or "tail" in r.lower() for r in pred.risk_factors))
    print()


def test_prediction() -> None:
    print("prediction:")
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    t0 = now - timedelta(hours=30)

    # crash narrative + regulatory history
    base = make_candles(100.0, 30, start=t0)
    last_base_price = 100.0  # base with step=0.0
    crash = crash_series(t0, start_close=last_base_price)
    history = [
        {"asset": "BTC", "category": "regulatory", "fomo_score": 75, "measured_return": -4.2,
         "epistemic_status": "confirmed_true"},
        {"asset": "BTC", "category": "regulatory", "fomo_score": 70, "measured_return": -5.5,
         "epistemic_status": "likely_true"},
    ]
    narrative = narrative_with("SEC files lawsuit against crypto exchange", t0, fomo=78, confidence=0.8, status="likely_true")
    pred = predict_asset("BTC", narrative, base + crash, history)
    check("direction down", pred.direction == "down")
    check("probability in range", 0 < pred.probability <= 1)
    check("expected range present", pred.expected_low_pct is not None and pred.expected_high_pct is not None)
    check("category regulatory", pred.category == "regulatory")
    check("history used", pred.historical_events_used == 2)
    check("measured returns recorded", pred.measured_returns_pct.get(1) is not None)
    check("main risk set", pred.main_risk in ("historical sample is small", "rumor may be false"))

    # false narrative -> reversal risk
    false_narrative = narrative_with("Binance denies hack rumors", t0, status="confirmed_false", confidence=0.9)
    pred2 = predict_asset("BTC", false_narrative, base + crash, [])
    check("false narrative reversal risk", "false" in pred2.main_risk)

    # no candles, no history -> unknown direction
    pred3 = predict_asset("BTC", narrative_with("Something vague", t0), None, [])
    check("no data unknown", pred3.direction == "unknown" and pred3.probability > 0)
    print()


def test_assess_risk_factors() -> None:
    print("assess risk factors:")
    now = datetime.now(UTC)

    # Base mock narrative
    n = narrative_with("Some claim", now, status="confirmed_true", confidence=0.8, coord=10.0)

    # 1. Base case: perfect conditions
    risks = _assess_risk_factors(n, {}, {"used": 5, "similarity": 0.8}, {}, {})
    check("standard risk only", risks == ["standard market risk"])

    # 2. Narrative risks
    n.epistemic_status = "confirmed_false"
    check("narrative false risk", "narrative likely false — impact may reverse" in _assess_risk_factors(n, {}, {"used": 5, "similarity": 0.8}, {}, {}))
    n.epistemic_status = "disputed"
    check("narrative disputed risk", "conflicting sources — high uncertainty" in _assess_risk_factors(n, {}, {"used": 5, "similarity": 0.8}, {}, {}))
    n.epistemic_status = "unconfirmed"
    check("narrative unconfirmed risk", "unverified claim — treat with caution" in _assess_risk_factors(n, {}, {"used": 5, "similarity": 0.8}, {}, {}))
    n.epistemic_status = "confirmed_true" # reset

    # 3. Market risks
    check("multiple jumps risk", "multiple price jumps detected — unstable" in _assess_risk_factors(n, {"jump_count": 3}, {"used": 5, "similarity": 0.8}, {}, {}))
    check("high tail risk", "high tail risk (VaR95 < -3%)" in _assess_risk_factors(n, {"var_95_pct": -4.0}, {"used": 5, "similarity": 0.8}, {}, {}))
    check("max drawdown risk", "recent max drawdown 15.0%" in _assess_risk_factors(n, {}, {"used": 5, "similarity": 0.8}, {"max_drawdown_pct": 15.0}, {}))
    check("recent jumps risk", "1 price jump(s) in recent history" in _assess_risk_factors(n, {}, {"used": 5, "similarity": 0.8}, {}, {"jump_count": 1}))

    # 4. Historical risks
    check("no analog risk", "no historical analog — pure speculation" in _assess_risk_factors(n, {}, None, {}, {}))
    check("small sample risk", "historical sample is small" in _assess_risk_factors(n, {}, {"used": 2, "similarity": 0.8}, {}, {}))
    check("poor analog risk", "low historical similarity — analog quality poor" in _assess_risk_factors(n, {}, {"used": 5, "similarity": 0.3}, {}, {}))

    # 5. Verification / Coordination risks
    n.confidence = 0.2
    check("low confidence risk", "low verification confidence" in _assess_risk_factors(n, {}, {"used": 5, "similarity": 0.8}, {}, {}))
    n.confidence = 0.8 # reset

    n.coordination_score = 70.0
    check("manipulation risk", "coordinated amplification detected — manipulation risk" in _assess_risk_factors(n, {}, {"used": 5, "similarity": 0.8}, {}, {}))

    print()


if __name__ == "__main__":
    test_categories()
    test_impact_measurement()
    test_history()
    test_detect_regime()
    test_predict_asset_enhanced()
    test_prediction()
    test_price_at()
    test_assess_risk_factors()
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)
