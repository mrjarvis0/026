"""SQLite storage for trades, positions, and performance snapshots."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from backend.config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL,                 -- 'paper' or 'real'
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,                 -- 'buy' / 'sell'
    entry_price REAL NOT NULL,
    exit_price REAL,
    quantity REAL NOT NULL,
    stop_loss REAL,
    take_profit REAL,
    status TEXT NOT NULL DEFAULT 'open', -- 'open' / 'closed'
    pnl REAL,                           -- realized profit/loss in quote currency
    pnl_pct REAL,
    entry_reason TEXT,
    exit_reason TEXT,
    entry_factor TEXT,                  -- dominant sub-signal family that opened it
    entry_regime TEXT,                  -- 'trend' / 'chop' at entry (from ADX)
    entry_adx REAL,                     -- ADX reading at entry
    opened_at TEXT NOT NULL,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS equity_curve (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL,
    balance REAL NOT NULL,
    equity REAL NOT NULL,               -- balance + open position value
    ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS state (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- F3: every strategy-param change is journaled here (who changed what, when, why),
-- so a tuned threshold is provenance, not magic — per 026's evidence standard.
CREATE TABLE IF NOT EXISTS param_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    source TEXT NOT NULL,             -- 'self_tune' | 'reflection' | 'manual'
    reason TEXT NOT NULL DEFAULT '',  -- human-readable why, e.g. 'accuracy 62% -> net_threshold 1.05'
    params TEXT NOT NULL              -- full params JSON snapshot AFTER the change
);

-- Hot paths: get_open_trades / get_closed_trades filter by (mode, status);
-- daily_pnl filters closed rows by date. Without these, is_real_trading_unlocked
-- scanned the whole table on every /api/status.
CREATE INDEX IF NOT EXISTS idx_trades_mode_status  ON trades(mode, status);
CREATE INDEX IF NOT EXISTS idx_trades_status_closed ON trades(status, closed_at);
CREATE INDEX IF NOT EXISTS idx_equity_mode_id       ON equity_curve(mode, id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn():
    # timeout: block up to 5s on a locked DB instead of raising immediately.
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    # WAL lets the bot task and the API threadpool read/write concurrently
    # without tripping over each other; busy_timeout backs the Python timeout.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # Migrate DBs created before the loss-attribution columns existed. ADD
        # COLUMN on an existing column raises OperationalError — ignore that.
        for col, decl in (("entry_factor", "TEXT"),
                          ("entry_regime", "TEXT"),
                          ("entry_adx", "REAL")):
            try:
                conn.execute(f"ALTER TABLE trades ADD COLUMN {col} {decl}")
            except sqlite3.OperationalError:
                pass


# ---------------- Trades ----------------

def insert_trade(trade: dict[str, Any]) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO trades
               (mode, symbol, side, entry_price, quantity, stop_loss, take_profit,
                status, entry_reason, entry_factor, entry_regime, entry_adx, opened_at)
               VALUES (:mode, :symbol, :side, :entry_price, :quantity, :stop_loss,
                       :take_profit, 'open', :entry_reason, :entry_factor,
                       :entry_regime, :entry_adx, :opened_at)""",
            {
                "mode": trade["mode"],
                "symbol": trade["symbol"],
                "side": trade["side"],
                "entry_price": trade["entry_price"],
                "quantity": trade["quantity"],
                "stop_loss": trade.get("stop_loss"),
                "take_profit": trade.get("take_profit"),
                "entry_reason": trade.get("entry_reason", ""),
                "entry_factor": trade.get("entry_factor"),
                "entry_regime": trade.get("entry_regime"),
                "entry_adx": trade.get("entry_adx"),
                "opened_at": trade.get("opened_at", _now()),
            },
        )
        return cur.lastrowid


def close_trade(trade_id: int, exit_price: float, pnl: float,
                pnl_pct: float, exit_reason: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """UPDATE trades
               SET exit_price=?, pnl=?, pnl_pct=?, exit_reason=?,
                   status='closed', closed_at=?
               WHERE id=?""",
            (exit_price, pnl, pnl_pct, exit_reason, _now(), trade_id),
        )


def update_trade_stop_loss(trade_id: int, stop_loss: float) -> None:
    """Move a still-open trade's stop (used by trailing stops). Never closes it."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE trades SET stop_loss=? WHERE id=? AND status='open'",
            (stop_loss, trade_id),
        )


def get_open_trades(mode: Optional[str] = None) -> list[dict]:
    query = "SELECT * FROM trades WHERE status='open'"
    params: tuple = ()
    if mode:
        query += " AND mode=?"
        params = (mode,)
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_closed_trades(mode: Optional[str] = None, limit: int = 500) -> list[dict]:
    query = "SELECT * FROM trades WHERE status='closed'"
    params: list = []
    if mode:
        query += " AND mode=?"
        params.append(mode)
    query += " ORDER BY closed_at DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_all_trades(mode: Optional[str] = None, limit: int = 500) -> list[dict]:
    query = "SELECT * FROM trades"
    params: list = []
    if mode:
        query += " WHERE mode=?"
        params.append(mode)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# ---------------- Equity curve ----------------

def record_equity(mode: str, balance: float, equity: float) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO equity_curve (mode, balance, equity, ts) VALUES (?,?,?,?)",
            (mode, balance, equity, _now()),
        )


def get_equity_curve(mode: str, limit: int = 500) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT balance, equity, ts FROM equity_curve WHERE mode=? "
            "ORDER BY id DESC LIMIT ?",
            (mode, limit),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]


# ---------------- Param-change audit trail (F3) ----------------

def insert_param_history(source: str, reason: str, params_json: str) -> int:
    """Journal one strategy-param change. `params_json` is the full snapshot
    AFTER the change. Returns the row id."""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO param_history (ts, source, reason, params) VALUES (?,?,?,?)",
            (_now(), source, reason, params_json),
        )
        return cur.lastrowid


def get_param_history(limit: int = 100) -> list[dict]:
    """Newest-first audit rows: when, who (source), why, and the full snapshot."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT ts, source, reason, params FROM param_history "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------- Key/value state ----------------

def set_state(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO state (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def get_state(key: str, default: Optional[str] = None) -> Optional[str]:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default
