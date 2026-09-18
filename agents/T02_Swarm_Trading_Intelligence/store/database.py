import sqlite3
import json
from contextlib import closing
from typing import List, Dict, Any

# `with sqlite3.connect(...) as conn` commits/rolls back but does NOT close the
# connection, so it leaked handles and — on Windows — kept the .db file locked so
# it could not be deleted (test teardown failed). `closing()` guarantees close();
# the inner `with conn` still gives a commit/rollback transaction where we write.


class Database:
    def __init__(self, db_path: str = "swarm.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS bots (
                    bot_id TEXT PRIMARY KEY,
                    strategy TEXT,
                    parameters TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reactions (
                    reaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id TEXT,
                    trade_event_id TEXT,
                    action TEXT,
                    price REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bot_id) REFERENCES bots(bot_id)
                )
            ''')

    def reset(self):
        """Clears all data for testing."""
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute('DELETE FROM reactions')
            conn.execute('DELETE FROM bots')

    def insert_bots(self, bots: List[Dict[str, Any]]):
        """Inserts bots in chunks to avoid SQLite's bound-variable limit."""
        chunk_size = 900
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            for i in range(0, len(bots), chunk_size):
                chunk = bots[i:i + chunk_size]
                values = [
                    (bot.get('bot_id'), bot.get('strategy'),
                     json.dumps(bot.get('parameters', {})))
                    for bot in chunk
                ]
                conn.executemany(
                    'INSERT OR REPLACE INTO bots (bot_id, strategy, parameters) VALUES (?, ?, ?)',
                    values
                )

    def get_bots_by_ids(self, bot_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetches bots by ID, chunking the IN clause to avoid SQLite limits."""
        chunk_size = 900
        results = []
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            for i in range(0, len(bot_ids), chunk_size):
                chunk = bot_ids[i:i + chunk_size]
                placeholders = ','.join(['?'] * len(chunk))
                cursor = conn.execute(
                    f"SELECT * FROM bots WHERE bot_id IN ({placeholders})", chunk)
                for row in cursor.fetchall():
                    results.append({
                        'bot_id': row['bot_id'],
                        'strategy': row['strategy'],
                        'parameters': json.loads(row['parameters'])
                    })
        return results

    def get_all_bots(self) -> List[Dict[str, Any]]:
        results = []
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM bots")
            for row in cursor.fetchall():
                results.append({
                    'bot_id': row['bot_id'],
                    'strategy': row['strategy'],
                    'parameters': json.loads(row['parameters'])
                })
        return results

    def record_reactions(self, reactions: List[Dict[str, Any]]):
        """Inserts reactions in chunks to avoid SQLite's bound-variable limit."""
        chunk_size = 900
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            for i in range(0, len(reactions), chunk_size):
                chunk = reactions[i:i + chunk_size]
                values = [
                    (r.get('bot_id'), r.get('trade_event_id'),
                     r.get('action'), r.get('price'))
                    for r in chunk
                ]
                conn.executemany(
                    'INSERT INTO reactions (bot_id, trade_event_id, action, price) VALUES (?, ?, ?, ?)',
                    values
                )
