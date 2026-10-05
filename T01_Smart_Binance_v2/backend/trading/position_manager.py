"""Position Manager for T01 Smart Binance Intelligence v2.

This module provides comprehensive position management including:
- Position entry and exit
- Stop-loss and take-profit management
- Trailing stop functionality
- Position risk management
- Integration with OrderManager for order execution
- Integration with database for persistence
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.trading.order_manager import Order, OrderManager, OrderSide, OrderType, OrderStatus
    from backend.data.database import Database

log = logging.getLogger("trading.position_manager")


# ============================================================================
# ENUMS
# ============================================================================

class PositionSide(Enum):
    """Position side: long or short."""
    LONG = "long"
    SHORT = "short"


class PositionStatus(Enum):
    """Position status lifecycle."""
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"


class ExitReason(Enum):
    """Reason for position exit."""
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"
    SIGNAL = "signal"
    MANUAL = "manual"
    LIQUIDATION = "liquidation"
    BACKTEST_END = "backtest_end"


# ============================================================================
# POSITION DATACLASS
# ============================================================================

@dataclass
class Position:
    """Represents a trading position.
    
    Attributes:
        position_id: Unique internal position ID
        symbol: Trading pair (e.g., 'BTC/USDT')
        side: PositionSide.LONG or PositionSide.SHORT
        entry_price: Price at which position was opened
        current_qty: Current quantity (can change with partial exits)
        entry_qty: Original quantity when position was opened
        entry_time: When the position was opened
        exit_time: When the position was closed
        stop_loss: Stop-loss price
        take_profit: Take-profit price
        trailing_stop: Trailing stop distance (price or percentage)
        trailing_stop_activated: Whether trailing stop is active
        highest_price: Highest price since entry (for long positions)
        lowest_price: Lowest price since entry (for short positions)
        status: Current position status
        entry_order_id: ID of the order that opened this position
        exit_order_id: ID of the order that closed this position
        mode: 'paper' or 'real'
        test: Whether this is a test position
        bot_id: ID of the bot that created this position
    """
    position_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    side: PositionSide = PositionSide.LONG
    entry_price: float = 0.0
    current_qty: float = 0.0
    entry_qty: float = 0.0
    entry_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    exit_time: Optional[datetime] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop: Optional[float] = None  # Can be absolute price or percentage
    trailing_stop_activated: bool = False
    highest_price: float = 0.0
    lowest_price: float = float('inf')
    status: PositionStatus = PositionStatus.OPEN
    entry_order_id: Optional[str] = None
    exit_order_id: Optional[str] = None
    mode: str = "paper"
    test: bool = True
    bot_id: Optional[str] = None

    def __post_init__(self):
        """Validate position fields after initialization."""
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if self.entry_price <= 0:
            raise ValueError("Entry price must be positive")
        if self.current_qty <= 0:
            raise ValueError("Current quantity must be positive")
        if self.entry_qty <= 0:
            self.entry_qty = self.current_qty

    @property
    def is_open(self) -> bool:
        """Check if position is open."""
        return self.status == PositionStatus.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if position is closed."""
        return self.status in [
            PositionStatus.CLOSED,
            PositionStatus.LIQUIDATED
        ]

    @property
    def is_active(self) -> bool:
        """Check if position is active (open or closing)."""
        return self.status in [
            PositionStatus.OPEN,
            PositionStatus.CLOSING
        ]

    @property
    def pnl(self, current_price: float) -> float:
        """Calculate current P&L at given price."""
        if self.side == PositionSide.LONG:
            return (current_price - self.entry_price) * self.current_qty
        else:
            return (self.entry_price - current_price) * self.current_qty

    @property
    def pnl_pct(self, current_price: float) -> float:
        """Calculate current P&L percentage at given price."""
        if self.entry_price == 0:
            return 0.0
        pnl = self.pnl(current_price)
        investment = self.entry_price * self.entry_qty
        return (pnl / investment) * 100 if investment > 0 else 0.0

    @property
    def unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L."""
        return self.pnl(current_price)

    @property
    def quantity_pct(self) -> float:
        """Calculate percentage of original quantity remaining."""
        if self.entry_qty == 0:
            return 0.0
        return (self.current_qty / self.entry_qty) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert position to dictionary for storage."""
        data = asdict(self)
        data["side"] = self.side.value
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Position":
        """Create position from dictionary."""
        data = data.copy()
        data["side"] = PositionSide(data.get("side", "long"))
        data["status"] = PositionStatus(data.get("status", "open"))
        data["entry_time"] = data.get("entry_time", datetime.now(timezone.utc))
        data["exit_time"] = data.get("exit_time")
        return cls(**data)

    def __repr__(self) -> str:
        return (
            f"Position(id={self.position_id[:8]}..., "
            f"symbol={self.symbol}, "
            f"side={self.side.value}, "
            f"entry={self.entry_price}, "
            f"qty={self.current_qty}, "
            f"status={self.status.value})"
        )


