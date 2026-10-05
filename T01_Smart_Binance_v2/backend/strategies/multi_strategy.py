"""Multi-Strategy Engine for T01 Smart Binance Intelligence v2.

This module provides a unified interface for managing multiple trading strategies.
It coordinates between different strategies and provides:

1. Strategy selection and weighting
2. Signal aggregation and voting
3. Risk allocation across strategies
4. Performance tracking per strategy
5. Dynamic strategy switching

The engine works by:
- Running multiple strategies in parallel
- Aggregating signals from all strategies
- Applying weights to each strategy's signals
- Executing the highest-confidence signals
- Tracking performance of each strategy
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.data.collector import DataCollector
    from backend.trading.order_manager import OrderManager
    from backend.trading.position_manager import PositionManager
    from backend.strategies.scalping import ScalpingStrategy, ScalpingSignal
    from backend.analysis.multitimeframe import MultiTimeframeAnalyzer
    from backend.analysis.patterns import PatternDetector, PatternSignal

log = logging.getLogger("strategies.multi_strategy")


# ============================================================================
# ENUMS
# ============================================================================

class StrategyType(Enum):
    """Types of trading strategies."""
    SCALPING = "scalping"
    SWING = "swing"
    TREND = "trend"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    MULTI_TIMEFRAME = "multi_timeframe"
    PATTERN = "pattern"


class StrategyStatus(Enum):
    """Status of a strategy."""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class StrategyConfig:
    """Configuration for a single strategy.
    
    Attributes:
        strategy_type: Type of strategy
        enabled: Whether the strategy is enabled
        weight: Weight for signal aggregation (0-100)
        symbols: List of symbols to trade
        timeframes: List of timeframes to analyze
        risk_allocation: Percentage of total risk to allocate
        params: Additional strategy-specific parameters
    """
    strategy_type: StrategyType = StrategyType.SCALPING
    enabled: bool = True
    weight: float = 25.0  # Equal weight by default
    symbols: List[str] = field(default_factory=lambda: ["BTC/USDT"])
    timeframes: List[str] = field(default_factory=lambda: ["1h"])
    risk_allocation: float = 20.0  # 20% of total risk
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedSignal:
    """Aggregated signal from multiple strategies.
    
    Attributes:
        symbol: Trading pair
        direction: Overall direction (buy, sell, hold)
        confidence: Overall confidence (0-100)
        strength: Overall strength (0-100)
        strategies: Dictionary of strategy -> signal
        weighted_score: Weighted score from all strategies
        entry_price: Suggested entry price
        stop_loss: Suggested stop-loss price
        take_profit: Suggested take-profit price
        risk_reward: Risk/reward ratio
        timestamp: When the aggregated signal was generated
    """
    symbol: str = ""
    direction: str = "hold"
    confidence: float = 0.0
    strength: float = 0.0
    strategies: Dict[str, Any] = field(default_factory=dict)
    weighted_score: float = 0.0
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_reward: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert aggregated signal to dictionary."""
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "confidence": self.confidence,
            "strength": self.strength,
            "strategies": {s: v.to_dict() if hasattr(v, 'to_dict') else str(v) for s, v in self.strategies.items()},
            "weighted_score": self.weighted_score,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_reward": self.risk_reward,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class StrategyPerformance:
    """Performance statistics for a strategy.
    
    Attributes:
        strategy_type: Type of strategy
        total_trades: Total number of trades
        winning_trades: Number of winning trades
        losing_trades: Number of losing trades
        win_rate: Win rate percentage
        total_pnl: Total P&L
        avg_pnl: Average P&L per trade
        max_drawdown: Maximum drawdown
        sharpe_ratio: Sharpe ratio
        active_positions: Number of active positions
        last_trade_time: Time of last trade
    """
    strategy_type: StrategyType = StrategyType.SCALPING
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    avg_pnl: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    active_positions: int = 0
    last_trade_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert performance to dictionary."""
        return {
            "strategy_type": self.strategy_type.value,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "total_pnl": self.total_pnl,
            "avg_pnl": self.avg_pnl,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "active_positions": self.active_positions,
            "last_trade_time": self.last_trade_time.isoformat() if self.last_trade_time else None
        }


# ============================================================================
# MULTI-STRATEGY ENGINE
# ============================================================================

class MultiStrategyEngine:
    """Manages multiple trading strategies.
    
    The MultiStrategyEngine provides:
    
    1. Unified interface for multiple strategies
    2. Signal aggregation and voting
    3. Risk allocation across strategies
    4. Performance tracking per strategy
    5. Dynamic strategy switching
    
    The engine works by:
    - Initializing and managing multiple strategy instances
    - Running strategies in parallel
    - Aggregating signals from all strategies
    - Applying weights to each strategy's signals
    - Executing the highest-confidence aggregated signals
    - Tracking performance of each strategy
    """

    def __init__(
        self,
        data_collector: "DataCollector",
        order_manager: "OrderManager",
        position_manager: "PositionManager",
        mtf_analyzer: Optional["MultiTimeframeAnalyzer"] = None,
        pattern_detector: Optional["PatternDetector"] = None,
        config: Optional[Dict[StrategyType, StrategyConfig]] = None
    ):
        """Initialize MultiStrategyEngine.
        
        Args:
            data_collector: DataCollector instance
            order_manager: OrderManager instance
            position_manager: PositionManager instance
            mtf_analyzer: Optional MultiTimeframeAnalyzer
            pattern_detector: Optional PatternDetector
            config: Optional configuration for strategies
        """
        self.data_collector = data_collector
        self.order_manager = order_manager
        self.position_manager = position_manager
        self.mtf_analyzer = mtf_analyzer
        self.pattern_detector = pattern_detector
        
        # Strategy instances
        self.strategies: Dict[StrategyType, Any] = {}
        
        # Strategy configurations
        self.config = config or self._create_default_config()
        
        # Strategy status
        self._status: Dict[StrategyType, StrategyStatus] = {}
        
        # Aggregated signals
        self._aggregated_signals: Dict[str, AggregatedSignal] = {}
        
        # Performance tracking
        self._performance: Dict[StrategyType, StrategyPerformance] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        log.info("MultiStrategyEngine initialized")

    def _create_default_config(self) -> Dict[StrategyType, StrategyConfig]:
        """Create default configuration for all strategies.
        
        Returns:
            Dictionary of strategy configurations
        """
        return {
            StrategyType.SCALPING: StrategyConfig(
                strategy_type=StrategyType.SCALPING,
                enabled=True,
                weight=20.0,
                symbols=["BTC/USDT", "ETH/USDT", "BNB/USDT"],
                timeframes=["1m", "5m"],
                risk_allocation=15.0,
                params={"mode": "balanced"}
            ),
            StrategyType.SWING: StrategyConfig(
                strategy_type=StrategyType.SWING,
                enabled=True,
                weight=25.0,
                symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"],
                timeframes=["1h", "4h"],
                risk_allocation=25.0,
                params={"hold_period": "2-5 days"}
            ),
            StrategyType.TREND: StrategyConfig(
                strategy_type=StrategyType.TREND,
                enabled=True,
                weight=20.0,
                symbols=["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"],
                timeframes=["1h", "4h", "1d"],
                risk_allocation=20.0,
                params={}
            ),
            StrategyType.MEAN_REVERSION: StrategyConfig(
                strategy_type=StrategyType.MEAN_REVERSION,
                enabled=True,
                weight=15.0,
                symbols=["BTC/USDT", "ETH/USDT"],
                timeframes=["1h", "4h"],
                risk_allocation=15.0,
                params={}
            ),
            StrategyType.BREAKOUT: StrategyConfig(
                strategy_type=StrategyType.BREAKOUT,
                enabled=True,
                weight=20.0,
                symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
                timeframes=["1h", "4h", "1d"],
                risk_allocation=25.0,
                params={}
            )
        }

    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================

    async def start(self) -> None:
        """Start all enabled strategies."""
        log.info("Starting MultiStrategyEngine")
        
        # Initialize strategies
        await self._initialize_strategies()
        
        # Start strategies
        for strategy_type, strategy in self.strategies.items():
            if self.config[strategy_type].enabled:
                try:
                    await strategy.start()
                    self._status[strategy_type] = StrategyStatus.RUNNING
                    self._performance[strategy_type] = StrategyPerformance(
                        strategy_type=strategy_type
                    )
                    log.info(f"Started strategy: {strategy_type.value}")
                except Exception as e:
                    self._status[strategy_type] = StrategyStatus.ERROR
                    log.error(f"Failed to start strategy {strategy_type.value}: {e}")
        
        log.info("MultiStrategyEngine started")

    async def stop(self) -> None:
        """Stop all strategies."""
        log.info("Stopping MultiStrategyEngine")
        
        for strategy_type, strategy in self.strategies.items():
            if self._status.get(strategy_type) == StrategyStatus.RUNNING:
                try:
                    await strategy.stop()
                    self._status[strategy_type] = StrategyStatus.STOPPED
                    log.info(f"Stopped strategy: {strategy_type.value}")
                except Exception as e:
                    log.error(f"Failed to stop strategy {strategy_type.value}: {e}")
        
        log.info("MultiStrategyEngine stopped")

    async def pause(self, strategy_type: Optional[StrategyType] = None) -> None:
        """Pause a specific strategy or all strategies.
        
        Args:
            strategy_type: Optional strategy type to pause
        """
        if strategy_type:
            if strategy_type in self.strategies:
                self._status[strategy_type] = StrategyStatus.PAUSED
                log.info(f"Paused strategy: {strategy_type.value}")
        else:
            for st in self._status:
                self._status[st] = StrategyStatus.PAUSED
            log.info("Paused all strategies")

    async def resume(self, strategy_type: Optional[StrategyType] = None) -> None:
        """Resume a specific strategy or all strategies.
        
        Args:
            strategy_type: Optional strategy type to resume
        """
        if strategy_type:
            if strategy_type in self.strategies:
                self._status[strategy_type] = StrategyStatus.RUNNING
                log.info(f"Resumed strategy: {strategy_type.value}")
        else:
            for st in self._status:
                self._status[st] = StrategyStatus.RUNNING
            log.info("Resumed all strategies")

    # ========================================================================
    # STRATEGY INITIALIZATION
    # ========================================================================

    async def _initialize_strategies(self) -> None:
        """Initialize all strategy instances."""
        # Scalping Strategy
        from backend.strategies.scalping import ScalpingStrategy, ScalpingConfig
        scalping_config = ScalpingConfig(
            timeframes=self.config[StrategyType.SCALPING].timeframes,
            mode="ScalpingMode.BALANCED"
        )
        self.strategies[StrategyType.SCALPING] = ScalpingStrategy(
            data_collector=self.data_collector,
            order_manager=self.order_manager,
            position_manager=self.position_manager,
            config=scalping_config,
            symbols=self.config[StrategyType.SCALPING].symbols
        )
        
        # Note: Other strategies (Swing, Trend, MeanReversion, Breakout) would be
        # initialized similarly. For brevity, we'll focus on Scalping and
        # add placeholders for others.
        
        # Placeholder for other strategies
        for st in [StrategyType.SWING, StrategyType.TREND, 
                   StrategyType.MEAN_REVERSION, StrategyType.BREAKOUT]:
            if st not in self.strategies:
                self.strategies[st] = None  # Placeholder
        
        log.info(f"Initialized {len(self.strategies)} strategies")

    # ========================================================================
    # SCANNING & SIGNAL GENERATION
    # ========================================================================

    async def scan_all(self) -> Dict[str, AggregatedSignal]:
        """Scan all strategies and aggregate signals.
        
        Returns:
            Dictionary of symbol -> AggregatedSignal
        """
        async with self._lock:
            self._aggregated_signals.clear()
            
            # Collect signals from all strategies
            all_signals = await self._collect_all_signals()
            
            # Aggregate signals by symbol
            for symbol, signals in all_signals.items():
                aggregated = self._aggregate_signals(symbol, signals)
                if aggregated:
                    self._aggregated_signals[symbol] = aggregated
            
            return self._aggregated_signals.copy()

    async def _collect_all_signals(self) -> Dict[str, List[Any]]:
        """Collect signals from all enabled strategies.
        
        Returns:
            Dictionary of symbol -> List of signals from different strategies
        """
        all_signals: Dict[str, List[Any]] = {}
        
        for strategy_type, strategy in self.strategies.items():
            if not self.config[strategy_type].enabled:
                continue
            
            if self._status.get(strategy_type) != StrategyStatus.RUNNING:
                continue
            
            try:
                # Get signals from strategy
                if strategy_type == StrategyType.SCALPING:
                    signals = await strategy.scan()
                elif strategy_type == StrategyType.MULTI_TIMEFRAME and self.mtf_analyzer:
                    signals = await self._get_mtf_signals()
                elif strategy_type == StrategyType.PATTERN and self.pattern_detector:
                    signals = await self._get_pattern_signals()
                else:
                    continue  # Strategy not implemented
                
                # Add signals to collection
                for signal in signals:
                    symbol = signal.symbol
                    if symbol not in all_signals:
                        all_signals[symbol] = []
                    
                    # Store signal with strategy type
                    all_signals[symbol].append({
                        "strategy": strategy_type.value,
                        "signal": signal
                    })
                    
            except Exception as e:
                log.error(f"Failed to collect signals from {strategy_type.value}: {e}")
        
        return all_signals

    async def _get_mtf_signals(self) -> List[Any]:
        """Get signals from MTF analyzer.
        
        Returns:
            List of MTF signals
        """
        signals = []
        
        for symbol in self.config[StrategyType.MULTI_TIMEFRAME].symbols:
            try:
                signal = await self.mtf_analyzer.generate_signal(
                    symbol=symbol,
                    timeframes=self.config[StrategyType.MULTI_TIMEFRAME].timeframes
                )
                signals.append(signal)
            except Exception as e:
                log.error(f"Failed to get MTF signal for {symbol}: {e}")
        
        return signals

    async def _get_pattern_signals(self) -> List[Any]:
        """Get signals from pattern detector.
        
        Returns:
            List of pattern signals
        """
        signals = []
        
        for symbol in self.config[StrategyType.PATTERN].symbols:
            try:
                pattern_signals = await self.pattern_detector.generate_signals(
                    symbol=symbol,
                    timeframe=self.config[StrategyType.PATTERN].timeframes[0]
                )
                signals.extend(pattern_signals)
            except Exception as e:
                log.error(f"Failed to get pattern signals for {symbol}: {e}")
        
        return signals

    def _aggregate_signals(
        self,
        symbol: str,
        signals: List[Dict[str, Any]]
    ) -> Optional[AggregatedSignal]:
        """Aggregate signals from multiple strategies for a symbol.
        
        Args:
            symbol: Trading pair
            signals: List of signals from different strategies
            
        Returns:
            AggregatedSignal or None
        """
        if not signals:
            return None
        
        # Count buy/sell signals
        buy_signals = []
        sell_signals = []
        
        for item in signals:
            signal = item["signal"]
            strategy = item["strategy"]
            config = self._get_strategy_config(StrategyType(strategy))
            
            if config is None:
                continue
            
            # Get signal direction
            if hasattr(signal, 'signal_type'):
                direction = signal.signal_type.value
            elif hasattr(signal, 'direction'):
                direction = signal.direction.value if hasattr(signal.direction, 'value') else signal.direction
            elif hasattr(signal, 'action'):
                direction = signal.action
            else:
                direction = "neutral"
            
            # Calculate weighted score
            weight = config.weight
            
            if hasattr(signal, 'confidence'):
                confidence = signal.confidence
            else:
                confidence = 50.0
            
            weighted_score = (confidence / 100) * weight
            
            if direction.startswith("buy"):
                buy_signals.append({
                    "strategy": strategy,
                    "signal": signal,
                    "weight": weight,
                    "confidence": confidence,
                    "weighted_score": weighted_score
                })
            elif direction.startswith("sell"):
                sell_signals.append({
                    "strategy": strategy,
                    "signal": signal,
                    "weight": weight,
                    "confidence": confidence,
                    "weighted_score": weighted_score
                })
        
        # Calculate overall direction
        total_buy_score = sum(s["weighted_score"] for s in buy_signals)
        total_sell_score = sum(s["weighted_score"] for s in sell_signals)
        
        # Determine direction
        if total_buy_score > total_sell_score * 1.2:
            direction = "buy"
            confidence = min(total_buy_score, 100)
        elif total_sell_score > total_buy_score * 1.2:
            direction = "sell"
            confidence = min(total_sell_score, 100)
        else:
            direction = "hold"
            confidence = 0.0
        
        # Calculate strength
        strength = min((total_buy_score + total_sell_score), 100)
        
        # Build strategies dictionary
        strategies_dict = {}
        for item in signals:
            strategies_dict[item["strategy"]] = item["signal"]
        
        # Calculate levels (use first signal's levels as baseline)
        entry_price = 0.0
        stop_loss = 0.0
        take_profit = 0.0
        
        if signals:
            first_signal = signals[0]["signal"]
            if hasattr(first_signal, 'entry_price'):
                entry_price = first_signal.entry_price
            if hasattr(first_signal, 'stop_loss'):
                stop_loss = first_signal.stop_loss
            if hasattr(first_signal, 'take_profit'):
                take_profit = first_signal.take_profit
        
        # Calculate risk/reward
        risk_reward = 0.0
        if stop_loss != 0 and take_profit != 0 and entry_price != 0:
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            risk_reward = reward / risk if risk > 0 else 0.0
        
        return AggregatedSignal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            strength=strength,
            strategies=strategies_dict,
            weighted_score=total_buy_score + total_sell_score,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=risk_reward
        )

    def _get_strategy_config(self, strategy_type: StrategyType) -> Optional[StrategyConfig]:
        """Get configuration for a strategy.
        
        Args:
            strategy_type: Strategy type
            
        Returns:
            StrategyConfig or None
        """
        return self.config.get(strategy_type)

    # ========================================================================
    # SIGNAL EXECUTION
    # ========================================================================

    async def execute_top_signals(self, limit: int = 5) -> List[str]:
        """Execute the top aggregated signals.
        
        Args:
            limit: Maximum number of signals to execute
            
        Returns:
            List of executed signal IDs/symbols
        """
        # Scan all strategies
        signals = await self.scan_all()
        
        # Sort by confidence and strength
        sorted_signals = sorted(
            signals.values(),
            key=lambda s: (s.confidence, s.strength),
            reverse=True
        )
        
        executed = []
        
        for signal in sorted_signals[:limit]:
            if signal.direction != "hold":
                success = await self._execute_signal(signal)
                if success:
                    executed.append(signal.symbol)
        
        return executed

    async def _execute_signal(self, signal: AggregatedSignal) -> bool:
        """Execute an aggregated signal.
        
        Args:
            signal: Aggregated signal to execute
            
        Returns:
            True if execution was successful
        """
        async with self._lock:
            # Check if we can open a position for this symbol
            position = await self.position_manager.get_position_for_symbol(signal.symbol)
            if position:
                log.info(f"Cannot execute signal: already have position for {signal.symbol}")
                return False
            
            # Check maximum positions
            open_positions = await self.position_manager.get_open_positions()
            if len(open_positions) >= 10:  # Max 10 positions
                log.info("Cannot execute signal: maximum positions reached")
                return False
            
            try:
                # Determine side
                side = "OrderSide.BUY" if signal.direction == "buy" else "OrderSide.SELL"
                
                # Calculate quantity based on aggregated risk
                current_price = signal.entry_price
                balance = 1000.0  # Would use actual balance
                
                # Use average risk allocation from contributing strategies
                avg_risk = sum(
                    self.config[s].risk_allocation 
                    for s in signal.strategies
                ) / len(signal.strategies) if signal.strategies else 20.0
                
                qty = self._calculate_position_size(
                    current_price,
                    signal.stop_loss,
                    avg_risk / 100,  # Convert percentage to decimal
                    balance
                )
                
                if qty <= 0:
                    log.warning(f"Position size is zero for {signal.symbol}")
                    return False
                
                # Create order
                order = await self.order_manager.create_order(
                    symbol=signal.symbol,
                    side=side,
                    order_type="OrderType.MARKET",
                    qty=qty,
                    test=True  # Paper trading for now
                )
                
                # Create position
                position_side = "PositionSide.LONG" if side == "OrderSide.BUY" else "PositionSide.SHORT"
                position = await self.position_manager.open_position(
                    symbol=signal.symbol,
                    side=position_side,
                    entry_price=current_price,
                    qty=qty,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    entry_order_id=order.order_id,
                    test=True
                )
                
                # Update performance tracking
                strategy_types = [StrategyType(s) for s in signal.strategies.keys()]
                for st in strategy_types:
                    if st in self._performance:
                        self._performance[st].total_trades += 1
                        self._performance[st].last_trade_time = datetime.now(timezone.utc)
                
                log.info(f"Executed aggregated signal: {signal.symbol} {side} {qty} @ {current_price}")
                return True
                
            except Exception as e:
                log.error(f"Failed to execute signal: {e}")
                return False

    def _calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        risk_pct: float,
        balance: float
    ) -> float:
        """Calculate position size based on risk.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop-loss price
            risk_pct: Risk percentage
            balance: Account balance
            
        Returns:
            Position size (quantity)
        """
        risk_amount = balance * risk_pct
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit == 0:
            return 0.0
        
        return risk_amount / risk_per_unit

    # ========================================================================
    # PERFORMANCE TRACKING
    # ========================================================================

    async def update_performance(
        self,
        strategy_type: StrategyType,
        pnl: float,
        is_win: bool
    ) -> None:
        """Update performance statistics for a strategy.
        
        Args:
            strategy_type: Strategy type
            pnl: Profit and loss amount
            is_win: Whether the trade was a win
        """
        if strategy_type not in self._performance:
            self._performance[strategy_type] = StrategyPerformance(
                strategy_type=strategy_type
            )
        
        perf = self._performance[strategy_type]
        perf.total_trades += 1
        perf.total_pnl += pnl
        
        if is_win:
            perf.winning_trades += 1
        else:
            perf.losing_trades += 1
        
        # Update win rate
        if perf.total_trades > 0:
            perf.win_rate = (perf.winning_trades / perf.total_trades) * 100
        
        # Update average P&L
        if perf.total_trades > 0:
            perf.avg_pnl = perf.total_pnl / perf.total_trades

    async def get_performance(self) -> Dict[str, Any]:
        """Get performance statistics for all strategies.
        
        Returns:
            Dictionary with performance data
        """
        return {
            "strategies": {
                st.value: perf.to_dict() 
                for st, perf in self._performance.items()
            },
            "total_trades": sum(perf.total_trades for perf in self._performance.values()),
            "total_pnl": sum(perf.total_pnl for perf in self._performance.values())
        }

    async def get_strategy_performance(
        self,
        strategy_type: StrategyType
    ) -> Optional[StrategyPerformance]:
        """Get performance for a specific strategy.
        
        Args:
            strategy_type: Strategy type
            
        Returns:
            StrategyPerformance or None
        """
        return self._performance.get(strategy_type)

    # ========================================================================
    # STRATEGY MANAGEMENT
    # ========================================================================

    async def enable_strategy(self, strategy_type: StrategyType) -> bool:
        """Enable a strategy.
        
        Args:
            strategy_type: Strategy type to enable
            
        Returns:
            True if strategy was enabled
        """
        if strategy_type in self.config:
            self.config[strategy_type].enabled = True
            log.info(f"Enabled strategy: {strategy_type.value}")
            return True
        return False

    async def disable_strategy(self, strategy_type: StrategyType) -> bool:
        """Disable a strategy.
        
        Args:
            strategy_type: Strategy type to disable
            
        Returns:
            True if strategy was disabled
        """
        if strategy_type in self.config:
            self.config[strategy_type].enabled = False
            log.info(f"Disabled strategy: {strategy_type.value}")
            return True
        return False

    async def set_strategy_weight(
        self,
        strategy_type: StrategyType,
        weight: float
    ) -> bool:
        """Set weight for a strategy.
        
        Args:
            strategy_type: Strategy type
            weight: Weight (0-100)
            
        Returns:
            True if weight was set
        """
        if strategy_type in self.config:
            self.config[strategy_type].weight = max(0, min(100, weight))
            log.info(f"Set weight for {strategy_type.value}: {weight}")
            return True
        return False

    async def set_strategy_symbols(
        self,
        strategy_type: StrategyType,
        symbols: List[str]
    ) -> bool:
        """Set symbols for a strategy.
        
        Args:
            strategy_type: Strategy type
            symbols: List of symbols
            
        Returns:
            True if symbols were set
        """
        if strategy_type in self.config:
            self.config[strategy_type].symbols = symbols
            log.info(f"Set symbols for {strategy_type.value}: {symbols}")
            return True
        return False

    # ========================================================================
    # SIGNAL MANAGEMENT
    # ========================================================================

    async def get_aggregated_signals(self) -> Dict[str, AggregatedSignal]:
        """Get all aggregated signals.
        
        Returns:
            Dictionary of symbol -> AggregatedSignal
        """
        return self._aggregated_signals.copy()

    async def get_signal(self, symbol: str) -> Optional[AggregatedSignal]:
        """Get aggregated signal for a specific symbol.
        
        Args:
            symbol: Symbol to get signal for
            
        Returns:
            AggregatedSignal or None
        """
        return self._aggregated_signals.get(symbol)

    async def clear_signals(self) -> None:
        """Clear all aggregated signals."""
        self._aggregated_signals.clear()
        log.info("Cleared all aggregated signals")

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def get_status(self) -> Dict[str, Any]:
        """Get engine status.
        
        Returns:
            Dictionary with engine status
        """
        return {
            "strategies": {
                st.value: {
                    "status": self._status.get(st, StrategyStatus.STOPPED).value,
                    "enabled": self.config[st].enabled,
                    "weight": self.config[st].weight
                }
                for st in self.strategies
            },
            "aggregated_signals": len(self._aggregated_signals),
            "total_trades": sum(perf.total_trades for perf in self._performance.values())
        }

    async def get_config(self) -> Dict[str, Any]:
        """Get engine configuration.
        
        Returns:
            Dictionary with engine configuration
        """
        return {
            st.value: config.to_dict() if hasattr(config, 'to_dict') else str(config)
            for st, config in self.config.items()
        }

    async def set_config(self, config: Dict[StrategyType, StrategyConfig]) -> None:
        """Set engine configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        log.info("Updated engine configuration")
