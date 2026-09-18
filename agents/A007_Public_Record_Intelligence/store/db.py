import sqlite3
import os
import json

DB_PATH = "data/processed/a007.db"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS congress_trades (
            id TEXT PRIMARY KEY,
            politician TEXT,
            ticker TEXT,
            transaction_date TEXT,
            filing_date TEXT,
            transaction_type TEXT,
            amount_min INTEGER,
            amount_max INTEGER,
            raw_data TEXT,
            source_id TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS insider_trades (
            id TEXT PRIMARY KEY,
            insider_name TEXT,
            insider_title TEXT,
            ticker TEXT,
            transaction_date TEXT,
            filing_date TEXT,
            transaction_type TEXT,
            shares INTEGER,
            price REAL,
            value REAL,
            raw_data TEXT,
            source_id TEXT
        )
    """)
    conn.commit()
    return conn

def store_trade(conn, trade):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO congress_trades
        (id, politician, ticker, transaction_date, filing_date, transaction_type, amount_min, amount_max, raw_data, source_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        trade["id"],
        trade["politician"],
        trade["ticker"],
        trade["transaction_date"],
        trade["filing_date"],
        trade["transaction_type"],
        trade["amount_min"],
        trade["amount_max"],
        json.dumps(trade["raw_data"]),
        trade.get("source_id", "S119")
    ))
    conn.commit()

def get_trades_by_ticker(conn, ticker):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM congress_trades WHERE ticker = ?", (ticker,))
    return cursor.fetchall()

def store_insider_trade(conn, trade):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO insider_trades
        (id, insider_name, insider_title, ticker, transaction_date, filing_date, transaction_type, shares, price, value, raw_data, source_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        trade["id"],
        trade["insider_name"],
        trade["insider_title"],
        trade["ticker"],
        trade["transaction_date"],
        trade["filing_date"],
        trade["transaction_type"],
        trade.get("shares", 0),
        trade.get("price", 0.0),
        trade.get("value", 0.0),
        json.dumps(trade["raw_data"]),
        trade.get("source_id", "S119")
    ))
    conn.commit()

def get_insider_trades_by_ticker(conn, ticker):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM insider_trades WHERE ticker = ?", (ticker,))
    return cursor.fetchall()
