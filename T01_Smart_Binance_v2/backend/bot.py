"""Main Trading Bot for T01 Smart Binance Intelligence v2.

This module provides the core trading bot functionality, integrating:
- Exchange connectivity via CCXT
- Order management
- Position management
- State reconciliation
- State persistence
- Signal generation
- Risk management

The bot can operate in both paper trading and real trading modes.
"""

import asyncio
import logging
import signal
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Callable, TYPE_CHECKING

import ccxt.async_support as ccxt

from backend import config
from backend.data.database import Database
from backend.data.collector import DataCollector
from backend.trading.order_manager import OrderManager, Order, OrderSide, OrderType, OrderStatus
from backend.trading.position_manager import PositionManager, Position, PositionSide, PositionStatus, ExitReason
from backend.trading.reconciliation import ReconciliationEngine
from backend.trading.state_persistence import StatePersistence

if TYPE_CHECKING:
    from backend.analysis.indicators import TechnicalIndicators
    from backend.analysis.signals import SignalGenerator

log = logging.getLogger("bot")


# ============================================================================
# ENUMS
# ============================================================================

class BotStatus(Enum):
    """Current status of the bot."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


class BotMode(Enum):
    """Trading mode of the bot."""
    PAPER = "paper"
    REAL = "real"


class TradeDirection(Enum):
    """Trade direction signal."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class BotConfig:
    """Configuration for the trading bot.
    
    Attributes:
        bot_id: Unique ID for this bot instance
        name: Name of the bot
        symbols: List of symbols to trade
        timeframes: List of timeframes to analyze
        mode: BotMode (PAPER or REAL)
        initial_balance: Initial balance for paper trading
        risk_per_trade: Risk per trade as percentage
        stop_loss_pct: Stop-loss percentage
        take_profit_pct: Take-profit percentage
        trail_pct: Trailing stop percentage
        use_atr_stops: Whether to use ATR-based stops
        max_concurrent_positions: Maximum number of concurrent positions
        daily_loss_limit_pct: Daily loss limit percentage
        enabled: Whether the bot is enabled
        strategy: Strategy to use
    """
    bot_id: str = "t01_bot"
    name: str = "T01 Smart Binance Intelligence"
    symbols: List[str] = field(default_factory=lambda: ["BTC/USDT"])
    timeframes: List[str] = field(default_factory=lambda: ["1h"])
    mode: BotMode = BotMode.PAPER
    initial_balance: float = 1000.0
    risk_per_trade: float = 0.02
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04
    trail_pct: float = 0.015
    use_atr_stops: bool = False
    max_concurrent_positions: int = 3
    daily_loss_limit_pct: float = 0.03
    enabled: bool = True
    strategy: str = "scalping"

    @classmethod
    def from_config(cls) -> "BotConfig":
        """Create BotConfig from global config."""
        return cls(
            bot_id=config.BOT_ID if hasattr(config, 'BOT_ID') else "t01_bot",
            name=config.BOT_NAME if hasattr(config, 'BOT_NAME') else "T01 Smart Binance Intelligence",
            symbols=config.TRADE_SYMBOLS if hasattr(config, 'TRADE_SYMBOLS') else ["BTC/USDT"],
            timeframes=config.TIMEFRAMES if hasattr(config, 'TIMEFRAMES') else ["1h"],
            mode=BotMode.PAPER if config.PAPER_TRADING else BotMode.REAL,
            initial_balance=config.PAPER_START_BALANCE,
            risk_per_trade=config.RISK_PER_TRADE_PAPER if config.PAPER_TRADING else config.RISK_PER_TRADE_REAL,
            stop_loss_pct=config.STOP_LOSS_PCT,
            take_profit_pct=config.TAKE_PROFIT_PCT,
            trail_pct=config.TRAIL_PCT,
            use_atr_stops=config.USE_ATR_STOPS,
            max_concurrent_positions=config.MAX_CONCURRENT_POSITIONS,
            daily_loss_limit_pct=config.DAILY_LOSS_LIMIT_PCT,
            enabled=True,
            strategy="scalping"
        )


@dataclass
class TradeSignal:
    """Represents a trading signal.
    
    Attributes:
        symbol: Trading pair
        timeframe: Timeframe of the signal
        direction: TradeDirection (BUY, SELL, HOLD, CLOSE)
        strength: Signal strength (0-100)
        confidence: Confidence level (0-100)
        timestamp: When the signal was generated
        indicators: Dictionary of indicator values
        strategy: Strategy that generated the signal
        position_id: Optional position ID this signal relates to
    """
    symbol: str = ""
    timeframe: str = ""
    direction: TradeDirection = TradeDirection.HOLD
    strength: float = 0.0
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    indicators: Dict[str, float] = field(default_factory=dict)
    strategy: str = ""
    position_id: Optional[str] = None


