"""Scalper risk wiring — each test names the defect it guards (found in the 2026-10-28 orchestration audit).

Defects: RiskEngine was rebuilt empty every step and handed a dict where it expects a float equity, so no
breaker (drawdown, daily loss, trades/day) could ever trip; and position_size got the ATR in PRICE units
where it expects a FRACTION, making every size ~price-times too small.

Run: python -m pytest agents/T03_Strategy_Intelligence_Hub/tests/test_scalper_risk.py -q
"""
import sys
from datetime import date
from pathlib import Path

import pytest

T03_ROOT = Path(__file__).resolve().parent.parent
if str(T03_ROOT) not in sys.path:
    sys.path.insert(0, str(T03_ROOT))

from core.futures.scalper import risk_gate, size_units
from core.live.risk import RiskEngine, RiskLimits

TODAY = date.today().isoformat()
LIMITS = RiskLimits(max_drawdown_pct=0.25, daily_loss_limit_pct=0.05, max_trades_per_day=50)


def test_drawdown_breaker_trips_across_steps_and_stays_tripped():
    state: dict = {}
    assert risk_gate(LIMITS, state, 10_000.0)[1] is True          # first step sets the peak
    _, ok, why = risk_gate(LIMITS, state, 7_000.0)                # -30% from peak
    assert ok is False and "max-drawdown" in why
    _, ok, why = risk_gate(LIMITS, state, 10_000.0)               # back at the peak: the halt is sticky
    assert ok is False and "halted" in why.lower()


def test_daily_loss_limit_blocks_within_the_day():
    state = {"daily_date": TODAY, "day_start_equity": 10_000.0, "equity_peak": 10_000.0}
    _, ok, why = risk_gate(LIMITS, state, 9_400.0)                # -6% on the day
    assert ok is False and "daily-loss" in why


def test_a_new_day_starts_a_fresh_daily_baseline():
    state = {"daily_date": "2000-01-01", "day_start_equity": 10_000.0, "equity_peak": 10_000.0, "trades_today": 40}
    _, ok, _ = risk_gate(LIMITS, state, 9_400.0)                  # yesterday's baseline no longer applies
    assert ok is True and state["day_start_equity"] == 9_400.0 and state["trades_today"] == 0


def test_trades_per_day_cap_is_enforced():
    state = {"daily_date": TODAY, "day_start_equity": 10_000.0, "equity_peak": 10_000.0, "trades_today": 50}
    _, ok, why = risk_gate(LIMITS, state, 10_000.0)
    assert ok is False and "max_trades_per_day" in why


def test_risk_state_is_written_back_for_the_next_step():
    state: dict = {}
    risk_gate(LIMITS, state, 12_000.0)
    assert state["equity_peak"] == 12_000.0 and state["daily_date"] == TODAY
    assert state["day_start_equity"] == 12_000.0 and state["risk_halted"] is False


def test_atr_is_converted_to_a_fraction_before_sizing():
    # 1% of 10k = 100 at risk; ATR 600 on a 60k price = 1% stop -> 100/600 = 0.1667 units.
    # (Passing 600 as if it were a fraction gave ~2.8e-6 units.)
    units = size_units(RiskEngine(LIMITS), equity=10_000.0, price=60_000.0, atr=600.0)
    assert units == pytest.approx(100 / 600, rel=1e-6)


def test_size_is_capped_by_leverage_and_safe_on_bad_input():
    assert size_units(RiskEngine(LIMITS), 10_000.0, 60_000.0, 1.0) == pytest.approx(10_000.0 * 3 / 60_000.0)
    assert size_units(RiskEngine(LIMITS), 10_000.0, 0.0, 600.0) == 0.0
    assert size_units(RiskEngine(LIMITS), 10_000.0, 60_000.0, 0.0) > 0.0   # no ATR -> falls back to a 1% stop


# ---- independent review (2026-10-29) ---------------------------------------------------------------------

def test_simulated_equity_never_trips_or_persists_breakers():
    # review #3: _account() falls back to a fake 10,000 when the broker read fails; persisting that as the
    # peak (or as a drawdown from a real 50,000) wrote a sticky halt from numbers that were never real
    state: dict = {}
    _, ok, why = risk_gate(LIMITS, state, 10_000.0, mode="simulated(no keys)")
    assert ok is True and state == {} and "simulated" in why


def test_a_failed_broker_read_cannot_halt_a_real_account():
    state = {"equity_peak": 50_000.0, "daily_date": TODAY, "day_start_equity": 50_000.0}
    risk_gate(LIMITS, state, 10_000.0, mode="simulated(no keys)")      # the 10k fallback after an API error
    assert state["equity_peak"] == 50_000.0 and not state.get("risk_halted")