# ============================================================================
# POSITION MANAGER
# ============================================================================

class PositionManager:
    """Manages position lifecycle and risk management.
    
    Features:
    - Open and close positions
    - Stop-loss and take-profit management
    - Trailing stop functionality
    - Partial position management
    - Risk calculation and validation
    - Integration with OrderManager for order execution
    - Integration with database for persistence
    
    The PositionManager works closely with OrderManager to execute
    trades and maintain position state.
    """

    def __init__(
        self,
        order_manager: "OrderManager",
        db: "Database",
        risk_per_trade: float = 0.02,  # 2% risk per trade
        stop_loss_pct: float = 0.02,  # 2% stop loss
        take_profit_pct: float = 0.04,  # 4% take profit
        trail_pct: float = 0.015,  # 1.5% trailing stop
        use_atr_stops: bool = False,
        atr_period: int = 14,
        atr_stop_mult: float = 1.5,
        atr_tp_mult: float = 3.0,
        test: bool = True
    ):
        """Initialize PositionManager.
        
        Args:
            order_manager: OrderManager instance for order execution
            db: Database instance for persistence
            risk_per_trade: Maximum risk per trade (0.01 = 1%)
            stop_loss_pct: Default stop-loss percentage
            take_profit_pct: Default take-profit percentage
            trail_pct: Trailing stop percentage
            use_atr_stops: Whether to use ATR-based stops
            atr_period: ATR period for calculation
            atr_stop_mult: ATR multiplier for stop-loss
            atr_tp_mult: ATR multiplier for take-profit
            test: Whether to use paper trading mode
        """
        self.order_manager = order_manager
        self.db = db
        self.risk_per_trade = risk_per_trade
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trail_pct = trail_pct
        self.use_atr_stops = use_atr_stops
        self.atr_period = atr_period
        self.atr_stop_mult = atr_stop_mult
        self.atr_tp_mult = atr_tp_mult
        self.test = test
        
        # Local position cache: position_id -> Position
        self.positions: Dict[str, Position] = {}
        
        # Symbol position cache: symbol -> List[position_id]
        self._positions_by_symbol: Dict[str, List[str]] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Current prices cache for P&L calculation
        self._prices: Dict[str, float] = {}
        
        # Background monitoring task
        self._monitor_task: Optional[asyncio.Task] = None
        self._monitor_interval = 1.0  # Check positions every second
        
        log.info(f"PositionManager initialized (test={self.test})")

    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================

    async def start(self) -> None:
        """Start background tasks."""
        log.info("Starting PositionManager background tasks")
        
        # Load existing positions from database
        await self._load_positions_from_db()
        
        # Start background monitoring
        self._monitor_task = asyncio.create_task(
            self._background_monitor()
        )
        
        log.info(f"PositionManager started with {len(self.positions)} existing positions")

    async def stop(self) -> None:
        """Stop background tasks."""
        log.info("Stopping PositionManager background tasks")
        
        # Cancel monitoring task
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        log.info("PositionManager stopped")

    # ========================================================================
    # POSITION CREATION
    # ========================================================================

    async def open_position(
        self,
        symbol: str,
        side: PositionSide,
        entry_price: float,
        qty: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        trailing_stop: Optional[float] = None,
        reduce_only: bool = False,
        bot_id: Optional[str] = None,
        entry_order_id: Optional[str] = None
    ) -> Position:
        """Open a new position.
        
        Args:
            symbol: Trading pair
            side: PositionSide.LONG or PositionSide.SHORT
            entry_price: Price at which to open position
            qty: Quantity to open
            stop_loss: Stop-loss price (optional, calculated if None)
            take_profit: Take-profit price (optional, calculated if None)
            trailing_stop: Trailing stop distance (optional)
            reduce_only: Whether this is a reduce-only position
            bot_id: ID of the bot creating this position
            entry_order_id: ID of the order that triggered this position
            
        Returns:
            Created Position object
        """
        async with self._lock:
            # Create position object
            position = Position(
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                current_qty=qty,
                entry_qty=qty,
                stop_loss=stop_loss,
                take_profit=take_profit,
                trailing_stop=trailing_stop,
                mode="paper" if self.test else "real",
                test=self.test,
                bot_id=bot_id,
                entry_order_id=entry_order_id
            )
            
            # Initialize highest/lowest prices
            position.highest_price = entry_price
            position.lowest_price = entry_price
            
            # Calculate stops if not provided
            if stop_loss is None:
                position.stop_loss = self._calculate_stop_loss(position, entry_price)
            if take_profit is None:
                position.take_profit = self._calculate_take_profit(position, entry_price)
            if trailing_stop is None and self.trail_pct > 0:
                position.trailing_stop = self._calculate_trailing_stop(position)
            
            # Save to local cache
            self.positions[position.position_id] = position
            
            # Update symbol index
            if symbol not in self._positions_by_symbol:
                self._positions_by_symbol[symbol] = []
            self._positions_by_symbol[symbol].append(position.position_id)
            
            # Save to database
            await self._save_position(position)
            
            log.info(f"Position opened: {position}")
            
            return position

    def _calculate_stop_loss(self, position: Position, entry_price: float) -> float:
        """Calculate stop-loss price based on configuration."""
        if self.use_atr_stops:
            # ATR-based stop (placeholder - would need ATR value)
            return entry_price * (1 - self.atr_stop_mult * 0.01) if position.side == PositionSide.LONG else entry_price * (1 + self.atr_stop_mult * 0.01)
        else:
            # Percentage-based stop
            if position.side == PositionSide.LONG:
                return entry_price * (1 - self.stop_loss_pct)
            else:
                return entry_price * (1 + self.stop_loss_pct)

    def _calculate_take_profit(self, position: Position, entry_price: float) -> float:
        """Calculate take-profit price based on configuration."""
        if self.use_atr_stops:
            # ATR-based take profit
            return entry_price * (1 + self.atr_tp_mult * 0.01) if position.side == PositionSide.LONG else entry_price * (1 - self.atr_tp_mult * 0.01)
        else:
            # Percentage-based take profit
            if position.side == PositionSide.LONG:
                return entry_price * (1 + self.take_profit_pct)
            else:
                return entry_price * (1 - self.take_profit_pct)

    def _calculate_trailing_stop(self, position: Position) -> float:
        """Calculate trailing stop distance."""
        # For now, use percentage-based trailing stop
        return self.trail_pct

    async def _save_position(self, position: Position) -> None:
        """Save position to database."""
        await self.db.create_position(
            position_id=position.position_id,
            symbol=position.symbol,
            side=position.side.value,
            entry_price=position.entry_price,
            current_qty=position.current_qty,
            entry_qty=position.entry_qty,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            trailing_stop=position.trailing_stop,
            status=position.status.value,
            entry_order_id=position.entry_order_id,
            mode=position.mode,
            test=position.test,
            bot_id=position.bot_id
        )

    # ========================================================================
    # POSITION CLOSING
    # ========================================================================

    async def close_position(
        self,
        position_id: str,
        exit_price: float,
        exit_qty: Optional[float] = None,
        exit_reason: ExitReason = ExitReason.MANUAL,
        exit_order_id: Optional[str] = None
    ) -> Tuple[Position, float, float]:
        """Close a position (fully or partially).
        
        Args:
            position_id: ID of position to close
            exit_price: Price at which to close
            exit_qty: Quantity to close (None for full close)
            exit_reason: Reason for closing
            exit_order_id: ID of the order that closed this position
            
        Returns:
            Tuple of (position, pnl, pnl_pct)
        """
        async with self._lock:
            position = self.positions.get(position_id)
            if not position:
                raise ValueError(f"Position not found: {position_id}")
            
            if not position.is_active:
                raise ValueError(f"Position is not active: {position_id}")
            
            # Calculate quantity to close
            close_qty = exit_qty if exit_qty else position.current_qty
            
            # Calculate P&L
            pnl = position.pnl(exit_price)
            pnl_pct = position.pnl_pct(exit_price)
            
            # Update position
            position.current_qty -= close_qty
            position.exit_time = datetime.now(timezone.utc)
            position.exit_order_id = exit_order_id
            
            # Check if fully closed
            if position.current_qty <= 0:
                position.current_qty = 0
                position.status = PositionStatus.CLOSED
            else:
                position.status = PositionStatus.OPEN  # Still open with reduced quantity
            
            # Update in database
            await self.db.update_position(
                position_id=position_id,
                current_qty=position.current_qty,
                exit_time=position.exit_time,
                exit_order_id=position.exit_order_id,
                status=position.status.value
            )
            
            # If fully closed, remove from active tracking
            if position.is_closed:
                # Remove from symbol index
                if position.symbol in self._positions_by_symbol:
                    self._positions_by_symbol[position.symbol].remove(position_id)
                    if not self._positions_by_symbol[position.symbol]:
                        del self._positions_by_symbol[position.symbol]
            
            log.info(f"Position closed: {position_id}, P&L: {pnl:.4f} ({pnl_pct:.2f}%), Reason: {exit_reason.value}")
            
            return position, pnl, pnl_pct

    async def close_all_positions(
        self,
        symbol: Optional[str] = None,
        exit_reason: ExitReason = ExitReason.MANUAL
    ) -> List[Tuple[Position, float, float]]:
        """Close all positions (optionally filtered by symbol).
        
        Args:
            symbol: Optional symbol filter
            exit_reason: Reason for closing
            
        Returns:
            List of (position, pnl, pnl_pct) tuples
        """
        results = []
        
        async with self._lock:
            position_ids = [
                pid for pid, position in self.positions.items()
                if position.is_active and (symbol is None or position.symbol == symbol)
            ]
        
        for position_id in position_ids:
            position = self.positions[position_id]
            # Use current price or entry price as fallback
            current_price = self._prices.get(position.symbol, position.entry_price)
            result = await self.close_position(
                position_id=position_id,
                exit_price=current_price,
                exit_reason=exit_reason
            )
            results.append(result)
        
        log.info(f"Closed {len(results)} positions" + (
            f" for {symbol}" if symbol else ""
        ))
        return results

    # ========================================================================
    # POSITION UPDATES
    # ========================================================================

    async def update_position_price(
        self,
        position_id: str,
        current_price: float
    ) -> None:
        """Update position with current price for P&L tracking.
        
        Args:
            position_id: ID of position to update
            current_price: Current market price
        """
        async with self._lock:
            position = self.positions.get(position_id)
            if not position or not position.is_active:
                return
            
            # Update highest/lowest prices for trailing stop
            if position.side == PositionSide.LONG:
                if current_price > position.highest_price:
                    position.highest_price = current_price
                    # Activate trailing stop once price moves in our favor
                    if position.trailing_stop and not position.trailing_stop_activated:
                        position.trailing_stop_activated = True
            else:
                if current_price < position.lowest_price:
                    position.lowest_price = current_price
                    if position.trailing_stop and not position.trailing_stop_activated:
                        position.trailing_stop_activated = True
            
            # Update price cache
            self._prices[position.symbol] = current_price

    async def update_stop_loss(
        self,
        position_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        trailing_stop: Optional[float] = None
    ) -> None:
        """Update stop-loss, take-profit, or trailing stop for a position.
        
        Args:
            position_id: ID of position to update
            stop_loss: New stop-loss price (None to keep current)
            take_profit: New take-profit price (None to keep current)
            trailing_stop: New trailing stop distance (None to keep current)
        """
        async with self._lock:
            position = self.positions.get(position_id)
            if not position or not position.is_active:
                return
            
            if stop_loss is not None:
                position.stop_loss = stop_loss
            if take_profit is not None:
                position.take_profit = take_profit
            if trailing_stop is not None:
                position.trailing_stop = trailing_stop
            
            # Save to database
            await self.db.update_position(
                position_id=position_id,
                stop_loss=position.stop_loss,
                take_profit=position.take_profit,
                trailing_stop=position.trailing_stop
            )
            
            log.info(f"Updated stops for position: {position_id}")

    # ========================================================================
    # RISK MANAGEMENT
    # ========================================================================

    async def validate_position_risk(
        self,
        symbol: str,
        entry_price: float,
        qty: float,
        current_balance: float
    ) -> Tuple[bool, str]:
        """Validate that a new position is within risk limits.
        
        Args:
            symbol: Trading pair
            entry_price: Entry price
            qty: Quantity
            current_balance: Current account balance
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Calculate position value
        position_value = entry_price * qty
        
        # Check risk per trade
        if position_value > (current_balance * self.risk_per_trade):
            return False, f"Position value {position_value:.2f} exceeds risk limit {current_balance * self.risk_per_trade:.2f}"
        
        # Check maximum concurrent positions
        async with self._lock:
            active_positions = sum(
                1 for p in self.positions.values()
                if p.is_active
            )
        
        from backend import config
        max_positions = config.MAX_CONCURRENT_POSITIONS
        if active_positions >= max_positions:
            return False, f"Maximum concurrent positions ({max_positions}) reached"
        
        return True, ""

    async def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        risk_amount: Optional[float] = None,
        risk_pct: Optional[float] = None,
        current_balance: Optional[float] = None
    ) -> float:
        """Calculate optimal position size based on risk management.
        
        Args:
            symbol: Trading pair
            entry_price: Entry price
            stop_loss: Stop-loss price
            risk_amount: Amount to risk (optional)
            risk_pct: Percentage of balance to risk (optional)
            current_balance: Current account balance (optional)
            
        Returns:
            Optimal position size (quantity)
        """
        # Calculate risk per unit
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit == 0:
            return 0.0
        
        # Determine risk amount
        if risk_amount is not None:
            risk = risk_amount
        elif risk_pct is not None and current_balance is not None:
            risk = current_balance * risk_pct
        else:
            # Use default risk per trade
            if current_balance is None:
                current_balance = 1000.0  # Default for calculation
            risk = current_balance * self.risk_per_trade
        
        # Calculate quantity
        qty = risk / risk_per_unit
        
        return qty

    # ========================================================================
    # POSITION RETRIEVAL
    # ========================================================================

    async def get_position(self, position_id: str) -> Optional[Position]:
        """Get a position by ID.
        
        Args:
            position_id: ID of position to retrieve
            
        Returns:
            Position object or None if not found
        """
        async with self._lock:
            return self.positions.get(position_id)

    async def get_positions(
        self,
        symbol: Optional[str] = None,
        side: Optional[PositionSide] = None,
        status: Optional[PositionStatus] = None
    ) -> List[Position]:
        """Get positions filtered by criteria.
        
        Args:
            symbol: Optional symbol filter
            side: Optional side filter
            status: Optional status filter
            
        Returns:
            List of matching positions
        """
        async with self._lock:
            positions = list(self.positions.values())
        
        result = []
        for position in positions:
            if symbol and position.symbol != symbol:
                continue
            if side and position.side != side:
                continue
            if status and position.status != status:
                continue
            result.append(position)
        
        return result

    async def get_open_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get all open positions.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            List of open positions
        """
        return await self.get_positions(
            symbol=symbol,
            status=PositionStatus.OPEN
        )

    async def get_position_for_symbol(self, symbol: str) -> Optional[Position]:
        """Get the position for a specific symbol (returns first open position).
        
        Args:
            symbol: Symbol to find position for
            
        Returns:
            Position object or None if not found
        """
        positions = await self.get_open_positions(symbol)
        return positions[0] if positions else None

    # ========================================================================
    # MONITORING & CHECKS
    # ========================================================================

    async def check_stop_losses(self, current_prices: Dict[str, float]) -> List[str]:
        """Check if any positions have hit their stop-loss.
        
        Args:
            current_prices: Dict of symbol -> current price
            
        Returns:
            List of position IDs that hit stop-loss
        """
        triggered = []
        
        for symbol, price in current_prices.items():
            positions = await self.get_open_positions(symbol)
            
            for position in positions:
                if position.stop_loss is None:
                    continue
                
                if (position.side == PositionSide.LONG and price <= position.stop_loss) or \
                   (position.side == PositionSide.SHORT and price >= position.stop_loss):
                    triggered.append(position.position_id)
                    log.info(f"Stop-loss triggered for position: {position.position_id}")
        
        return triggered

    async def check_take_profits(self, current_prices: Dict[str, float]) -> List[str]:
        """Check if any positions have hit their take-profit.
        
        Args:
            current_prices: Dict of symbol -> current price
            
        Returns:
            List of position IDs that hit take-profit
        """
        triggered = []
        
        for symbol, price in current_prices.items():
            positions = await self.get_open_positions(symbol)
            
            for position in positions:
                if position.take_profit is None:
                    continue
                
                if (position.side == PositionSide.LONG and price >= position.take_profit) or \
                   (position.side == PositionSide.SHORT and price <= position.take_profit):
                    triggered.append(position.position_id)
                    log.info(f"Take-profit triggered for position: {position.position_id}")
        
        return triggered

    async def check_trailing_stops(self, current_prices: Dict[str, float]) -> List[str]:
        """Check if any positions have hit their trailing stop.
        
        Args:
            current_prices: Dict of symbol -> current price
            
        Returns:
            List of position IDs that hit trailing stop
        """
        triggered = []
        
        for symbol, price in current_prices.items():
            positions = await self.get_open_positions(symbol)
            
            for position in positions:
                if not position.trailing_stop or not position.trailing_stop_activated:
                    continue
                
                # Calculate trailing stop price
                if position.side == PositionSide.LONG:
                    # For long positions, trailing stop is below highest price
                    trail_price = position.highest_price * (1 - position.trailing_stop)
                    if price <= trail_price:
                        triggered.append(position.position_id)
                        log.info(f"Trailing stop triggered for position: {position.position_id}")
                else:
                    # For short positions, trailing stop is above lowest price
                    trail_price = position.lowest_price * (1 + position.trailing_stop)
                    if price >= trail_price:
                        triggered.append(position.position_id)
                        log.info(f"Trailing stop triggered for position: {position.position_id}")
        
        return triggered

    async def _background_monitor(self) -> None:
        """Background monitoring task for position checks."""
        try:
            while True:
                await asyncio.sleep(self._monitor_interval)
                
                # Get current prices (would integrate with data module)
                # For now, use cached prices
                if self._prices:
                    # Check stops
                    await self.check_stop_losses(self._prices)
                    await self.check_take_profits(self._prices)
                    await self.check_trailing_stops(self._prices)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"Background monitoring failed: {e}")

    # ========================================================================
    # DATABASE INTEGRATION
    # ========================================================================

    async def _load_positions_from_db(self) -> None:
        """Load positions from database on startup."""
        try:
            db_positions = await self.db.get_all_positions()
            
            for db_position in db_positions:
                position = Position.from_dict(db_position)
                self.positions[position.position_id] = position
                
                # Update symbol index
                if position.symbol not in self._positions_by_symbol:
                    self._positions_by_symbol[position.symbol] = []
                self._positions_by_symbol[position.symbol].append(position.position_id)
                
                # Initialize highest/lowest prices if not set
                if position.highest_price == 0:
                    position.highest_price = position.entry_price
                if position.lowest_price == float('inf'):
                    position.lowest_price = position.entry_price
            
            log.info(f"Loaded {len(self.positions)} positions from database")
        except Exception as e:
            log.error(f"Failed to load positions from database: {e}")

    async def sync_with_orders(self) -> None:
        """Synchronize position state with order state.
        
        This ensures positions reflect the actual state from completed orders.
        """
        try:
            # Get all orders from OrderManager
            orders = await self.order_manager.get_orders()
            
            for order in orders:
                if order.bot_position_id and order.is_terminal:
                    # Find the position
                    position = await self.get_position(str(order.bot_position_id))
                    if position:
                        # Check if this is an exit order
                        if position.exit_order_id == order.order_id:
                            # Position should be closed
                            if not position.is_closed:
                                position.status = PositionStatus.CLOSED
                                position.exit_time = order.updated_at
                                
                                await self.db.update_position(
                                    position_id=position.position_id,
                                    status=position.status.value,
                                    exit_time=position.exit_time
                                )
                                
                                log.info(f"Position marked as closed from order: {position.position_id}")
        except Exception as e:
            log.error(f"Failed to sync positions with orders: {e}")

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def get_total_pnl(self, current_prices: Optional[Dict[str, float]] = None) -> Tuple[float, float]:
        """Calculate total P&L across all open positions.
        
        Args:
            current_prices: Optional dict of symbol -> price (uses cached if not provided)
            
        Returns:
            Tuple of (total_pnl, total_pnl_pct)
        """
        prices = current_prices or self._prices
        
        total_pnl = 0.0
        total_investment = 0.0
        
        positions = await self.get_open_positions()
        
        for position in positions:
            price = prices.get(position.symbol, position.entry_price)
            total_pnl += position.pnl(price)
            total_investment += position.entry_price * position.entry_qty
        
        if total_investment == 0:
            return total_pnl, 0.0
        
        total_pnl_pct = (total_pnl / total_investment) * 100
        return total_pnl, total_pnl_pct

    async def get_position_summary(self) -> Dict[str, Any]:
        """Get a summary of all positions.
        
        Returns:
            Summary dictionary with position statistics
        """
        open_positions = await self.get_open_positions()
        closed_positions = await self.get_positions(status=PositionStatus.CLOSED)
        
        total_pnl = 0.0
        total_investment = 0.0
        
        for position in open_positions:
            price = self._prices.get(position.symbol, position.entry_price)
            total_pnl += position.pnl(price)
            total_investment += position.entry_price * position.entry_qty
        
        return {
            "total_positions": len(self.positions),
            "open_positions": len(open_positions),
            "closed_positions": len(closed_positions),
            "total_pnl": total_pnl,
            "total_pnl_pct": (total_pnl / total_investment * 100) if total_investment > 0 else 0.0,
            "total_investment": total_investment,
            "positions": [
                {
                    "position_id": p.position_id,
                    "symbol": p.symbol,
                    "side": p.side.value,
                    "entry_price": p.entry_price,
                    "current_qty": p.current_qty,
                    "status": p.status.value,
                    "pnl": p.pnl(self._prices.get(p.symbol, p.entry_price)),
                    "pnl_pct": p.pnl_pct(self._prices.get(p.symbol, p.entry_price))
                }
                for p in open_positions
            ]
        }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def PositionSide_from_order_side(side: "OrderSide") -> PositionSide:
    """Convert OrderSide to PositionSide."""
    return PositionSide.LONG if side == "OrderSide.BUY" else PositionSide.SHORT
