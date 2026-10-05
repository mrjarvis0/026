"""Order Manager for T01 Smart Binance Intelligence v2.

This module provides comprehensive order management including:
- Order creation (market, limit, stop-loss, stop-limit, OCO)
- Order cancellation
- Order status tracking with background polling
- Order reconciliation with exchange
- Integration with SQLite database for persistence
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING

import ccxt.async_support as ccxt

if TYPE_CHECKING:
    from backend.data.database import Database

log = logging.getLogger("trading.order_manager")


# ============================================================================
# ENUMS
# ============================================================================

class OrderSide(Enum):
    """Order side: buy or sell."""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Supported order types."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    STOP_LIMIT = "stop_limit"
    OCO = "oco"


class OrderStatus(Enum):
    """Order status lifecycle."""
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


# ============================================================================
# ORDER DATACLASS
# ============================================================================

@dataclass
class Order:
    """Represents a trading order.
    
    Attributes:
        order_id: Unique internal order ID (UUID)
        exchange_order_id: Order ID from the exchange (if assigned)
        symbol: Trading pair (e.g., 'BTC/USDT')
        side: OrderSide.BUY or OrderSide.SELL
        order_type: OrderType (MARKET, LIMIT, STOP_LOSS, STOP_LIMIT, OCO)
        price: Price for limit/stop orders
        qty: Quantity to buy/sell
        filled: Amount already filled
        avg_fill_price: Average price of filled portion
        status: Current order status
        created_at: When the order was created
        updated_at: When the order was last updated
        bot_position_id: Link to the bot's position (if any)
        exchange_data: Raw exchange response data
        stop_price: Stop price for stop-loss/stop-limit orders
        stop_limit_price: Limit price for stop-limit orders
        oco_orders: List of child order IDs for OCO orders
        reduce_only: Whether this is a reduce-only order
        test: Whether this is a test order (paper trading)
    """
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    exchange_order_id: Optional[str] = None
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None
    qty: float = 0.0
    filled: float = 0.0
    avg_fill_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    bot_position_id: Optional[int] = None
    exchange_data: Dict[str, Any] = field(default_factory=dict)
    stop_price: Optional[float] = None
    stop_limit_price: Optional[float] = None
    oco_orders: List[str] = field(default_factory=list)
    reduce_only: bool = False
    test: bool = True

    def __post_init__(self):
        """Validate order fields after initialization."""
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if self.qty <= 0:
            raise ValueError("Quantity must be positive")
        if self.filled < 0:
            raise ValueError("Filled cannot be negative")
        if self.filled > self.qty:
            raise ValueError("Filled cannot exceed quantity")

    @property
    def remaining_qty(self) -> float:
        """Calculate remaining quantity to fill."""
        return self.qty - self.filled

    @property
    def is_terminal(self) -> bool:
        """Check if order is in a terminal state."""
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED
        ]

    @property
    def is_active(self) -> bool:
        """Check if order is still active (not terminal)."""
        return not self.is_terminal

    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary for storage."""
        data = asdict(self)
        data["side"] = self.side.value
        data["order_type"] = self.order_type.value
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Order":
        """Create order from dictionary."""
        data = data.copy()
        data["side"] = OrderSide(data.get("side", "buy"))
        data["order_type"] = OrderType(data.get("order_type", "market"))
        data["status"] = OrderStatus(data.get("status", "pending"))
        data["created_at"] = data.get("created_at", datetime.now(timezone.utc))
        data["updated_at"] = data.get("updated_at", datetime.now(timezone.utc))
        return cls(**data)

    def __repr__(self) -> str:
        return (
            f"Order(id={self.order_id[:8]}..., "
            f"symbol={self.symbol}, "
            f"side={self.side.value}, "
            f"type={self.order_type.value}, "
            f"qty={self.qty}, "
            f"filled={self.filled}, "
            f"status={self.status.value})"
        )


# ============================================================================
# ORDER MANAGER
# ============================================================================

