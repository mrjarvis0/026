"""Emergency stop and daily loss-limit circuit breaker."""
from datetime import datetime, timezone

from backend import config
from backend.data import database as db


def is_stopped() -> bool:
    return db.get_state("emergency_stop", "false") == "true"


def emergency_stop() -> None:
    db.set_state("emergency_stop", "true")
    db.set_state("stop_ts", datetime.now(timezone.utc).isoformat())


def resume() -> None:
    db.set_state("emergency_stop", "false")


def daily_pnl(mode: str = "paper") -> float:
    today = datetime.now(timezone.utc).date().isoformat()
    closed = db.get_closed_trades(mode=mode, limit=1000)
    return sum(
        (t["pnl"] or 0.0)
        for t in closed
        if (t.get("closed_at") or "").startswith(today)   # closed_at may be NULL
    )


def daily_loss_breached(mode: str = "paper", base: float | None = None) -> bool:
    # `base` is the account size the % limit applies to. Paper uses the fixed
    # starting balance; real passes its own day-start equity (the paper start
    # balance is meaningless for a real account).
    if base is None:
        base = config.PAPER_START_BALANCE
    limit = base * config.DAILY_LOSS_LIMIT_PCT
    return daily_pnl(mode) <= -limit


def trading_allowed(mode: str = "paper", base: float | None = None) -> tuple[bool, str]:
    if is_stopped():
        return False, "Emergency stop is active."
    if daily_loss_breached(mode, base):
        return False, "Daily loss limit reached — trading halted for today."
    return True, "ok"
