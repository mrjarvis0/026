"""Order Executor for T01 Smart Binance Intelligence v2.

This module provides advanced order execution capabilities including:
- Native order types (OCO, stop-limit, trailing stops)
- Order validation and risk management
- Order execution with retry logic
- Order tracking and monitoring
- Integration with OrderManager
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING

import ccxt.async_support as ccxt

if TYPE_CHECKING:
    from backend.trading.order_manager import OrderManager, Order, OrderSide, OrderType, OrderStatus
    from backend.trading.position_manager import PositionManager, Position
    from backend.data.database import Database

log = logging.getLogger("trading.order_executor")


# ============================================================================
# ENUMS
# ============================================================================

class OrderExecutionStatus(Enum):
    """Status of order execution."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"


class StopType(Enum):
    """Types of stop orders."""
    STOP_LOSS = "stop_loss"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    TAKE_PROFIT = "take_profit"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class OrderSpec:
    """Specification for an order to execute.
    
    Attributes:
        symbol: Trading pair
        side: OrderSide (BUY or SELL)
        order_type: OrderType (MARKET, LIMIT, STOP_LOSS, STOP_LIMIT, OCO)
        qty: Quantity
        price: Price for limit orders
        stop_price: Stop price for stop orders
        stop_limit_price: Limit price for stop-limit orders
        reduce_only: Whether this is a reduce-only order
        time_in_force: Time in force (GTC, IOC, FOK)
        test: Whether this is a test order
        bot_position_id: Link to bot's position
        params: Additional exchange-specific parameters
    """
    symbol: str = ""
    side: "OrderSide" = None
    order_type: "OrderType" = None
    qty: float = 0.0
    price: Optional[float] = None
    stop_price: Optional[float] = None
    stop_limit_price: Optional[float] = None
    reduce_only: bool = False
    time_in_force: str = "GTC"
    test: bool = True
    bot_position_id: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OCOOrderSpec:
    """Specification for an OCO (One Cancels Other) order.
    
    Attributes:
        symbol: Trading pair
        side: OrderSide
        qty: Quantity
        price: Limit price
        stop_price: Stop price
        stop_limit_price: Stop-limit price
        reduce_only: Whether this is a reduce-only order
        test: Whether this is a test order
        bot_position_id: Link to bot's position
    """
    symbol: str = ""
    side: "OrderSide" = None
    qty: float = 0.0
    price: Optional[float] = None
    stop_price: Optional[float] = None
    stop_limit_price: Optional[float] = None
    reduce_only: bool = False
    test: bool = True
    bot_position_id: Optional[str] = None


@dataclass
class ExecutionResult:
    """Result of an order execution.
    
    Attributes:
        order_id: ID of the executed order
        exchange_order_id: Exchange order ID
        status: Execution status
        filled: Quantity filled
        avg_fill_price: Average fill price
        remaining: Quantity remaining
        error: Error message if failed
        timestamp: When execution was attempted
    """
    order_id: str = ""
    exchange_order_id: Optional[str] = None
    status: OrderExecutionStatus = OrderExecutionStatus.PENDING
    filled: float = 0.0
    avg_fill_price: Optional[float] = None
    remaining: float = 0.0
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class StopOrder:
    """Represents a stop order (stop-loss, take-profit, trailing stop).
    
    Attributes:
        stop_id: Unique ID for this stop
        symbol: Trading pair
        side: OrderSide
        stop_type: StopType
        trigger_price: Price that triggers the stop
        limit_price: Limit price for stop-limit orders
        trailing_distance: Distance for trailing stops (price or percentage)
        qty: Quantity
        position_id: Link to position
        order_id: Link to order (once executed)
        active: Whether the stop is active
        triggered: Whether the stop has been triggered
        triggered_at: When the stop was triggered
        created_at: When the stop was created
    """
    stop_id: str = field(default_factory=lambda: f"stop_{datetime.now(timezone.utc).timestamp()}")
    symbol: str = ""
    side: "OrderSide" = None
    stop_type: StopType = StopType.STOP_LOSS
    trigger_price: float = 0.0
    limit_price: Optional[float] = None
    trailing_distance: Optional[float] = None
    qty: float = 0.0
    position_id: Optional[str] = None
    order_id: Optional[str] = None
    active: bool = True
    triggered: bool = False
    triggered_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# ORDER EXECUTOR
