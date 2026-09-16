import sqlite3
import os
import json
from contextlib import contextmanager

from backend import config

def _get_conn():
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                quantity REAL,
                stop_loss REAL,
                take_profit REAL,
                entry_reason TEXT,
                exit_price REAL,
                pnl REAL,
                pnl_pct REAL,
                exit_reason TEXT,
                opened_at TEXT,
                closed_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS equity_curve (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT,
                balance REAL,
                equity REAL,
                timestamp TEXT
            )
        """)
        conn.commit()

def set_state(key: str, value: str):
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO state (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )
        conn.commit()

def get_state(key: str, default: str = None) -> str:
    with _get_conn() as conn:
        row = conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

def get_open_trades(mode: str) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM trades WHERE mode = ? AND closed_at IS NULL", (mode,)).fetchall()
        return [dict(r) for r in rows]

def get_closed_trades(mode: str, limit: int = 100) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM trades WHERE mode = ? AND closed_at IS NOT NULL ORDER BY id DESC LIMIT ?", (mode, limit)).fetchall()
        return [dict(r) for r in rows]

def close_trade(id: int, price: float, pnl: float, pnl_pct: float, reason: str):
    from datetime import datetime, timezone
    with _get_conn() as conn:
        conn.execute(
            "UPDATE trades SET exit_price = ?, pnl = ?, pnl_pct = ?, exit_reason = ?, closed_at = ? WHERE id = ?",
            (price, pnl, pnl_pct, reason, datetime.now(timezone.utc).isoformat(), id)
        )
        conn.commit()

def insert_trade(trade: dict) -> int:
    with _get_conn() as conn:
        keys = list(trade.keys())
        values = list(trade.values())
        placeholders = ",".join(["?"] * len(keys))
        cols = ",".join(keys)
        cursor = conn.execute(f"INSERT INTO trades ({cols}) VALUES ({placeholders})", values)
        conn.commit()
        return cursor.lastrowid

def record_equity(mode: str, balance: float, equity: float):
    from datetime import datetime, timezone
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO equity_curve (mode, balance, equity, timestamp) VALUES (?, ?, ?, ?)",
            (mode, balance, equity, datetime.now(timezone.utc).isoformat())
        )
        conn.commit()

def update_trade_stop_loss(trade_id: int, new_stop: float):
    with _get_conn() as conn:
        conn.execute("UPDATE trades SET stop_loss = ? WHERE id = ?", (new_stop, trade_id))
        conn.commit()
