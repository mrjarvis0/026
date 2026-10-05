"""Database module for T01 Smart Binance Intelligence v2.

This module provides SQLite database functionality for:
- Storing trades
- Storing orders
- Storing positions
- Storing equity curve
- Storing state (key-value pairs)
- Managing database schema
"""

import logging
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timezone
import pandas as pd

from backend import config

log = logging.getLogger("data.database")


# Database schema versions
SCHEMA_VERSION = 2

# SQL for creating tables
CREATE_TABLE_TRADES = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    entry_price REAL NOT NULL,
    exit_price REAL,
    qty REAL NOT NULL,
    side TEXT NOT NULL,  -- 'long' or 'short'
    pnl REAL NOT NULL,
    pnl_pct REAL NOT NULL,
    fee REAL NOT NULL,
    stop_loss REAL,
    take_profit REAL,
    exit_reason TEXT NOT NULL,  -- 'stop_loss', 'take_profit', 'signal', 'manual', 'backtest_end'
    mode TEXT NOT NULL,  -- 'paper' or 'real'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_TABLE_ORDERS = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT UNIQUE,  -- Exchange order ID
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,  -- 'buy' or 'sell'
    order_type TEXT NOT NULL,  -- 'market', 'limit', 'stop_loss', 'stop_limit', 'oco'
    price REAL,
    qty REAL NOT NULL,
    filled REAL DEFAULT 0,
    avg_fill_price REAL,
    status TEXT NOT NULL,  -- 'pending', 'partially_filled', 'filled', 'canceled', 'rejected', 'expired'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bot_position_id INTEGER,  -- Link to bot's position
    exchange_data TEXT,  -- Raw exchange response
    FOREIGN KEY (bot_position_id) REFERENCES positions(id)
);
"""

CREATE_TABLE_POSITIONS = """
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,  -- 'long' or 'short'
    entry_price REAL NOT NULL,
    current_qty REAL NOT NULL,
    stop_loss REAL,
    take_profit REAL,
    trailing_stop REAL,
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    status TEXT NOT NULL,  -- 'open', 'closed', 'liquidated'
    entry_order_id INTEGER,  -- Link to entry order
    exit_order_id INTEGER,  -- Link to exit order
    mode TEXT NOT NULL,  -- 'paper' or 'real'
    FOREIGN KEY (entry_order_id) REFERENCES orders(id),
    FOREIGN KEY (exit_order_id) REFERENCES orders(id)
);
"""

CREATE_TABLE_EQUITY_CURVE = """
CREATE TABLE IF NOT EXISTS equity_curve (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    balance REAL NOT NULL,
    equity REAL NOT NULL,
    open_positions INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_TABLE_STATE = """
CREATE TABLE IF NOT EXISTS state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_TABLE_SCHEMA_VERSION = """
CREATE TABLE IF NOT EXISTS schema_version (
    id INTEGER PRIMARY KEY,
    version INTEGER NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class Database:
    """SQLite database manager for T01 trading bot.
    
    This class provides a high-level interface for database operations,
    including automatic connection management and schema migrations.
    """
    
    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """Initialize the database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path) if db_path else config.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[sqlite3.Connection] = None
        self._initialized = False
        
    @property
    def connection(self) -> sqlite3.Connection:
        """Get database connection, creating if necessary."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                str(self.db_path),
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            # Enable foreign key support
            self._connection.execute("PRAGMA foreign_keys = ON")
            # Return rows as dictionaries
            self._connection.row_factory = sqlite3.Row
        return self._connection
    
    def init_db(self) -> bool:
        """Initialize database with schema and migrations.
        
        Returns:
            True if initialization was successful
        """
        try:
            # Check current schema version
            current_version = self._get_schema_version()
            
            # Apply migrations if needed
            if current_version < SCHEMA_VERSION:
                self._apply_migrations(current_version)
            else:
                # Create tables if they don't exist
                self._create_tables()
            
            self._initialized = True
            log.info(f"Database initialized at {self.db_path}")
            return True
            
        except Exception as e:
            log.error(f"Failed to initialize database: {e}")
            return False
    
    def _get_schema_version(self) -> int:
        """Get current schema version."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT version FROM schema_version ORDER BY id DESC LIMIT 1")
            result = cursor.fetchone()
            return result['version'] if result else 0
        except sqlite3.OperationalError:
            return 0
    
    def _apply_migrations(self, current_version: int) -> None:
        """Apply database migrations.
        
        Args:
            current_version: Current schema version
        """
        log.info(f"Applying migrations from version {current_version} to {SCHEMA_VERSION}")
        
        # Create schema_version table if it doesn't exist
        cursor = self.connection.cursor()
        cursor.execute(CREATE_TABLE_SCHEMA_VERSION)
        
        # Apply migrations based on current version
        if current_version < 1:
            # Initial schema
            self._create_tables()
            current_version = 1
        
        if current_version < 2:
            # Add orders and positions tables (for Order Reconciliation)
            cursor.execute(CREATE_TABLE_ORDERS)
            cursor.execute(CREATE_TABLE_POSITIONS)
            current_version = 2
        
        # Update schema version
        cursor.execute(
            "INSERT INTO schema_version (id, version) VALUES (1, ?)",
            (current_version,)
        )
        self.connection.commit()
        
        log.info(f"Migrations applied, current version: {current_version}")
    
    def _create_tables(self) -> None:
        """Create all database tables."""
        cursor = self.connection.cursor()
        
        # Create all tables
        cursor.execute(CREATE_TABLE_TRADES)
        cursor.execute(CREATE_TABLE_ORDERS)
        cursor.execute(CREATE_TABLE_POSITIONS)
        cursor.execute(CREATE_TABLE_EQUITY_CURVE)
        cursor.execute(CREATE_TABLE_STATE)
        cursor.execute(CREATE_TABLE_SCHEMA_VERSION)
        
        # Insert schema version
        cursor.execute(
            "INSERT OR IGNORE INTO schema_version (id, version) VALUES (1, ?)",
            (SCHEMA_VERSION,)
        )
        
        self.connection.commit()
        log.info("All database tables created")
    
    # ============================================================================
    # TRADE OPERATIONS
    # ============================================================================
    
    def save_trade(self, trade_data: Dict[str, Any]) -> int:
        """Save a trade to the database.
        
        Args:
            trade_data: Dictionary with trade data
            
        Returns:
            ID of the saved trade
        """
        try:
            cursor = self.connection.cursor()
            
            # Prepare data
            data = {
                'symbol': trade_data.get('symbol'),
                'entry_time': trade_data.get('entry_time'),
                'exit_time': trade_data.get('exit_time'),
                'entry_price': trade_data.get('entry_price'),
                'exit_price': trade_data.get('exit_price'),
                'qty': trade_data.get('qty'),
                'side': trade_data.get('side'),
                'pnl': trade_data.get('pnl'),
                'pnl_pct': trade_data.get('pnl_pct'),
                'fee': trade_data.get('fee'),
                'stop_loss': trade_data.get('stop_loss'),
                'take_profit': trade_data.get('take_profit'),
                'exit_reason': trade_data.get('exit_reason', 'unknown'),
                'mode': trade_data.get('mode', 'paper'),
                'created_at': datetime.now(timezone.utc)
            }
            
            # Convert timestamps to ISO format if they're datetime objects
            if isinstance(data['entry_time'], datetime):
                data['entry_time'] = data['entry_time'].isoformat()
            if isinstance(data['exit_time'], datetime):
                data['exit_time'] = data['exit_time'].isoformat()
            
            # Build INSERT query
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?'] * len(data))
            query = f"INSERT INTO trades ({columns}) VALUES ({placeholders})"
            
            cursor.execute(query, tuple(data.values()))
            self.connection.commit()
            
            trade_id = cursor.lastrowid
            log.debug(f"Saved trade {trade_id}")
            return trade_id
            
        except Exception as e:
            log.error(f"Failed to save trade: {e}")
            self.connection.rollback()
            return 0
    
    def get_trades(
        self,
        limit: int = 100,
        offset: int = 0,
        symbol: Optional[str] = None,
        mode: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get trades from the database.
        
        Args:
            limit: Maximum number of trades to return
            offset: Offset for pagination
            symbol: Filter by symbol
            mode: Filter by mode ('paper' or 'real')
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            List of trade dictionaries
        """
        try:
            cursor = self.connection.cursor()
            
            query = "SELECT * FROM trades"
            conditions = []
            params = []
            
            if symbol:
                conditions.append("symbol = ?")
                params.append(symbol)
            
            if mode:
                conditions.append("mode = ?")
                params.append(mode)
            
            if start_date:
                conditions.append("entry_time >= ?")
                params.append(start_date.isoformat())
            
            if end_date:
                conditions.append("entry_time <= ?")
                params.append(end_date.isoformat())
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY entry_time DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            log.error(f"Failed to get trades: {e}")
            return []
    
    def get_trade(self, trade_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific trade by ID.
        
        Args:
            trade_id: Trade ID
            
        Returns:
            Trade dictionary or None if not found
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            log.error(f"Failed to get trade {trade_id}: {e}")
            return None
    
    def delete_trade(self, trade_id: int) -> bool:
        """Delete a trade from the database.
        
        Args:
            trade_id: Trade ID
            
        Returns:
            True if deletion was successful
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
            self.connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            log.error(f"Failed to delete trade {trade_id}: {e}")
            self.connection.rollback()
            return False
    
    def get_trade_count(
        self,
        symbol: Optional[str] = None,
        mode: Optional[str] = None
    ) -> int:
        """Get the number of trades.
        
        Args:
            symbol: Filter by symbol
            mode: Filter by mode
            
        Returns:
            Number of trades
        """
        try:
            cursor = self.connection.cursor()
            query = "SELECT COUNT(*) as count FROM trades"
            conditions = []
            params = []
            
            if symbol:
                conditions.append("symbol = ?")
                params.append(symbol)
            
            if mode:
                conditions.append("mode = ?")
                params.append(mode)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            return row['count'] if row else 0
        except Exception as e:
            log.error(f"Failed to get trade count: {e}")
            return 0
    
    # ============================================================================
    # ORDER OPERATIONS
    # ============================================================================
    
    def save_order(self, order_data: Dict[str, Any]) -> int:
        """Save an order to the database.
        
        Args:
            order_data: Dictionary with order data
            
        Returns:
            ID of the saved order
        """
        try:
            cursor = self.connection.cursor()
            
            # Prepare data
            data = {
                'order_id': order_data.get('order_id'),
                'symbol': order_data.get('symbol'),
                'side': order_data.get('side'),
                'order_type': order_data.get('order_type'),
                'price': order_data.get('price'),
                'qty': order_data.get('qty'),
                'filled': order_data.get('filled', 0),
                'avg_fill_price': order_data.get('avg_fill_price'),
                'status': order_data.get('status'),
                'bot_position_id': order_data.get('bot_position_id'),
                'exchange_data': order_data.get('exchange_data'),
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            # Build INSERT query
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?'] * len(data))
            query = f"INSERT INTO orders ({columns}) VALUES ({placeholders})"
            
            cursor.execute(query, tuple(data.values()))
            self.connection.commit()
            
            order_id = cursor.lastrowid
            log.debug(f"Saved order {order_id}")
            return order_id
            
        except Exception as e:
            log.error(f"Failed to save order: {e}")
            self.connection.rollback()
            return 0
    
    def update_order(self, order_id: int, updates: Dict[str, Any]) -> bool:
        """Update an order in the database.
        
        Args:
            order_id: Order ID
            updates: Dictionary with fields to update
            
        Returns:
            True if update was successful
        """
        try:
            cursor = self.connection.cursor()
            
            # Build SET clause
            set_clauses = []
            params = []
            for key, value in updates.items():
                set_clauses.append(f"{key} = ?")
                params.append(value)
            
            params.append(order_id)
            query = f"UPDATE orders SET {', '.join(set_clauses)} WHERE id = ?"
            
            cursor.execute(query, params)
            self.connection.commit()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            log.error(f"Failed to update order {order_id}: {e}")
            self.connection.rollback()
            return False
    
    def get_orders(
        self,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get orders from the database.
        
        Args:
            status: Filter by status
            symbol: Filter by symbol
            limit: Maximum number of orders to return
            offset: Offset for pagination
            
        Returns:
            List of order dictionaries
        """
        try:
            cursor = self.connection.cursor()
            
            query = "SELECT * FROM orders"
            conditions = []
            params = []
            
            if status:
                conditions.append("status = ?")
                params.append(status)
            
            if symbol:
                conditions.append("symbol = ?")
                params.append(symbol)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            log.error(f"Failed to get orders: {e}")
            return []
    
    def get_active_orders(self) -> List[Dict[str, Any]]:
        """Get all active (non-terminal) orders.
        
        Returns:
            List of active order dictionaries
        """
        return self.get_orders(status=None)  # Get all, filter in code
    
    def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific order by ID.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order dictionary or None if not found
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            log.error(f"Failed to get order {order_id}: {e}")
            return None
    
    def get_order_by_exchange_id(self, exchange_order_id: str) -> Optional[Dict[str, Any]]:
        """Get an order by exchange order ID.
        
        Args:
            exchange_order_id: Exchange order ID
            
        Returns:
            Order dictionary or None if not found
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM orders WHERE order_id = ?", (exchange_order_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            log.error(f"Failed to get order by exchange ID {exchange_order_id}: {e}")
            return None
    
    def delete_order(self, order_id: int) -> bool:
        """Delete an order from the database.
        
        Args:
            order_id: Order ID
            
        Returns:
            True if deletion was successful
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
            self.connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            log.error(f"Failed to delete order {order_id}: {e}")
            self.connection.rollback()
            return False
    
    # ============================================================================
    # POSITION OPERATIONS
    # ============================================================================
    
    def save_position(self, position_data: Dict[str, Any]) -> int:
        """Save a position to the database.
        
        Args:
            position_data: Dictionary with position data
            
        Returns:
            ID of the saved position
        """
        try:
            cursor = self.connection.cursor()
            
            # Prepare data
            data = {
                'symbol': position_data.get('symbol'),
                'side': position_data.get('side'),
                'entry_price': position_data.get('entry_price'),
                'current_qty': position_data.get('current_qty'),
                'stop_loss': position_data.get('stop_loss'),
                'take_profit': position_data.get('take_profit'),
                'trailing_stop': position_data.get('trailing_stop'),
                'opened_at': position_data.get('opened_at'),
                'closed_at': position_data.get('closed_at'),
                'status': position_data.get('status', 'open'),
                'entry_order_id': position_data.get('entry_order_id'),
                'exit_order_id': position_data.get('exit_order_id'),
                'mode': position_data.get('mode', 'paper'),
                'created_at': datetime.now(timezone.utc)
            }
            
            # Convert timestamps to ISO format if they're datetime objects
            if isinstance(data['opened_at'], datetime):
                data['opened_at'] = data['opened_at'].isoformat()
            if isinstance(data['closed_at'], datetime):
                data['closed_at'] = data['closed_at'].isoformat()
            
            # Build INSERT query
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?'] * len(data))
            query = f"INSERT INTO positions ({columns}) VALUES ({placeholders})"
            
            cursor.execute(query, tuple(data.values()))
            self.connection.commit()
            
            position_id = cursor.lastrowid
            log.debug(f"Saved position {position_id}")
            return position_id
            
        except Exception as e:
            log.error(f"Failed to save position: {e}")
            self.connection.rollback()
            return 0
    
    def update_position(self, position_id: int, updates: Dict[str, Any]) -> bool:
        """Update a position in the database.
        
        Args:
            position_id: Position ID
            updates: Dictionary with fields to update
            
        Returns:
            True if update was successful
        """
        try:
            cursor = self.connection.cursor()
            
            # Build SET clause
            set_clauses = []
            params = []
            for key, value in updates.items():
                set_clauses.append(f"{key} = ?")
                params.append(value)
            
            params.append(position_id)
            query = f"UPDATE positions SET {', '.join(set_clauses)} WHERE id = ?"
            
            cursor.execute(query, params)
            self.connection.commit()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            log.error(f"Failed to update position {position_id}: {e}")
            self.connection.rollback()
            return False
    
    def get_positions(
        self,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get positions from the database.
        
        Args:
            status: Filter by status
            symbol: Filter by symbol
            limit: Maximum number of positions to return
            offset: Offset for pagination
            
        Returns:
            List of position dictionaries
        """
        try:
            cursor = self.connection.cursor()
            
            query = "SELECT * FROM positions"
            conditions = []
            params = []
            
            if status:
                conditions.append("status = ?")
                params.append(status)
            
            if symbol:
                conditions.append("symbol = ?")
                params.append(symbol)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY opened_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            log.error(f"Failed to get positions: {e}")
            return []
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions.
        
        Returns:
            List of open position dictionaries
        """
        return self.get_positions(status='open')
    
    def get_position(self, position_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific position by ID.
        
        Args:
            position_id: Position ID
            
        Returns:
            Position dictionary or None if not found
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM positions WHERE id = ?", (position_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            log.error(f"Failed to get position {position_id}: {e}")
            return None
    
    def get_position_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get position by symbol.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Position dictionary or None if not found
        """
        positions = self.get_positions(symbol=symbol, status='open')
        return positions[0] if positions else None
    
    def delete_position(self, position_id: int) -> bool:
        """Delete a position from the database.
        
        Args:
            position_id: Position ID
            
        Returns:
            True if deletion was successful
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM positions WHERE id = ?", (position_id,))
            self.connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            log.error(f"Failed to delete position {position_id}: {e}")
            self.connection.rollback()
            return False
    
    # ============================================================================
    # EQUITY CURVE OPERATIONS
    # ============================================================================
    
    def save_equity_point(self, equity_data: Dict[str, Any]) -> int:
        """Save an equity curve point to the database.
        
        Args:
            equity_data: Dictionary with equity data
            
        Returns:
            ID of the saved equity point
        """
        try:
            cursor = self.connection.cursor()
            
            # Prepare data
            data = {
                'timestamp': equity_data.get('timestamp'),
                'balance': equity_data.get('balance'),
                'equity': equity_data.get('equity'),
                'open_positions': equity_data.get('open_positions', 0),
                'created_at': datetime.now(timezone.utc)
            }
            
            # Convert timestamp to ISO format if it's a datetime object
            if isinstance(data['timestamp'], datetime):
                data['timestamp'] = data['timestamp'].isoformat()
            
            # Build INSERT query
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?'] * len(data))
            query = f"INSERT INTO equity_curve ({columns}) VALUES ({placeholders})"
            
            cursor.execute(query, tuple(data.values()))
            self.connection.commit()
            
            equity_id = cursor.lastrowid
            log.debug(f"Saved equity point {equity_id}")
            return equity_id
            
        except Exception as e:
            log.error(f"Failed to save equity point: {e}")
            self.connection.rollback()
            return 0
    
    def get_equity_curve(
        self,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get equity curve from the database.
        
        Args:
            limit: Maximum number of points to return
            offset: Offset for pagination
            
        Returns:
            List of equity point dictionaries
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT * FROM equity_curve ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            log.error(f"Failed to get equity curve: {e}")
            return []
    
    # ============================================================================
    # STATE OPERATIONS
    # ============================================================================
    
    def set_state(self, key: str, value: Any) -> bool:
        """Set a state value.
        
        Args:
            key: State key
            value: State value (will be converted to string)
            
        Returns:
            True if set was successful
        """
        try:
            cursor = self.connection.cursor()
            
            # Convert value to string
            if isinstance(value, (dict, list)):
                import json
                value_str = json.dumps(value)
            else:
                value_str = str(value)
            
            # Insert or update
            cursor.execute(
                "INSERT OR REPLACE INTO state (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value_str, datetime.now(timezone.utc).isoformat())
            )
            self.connection.commit()
            return True
            
        except Exception as e:
            log.error(f"Failed to set state {key}: {e}")
            self.connection.rollback()
            return False
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get a state value.
        
        Args:
            key: State key
            default: Default value if key not found
            
        Returns:
            State value or default
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT value FROM state WHERE key = ?", (key,))
            row = cursor.fetchone()
            
            if row:
                value_str = row['value']
                
                # Try to parse as JSON
                try:
                    import json
                    return json.loads(value_str)
                except (json.JSONDecodeError, TypeError):
                    # Return as string
                    return value_str
            
            return default
            
        except Exception as e:
            log.error(f"Failed to get state {key}: {e}")
            return default
    
    def delete_state(self, key: str) -> bool:
        """Delete a state value.
        
        Args:
            key: State key
            
        Returns:
            True if deletion was successful
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM state WHERE key = ?", (key,))
            self.connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            log.error(f"Failed to delete state {key}: {e}")
            self.connection.rollback()
            return False
    
    def get_all_state(self) -> Dict[str, Any]:
        """Get all state values.
        
        Returns:
            Dictionary of all state key-value pairs
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT key, value FROM state")
            rows = cursor.fetchall()
            
            state = {}
            for row in rows:
                try:
                    import json
                    state[row['key']] = json.loads(row['value'])
                except (json.JSONDecodeError, TypeError):
                    state[row['key']] = row['value']
            
            return state
        except Exception as e:
            log.error(f"Failed to get all state: {e}")
            return {}
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            cursor = self.connection.cursor()
            
            stats = {}
            
            # Trade count
            cursor.execute("SELECT COUNT(*) as count FROM trades")
            stats['trade_count'] = cursor.fetchone()['count']
            
            # Order count
            cursor.execute("SELECT COUNT(*) as count FROM orders")
            stats['order_count'] = cursor.fetchone()['count']
            
            # Position count
            cursor.execute("SELECT COUNT(*) as count FROM positions")
            stats['position_count'] = cursor.fetchone()['count']
            
            # Open positions
            cursor.execute("SELECT COUNT(*) as count FROM positions WHERE status = 'open'")
            stats['open_position_count'] = cursor.fetchone()['count']
            
            # Equity points
            cursor.execute("SELECT COUNT(*) as count FROM equity_curve")
            stats['equity_point_count'] = cursor.fetchone()['count']
            
            # State count
            cursor.execute("SELECT COUNT(*) as count FROM state")
            stats['state_count'] = cursor.fetchone()['count']
            
            # Recent trades
            cursor.execute("SELECT COUNT(*) as count FROM trades WHERE entry_time >= datetime('now', '-7 days')")
            stats['recent_trade_count'] = cursor.fetchone()['count']
            
            return stats
            
        except Exception as e:
            log.error(f"Failed to get stats: {e}")
            return {}
    
    def backup(self, backup_path: Path) -> bool:
        """Create a backup of the database.
        
        Args:
            backup_path: Path to save backup
            
        Returns:
            True if backup was successful
        """
        try:
            import shutil
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.db_path, backup_path)
            log.info(f"Database backup created at {backup_path}")
            return True
        except Exception as e:
            log.error(f"Failed to create backup: {e}")
            return False
    
    def restore(self, backup_path: Path) -> bool:
        """Restore database from backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if restore was successful
        """
        try:
            # Close existing connection
            if self._connection:
                self._connection.close()
                self._connection = None
            
            import shutil
            shutil.copy2(backup_path, self.db_path)
            
            # Reinitialize
            self._initialized = False
            self.init_db()
            
            log.info(f"Database restored from {backup_path}")
            return True
        except Exception as e:
            log.error(f"Failed to restore database: {e}")
            return False
    
    def clear_all(self) -> bool:
        """Clear all data from the database.
        
        WARNING: This will delete all data!
        
        Returns:
            True if clear was successful
        """
        try:
            cursor = self.connection.cursor()
            
            # Delete from all tables
            cursor.execute("DELETE FROM trades")
            cursor.execute("DELETE FROM orders")
            cursor.execute("DELETE FROM positions")
            cursor.execute("DELETE FROM equity_curve")
            cursor.execute("DELETE FROM state")
            
            self.connection.commit()
            log.info("All data cleared from database")
            return True
            
        except Exception as e:
            log.error(f"Failed to clear database: {e}")
            self.connection.rollback()
            return False
    
    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            log.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Singleton instance for convenience
database = Database()


# Initialize database on module import
try:
    database.init_db()
except Exception as e:
    log.error(f"Failed to initialize database on import: {e}")
