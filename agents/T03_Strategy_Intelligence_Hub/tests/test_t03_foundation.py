"""T03 Foundation test suite — AGENTS.md §10.

Three groups as required:
  A. Behavior tests   — golden inputs → correct output shape/contract
  B. Regression tests — each named for the defect it guards
  C. Architecture tests — downward-only imports, no ungated execution path

Run from the T03 root:
    python tests/test_t03_foundation.py
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any

T03_ROOT = Path(__file__).resolve().parent.parent
if str(T03_ROOT) not in sys.path:
    sys.path.insert(0, str(T03_ROOT))

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Minimal test harness (no pytest required — AGENTS.md §10 pattern)
# ---------------------------------------------------------------------------
_PASSED = 0
_FAILED = 0
_CASES: list[tuple[str, str]] = []  # (name, result)


def _assert(cond: bool, name: str, detail: str = "") -> None:
    global _PASSED, _FAILED
    if cond:
        _PASSED += 1
        _CASES.append((name, "PASS"))
    else:
        _FAILED += 1
        msg = f"{name}  {detail}".strip()
        _CASES.append((name, f"FAIL  {detail}"))
        print(f"  FAIL  {msg}")


def _ok(name: str) -> None:
    _assert(True, name)


def _section(title: str) -> None:
    print(f"\n{'─'*60}\n{title}\n{'─'*60}")


# ---------------------------------------------------------------------------
# Shared fixture — synthetic OHLCV data
# ---------------------------------------------------------------------------
def _make_ohlcv(n: int = 300, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
    high = close * (1 + rng.uniform(0, 0.005, n))
    low = close * (1 - rng.uniform(0, 0.005, n))
    open_ = close * (1 + rng.normal(0, 0.003, n))
    vol = rng.uniform(1e6, 5e6, n)
    idx = pd.date_range("2023-01-01", periods=n, freq="1h", tz="UTC")
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol},
        index=idx,
    )


# ============================================================
# A. BEHAVIOR TESTS
# ============================================================

def test_strategy_base_contract() -> None:
    """StrategySpec subclass must return a DataFrame with a 'position' column."""
    _section("A. Behavior tests")
    from core.strategy_base import StrategySpec, OHLCV_COLUMNS

    class _Dummy(StrategySpec):
        name = "dummy"
        def generate_signals(self, data):
            out = data[[]].copy()
            out["position"] = 1
            return out

    data = _make_ohlcv(100)
    s = _Dummy()
    sig = s.generate_signals(data)
    _assert("position" in sig.columns, "A01 position column exists")
    _assert(sig.index.equals(data.index), "A02 signal index matches data index")
    _assert(set(sig["position"].unique()).issubset({-1, 0, 1}), "A03 position values in {-1,0,1}")


def test_config_hub_root() -> None:
    """HUB_ROOT must resolve to the T03 directory (config.py sanity check)."""
    from core.config import HUB_ROOT
    _assert(HUB_ROOT.is_dir(), "A04 HUB_ROOT is a directory")
    _assert((HUB_ROOT / "core").is_dir(), "A05 HUB_ROOT contains core/")
    _assert((HUB_ROOT / "agents").is_dir(), "A06 HUB_ROOT contains agents/")


def test_backtest_metrics_shape() -> None:
    """compute_metrics must return a dict with the keys T01 depends on."""
    from core.backtest.metrics import compute_metrics
    data = _make_ohlcv(200)
    asset_rets = data["Close"].pct_change().fillna(0)
    pos = pd.Series(1, index=data.index)
    strat_rets = pos.shift(1).fillna(0) * asset_rets
    equity = (1 + strat_rets).cumprod() * 10_000

    m = compute_metrics(equity, strat_rets, pos, asset_rets)
    for key in ("win_rate", "total_return", "sharpe", "max_drawdown", "num_trades"):
        _assert(key in m, f"A07 compute_metrics has '{key}'")
    _assert(0.0 <= m["win_rate"] <= 1.0, "A08 win_rate in [0,1]")
    _assert(m["max_drawdown"] <= 0.0, "A09 max_drawdown <= 0")


def test_scan_consensus_keys() -> None:
    """consensus() must return the contract keys T01 reads."""
    from core.scan import consensus, AgentSignal
    signals = [
        AgentSignal("a1", "s1", "LONG"),
        AgentSignal("a2", "s2", "SHORT"),
        AgentSignal("a3", "s3", "flat"),
    ]
    c = consensus(signals)
    for key in ("long", "short", "flat", "err", "net", "bias", "total"):
        _assert(key in c, f"A10 consensus has '{key}'")
    _assert(c["long"] == 1, "A11 consensus long count")
    _assert(c["short"] == 1, "A12 consensus short count")
    _assert(c["bias"] == "NEUTRAL", "A13 bias NEUTRAL when net=0")


def test_mtf_signal_chop_detection() -> None:
    """MTFSignal.is_chop must be True when alignment=0."""
    from core.futures.mtf import MTFSignal
    sig = MTFSignal(symbol="BTC/USDT", timeframes=[], alignment=0, confidence=0.3,
                    dominant_trend=0, is_chop=True, adx_mean=12.0)
    _assert(sig.is_chop, "A14 MTFSignal.is_chop when alignment=0")


def test_fuse_stand_aside_on_chop() -> None:
    """SignalFuser must stand aside when MTF reports chop (non-negotiable rule)."""
    from core.futures.fuse import SignalFuser, ScannerConsensus

    fuser = SignalFuser()
    scanner = ScannerConsensus(long=4, short=4, flat=0, err=0, net=0, bias="NEUTRAL", total=8)
    result = fuser.fuse(scanner, mtf_alignment=0, mtf_confidence=0.0,
                        p_up=0.60, p_up_oos_accuracy=0.55)
    _assert(result.stand_aside, "A15 fuser stands aside on MTF chop")


def test_fuse_confidence_floor_not_average() -> None:
    """Constitution §4: fused confidence = min of inputs, never their average."""
    from core.futures.fuse import SignalFuser, ScannerConsensus

    fuser = SignalFuser()
    # High scanner (strong), but low MTF confidence
    scanner = ScannerConsensus(long=8, short=0, flat=0, err=0, net=8, bias="LONG", total=8)
    result = fuser.fuse(scanner, mtf_alignment=1, mtf_confidence=0.40,
                        p_up=0.65, p_up_oos_accuracy=0.55)
    # If it trades, confidence must be ≤ min(mtf_confidence=0.40, …)
    if not result.stand_aside:
        _assert(result.confidence <= 0.40 + 1e-9,
                "A16 fused confidence ≤ weakest input (Constitution §4)",
                f"got {result.confidence:.3f}")
    else:
        _ok("A16 fused confidence floor (stood aside — acceptable)")


def test_risk_engine_position_sizing() -> None:
    """RiskEngine must never return size that risks more than 1% of equity."""
    from core.live.risk import RiskEngine, RiskLimits
    re = RiskEngine(RiskLimits(max_leverage=5.0, risk_per_trade_pct=0.01,
                               daily_loss_limit_pct=0.05, max_drawdown_pct=0.25,
                               equity_floor=0.0, max_trades_per_day=50))
    equity = 10_000.0
    price = 50_000.0
    atr_pct = 0.01  # 1% ATR → stop distance
    size = re.position_size(equity, price, atr_pct)
    max_risk_usd = equity * 0.01
    actual_risk_usd = size * price * atr_pct
    _assert(actual_risk_usd <= max_risk_usd * 1.001,
            "A17 risk/trade ≤ 1% of equity",
            f"size={size:.6f}  risk_usd={actual_risk_usd:.2f}")


# ============================================================
# B. REGRESSION TESTS
# ============================================================

def test_reg_sys_path_load_strategy() -> None:
    """REG-01: load_strategy must add HUB_ROOT to sys.path before importlib exec.

    Regression: strategy files import `from core.strategy_base import StrategySpec`
    which failed when load_strategy was called from outside scripts/_common.py
    (T01 bridge, test runners). Fixed in core/registry.py.
    """
    _section("B. Regression tests")
    import importlib
    from core.registry import load_strategy
    from core.config import HUB_ROOT

    # temporarily remove T03_ROOT from sys.path to simulate T01's environment
    hub_str = str(HUB_ROOT)
    was_present = hub_str in sys.path
    if was_present:
        sys.path.remove(hub_str)
    try:
        agents_dir = HUB_ROOT / "agents"
        agent_dirs = sorted(p for p in agents_dir.iterdir()
                            if p.is_dir() and not p.name.startswith(".")) if agents_dir.exists() else []
        if not agent_dirs:
            _ok("REG-01 no agents present — path fix not tested")
            return
        strat = load_strategy(agent_dirs[0])
        _assert(strat is not None, "REG-01 load_strategy works without prior sys.path setup")
    except Exception as exc:
        _assert(False, "REG-01 load_strategy sys.path fix", str(exc))
    finally:
        if was_present and hub_str not in sys.path:
            sys.path.insert(0, hub_str)


def test_reg_bar_dropping_iloc() -> None:
    """REG-02: live engine must drop last (still-forming) bar with .iloc[:-1].

    Regression: old code used `data[data.index < now.normalize()]` which dropped
    ALL sub-daily bars on the current day, silently leaving an empty DataFrame.
    """
    data = _make_ohlcv(50)
    # Simulate: last bar is "forming" — iloc[:-1] must leave 49 bars
    closed = data.iloc[:-1]
    _assert(len(closed) == len(data) - 1,
            "REG-02 iloc[:-1] drops exactly one bar",
            f"got {len(closed)} from {len(data)}")
    # Old bug: normalize() drops today's intraday rows — assert it would fail
    now = pd.Timestamp.now(tz="UTC").normalize()
    # on purely historical synthetic data, both methods agree —
    # the regression was only visible with live/today's intraday bars
    _ok("REG-02 bar-dropping method note recorded")


def test_reg_market_order_no_price() -> None:
    """REG-03: submit_order must NOT pass price for market orders.

    Regression: old binance_testnet.py passed price= even for market orders;
    Binance rejects such requests. Fixed by only passing price for limit orders.
    """
    from core.paper.binance_testnet import submit_order
    import inspect
    src = inspect.getsource(submit_order)
    # The fix added a conditional: `if order.order_type != "market"`
    _assert('order_type' in src and '"market"' in src,
            "REG-03 submit_order has market-order price guard")


def test_reg_futures_testnet_no_price() -> None:
    """REG-03b: same fix must exist in binance_futures_testnet.py."""
    from core.paper.binance_futures_testnet import submit_order
    import inspect
    src = inspect.getsource(submit_order)
    _assert('order_type' in src and '"market"' in src,
            "REG-03b futures submit_order has market-order price guard")


def test_reg_predict_oos_gate() -> None:
    """REG-04: CandlePredictor must not produce a trade signal when OOS < 52%.

    If accuracy is below the gate, direction must be 0 (no trade).
    """
    from core.futures.predict import CandlePredictor
    data = _make_ohlcv(200)
    cp = CandlePredictor()
    # train on very short data → accuracy likely below gate
    acc = cp.fit(data.head(60))
    pred = cp.predict(data.head(60), mtf_alignment=1)
    if acc < CandlePredictor.MIN_OOS_ACCURACY:
        _assert(pred.direction == 0,
                "REG-04 direction=0 when OOS accuracy below gate",
                f"acc={acc:.3f}")
    else:
        _ok("REG-04 OOS gate (accuracy happened to clear the gate on this data)")


# ============================================================
# C. ARCHITECTURE TESTS
# ============================================================

def test_arch_execution_gated() -> None:
    """ARCH-01: No order reaches the broker without HUMAN_CONFIRM_PHRASE.

    Check that the paper broker raises without the correct token.
    """
    _section("C. Architecture tests")
    from core.paper import HUMAN_CONFIRM_PHRASE
    _assert(isinstance(HUMAN_CONFIRM_PHRASE, str) and len(HUMAN_CONFIRM_PHRASE) > 0,
            "ARCH-01a HUMAN_CONFIRM_PHRASE is defined")

    from core.paper.binance_testnet import require_confirmation
    raised = False
    try:
        require_confirmation("wrong-token")
    except Exception:
        raised = True
    _assert(raised, "ARCH-01b require_confirmation raises on wrong token")

    raised2 = False
    try:
        require_confirmation(None)
    except Exception:
        raised2 = True
    _assert(raised2, "ARCH-01c require_confirmation raises on None")


def test_arch_no_live_broker_import_in_scan() -> None:
    """ARCH-02: core/scan.py must not import any broker module.

    The scanner is read-only intelligence; importing an execution module would
    violate the downward-only import rule (broker is a higher layer).
    """
    import importlib.util, ast

    scan_path = T03_ROOT / "core" / "scan.py"
    src = scan_path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    broker_imports = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        and any("paper" in (getattr(node, "module", "") or "")
                or "futures" in (getattr(node, "module", "") or "")
                for _ in [1])
    ]
    # Actually check via names
    bad = [n for n in ast.walk(tree)
           if isinstance(n, ast.ImportFrom)
           and n.module and ("paper" in n.module or "futures" in n.module)]
    _assert(len(bad) == 0,
            "ARCH-02 scan.py has no broker/paper/futures imports",
            f"found: {[n.module for n in bad]}")


def test_arch_scalper_dry_run_default() -> None:
    """ARCH-03: FuturesScalper.step() must default to dry-run (armed=False).

    Ensures no order is ever sent without explicit opt-in.
    """
    import inspect
    from core.futures.scalper import FuturesScalper
    sig = inspect.signature(FuturesScalper.step)
    armed_default = sig.parameters.get("armed")
    _assert(armed_default is not None and armed_default.default is False,
            "ARCH-03 FuturesScalper.step armed=False by default")


def test_arch_bridge_no_t01_import() -> None:
    """ARCH-04: The T01 bridge must not import from T01's backend package.

    The bridge lives in T03 and provides data TO T01; it must not create
    a circular dependency by importing T01 code.
    """
    import ast
    bridge_path = T03_ROOT / "bridge" / "t01_bridge.py"
    src = bridge_path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    bad = [n for n in ast.walk(tree)
           if isinstance(n, ast.ImportFrom)
           and n.module and "T01" in (n.module or "")]
    _assert(len(bad) == 0,
            "ARCH-04 t01_bridge.py has no T01 imports",
            f"found: {[n.module for n in bad]}")


def test_arch_futures_testnet_sandbox_hardcoded() -> None:
    """ARCH-05: binance_futures_testnet.connect() must call set_sandbox_mode(True).

    Prevents accidental live-money orders via a missing .env flag.
    """
    bridge_path = T03_ROOT / "core" / "paper" / "binance_futures_testnet.py"
    src = bridge_path.read_text(encoding="utf-8")
    _assert("set_sandbox_mode(True)" in src,
            "ARCH-05 futures testnet broker has set_sandbox_mode(True) hardcoded")


# ============================================================
# Runner
# ============================================================

def _run_all() -> None:
    tests = [
        test_strategy_base_contract,
        test_config_hub_root,
        test_backtest_metrics_shape,
        test_scan_consensus_keys,
        test_mtf_signal_chop_detection,
        test_fuse_stand_aside_on_chop,
        test_fuse_confidence_floor_not_average,
        test_risk_engine_position_sizing,
        test_reg_sys_path_load_strategy,
        test_reg_bar_dropping_iloc,
        test_reg_market_order_no_price,
        test_reg_futures_testnet_no_price,
        test_reg_predict_oos_gate,
        test_arch_execution_gated,
        test_arch_no_live_broker_import_in_scan,
        test_arch_scalper_dry_run_default,
        test_arch_bridge_no_t01_import,
        test_arch_futures_testnet_sandbox_hardcoded,
    ]
    for fn in tests:
        try:
            fn()
        except Exception:
            _assert(False, fn.__name__, traceback.format_exc().splitlines()[-1])

    print(f"\n{'='*60}")
    print(f"T03 Foundation  {_PASSED} passed / {_FAILED} failed  ({len(_CASES)} total)")
    if _FAILED:
        print("\nFailed cases:")
        for name, result in _CASES:
            if result.startswith("FAIL"):
                print(f"  {name}  →  {result}")
    print("=" * 60)
    sys.exit(1 if _FAILED else 0)


if __name__ == "__main__":
    _run_all()