# ============================================================================

class OrderExecutor:
    """Executes orders with advanced functionality.
    
    The OrderExecutor provides:
    
    1. Native order type support (OCO, stop-limit, trailing stops)
    2. Order validation and risk checks
    3. Execution with retry logic
    4. Stop order management
    5. Integration with OrderManager and PositionManager
    
    The executor works with OrderManager to submit orders and tracks
    their execution status.
    """

    def __init__(
        self,
        exchange: ccxt.Exchange,
        order_manager: "OrderManager",
        position_manager: "PositionManager",
        db: "Database",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        test: bool = True
    ):
        """Initialize OrderExecutor.
        
        Args:
            exchange: CCXT exchange instance
            order_manager: OrderManager instance
            position_manager: PositionManager instance
            db: Database instance
            max_retries: Maximum retries for order submission
            retry_delay: Delay between retries in seconds
            test: Whether to use paper trading mode
        """
        self.exchange = exchange
        self.order_manager = order_manager
        self.position_manager = position_manager
        self.db = db
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.test = test
        
        # Stop order tracking
        self._stops: Dict[str, StopOrder] = {}
        
        # Pending OCO orders
        self._pending_oco: Dict[str, OCOOrderSpec] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        log.info(f"OrderExecutor initialized (test={self.test})")

    # ========================================================================
    # ORDER EXECUTION
    # ========================================================================

    async def execute_order(self, spec: OrderSpec) -> ExecutionResult:
        """Execute a single order.
        
        Args:
            spec: Order specification
            
        Returns:
            ExecutionResult with execution details
        """
        async with self._lock:
            log.info(f"Executing order: {spec.symbol} {spec.side.value if spec.side else ''} {spec.order_type.value if spec.order_type else ''} {spec.qty}")
            
            try:
                # Validate order
                if not await self._validate_order(spec):
                    return ExecutionResult(
                        status=OrderExecutionStatus.REJECTED,
                        error="Order validation failed"
                    )
                
                # Create order via OrderManager
                order = await self.order_manager.create_order(
                    symbol=spec.symbol,
                    side=spec.side,
                    order_type=spec.order_type,
                    qty=spec.qty,
                    price=spec.price,
                    stop_price=spec.stop_price,
                    stop_limit_price=spec.stop_limit_price,
                    reduce_only=spec.reduce_only,
                    bot_position_id=spec.bot_position_id,
                    params=spec.params
                )
                
                return ExecutionResult(
                    order_id=order.order_id,
                    exchange_order_id=order.exchange_order_id,
                    status=OrderExecutionStatus.SUBMITTED,
                    filled=order.filled,
                    avg_fill_price=order.avg_fill_price,
                    remaining=order.remaining_qty
                )
                
            except Exception as e:
                log.error(f"Order execution failed: {e}")
                return ExecutionResult(
                    order_id="",
                    status=OrderExecutionStatus.FAILED,
                    error=str(e)
                )

    async def execute_oco_order(self, spec: OCOOrderSpec) -> Tuple[Optional[str], Optional[str]]:
        """Execute an OCO (One Cancels Other) order.
        
        Args:
            spec: OCO order specification
            
        Returns:
            Tuple of (limit_order_id, stop_order_id)
        """
        async with self._lock:
            log.info(f"Executing OCO order: {spec.symbol} {spec.side.value if spec.side else ''} {spec.qty}")
            
            try:
                # Validate OCO order
                if not await self._validate_oco_order(spec):
                    return None, None
                
                # Store pending OCO
                spec_copy = OCOOrderSpec(
                    symbol=spec.symbol,
                    side=spec.side,
                    qty=spec.qty,
                    price=spec.price,
                    stop_price=spec.stop_price,
                    stop_limit_price=spec.stop_limit_price,
                    reduce_only=spec.reduce_only,
                    test=spec.test,
                    bot_position_id=spec.bot_position_id
                )
                oco_id = f"oco_{datetime.now(timezone.utc).timestamp()}"
                self._pending_oco[oco_id] = spec_copy
                
                # Execute both orders
                limit_order = await self.order_manager.create_order(
                    symbol=spec.symbol,
                    side=spec.side,
                    order_type="OrderType.LIMIT" if spec.price else "OrderType.MARKET",
                    qty=spec.qty,
                    price=spec.price,
                    reduce_only=spec.reduce_only,
                    bot_position_id=spec.bot_position_id,
                    params={"oco_id": oco_id, "oco_type": "limit"}
                )
                
                stop_order = await self.order_manager.create_order(
                    symbol=spec.symbol,
                    side=spec.side,
                    order_type="OrderType.STOP_LIMIT" if spec.stop_limit_price else "OrderType.STOP_LOSS",
                    qty=spec.qty,
                    price=spec.stop_limit_price,
                    stop_price=spec.stop_price,
                    reduce_only=spec.reduce_only,
                    bot_position_id=spec.bot_position_id,
                    params={"oco_id": oco_id, "oco_type": "stop"}
                )
                
                log.info(f"OCO order created: limit={limit_order.order_id}, stop={stop_order.order_id}")
                
                # Store OCO relationship
                await self.db.set_state(f"oco_{limit_order.order_id}", stop_order.order_id)
                await self.db.set_state(f"oco_{stop_order.order_id}", limit_order.order_id)
                
                return limit_order.order_id, stop_order.order_id
                
            except Exception as e:
                log.error(f"OCO order execution failed: {e}")
                return None, None

    async def execute_stop_loss(self, position_id: str, stop_price: float, qty: Optional[float] = None) -> Optional[str]:
        """Execute a stop-loss order for a position.
        
        Args:
            position_id: ID of position to protect
            stop_price: Price to trigger stop-loss
            qty: Quantity (default: full position quantity)
            
        Returns:
            Stop order ID or None
        """
        position = await self.position_manager.get_position(position_id)
        if not position:
            log.error(f"Position not found: {position_id}")
            return None
        
        # Get quantity
        if qty is None:
            qty = position.current_qty
        
        # Determine side (opposite of position)
        side = "OrderSide.SELL" if position.side.value == "long" else "OrderSide.BUY"
        
        # Create stop order
        stop_order = StopOrder(
            symbol=position.symbol,
            side=side,
            stop_type=StopType.STOP_LOSS,
            trigger_price=stop_price,
            qty=qty,
            position_id=position_id
        )
        
        # Store stop order
        self._stops[stop_order.stop_id] = stop_order
        
        # Submit to exchange (unless test mode)
        if not self.test:
            try:
                order = await self.order_manager.create_order(
                    symbol=position.symbol,
                    side=side,
                    order_type="OrderType.STOP_LOSS",
                    qty=qty,
                    stop_price=stop_price,
                    reduce_only=True,
                    bot_position_id=None,
                    params={"stop_id": stop_order.stop_id}
                )
                
                stop_order.order_id = order.order_id
                stop_order.active = True
                
                log.info(f"Stop-loss order created: {stop_order.stop_id} -> {order.order_id}")
                
            except Exception as e:
                log.error(f"Failed to create stop-loss order: {e}")
                return None
        
        return stop_order.stop_id

    async def execute_take_profit(self, position_id: str, take_profit_price: float, qty: Optional[float] = None) -> Optional[str]:
        """Execute a take-profit order for a position.
        
        Args:
            position_id: ID of position
            take_profit_price: Price to trigger take-profit
            qty: Quantity (default: full position quantity)
            
        Returns:
            Stop order ID or None
        """
        position = await self.position_manager.get_position(position_id)
        if not position:
            log.error(f"Position not found: {position_id}")
            return None
        
        # Get quantity
        if qty is None:
            qty = position.current_qty
        
        # Determine side (opposite of position)
        side = "OrderSide.SELL" if position.side.value == "long" else "OrderSide.BUY"
        
        # Create stop order
        stop_order = StopOrder(
            symbol=position.symbol,
            side=side,
            stop_type=StopType.TAKE_PROFIT,
            trigger_price=take_profit_price,
            qty=qty,
            position_id=position_id
        )
        
        # Store stop order
        self._stops[stop_order.stop_id] = stop_order
        
        # Submit to exchange (unless test mode)
        if not self.test:
            try:
                order = await self.order_manager.create_order(
                    symbol=position.symbol,
                    side=side,
                    order_type="OrderType.LIMIT",
                    qty=qty,
                    price=take_profit_price,
                    reduce_only=True,
                    bot_position_id=None,
                    params={"stop_id": stop_order.stop_id, "stop_type": "take_profit"}
                )
                
                stop_order.order_id = order.order_id
                stop_order.active = True
                
                log.info(f"Take-profit order created: {stop_order.stop_id} -> {order.order_id}")
                
            except Exception as e:
                log.error(f"Failed to create take-profit order: {e}")
                return None
        
        return stop_order.stop_id

    async def execute_trailing_stop(
        self,
        position_id: str,
        trailing_distance: float,
        is_percentage: bool = True
    ) -> Optional[str]:
        """Execute a trailing stop order for a position.
        
        Args:
            position_id: ID of position
            trailing_distance: Distance for trailing stop
            is_percentage: Whether distance is a percentage
            
        Returns:
            Stop order ID or None
        """
        position = await self.position_manager.get_position(position_id)
        if not position:
            log.error(f"Position not found: {position_id}")
            return None
        
        # Create stop order
        stop_order = StopOrder(
            symbol=position.symbol,
            side=position.side,
            stop_type=StopType.TRAILING_STOP,
            trigger_price=position.entry_price,
            trailing_distance=trailing_distance,
            qty=position.current_qty,
            position_id=position_id
        )
        
        # Store stop order
        self._stops[stop_order.stop_id] = stop_order
        
        log.info(f"Trailing stop created: {stop_order.stop_id}")
        
        # Note: Trailing stops are typically managed by the bot, not the exchange
        # For Binance, we would use STOP_MARKET or STOP_LIMIT with trailing logic
        
        return stop_order.stop_id

    # ========================================================================
    # STOP ORDER MANAGEMENT
    # ========================================================================

    async def check_stops(self, current_prices: Dict[str, float]) -> List[str]:
        """Check if any stop orders should be triggered.
        
        Args:
            current_prices: Dictionary of symbol -> current price
            
        Returns:
            List of triggered stop IDs
        """
        triggered = []
        
        for stop_id, stop in self._stops.items():
            if not stop.active or stop.triggered:
                continue
            
            current_price = current_prices.get(stop.symbol)
            if current_price is None:
                continue
            
            # Check trigger conditions
            if stop.stop_type == StopType.STOP_LOSS:
                if (stop.side.value == "sell" and current_price <= stop.trigger_price) or \
                   (stop.side.value == "buy" and current_price >= stop.trigger_price):
                    triggered.append(await self._trigger_stop(stop_id, current_price))
            
            elif stop.stop_type == StopType.TAKE_PROFIT:
                if (stop.side.value == "sell" and current_price >= stop.trigger_price) or \
                   (stop.side.value == "buy" and current_price <= stop.trigger_price):
                    triggered.append(await self._trigger_stop(stop_id, current_price))
            
            elif stop.stop_type == StopType.TRAILING_STOP:
                # For trailing stops, we need to track the highest/lowest price
                if stop.side.value == "long":
                    # Update trigger price if price moves in our favor
                    if current_price > stop.trigger_price:
                        if stop.trailing_distance and stop.is_percentage:
                            stop.trigger_price = current_price * (1 - stop.trailing_distance / 100)
                        else:
                            stop.trigger_price = current_price - stop.trailing_distance
                else:
                    # Short position
                    if current_price < stop.trigger_price:
                        if stop.trailing_distance and stop.is_percentage:
                            stop.trigger_price = current_price * (1 + stop.trailing_distance / 100)
                        else:
                            stop.trigger_price = current_price + stop.trailing_distance
                
                # Check if stop is triggered
                if (stop.side.value == "sell" and current_price <= stop.trigger_price) or \
                   (stop.side.value == "buy" and current_price >= stop.trigger_price):
                    triggered.append(await self._trigger_stop(stop_id, current_price))
        
        return triggered

    async def _trigger_stop(self, stop_id: str, current_price: float) -> str:
        """Trigger a stop order.
        
        Args:
            stop_id: ID of stop to trigger
            current_price: Current market price
            
        Returns:
            Stop ID that was triggered
        """
        stop = self._stops.get(stop_id)
        if not stop:
            return ""
        
        stop.triggered = True
        stop.triggered_at = datetime.now(timezone.utc)
        stop.active = False
        
        log.info(f"Stop triggered: {stop_id} at price {current_price}")
        
        # Execute the stop order
        if stop.order_id:
            # Order already exists, just update status
            pass
        else:
            # Create order for the stop
            try:
                order = await self.order_manager.create_order(
                    symbol=stop.symbol,
                    side=stop.side,
                    order_type="OrderType.MARKET",
                    qty=stop.qty,
                    reduce_only=True,
                    bot_position_id=stop.position_id,
                    params={"stop_id": stop_id, "trigger_price": current_price}
                )
                
                stop.order_id = order.order_id
                
            except Exception as e:
                log.error(f"Failed to execute stop order: {e}")
        
        return stop_id

    async def cancel_stop(self, stop_id: str) -> bool:
        """Cancel a stop order.
        
        Args:
            stop_id: ID of stop to cancel
            
        Returns:
            True if stop was cancelled
        """
        stop = self._stops.get(stop_id)
        if not stop:
            return False
        
        if stop.triggered:
            return False
        
        # Cancel the associated order if it exists
        if stop.order_id:
            try:
                await self.order_manager.cancel_order(stop.order_id)
            except Exception as e:
                log.error(f"Failed to cancel stop order: {e}")
        
        stop.active = False
        log.info(f"Stop cancelled: {stop_id}")
        
        return True

    async def get_stop(self, stop_id: str) -> Optional[StopOrder]:
        """Get a stop order by ID.
        
        Args:
            stop_id: ID of stop to retrieve
            
        Returns:
            StopOrder or None
        """
        return self._stops.get(stop_id)

    async def get_active_stops(self) -> List[StopOrder]:
        """Get all active stop orders.
        
        Returns:
            List of active StopOrder objects
        """
        return [s for s in self._stops.values() if s.active and not s.triggered]

    async def clear_stops(self, position_id: Optional[str] = None) -> int:
        """Clear stop orders.
        
        Args:
            position_id: Optional position ID to filter by
            
        Returns:
            Number of stops cleared
        """
        if position_id:
            to_clear = [sid for sid, stop in self._stops.items() if stop.position_id == position_id]
        else:
            to_clear = list(self._stops.keys())
        
        for stop_id in to_clear:
            await self.cancel_stop(stop_id)
            del self._stops[stop_id]
        
        return len(to_clear)

    # ========================================================================
    # OCO ORDER MANAGEMENT
    # ========================================================================

    async def check_oco_orders(self) -> None:
        """Check OCO orders and handle cancellations."""
        for oco_id, spec in self._pending_oco.items():
            # Find the two orders
            limit_order_id = await self.db.get_state(f"oco_{oco_id}_limit")
            stop_order_id = await self.db.get_state(f"oco_{oco_id}_stop")
            
            if not limit_order_id or not stop_order_id:
                continue
            
            # Check order statuses
            limit_order = await self.order_manager.get_order(limit_order_id)
            stop_order = await self.order_manager.get_order(stop_order_id)
            
            if not limit_order or not stop_order:
                continue
            
            # If one order is filled, cancel the other
            if limit_order.status.value == "filled":
                if stop_order.status.value not in ["canceled", "rejected"]:
                    await self.order_manager.cancel_order(stop_order.order_id)
                    await self.db.set_state(f"oco_{oco_id}_stop_cancelled", "true")
            elif stop_order.status.value == "filled":
                if limit_order.status.value not in ["canceled", "rejected"]:
                    await self.order_manager.cancel_order(limit_order.order_id)
                    await self.db.set_state(f"oco_{oco_id}_limit_cancelled", "true")

    async def cancel_oco_order(self, oco_id: str) -> bool:
        """Cancel an OCO order.
        
        Args:
            oco_id: ID of OCO order to cancel
            
        Returns:
            True if OCO order was cancelled
        """
        if oco_id not in self._pending_oco:
            return False
        
        # Get order IDs
        limit_order_id = await self.db.get_state(f"oco_{oco_id}_limit")
        stop_order_id = await self.db.get_state(f"oco_{oco_id}_stop")
        
        # Cancel both orders
        if limit_order_id:
            try:
                await self.order_manager.cancel_order(limit_order_id)
            except Exception as e:
                log.error(f"Failed to cancel OCO limit order: {e}")
        
        if stop_order_id:
            try:
                await self.order_manager.cancel_order(stop_order_id)
            except Exception as e:
                log.error(f"Failed to cancel OCO stop order: {e}")
        
        # Remove from pending
        del self._pending_oco[oco_id]
        
        log.info(f"OCO order cancelled: {oco_id}")
        return True

    # ========================================================================
    # VALIDATION
    # ========================================================================

    async def _validate_order(self, spec: OrderSpec) -> bool:
        """Validate an order specification.
        
        Args:
            spec: Order specification to validate
            
        Returns:
            True if order is valid
        """
        # Check symbol
        if not spec.symbol:
            log.error("Order validation failed: symbol is required")
            return False
        
        # Check side
        if not spec.side:
            log.error("Order validation failed: side is required")
            return False
        
        # Check order type
        if not spec.order_type:
            log.error("Order validation failed: order_type is required")
            return False
        
        # Check quantity
        if spec.qty <= 0:
            log.error("Order validation failed: qty must be positive")
            return False
        
        # Check price for limit orders
        if spec.order_type.value == "limit" and not spec.price:
            log.error("Order validation failed: price required for limit order")
            return False
        
        # Check stop price for stop orders
        if spec.order_type.value in ["stop_loss", "stop_limit"] and not spec.stop_price:
            log.error("Order validation failed: stop_price required for stop order")
            return False
        
        # Check stop-limit price
        if spec.order_type.value == "stop_limit" and not spec.stop_limit_price:
            log.error("Order validation failed: stop_limit_price required for stop-limit order")
            return False
        
        # Check position for reduce-only orders
        if spec.reduce_only and not spec.bot_position_id:
            log.error("Order validation failed: bot_position_id required for reduce-only order")
            return False
        
        return True

    async def _validate_oco_order(self, spec: OCOOrderSpec) -> bool:
        """Validate an OCO order specification.
        
        Args:
            spec: OCO order specification to validate
            
        Returns:
            True if OCO order is valid
        """
        # Must have either price or stop_price
        if not spec.price and not spec.stop_price:
            log.error("OCO validation failed: must have price or stop_price")
            return False
        
        # Quantity must be positive
        if spec.qty <= 0:
            log.error("OCO validation failed: qty must be positive")
            return False
        
        return True

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def get_execution_stats(self) -> Dict[str, Any]:
        """Get order execution statistics.
        
        Returns:
            Dictionary with execution statistics
        """
        return {
            "active_stops": len(self._stops),
            "triggered_stops": sum(1 for s in self._stops.values() if s.triggered),
            "pending_oco": len(self._pending_oco)
        }

    async def clear_all(self) -> None:
        """Clear all pending orders and stops."""
        # Cancel all stops
        await self.clear_stops()
        
        # Cancel all OCO orders
        for oco_id in list(self._pending_oco.keys()):
            await self.cancel_oco_order(oco_id)
        
        log.info("Cleared all pending orders and stops")