class OrderManager:
    """Manages order lifecycle and synchronization with exchange.
    
    Features:
    - Create orders (market, limit, stop-loss, stop-limit, OCO)
    - Cancel orders
    - Track order status with background polling
    - Reconcile with exchange state
    - Persist orders to database
    
    The OrderManager maintains a local cache of orders and periodically
    synchronizes with the exchange to ensure state consistency.
    """

    def __init__(
        self,
        exchange: ccxt.Exchange,
        db: "Database",
        poll_interval: float = 5.0,
        test: bool = True
    ):
        """Initialize OrderManager.
        
        Args:
            exchange: CCXT exchange instance
            db: Database instance for persistence
            poll_interval: Seconds between order status polls
            test: Whether to use paper trading mode
        """
        self.exchange = exchange
        self.db = db
        self.poll_interval = poll_interval
        self.test = test
        
        # Local order cache: order_id -> Order
        self.orders: Dict[str, Order] = {}
        
        # Active polling tasks: order_id -> Task
        self._poll_tasks: Dict[str, asyncio.Task] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Background reconciliation task
        self._reconcile_task: Optional[asyncio.Task] = None
        self._reconcile_interval = 60.0  # Reconcile every 60 seconds
        
        log.info(f"OrderManager initialized (test={self.test})")

    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================

    async def start(self) -> None:
        """Start background tasks."""
        log.info("Starting OrderManager background tasks")
        
        # Load existing orders from database
        await self._load_orders_from_db()
        
        # Start background reconciliation
        self._reconcile_task = asyncio.create_task(
            self._background_reconcile()
        )
        
        log.info(f"OrderManager started with {len(self.orders)} existing orders")

    async def stop(self) -> None:
        """Stop background tasks."""
        log.info("Stopping OrderManager background tasks")
        
        # Cancel all polling tasks
        for order_id, task in self._poll_tasks.items():
            task.cancel()
        
        self._poll_tasks.clear()
        
        # Cancel reconciliation task
        if self._reconcile_task:
            self._reconcile_task.cancel()
            try:
                await self._reconcile_task
            except asyncio.CancelledError:
                pass
        
        log.info("OrderManager stopped")

    # ========================================================================
    # ORDER CREATION
    # ========================================================================

    async def create_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType = OrderType.MARKET,
        qty: float = 0.0,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        stop_limit_price: Optional[float] = None,
        reduce_only: bool = False,
        bot_position_id: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Order:
        """Create and submit a new order.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            side: OrderSide.BUY or OrderSide.SELL
            order_type: Type of order
            qty: Quantity to buy/sell
            price: Price for limit orders
            stop_price: Stop price for stop-loss/stop-limit
            stop_limit_price: Limit price for stop-limit
            reduce_only: Whether this is a reduce-only order
            bot_position_id: Link to bot's position
            params: Additional exchange-specific parameters
            
        Returns:
            Created Order object
            
        Raises:
            ValueError: If order parameters are invalid
            Exception: If order submission fails
        """
        async with self._lock:
            # Create order object
            order = Order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                qty=qty,
                price=price,
                stop_price=stop_price,
                stop_limit_price=stop_limit_price,
                reduce_only=reduce_only,
                bot_position_id=bot_position_id,
                test=self.test
            )
            
            # Save to local cache
            self.orders[order.order_id] = order
            
            # Save to database
            await self.db.create_order(
                order_id=order.order_id,
                symbol=symbol,
                side=side.value,
                order_type=order_type.value,
                price=price,
                qty=qty,
                status=OrderStatus.PENDING.value,
                bot_position_id=bot_position_id,
                stop_price=stop_price,
                stop_limit_price=stop_limit_price,
                reduce_only=reduce_only,
                test=self.test
            )
            
            log.info(f"Order created: {order}")
            
            # Submit to exchange (unless test mode)
            if not self.test:
                try:
                    exchange_order = await self._submit_to_exchange(
                        order, params=params
                    )
                    order.exchange_order_id = str(exchange_order["id"])
                    order.exchange_data = exchange_order
                    order.status = OrderStatus.from_exchange(exchange_order["status"])
                    order.updated_at = datetime.now(timezone.utc)
                    
                    # Update in database
                    await self.db.update_order(
                        order_id=order.order_id,
                        exchange_order_id=order.exchange_order_id,
                        status=order.status.value,
                        exchange_data=str(exchange_order)
                    )
                    
                    log.info(f"Order submitted to exchange: {order.order_id} -> {order.exchange_order_id}")
                    
                except Exception as e:
                    order.status = OrderStatus.REJECTED
                    order.updated_at = datetime.now(timezone.utc)
                    
                    await self.db.update_order(
                        order_id=order.order_id,
                        status=OrderStatus.REJECTED.value,
                        exchange_data=str({"error": str(e)})
                    )
                    
                    log.error(f"Order submission failed: {order.order_id}: {e}")
                    raise
            else:
                # In test mode, immediately mark as filled for backtesting
                order.status = OrderStatus.FILLED
                order.filled = qty
                order.avg_fill_price = price if price else 0.0
                order.updated_at = datetime.now(timezone.utc)
                
                await self.db.update_order(
                    order_id=order.order_id,
                    status=OrderStatus.FILLED.value,
                    filled=qty,
                    avg_fill_price=order.avg_fill_price
                )
                
                log.debug(f"Test mode: Order auto-filled: {order.order_id}")
            
            # Start background polling for non-terminal orders
            if order.is_active and not self.test:
                self._start_polling(order.order_id)
            
            return order

    async def _submit_to_exchange(
        self,
        order: Order,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Submit order to exchange via CCXT.
        
        Args:
            order: Order to submit
            params: Additional exchange-specific parameters
            
        Returns:
            Exchange order response
        """
        method = "create_order"
        
        # Handle OCO orders separately
        if order.order_type == OrderType.OCO:
            method = "create_oco_order"
            exchange_params = {
                "symbol": order.symbol,
                "side": order.side.value,
                "price": order.price,
                "stopPrice": order.stop_price,
                "stopLimitPrice": order.stop_limit_price,
                "amount": order.qty,
                "reduceOnly": order.reduce_only
            }
        else:
            exchange_params = {
                "symbol": order.symbol,
                "side": order.side.value,
                "type": order.order_type.value,
                "amount": order.qty
            }
            
            if order.price:
                exchange_params["price"] = order.price
            if order.stop_price:
                exchange_params["stopPrice"] = order.stop_price
            if order.stop_limit_price:
                exchange_params["stopLimitPrice"] = order.stop_limit_price
            if order.reduce_only:
                exchange_params["reduceOnly"] = True
        
        # Add custom params
        if params:
            exchange_params.update(params)
        
        # Submit to exchange
        exchange_fn = getattr(self.exchange, method)
        return await exchange_fn(**exchange_params)

    def _start_polling(self, order_id: str) -> None:
        """Start background polling for an order.
        
        Args:
            order_id: ID of order to poll
        """
        if order_id in self._poll_tasks:
            return  # Already polling
        
        async def poll_order():
            try:
                while True:
                    await asyncio.sleep(self.poll_interval)
                    
                    async with self._lock:
                        order = self.orders.get(order_id)
                        if not order or order.is_terminal:
                            break
                    
                    # Update order status
                    await self._update_order_status(order_id)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                log.error(f"Polling error for order {order_id}: {e}")
            finally:
                async with self._lock:
                    self._poll_tasks.pop(order_id, None)
        
        task = asyncio.create_task(poll_order())
        self._poll_tasks[order_id] = task
        log.debug(f"Started polling for order: {order_id}")

    # ========================================================================
    # ORDER CANCELLATION
    # ========================================================================

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order.
        
        Args:
            order_id: ID of order to cancel
            
        Returns:
            True if cancellation was successful
        """
        async with self._lock:
            order = self.orders.get(order_id)
            if not order:
                log.warning(f"Cannot cancel order: {order_id} not found")
                return False
            
            if order.is_terminal:
                log.warning(f"Cannot cancel order: {order_id} is already {order.status.value}")
                return False
            
            # Update local state
            order.status = OrderStatus.CANCELED
            order.updated_at = datetime.now(timezone.utc)
            
            # Stop polling
            self._stop_polling(order_id)
        
        # Cancel on exchange (unless test mode)
        if not self.test and order.exchange_order_id:
            try:
                await self.exchange.cancel_order(
                    order.exchange_order_id,
                    order.symbol
                )
                log.info(f"Order cancelled on exchange: {order_id} -> {order.exchange_order_id}")
            except Exception as e:
                log.error(f"Failed to cancel order on exchange: {order_id}: {e}")
                # Order might still be cancelled locally
                pass
        
        # Update in database
        await self.db.update_order(
            order_id=order_id,
            status=OrderStatus.CANCELED.value,
            updated_at=order.updated_at
        )
        
        log.info(f"Order cancelled: {order_id}")
        return True

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """Cancel all active orders (optionally filtered by symbol).
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            Number of orders cancelled
        """
        async with self._lock:
            order_ids = [
                oid for oid, order in self.orders.items()
                if order.is_active and (symbol is None or order.symbol == symbol)
            ]
        
        cancelled_count = 0
        for order_id in order_ids:
            if await self.cancel_order(order_id):
                cancelled_count += 1
        
        log.info(f"Cancelled {cancelled_count} orders" + (
            f" for {symbol}" if symbol else ""
        ))
        return cancelled_count

    def _stop_polling(self, order_id: str) -> None:
        """Stop background polling for an order.
        
        Args:
            order_id: ID of order to stop polling
        """
        if order_id in self._poll_tasks:
            self._poll_tasks[order_id].cancel()
            self._poll_tasks.pop(order_id, None)
            log.debug(f"Stopped polling for order: {order_id}")

    # ========================================================================
    # ORDER STATUS UPDATE
    # ========================================================================

    async def _update_order_status(self, order_id: str) -> None:
        """Update order status from exchange.
        
        Args:
            order_id: ID of order to update
        """
        async with self._lock:
            order = self.orders.get(order_id)
            if not order or order.is_terminal:
                return
            
            if not order.exchange_order_id:
                return
        
        try:
            # Fetch order from exchange
            exchange_order = await self.exchange.fetch_order(
                order.exchange_order_id,
                order.symbol
            )
            
            async with self._lock:
                order = self.orders.get(order_id)
                if not order:
                    return
                
                # Update order from exchange data
                order.filled = float(exchange_order.get("filled", 0))
                order.avg_fill_price = float(exchange_order.get("average", 0)) if exchange_order.get("average") else None
                order.status = OrderStatus.from_exchange(exchange_order.get("status", "unknown"))
                order.updated_at = datetime.now(timezone.utc)
                order.exchange_data = exchange_order
                
                # Update in database
                await self.db.update_order(
                    order_id=order_id,
                    filled=order.filled,
                    avg_fill_price=order.avg_fill_price,
                    status=order.status.value,
                    updated_at=order.updated_at,
                    exchange_data=str(exchange_order)
                )
                
                log.debug(f"Order status updated: {order_id} -> {order.status.value}")
                
                # Stop polling if terminal
                if order.is_terminal:
                    self._stop_polling(order_id)
                
        except Exception as e:
            log.warning(f"Failed to update order status: {order_id}: {e}")

    # ========================================================================
    # ORDER RETRIEVAL
    # ========================================================================

    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order by ID.
        
        Args:
            order_id: ID of order to retrieve
            
        Returns:
            Order object or None if not found
        """
        async with self._lock:
            return self.orders.get(order_id)

    async def get_orders(
        self,
        symbol: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        side: Optional[OrderSide] = None
    ) -> List[Order]:
        """Get orders filtered by criteria.
        
        Args:
            symbol: Optional symbol filter
            status: Optional status filter
            side: Optional side filter
            
        Returns:
            List of matching orders
        """
        async with self._lock:
            orders = list(self.orders.values())
        
        result = []
        for order in orders:
            if symbol and order.symbol != symbol:
                continue
            if status and order.status != status:
                continue
            if side and order.side != side:
                continue
            result.append(order)
        
        return result

    async def get_active_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all active (non-terminal) orders.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            List of active orders
        """
        return await self.get_orders(
            symbol=symbol,
            status=None,
            side=None
        )

    # ========================================================================
    # RECONCILIATION
    # ========================================================================

    async def reconcile(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Reconcile local orders with exchange state.
        
        This method:
        1. Fetches all open orders from the exchange
        2. Compares with local orders
        3. Updates local state to match exchange
        4. Detects and handles orphaned orders
        
        Args:
            symbol: Optional symbol to reconcile (default: all symbols)
            
        Returns:
            Reconciliation report
        """
        log.info(f"Starting reconciliation" + (f" for {symbol}" if symbol else ""))
        
        report = {
            "total_exchange_orders": 0,
            "total_local_orders": 0,
            "matched": 0,
            "created_locally": 0,
            "canceled_locally": 0,
            "orphaned_on_exchange": 0,
            "discrepancies": []
        }
        
        try:
            # Fetch all open orders from exchange
            exchange_orders = []
            if not self.test:
                try:
                    exchange_orders = await self.exchange.fetch_open_orders(
                        symbol if symbol else None
                    )
                except Exception as e:
                    log.error(f"Failed to fetch open orders from exchange: {e}")
                    return report
            
            report["total_exchange_orders"] = len(exchange_orders)
            
            # Get local orders
            async with self._lock:
                local_orders = list(self.orders.values())
            
            report["total_local_orders"] = len(local_orders)
            
            # Build lookup maps
            exchange_by_id = {str(o["id"]): o for o in exchange_orders}
            local_by_exchange_id = {
                o.exchange_order_id: o for o in local_orders
                if o.exchange_order_id
            }
            
            # Check for orders on exchange that we don't have locally
            for exchange_id, exchange_order in exchange_by_id.items():
                if exchange_id not in local_by_exchange_id:
                    # Orphaned order on exchange - create local record
                    order = Order.from_exchange(exchange_order)
                    order.exchange_order_id = exchange_id
                    order.test = self.test
                    
                    async with self._lock:
                        self.orders[order.order_id] = order
                    
                    await self.db.create_order(
                        order_id=order.order_id,
                        exchange_order_id=exchange_id,
                        symbol=order.symbol,
                        side=order.side.value,
                        order_type=order.order_type.value,
                        price=order.price,
                        qty=order.qty,
                        filled=order.filled,
                        avg_fill_price=order.avg_fill_price,
                        status=order.status.value,
                        exchange_data=str(exchange_order),
                        test=self.test
                    )
                    
                    report["orphaned_on_exchange"] += 1
                    report["discrepancies"].append({
                        "type": "orphaned_on_exchange",
                        "exchange_order_id": exchange_id,
                        "symbol": exchange_order.get("symbol"),
                        "action": "created_locally"
                    })
                    
                    log.warning(f"Found orphaned order on exchange: {exchange_id}")
            
            # Check for local orders not on exchange
            for order_id, local_order in local_orders:
                if local_order.exchange_order_id and local_order.exchange_order_id not in exchange_by_id:
                    # Order exists locally but not on exchange
                    if local_order.is_active:
                        # Mark as cancelled
                        local_order.status = OrderStatus.CANCELED
                        local_order.updated_at = datetime.now(timezone.utc)
                        
                        await self.db.update_order(
                            order_id=order_id,
                            status=OrderStatus.CANCELED.value,
                            updated_at=local_order.updated_at
                        )
                        
                        report["canceled_locally"] += 1
                        report["discrepancies"].append({
                            "type": "missing_on_exchange",
                            "order_id": order_id,
                            "exchange_order_id": local_order.exchange_order_id,
                            "symbol": local_order.symbol,
                            "action": "canceled_locally"
                        })
                        
                        log.warning(f"Order missing on exchange, marked as cancelled: {order_id}")
            
            # Update status for matched orders
            for exchange_id, exchange_order in exchange_by_id.items():
                if exchange_id in local_by_exchange_id:
                    local_order = local_by_exchange_id[exchange_id]
                    
                    # Check if status needs updating
                    exchange_status = OrderStatus.from_exchange(
                        exchange_order.get("status", "unknown")
                    )
                    
                    if local_order.status != exchange_status:
                        local_order.status = exchange_status
                        local_order.filled = float(exchange_order.get("filled", local_order.filled))
                        local_order.avg_fill_price = float(exchange_order.get("average", 0)) if exchange_order.get("average") else local_order.avg_fill_price
                        local_order.updated_at = datetime.now(timezone.utc)
                        local_order.exchange_data = exchange_order
                        
                        await self.db.update_order(
                            order_id=local_order.order_id,
                            status=exchange_status.value,
                            filled=local_order.filled,
                            avg_fill_price=local_order.avg_fill_price,
                            updated_at=local_order.updated_at,
                            exchange_data=str(exchange_order)
                        )
                        
                        report["discrepancies"].append({
                            "type": "status_mismatch",
                            "order_id": local_order.order_id,
                            "exchange_order_id": exchange_id,
                            "old_status": local_order.status.value,
                            "new_status": exchange_status.value
                        })
                        
                        log.info(f"Order status updated during reconciliation: {local_order.order_id}")
                    
                    report["matched"] += 1
            
        except Exception as e:
            log.error(f"Reconciliation error: {e}")
            report["error"] = str(e)
        
        log.info(f"Reconciliation complete: {report}")
        return report

    async def _background_reconcile(self) -> None:
        """Background reconciliation task."""
        try:
            while True:
                await asyncio.sleep(self._reconcile_interval)
                await self.reconcile()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"Background reconciliation failed: {e}")

    # ========================================================================
    # DATABASE INTEGRATION
    # ========================================================================

    async def _load_orders_from_db(self) -> None:
        """Load orders from database on startup."""
        try:
            db_orders = await self.db.get_all_orders()
            
            for db_order in db_orders:
                order = Order.from_dict(db_order)
                self.orders[order.order_id] = order
                
                # Start polling for active orders
                if order.is_active and not self.test:
                    self._start_polling(order.order_id)
            
            log.info(f"Loaded {len(self.orders)} orders from database")
        except Exception as e:
            log.error(f"Failed to load orders from database: {e}")

    async def clear_completed_orders(self, days: int = 30) -> int:
        """Clear completed orders older than specified days.
        
        Args:
            days: Number of days to keep completed orders
            
        Returns:
            Number of orders cleared
        """
        cleared = await self.db.clear_completed_orders(days)
        
        # Also clear from local cache
        async with self._lock:
            now = datetime.now(timezone.utc)
            to_remove = [
                oid for oid, order in self.orders.items()
                if order.is_terminal and 
                (now - order.updated_at).days > days
            ]
            for oid in to_remove:
                del self.orders[oid]
        
        log.info(f"Cleared {cleared} completed orders")
        return cleared


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def OrderStatus_from_exchange(status: str) -> OrderStatus:
    """Convert exchange status string to OrderStatus enum."""
    status_map = {
        "open": OrderStatus.PENDING,
        "pending": OrderStatus.PENDING,
        "partially_filled": OrderStatus.PARTIALLY_FILLED,
        "filled": OrderStatus.FILLED,
        "canceled": OrderStatus.CANCELED,
        "rejected": OrderStatus.REJECTED,
        "expired": OrderStatus.EXPIRED,
        "closed": OrderStatus.FILLED,
    }
    return status_map.get(status.lower(), OrderStatus.UNKNOWN)


# Monkey-patch OrderStatus for from_exchange
OrderStatus.from_exchange = staticmethod(OrderStatus_from_exchange)


def Order_from_exchange(exchange_order: Dict[str, Any]) -> Order:
    """Create Order from exchange order data."""
    return Order(
        exchange_order_id=str(exchange_order.get("id", "")),
        symbol=exchange_order.get("symbol", ""),
        side=OrderSide(exchange_order.get("side", "buy")),
        order_type=OrderType(exchange_order.get("type", "market")),
        price=float(exchange_order.get("price")) if exchange_order.get("price") else None,
        qty=float(exchange_order.get("amount", exchange_order.get("cost", 0))),
        filled=float(exchange_order.get("filled", 0)),
        avg_fill_price=float(exchange_order.get("average")) if exchange_order.get("average") else None,
        status=OrderStatus.from_exchange(exchange_order.get("status", "unknown")),
        exchange_data=exchange_order
    )


# Monkey-patch Order for from_exchange
Order.from_exchange = staticmethod(Order_from_exchange)