@dataclass
class BotStats:
    """Statistics for the bot.
    
    Attributes:
        total_trades: Total number of trades executed
        winning_trades: Number of winning trades
        losing_trades: Number of losing trades
        win_rate: Win rate percentage
        total_pnl: Total P&L
        total_pnl_pct: Total P&L percentage
        current_streak: Current winning/losing streak
        max_drawdown: Maximum drawdown
        sharpe_ratio: Sharpe ratio
        sortino_ratio: Sortino ratio
        average_win: Average winning trade
        average_loss: Average losing trade
        profit_factor: Profit factor
        current_positions: Number of current open positions
        active_orders: Number of active orders
        last_trade_time: Time of last trade
        uptime: Bot uptime
    """
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    current_streak: int = 0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    profit_factor: float = 0.0
    current_positions: int = 0
    active_orders: int = 0
    last_trade_time: Optional[datetime] = None
    uptime: timedelta = timedelta(0)


# ============================================================================
# TRADING BOT
# ============================================================================

class TradingBot:
    """Main trading bot class.
    
    The TradingBot integrates all components to provide a complete trading system:
    
    - Exchange connectivity via CCXT
    - Data collection and caching
    - Order and position management
    - State reconciliation and persistence
    - Signal generation and execution
    - Risk management
    - Performance tracking
    
    The bot can run in paper trading mode (simulated) or real trading mode.
    """

    def __init__(
        self,
        config: BotConfig = None,
        exchange: Optional[ccxt.Exchange] = None,
        db: Optional[Database] = None,
        data_collector: Optional[DataCollector] = None
    ):
        """Initialize TradingBot.
        
        Args:
            config: Bot configuration
            exchange: CCXT exchange instance (created if None)
            db: Database instance (created if None)
            data_collector: DataCollector instance (created if None)
        """
        # Configuration
        self.config = config or BotConfig.from_config()
        
        # Status
        self._status = BotStatus.STOPPED
        self._start_time: Optional[datetime] = None
        self._shutdown_flag = False
        
        # Components
        self.exchange = exchange
        self.db = db or Database()
        self.data_collector = data_collector or DataCollector(self.exchange)
        
        # Initialize exchange if not provided
        if not self.exchange:
            self.exchange = self._create_exchange()
        
        # Trading components
        self.order_manager: Optional[OrderManager] = None
        self.position_manager: Optional[PositionManager] = None
        self.reconciliation_engine: Optional[ReconciliationEngine] = None
        self.state_persistence: Optional[StatePersistence] = None
        
        # Signal generator (would be imported from analysis module)
        self.signal_generator: Optional[Any] = None
        
        # Statistics
        self.stats = BotStats()
        self._daily_pnl = 0.0
        self._daily_loss = 0.0
        
        # Callbacks for signal handling
        self._signal_callbacks: List[Callable[[TradeSignal], None]] = []
        self._trade_callbacks: List[Callable[[Position, float, float], None]] = []
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        log.info(f"TradingBot initialized: {self.config.name} (mode={self.config.mode.value})")

    def _create_exchange(self) -> ccxt.Exchange:
        """Create and configure CCXT exchange instance.
        
        Returns:
            Configured exchange instance
        """
        # Use Binance by default
        exchange_class = getattr(ccxt.async_support, 'binance')
        
        exchange = exchange_class({
            'apiKey': config.BINANCE_API_KEY,
            'secret': config.BINANCE_API_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future' if config.FUTURES_TRADING else 'spot'
            }
        })
        
        # Use testnet if configured
        if config.BINANCE_TESTNET:
            exchange.set_sandbox_mode(True)
        
        log.info(f"Exchange created: {exchange.id} (testnet={config.BINANCE_TESTNET})")
        return exchange

    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================

    async def start(self) -> None:
        """Start the trading bot."""
        if self._status != BotStatus.STOPPED:
            log.warning(f"Bot is already {self._status.value}, cannot start")
            return
        
        self._status = BotStatus.STARTING
        self._start_time = datetime.now(timezone.utc)
        self._shutdown_flag = False
        
        log.info("Starting TradingBot...")
        
        try:
            # Initialize components
            await self._initialize_components()
            
            # Load state
            await self._load_state()
            
            # Start components
            await self._start_components()
            
            # Setup signal handlers
            self._setup_signal_handlers()
            
            # Start main trading loop
            self._main_task = asyncio.create_task(self._main_loop())
            
            self._status = BotStatus.RUNNING
            log.info("TradingBot started successfully")
            
        except Exception as e:
            self._status = BotStatus.ERROR
            log.error(f"Failed to start TradingBot: {e}")
            raise

    async def stop(self) -> None:
        """Stop the trading bot gracefully."""
        if self._status == BotStatus.STOPPED:
            return
        
        self._status = BotStatus.STOPPING
        self._shutdown_flag = True
        
        log.info("Stopping TradingBot...")
        
        try:
            # Cancel main loop
            if hasattr(self, '_main_task'):
                self._main_task.cancel()
                try:
                    await self._main_task
                except asyncio.CancelledError:
                    pass
            
            # Stop components
            await self._stop_components()
            
            # Save state
            await self._save_state()
            
            self._status = BotStatus.STOPPED
            log.info("TradingBot stopped")
            
        except Exception as e:
            self._status = BotStatus.ERROR
            log.error(f"Error stopping TradingBot: {e}")

    async def pause(self) -> None:
        """Pause the trading bot."""
        if self._status != BotStatus.RUNNING:
            return
        
        self._status = BotStatus.PAUSED
        log.info("TradingBot paused")

    async def resume(self) -> None:
        """Resume the trading bot."""
        if self._status != BotStatus.PAUSED:
            return
        
        self._status = BotStatus.RUNNING
        log.info("TradingBot resumed")

    # ========================================================================
    # COMPONENT INITIALIZATION
    # ========================================================================

    async def _initialize_components(self) -> None:
        """Initialize all bot components."""
        log.info("Initializing components...")
        
        # Initialize database
        await self.db.initialize()
        
        # Create OrderManager
        self.order_manager = OrderManager(
            exchange=self.exchange,
            db=self.db,
            test=(self.config.mode == BotMode.PAPER)
        )
        
        # Create PositionManager
        self.position_manager = PositionManager(
            order_manager=self.order_manager,
            db=self.db,
            risk_per_trade=self.config.risk_per_trade,
            stop_loss_pct=self.config.stop_loss_pct,
            take_profit_pct=self.config.take_profit_pct,
            trail_pct=self.config.trail_pct,
            use_atr_stops=self.config.use_atr_stops,
            test=(self.config.mode == BotMode.PAPER)
        )
        
        # Create ReconciliationEngine
        self.reconciliation_engine = ReconciliationEngine(
            exchange=self.exchange,
            order_manager=self.order_manager,
            position_manager=self.position_manager,
            db=self.db,
            test=(self.config.mode == BotMode.PAPER)
        )
        
        # Create StatePersistence
        self.state_persistence = StatePersistence(
            db=self.db,
            order_manager=self.order_manager,
            position_manager=self.position_manager
        )
        
        # Initialize signal generator (placeholder - would be imported)
        # self.signal_generator = SignalGenerator(
        #     data_collector=self.data_collector,
        #     config=self.config
        # )
        
        log.info("Components initialized")

    async def _start_components(self) -> None:
        """Start all bot components."""
        log.info("Starting components...")
        
        # Start OrderManager
        await self.order_manager.start()
        
        # Start PositionManager
        await self.position_manager.start()
        
        # Start ReconciliationEngine
        await self.reconciliation_engine.start()
        
        # Start StatePersistence
        await self.state_persistence.start()
        
        log.info("Components started")

    async def _stop_components(self) -> None:
        """Stop all bot components."""
        log.info("Stopping components...")
        
        # Stop components in reverse order
        if self.state_persistence:
            await self.state_persistence.stop()
        if self.reconciliation_engine:
            await self.reconciliation_engine.stop()
        if self.position_manager:
            await self.position_manager.stop()
        if self.order_manager:
            await self.order_manager.stop()
        
        log.info("Components stopped")

    # ========================================================================
    # STATE MANAGEMENT
    # ========================================================================

    async def _load_state(self) -> None:
        """Load bot state from persistence."""
        log.info("Loading state...")
        
        try:
            # Load state from database
            await self.order_manager._load_orders_from_db()
            await self.position_manager._load_positions_from_db()
            await self.reconciliation_engine.load_state()
            await self.state_persistence._load_state_info()
            
            # Check if recovery is needed
            if self.state_persistence._status.value == "corrupt":
                log.warning("State is marked as corrupt, attempting recovery")
                await self.state_persistence.recover_from_crash()
            
            log.info("State loaded")
        except Exception as e:
            log.error(f"Failed to load state: {e}")

    async def _save_state(self) -> None:
        """Save bot state to persistence."""
        log.info("Saving state...")
        
        try:
            await self.state_persistence.save_state()
            log.info("State saved")
        except Exception as e:
            log.error(f"Failed to save state: {e}")

    # ========================================================================
    # MAIN TRADING LOOP
    # ========================================================================

    async def _main_loop(self) -> None:
        """Main trading loop."""
        log.info("Main trading loop started")
        
        # Initial data collection
        await self._collect_initial_data()
        
        # Main loop
        while not self._shutdown_flag:
            try:
                # Check if paused
                if self._status == BotStatus.PAUSED:
                    await asyncio.sleep(1)
                    continue
                
                # Check daily loss limit
                if await self._check_daily_loss_limit():
                    log.warning("Daily loss limit reached, stopping trading")
                    await self.pause()
                    continue
                
                # Update market data
                await self._update_market_data()
                
                # Generate and process signals
                await self._generate_and_process_signals()
                
                # Check for stop-loss and take-profit hits
                await self._check_position_stops()
                
                # Update statistics
                await self._update_statistics()
                
                # Sleep for a short interval
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in main loop: {e}")
                await asyncio.sleep(5)
        
        log.info("Main trading loop stopped")

    async def _collect_initial_data(self) -> None:
        """Collect initial market data for all symbols."""
        log.info("Collecting initial market data...")
        
        for symbol in self.config.symbols:
            for timeframe in self.config.timeframes:
                try:
                    # Fetch OHLCV data
                    await self.data_collector.fetch_ohlcv(
                        symbol=symbol,
                        timeframe=timeframe,
                        limit=100
                    )
                    
                    # Fetch ticker data
                    await self.data_collector.fetch_ticker(symbol)
                except Exception as e:
                    log.error(f"Failed to fetch initial data for {symbol}/{timeframe}: {e}")
        
        log.info("Initial market data collected")

    async def _update_market_data(self) -> None:
        """Update market data for all symbols."""
        try:
            for symbol in self.config.symbols:
                # Update ticker data
                ticker = await self.data_collector.fetch_ticker(symbol)
                if ticker:
                    current_price = float(ticker.get("last", ticker.get("close", 0)))
                    
                    # Update position prices
                    await self.position_manager.update_position_price(
                        position_id="",  # Would need position ID
                        current_price=current_price
                    )
                    
                    # Update price cache in position manager
                    self.position_manager._prices[symbol] = current_price
        except Exception as e:
            log.error(f"Failed to update market data: {e}")

    async def _generate_and_process_signals(self) -> None:
        """Generate trading signals and process them."""
        # Placeholder for signal generation
        # In a real implementation, this would use the signal generator
        
        # For now, we'll just check for basic conditions
        for symbol in self.config.symbols:
            try:
                # Get current position for this symbol
                position = await self.position_manager.get_position_for_symbol(symbol)
                
                # Get current price
                ticker = await self.data_collector.fetch_ticker(symbol)
                if not ticker:
                    continue
                
                current_price = float(ticker.get("last", ticker.get("close", 0)))
                
                # Simple example: Check if we should open a position
                if not position and self._can_open_position():
                    # Check for buy signal (placeholder logic)
                    signal = await self._generate_signal(symbol, ticker)
                    if signal and signal.direction == TradeDirection.BUY:
                        await self._execute_buy_signal(signal, current_price)
                elif position:
                    # Check for sell signal (placeholder logic)
                    signal = await self._generate_signal(symbol, ticker)
                    if signal and signal.direction == TradeDirection.SELL:
                        await self._execute_sell_signal(signal, position, current_price)
                
            except Exception as e:
                log.error(f"Failed to process signals for {symbol}: {e}")

    async def _generate_signal(
        self,
        symbol: str,
        ticker: Dict[str, Any]
    ) -> Optional[TradeSignal]:
        """Generate a trading signal (placeholder).
        
        Args:
            symbol: Trading pair
            ticker: Current ticker data
            
        Returns:
            TradeSignal or None
        """
        # This is a placeholder implementation
        # In a real implementation, this would use the signal generator
        
        # Simple example: Random signal for demonstration
        import random
        
        # Only generate signals occasionally
        if random.random() > 0.1:
            return None
        
        # Random direction
        direction = random.choice([TradeDirection.BUY, TradeDirection.SELL, TradeDirection.HOLD])
        
        if direction == TradeDirection.HOLD:
            return None
        
        return TradeSignal(
            symbol=symbol,
            timeframe="1h",
            direction=direction,
            strength=random.uniform(50, 100),
            confidence=random.uniform(50, 100),
            indicators={"rsi": random.uniform(0, 100)},
            strategy="demo"
        )

    async def _execute_buy_signal(
        self,
        signal: TradeSignal,
        current_price: float
    ) -> Optional[Position]:
        """Execute a buy signal.
        
        Args:
            signal: Buy signal to execute
            current_price: Current market price
            
        Returns:
            Created Position or None
        """
        if self.config.mode == BotMode.PAPER:
            test = True
        else:
            test = False
        
        try:
            # Calculate position size based on risk
            balance = self.config.initial_balance
            position_size = await self.position_manager.calculate_position_size(
                symbol=signal.symbol,
                entry_price=current_price,
                stop_loss=current_price * (1 - self.config.stop_loss_pct),
                risk_pct=self.config.risk_per_trade,
                current_balance=balance
            )
            
            if position_size <= 0:
                log.warning(f"Position size is zero or negative for {signal.symbol}")
                return None
            
            # Create order
            order = await self.order_manager.create_order(
                symbol=signal.symbol,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                qty=position_size,
                test=test
            )
            
            # Create position
            position = await self.position_manager.open_position(
                symbol=signal.symbol,
                side=PositionSide.LONG,
                entry_price=current_price,
                qty=position_size,
                stop_loss=current_price * (1 - self.config.stop_loss_pct),
                take_profit=current_price * (1 + self.config.take_profit_pct),
                trailing_stop=self.config.trail_pct,
                entry_order_id=order.order_id,
                test=test
            )
            
            log.info(f"Opened position: {position}")
            
            # Notify callbacks
            for callback in self._trade_callbacks:
                callback(position, 0.0, 0.0)
            
            return position
            
        except Exception as e:
            log.error(f"Failed to execute buy signal for {signal.symbol}: {e}")
            return None

    async def _execute_sell_signal(
        self,
        signal: TradeSignal,
        position: Position,
        current_price: float
    ) -> bool:
        """Execute a sell signal.
        
        Args:
            signal: Sell signal to execute
            position: Position to close
            current_price: Current market price
            
        Returns:
            True if position was closed
        """
        try:
            # Create exit order
            order = await self.order_manager.create_order(
                symbol=position.symbol,
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                qty=position.current_qty,
                test=(self.config.mode == BotMode.PAPER)
            )
            
            # Close position
            position, pnl, pnl_pct = await self.position_manager.close_position(
                position_id=position.position_id,
                exit_price=current_price,
                exit_reason=ExitReason.SIGNAL,
                exit_order_id=order.order_id
            )
            
            # Update daily P&L
            self._daily_pnl += pnl
            if pnl < 0:
                self._daily_loss += abs(pnl)
            
            log.info(f"Closed position: {position}, P&L: {pnl:.4f} ({pnl_pct:.2f}%)")
            
            # Notify callbacks
            for callback in self._trade_callbacks:
                callback(position, pnl, pnl_pct)
            
            return True
            
        except Exception as e:
            log.error(f"Failed to execute sell signal for {position.symbol}: {e}")
            return False

    async def _check_position_stops(self) -> None:
        """Check if any positions have hit their stop-loss or take-profit."""
        try:
            # Get current prices
            prices = {}
            for symbol in self.config.symbols:
                ticker = await self.data_collector.fetch_ticker(symbol)
                if ticker:
                    prices[symbol] = float(ticker.get("last", ticker.get("close", 0)))
            
            if not prices:
                return
            
            # Check stop-losses
            stop_loss_hits = await self.position_manager.check_stop_losses(prices)
            for position_id in stop_loss_hits:
                position = await self.position_manager.get_position(position_id)
                if position:
                    current_price = prices.get(position.symbol, position.entry_price)
                    await self._execute_stop_loss(position, current_price)
            
            # Check take-profits
            take_profit_hits = await self.position_manager.check_take_profits(prices)
            for position_id in take_profit_hits:
                position = await self.position_manager.get_position(position_id)
                if position:
                    current_price = prices.get(position.symbol, position.entry_price)
                    await self._execute_take_profit(position, current_price)
            
            # Check trailing stops
            trailing_stop_hits = await self.position_manager.check_trailing_stops(prices)
            for position_id in trailing_stop_hits:
                position = await self.position_manager.get_position(position_id)
                if position:
                    current_price = prices.get(position.symbol, position.entry_price)
                    await self._execute_trailing_stop(position, current_price)
                    
        except Exception as e:
            log.error(f"Failed to check position stops: {e}")

    async def _execute_stop_loss(
        self,
        position: Position,
        current_price: float
    ) -> bool:
        """Execute stop-loss for a position.
        
        Args:
            position: Position to close
            current_price: Current market price
            
        Returns:
            True if stop-loss was executed
        """
        log.info(f"Executing stop-loss for position: {position.position_id}")
        
        try:
            # Create exit order
            order = await self.order_manager.create_order(
                symbol=position.symbol,
                side=OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY,
                order_type=OrderType.MARKET,
                qty=position.current_qty,
                test=(self.config.mode == BotMode.PAPER)
            )
            
            # Close position
            position, pnl, pnl_pct = await self.position_manager.close_position(
                position_id=position.position_id,
                exit_price=current_price,
                exit_reason=ExitReason.STOP_LOSS,
                exit_order_id=order.order_id
            )
            
            # Update daily P&L
            self._daily_pnl += pnl
            self._daily_loss += abs(pnl)
            
            log.info(f"Stop-loss executed: {position}, P&L: {pnl:.4f}")
            
            # Notify callbacks
            for callback in self._trade_callbacks:
                callback(position, pnl, pnl_pct)
            
            return True
            
        except Exception as e:
            log.error(f"Failed to execute stop-loss for {position.position_id}: {e}")
            return False

    async def _execute_take_profit(
        self,
        position: Position,
        current_price: float
    ) -> bool:
        """Execute take-profit for a position.
        
        Args:
            position: Position to close
            current_price: Current market price
            
        Returns:
            True if take-profit was executed
        """
        log.info(f"Executing take-profit for position: {position.position_id}")
        
        try:
            # Create exit order
            order = await self.order_manager.create_order(
                symbol=position.symbol,
                side=OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY,
                order_type=OrderType.MARKET,
                qty=position.current_qty,
                test=(self.config.mode == BotMode.PAPER)
            )
            
            # Close position
            position, pnl, pnl_pct = await self.position_manager.close_position(
                position_id=position.position_id,
                exit_price=current_price,
                exit_reason=ExitReason.TAKE_PROFIT,
                exit_order_id=order.order_id
            )
            
            # Update daily P&L
            self._daily_pnl += pnl
            
            log.info(f"Take-profit executed: {position}, P&L: {pnl:.4f}")
            
            # Notify callbacks
            for callback in self._trade_callbacks:
                callback(position, pnl, pnl_pct)
            
            return True
            
        except Exception as e:
            log.error(f"Failed to execute take-profit for {position.position_id}: {e}")
            return False

    async def _execute_trailing_stop(
        self,
        position: Position,
        current_price: float
    ) -> bool:
        """Execute trailing stop for a position.
        
        Args:
            position: Position to close
            current_price: Current market price
            
        Returns:
            True if trailing stop was executed
        """
        log.info(f"Executing trailing stop for position: {position.position_id}")
        
        try:
            # Create exit order
            order = await self.order_manager.create_order(
                symbol=position.symbol,
                side=OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY,
                order_type=OrderType.MARKET,
                qty=position.current_qty,
                test=(self.config.mode == BotMode.PAPER)
            )
            
            # Close position
            position, pnl, pnl_pct = await self.position_manager.close_position(
                position_id=position.position_id,
                exit_price=current_price,
                exit_reason=ExitReason.TRAILING_STOP,
                exit_order_id=order.order_id
            )
            
            # Update daily P&L
            self._daily_pnl += pnl
            
            log.info(f"Trailing stop executed: {position}, P&L: {pnl:.4f}")
            
            # Notify callbacks
            for callback in self._trade_callbacks:
                callback(position, pnl, pnl_pct)
            
            return True
            
        except Exception as e:
            log.error(f"Failed to execute trailing stop for {position.position_id}: {e}")
            return False

    # ========================================================================
    # RISK MANAGEMENT
    # ========================================================================

    async def _can_open_position(self) -> bool:
        """Check if we can open a new position.
        
        Returns:
            True if a new position can be opened
        """
        # Check maximum concurrent positions
        open_positions = await self.position_manager.get_open_positions()
        if len(open_positions) >= self.config.max_concurrent_positions:
            log.debug(f"Maximum concurrent positions ({self.config.max_concurrent_positions}) reached")
            return False
        
        return True

    async def _check_daily_loss_limit(self) -> bool:
        """Check if daily loss limit has been reached.
        
        Returns:
            True if daily loss limit has been reached
        """
        if self._daily_loss >= (self.config.initial_balance * self.config.daily_loss_limit_pct):
            log.warning(f"Daily loss limit reached: {self._daily_loss:.2f} / {self.config.initial_balance * self.config.daily_loss_limit_pct:.2f}")
            return True
        
        return False

    # ========================================================================
    # STATISTICS
    # ========================================================================

    async def _update_statistics(self) -> None:
        """Update bot statistics."""
        try:
            # Get current positions
            open_positions = await self.position_manager.get_open_positions()
            self.stats.current_positions = len(open_positions)
            
            # Get active orders
            active_orders = await self.order_manager.get_active_orders()
            self.stats.active_orders = len(active_orders)
            
            # Update uptime
            if self._start_time:
                self.stats.uptime = datetime.now(timezone.utc) - self._start_time
            
            # Calculate P&L
            prices = {}
            for symbol in self.config.symbols:
                ticker = await self.data_collector.fetch_ticker(symbol)
                if ticker:
                    prices[symbol] = float(ticker.get("last", ticker.get("close", 0)))
            
            total_pnl, total_pnl_pct = await self.position_manager.get_total_pnl(prices)
            self.stats.total_pnl = total_pnl + self._daily_pnl
            self.stats.total_pnl_pct = total_pnl_pct
            
            # Update last trade time
            trades = await self.db.get_recent_trades(limit=1)
            if trades:
                self.stats.last_trade_time = datetime.fromisoformat(trades[0]["exit_time"])
            
        except Exception as e:
            log.error(f"Failed to update statistics: {e}")

    async def get_statistics(self) -> BotStats:
        """Get current bot statistics.
        
        Returns:
            BotStats object
        """
        await self._update_statistics()
        return self.stats

    async def get_position_summary(self) -> Dict[str, Any]:
        """Get a summary of all positions.
        
        Returns:
            Summary dictionary
        """
        return await self.position_manager.get_position_summary()

    # ========================================================================
    # CALLBACK MANAGEMENT
    # ========================================================================

    def on_signal(self, callback: Callable[[TradeSignal], None]) -> None:
        """Register a callback for trading signals.
        
        Args:
            callback: Function to call when a signal is generated
        """
        self._signal_callbacks.append(callback)

    def on_trade(self, callback: Callable[[Position, float, float], None]) -> None:
        """Register a callback for trades.
        
        Args:
            callback: Function to call when a trade is executed
        """
        self._trade_callbacks.append(callback)

    # ========================================================================
    # MANUAL CONTROL
    # ========================================================================

    async def open_position(
        self,
        symbol: str,
        side: PositionSide,
        qty: float,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Optional[Position]:
        """Manually open a position.
        
        Args:
            symbol: Trading pair
            side: Position side
            qty: Quantity
            entry_price: Entry price (uses current price if None)
            stop_loss: Stop-loss price
            take_profit: Take-profit price
            
        Returns:
            Created Position or None
        """
        try:
            # Get current price if not provided
            if entry_price is None:
                ticker = await self.data_collector.fetch_ticker(symbol)
                if not ticker:
                    log.error(f"Could not fetch current price for {symbol}")
                    return None
                entry_price = float(ticker.get("last", ticker.get("close", 0)))
            
            # Create order
            order = await self.order_manager.create_order(
                symbol=symbol,
                side=OrderSide.BUY if side == PositionSide.LONG else OrderSide.SELL,
                order_type=OrderType.MARKET,
                qty=qty,
                test=(self.config.mode == BotMode.PAPER)
            )
            
            # Create position
            position = await self.position_manager.open_position(
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                qty=qty,
                stop_loss=stop_loss,
                take_profit=take_profit,
                entry_order_id=order.order_id,
                test=(self.config.mode == BotMode.PAPER)
            )
            
            log.info(f"Manual position opened: {position}")
            return position
            
        except Exception as e:
            log.error(f"Failed to open manual position: {e}")
            return None

    async def close_position(
        self,
        position_id: str,
        exit_price: Optional[float] = None
    ) -> Tuple[Optional[Position], float, float]:
        """Manually close a position.
        
        Args:
            position_id: ID of position to close
            exit_price: Exit price (uses current price if None)
            
        Returns:
            Tuple of (position, pnl, pnl_pct)
        """
        position = await self.position_manager.get_position(position_id)
        if not position:
            log.error(f"Position not found: {position_id}")
            return None, 0.0, 0.0
        
        try:
            # Get current price if not provided
            if exit_price is None:
                ticker = await self.data_collector.fetch_ticker(position.symbol)
                if not ticker:
                    log.error(f"Could not fetch current price for {position.symbol}")
                    return position, 0.0, 0.0
                exit_price = float(ticker.get("last", ticker.get("close", 0)))
            
            # Close position
            position, pnl, pnl_pct = await self.position_manager.close_position(
                position_id=position_id,
                exit_price=exit_price,
                exit_reason=ExitReason.MANUAL
            )
            
            # Update daily P&L
            self._daily_pnl += pnl
            if pnl < 0:
                self._daily_loss += abs(pnl)
            
            log.info(f"Manual position closed: {position}, P&L: {pnl:.4f}")
            
            # Notify callbacks
            for callback in self._trade_callbacks:
                callback(position, pnl, pnl_pct)
            
            return position, pnl, pnl_pct
            
        except Exception as e:
            log.error(f"Failed to close manual position: {e}")
            return position, 0.0, 0.0

    async def close_all_positions(self) -> List[Tuple[Position, float, float]]:
        """Close all open positions.
        
        Returns:
            List of (position, pnl, pnl_pct) tuples
        """
        results = []
        
        positions = await self.position_manager.get_open_positions()
        for position in positions:
            result = await self.close_position(position.position_id)
            results.append(result)
        
        return results

    async def cancel_all_orders(self) -> int:
        """Cancel all active orders.
        
        Returns:
            Number of orders cancelled
        """
        return await self.order_manager.cancel_all_orders()

    # ========================================================================
    # SIGNAL HANDLING
    # ========================================================================

    def _setup_signal_handlers(self) -> None:
        """Setup OS signal handlers for graceful shutdown."""
        def handle_shutdown(signame):
            log.info(f"Received signal {signame}, shutting down...")
            asyncio.create_task(self.stop())
        
        try:
            loop = asyncio.get_event_loop()
            loop.add_signal_handler(signal.SIGINT, handle_shutdown, "SIGINT")
            loop.add_signal_handler(signal.SIGTERM, handle_shutdown, "SIGTERM")
        except Exception as e:
            log.warning(f"Could not setup signal handlers: {e}")

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def get_status(self) -> Dict[str, Any]:
        """Get current bot status.
        
        Returns:
            Dictionary with bot status information
        """
        return {
            "status": self._status.value,
            "mode": self.config.mode.value,
            "symbols": self.config.symbols,
            "timeframes": self.config.timeframes,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "uptime": str(self.stats.uptime),
            "current_positions": self.stats.current_positions,
            "active_orders": self.stats.active_orders,
            "total_pnl": self.stats.total_pnl,
            "total_pnl_pct": self.stats.total_pnl_pct,
            "daily_pnl": self._daily_pnl,
            "daily_loss": self._daily_loss
        }

    async def get_open_positions(self) -> List[Position]:
        """Get all open positions.
        
        Returns:
            List of open positions
        """
        return await self.position_manager.get_open_positions()

    async def get_active_orders(self) -> List[Order]:
        """Get all active orders.
        
        Returns:
            List of active orders
        """
        return await self.order_manager.get_active_orders()

    async def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get trade history.
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of trade dictionaries
        """
        return await self.db.get_recent_trades(limit=limit)


# ============================================================================
# GLOBAL BOT INSTANCE
# ============================================================================

_bot: Optional[TradingBot] = None


async def get_bot() -> TradingBot:
    """Get the global bot instance, creating it if necessary.
    
    Returns:
        TradingBot instance
    """
    global _bot
    if _bot is None:
        _bot = TradingBot()
    return _bot


async def start_bot() -> TradingBot:
    """Start the global bot instance.
    
    Returns:
        TradingBot instance
    """
    bot = await get_bot()
    await bot.start()
    return bot


async def stop_bot() -> None:
    """Stop the global bot instance."""
    global _bot
    if _bot is not None:
        await _bot.stop()
