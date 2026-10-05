"""Scalping Strategy for T01 Smart Binance Intelligence v2.

This module implements a high-frequency scalping strategy that:
- Uses short timeframes (1m, 5m)
- Focuses on small, frequent profits
- Uses tight stop-losses
- Relies on momentum and volume
- Works best with WebSocket data

The scalping strategy is designed for:
- Fast execution (sub-second)
- Small profit targets (0.1-0.5%)
- High win rate (>60%)
- Quick stop-losses (<0.2%)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from backend.data.collector import DataCollector
    from backend.data.websocket_client import WebSocketClient
    from backend.trading.order_manager import OrderManager, OrderSide, OrderType
    from backend.trading.position_manager import PositionManager, PositionSide
    from backend.analysis.indicators import TechnicalIndicators

log = logging.getLogger("strategies.scalping")


# ============================================================================
# ENUMS
# ============================================================================

class ScalpingMode(Enum):
    """Scalping mode."""
    CONSERVATIVE = "conservative"  # Lower risk, lower reward
    AGGRESSIVE = "aggressive"      # Higher risk, higher reward
    BALANCED = "balanced"         # Balanced approach


class ScalpingSignal(Enum):
    """Scalping signal types."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    WEAK_BUY = "weak_buy"
    STRONG_SELL = "strong_sell"
    SELL = "sell"
    WEAK_SELL = "weak_sell"
    NEUTRAL = "neutral"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class ScalpingConfig:
    """Configuration for scalping strategy.
    
    Attributes:
        timeframes: Timeframes to analyze
        fast_timeframe: Primary timeframe for entries
        slow_timeframe: Confirmation timeframe
        profit_target_pct: Take-profit percentage
        stop_loss_pct: Stop-loss percentage
        trailing_stop_pct: Trailing stop percentage
        risk_per_trade_pct: Risk per trade percentage
        max_positions: Maximum concurrent positions
        min_volume: Minimum volume threshold
        min_volatility: Minimum volatility threshold
        rsi_overbought: RSI overbought level
        rsi_oversold: RSI oversold level
        mode: Scalping mode
    """
    timeframes: List[str] = field(default_factory=lambda: ["1m", "5m"])
    fast_timeframe: str = "1m"
    slow_timeframe: str = "5m"
    profit_target_pct: float = 0.003  # 0.3%
    stop_loss_pct: float = 0.0015  # 0.15%
    trailing_stop_pct: float = 0.002  # 0.2%
    risk_per_trade_pct: float = 0.005  # 0.5%
    max_positions: int = 3
    min_volume: float = 100000.0  # $100K volume
    min_volatility: float = 0.005  # 0.5% volatility
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    mode: ScalpingMode = ScalpingMode.BALANCED


@dataclass
class ScalpingSignal:
    """Scalping trading signal.
    
    Attributes:
        signal_type: Type of signal
        symbol: Trading pair
        timeframe: Timeframe
        entry_price: Suggested entry price
        stop_loss: Suggested stop-loss price
        take_profit: Suggested take-profit price
        confidence: Signal confidence (0-100)
        strength: Signal strength (0-100)
        indicators: Dictionary of indicator values
        timestamp: When signal was generated
    """
    signal_type: ScalpingSignal = ScalpingSignal.NEUTRAL
    symbol: str = ""
    timeframe: str = ""
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    confidence: float = 0.0
    strength: float = 0.0
    indicators: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# SCALPING STRATEGY
# ============================================================================

class ScalpingStrategy:
    """High-frequency scalping strategy.
    
    The ScalpingStrategy implements a momentum-based approach that:
    
    1. Uses short timeframes (1m, 5m) for fast entries
    2. Focuses on liquid pairs with high volume
    3. Uses tight stop-losses to limit risk
    4. Takes small profits frequently
    5. Relies on momentum and volume confirmation
    
    Entry signals:
    - Price breaks above/below recent high/low
    - Volume spike confirms momentum
    - RSI not in overbought/oversold
    - Moving averages aligned
    
    Exit signals:
    - Take-profit hit
    - Stop-loss hit
    - Trailing stop hit
    - Momentum reversal
    """

    def __init__(
        self,
        data_collector: "DataCollector",
        order_manager: "OrderManager",
        position_manager: "PositionManager",
        config: ScalpingConfig = None,
        symbols: List[str] = None
    ):
        """Initialize ScalpingStrategy.
        
        Args:
            data_collector: DataCollector instance
            order_manager: OrderManager instance
            position_manager: PositionManager instance
            config: Scalping configuration
            symbols: List of symbols to trade
        """
        self.data_collector = data_collector
        self.order_manager = order_manager
        self.position_manager = position_manager
        self.config = config or ScalpingConfig()
        self.symbols = symbols or ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
        
        # Strategy state
        self._active_signals: Dict[str, ScalpingSignal] = {}
        self._last_signal_time: Dict[str, datetime] = {}
        self._signal_cooldown = 5  # seconds between signals for same symbol
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        log.info(f"ScalpingStrategy initialized: {len(self.symbols)} symbols")

    # ========================================================================
    # MAIN METHODS
    # ========================================================================

    async def start(self) -> None:
        """Start the scalping strategy."""
        log.info("Starting ScalpingStrategy")
        
        # Initialize data for all symbols
        await self._initialize_data()
        
        log.info("ScalpingStrategy started")

    async def stop(self) -> None:
        """Stop the scalping strategy."""
        log.info("Stopping ScalpingStrategy")
        
        # Close all positions
        await self._close_all_positions()
        
        log.info("ScalpingStrategy stopped")

    async def scan(self) -> List[ScalpingSignal]:
        """Scan all symbols for trading opportunities.
        
        Returns:
            List of ScalpingSignal objects
        """
        signals = []
        
        for symbol in self.symbols:
            signal = await self._analyze_symbol(symbol)
            if signal and signal.signal_type != ScalpingSignal.NEUTRAL:
                signals.append(signal)
        
        # Sort by confidence and strength
        signals.sort(key=lambda s: (s.confidence, s.strength), reverse=True)
        
        return signals

    async def execute_signal(self, signal: ScalpingSignal) -> bool:
        """Execute a scalping signal.
        
        Args:
            signal: Signal to execute
            
        Returns:
            True if execution was successful
        """
        async with self._lock:
            # Check if we can open a position
            if not await self._can_open_position():
                log.info(f"Cannot open position: max positions reached")
                return False
            
            # Check for existing position on this symbol
            position = await self.position_manager.get_position_for_symbol(signal.symbol)
            if position:
                log.info(f"Cannot open position: already have position for {signal.symbol}")
                return False
            
            # Check cooldown
            last_time = self._last_signal_time.get(signal.symbol)
            if last_time:
                elapsed = (datetime.now(timezone.utc) - last_time).total_seconds()
                if elapsed < self._signal_cooldown:
                    log.info(f"Cannot execute signal: cooldown not expired for {signal.symbol}")
                    return False
            
            # Execute trade
            try:
                # Determine side
                side = "OrderSide.BUY" if signal.signal_type.value.startswith("buy") else "OrderSide.SELL"
                
                # Calculate quantity based on risk
                current_price = signal.entry_price
                balance = 1000.0  # Would use actual balance
                qty = self._calculate_position_size(
                    current_price,
                    signal.stop_loss,
                    self.config.risk_per_trade_pct,
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
                    trailing_stop=self.config.trailing_stop_pct,
                    entry_order_id=order.order_id,
                    test=True
                )
                
                # Update signal tracking
                self._last_signal_time[signal.symbol] = datetime.now(timezone.utc)
                self._active_signals[signal.symbol] = signal
                
                log.info(f"Executed scalping signal: {signal.symbol} {side} {qty} @ {current_price}")
                return True
                
            except Exception as e:
                log.error(f"Failed to execute signal: {e}")
                return False

    # ========================================================================
    # ANALYSIS METHODS
    # ========================================================================

    async def _initialize_data(self) -> None:
        """Initialize data for all symbols."""
        for symbol in self.symbols:
            for tf in self.config.timeframes:
                try:
                    await self.data_collector.fetch_ohlcv(
                        symbol=symbol,
                        timeframe=tf,
                        limit=100
                    )
                except Exception as e:
                    log.error(f"Failed to initialize data for {symbol}/{tf}: {e}")

    async def _analyze_symbol(self, symbol: str) -> Optional[ScalpingSignal]:
        """Analyze a single symbol for trading opportunities.
        
        Args:
            symbol: Symbol to analyze
            
        Returns:
            ScalpingSignal or None
        """
        try:
            # Fetch data
            fast_df = await self.data_collector.fetch_ohlcv(
                symbol=symbol,
                timeframe=self.config.fast_timeframe,
                limit=50
            )
            
            slow_df = await self.data_collector.fetch_ohlcv(
                symbol=symbol,
                timeframe=self.config.slow_timeframe,
                limit=50
            )
            
            if fast_df is None or slow_df is None:
                return None
            
            # Calculate indicators
            fast_indicators = self._calculate_indicators(fast_df)
            slow_indicators = self._calculate_indicators(slow_df)
            
            # Check volume
            fast_volume = fast_df['volume'].iloc[-1]
            if fast_volume < self.config.min_volume:
                return None
            
            # Check volatility
            fast_volatility = self._calculate_volatility(fast_df)
            if fast_volatility < self.config.min_volatility:
                return None
            
            # Generate signal
            return self._generate_signal(
                symbol,
                fast_df,
                fast_indicators,
                slow_df,
                slow_indicators
            )
            
        except Exception as e:
            log.error(f"Failed to analyze {symbol}: {e}")
            return None

    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate technical indicators for scalping.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Dictionary of indicator name -> Series
        """
        indicators = {}
        
        # EMAs for trend
        for period in [5, 10, 20]:
            indicators[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        
        # RSI for momentum
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(com=5, min_periods=5).mean()
        avg_loss = loss.ewm(com=5, min_periods=5).mean()
        rs = avg_gain / avg_loss
        indicators['rsi'] = 100 - (100 / (1 + rs))
        
        # Volume indicators
        indicators['volume_sma_5'] = df['volume'].rolling(window=5).mean()
        indicators['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        
        # ATR for volatility
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift(1))
        low_close = abs(df['low'] - df['close'].shift(1))
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        indicators['atr'] = true_range.ewm(span=5, adjust=False).mean()
        
        return indicators

    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Calculate volatility as percentage.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Volatility percentage
        """
        returns = df['close'].pct_change().dropna()
        return float(returns.std() * 100)

    def _generate_signal(
        self,
        symbol: str,
        fast_df: pd.DataFrame,
        fast_indicators: Dict[str, pd.Series],
        slow_df: pd.DataFrame,
        slow_indicators: Dict[str, pd.Series]
    ) -> Optional[ScalpingSignal]:
        """Generate a trading signal from indicator data.
        
        Args:
            symbol: Symbol
            fast_df: Fast timeframe data
            fast_indicators: Fast timeframe indicators
            slow_df: Slow timeframe data
            slow_indicators: Slow timeframe indicators
            
        Returns:
            ScalpingSignal or None
        """
        # Get current prices
        fast_close = fast_df['close'].iloc[-1]
        slow_close = slow_df['close'].iloc[-1]
        
        # Get recent highs/lows
        fast_high = fast_df['high'].iloc[-1]
        fast_low = fast_df['low'].iloc[-1]
        
        # Get indicators
        fast_rsi = fast_indicators['rsi'].iloc[-1]
        slow_rsi = slow_indicators['rsi'].iloc[-1]
        
        fast_ema_5 = fast_indicators['ema_5'].iloc[-1]
        fast_ema_10 = fast_indicators['ema_10'].iloc[-1]
        fast_ema_20 = fast_indicators['ema_20'].iloc[-1]
        
        slow_ema_5 = slow_indicators['ema_5'].iloc[-1]
        slow_ema_10 = slow_indicators['ema_10'].iloc[-1]
        
        # Get volumes
        fast_volume = fast_df['volume'].iloc[-1]
        fast_volume_sma_5 = fast_indicators['volume_sma_5'].iloc[-1]
        
        # Check for buy signals
        buy_score = 0
        
        # Price above EMAs
        if fast_close > fast_ema_5:
            buy_score += 1
        if fast_close > fast_ema_10:
            buy_score += 1
        if fast_close > fast_ema_20:
            buy_score += 1
        
        # EMAs aligned bullish
        if fast_ema_5 > fast_ema_10 > fast_ema_20:
            buy_score += 2
        
        # Volume spike
        if fast_volume > fast_volume_sma_5 * 1.5:
            buy_score += 1
        
        # RSI not overbought
        if fast_rsi < self.config.rsi_overbought:
            buy_score += 1
        
        # Slow timeframe confirmation
        if slow_close > slow_ema_5:
            buy_score += 1
        
        # Check for sell signals
        sell_score = 0
        
        if fast_close < fast_ema_5:
            sell_score += 1
        if fast_close < fast_ema_10:
            sell_score += 1
        if fast_close < fast_ema_20:
            sell_score += 1
        
        if fast_ema_5 < fast_ema_10 < fast_ema_20:
            sell_score += 2
        
        if fast_volume > fast_volume_sma_5 * 1.5:
            sell_score += 1
        
        if fast_rsi > self.config.rsi_oversold:
            sell_score += 1
        
        if slow_close < slow_ema_5:
            sell_score += 1
        
        # Determine signal
        if buy_score >= 5:
            signal_type = ScalpingSignal.STRONG_BUY
            confidence = min(buy_score * 15, 100)
        elif buy_score >= 3:
            signal_type = ScalpingSignal.BUY
            confidence = buy_score * 15
        elif sell_score >= 5:
            signal_type = ScalpingSignal.STRONG_SELL
            confidence = min(sell_score * 15, 100)
        elif sell_score >= 3:
            signal_type = ScalpingSignal.SELL
            confidence = sell_score * 15
        else:
            return None
        
        # Calculate levels
        atr = fast_indicators['atr'].iloc[-1]
        stop_loss = fast_close - atr if signal_type.value.startswith("buy") else fast_close + atr
        take_profit = fast_close + (atr * 2) if signal_type.value.startswith("buy") else fast_close - (atr * 2)
        
        return ScalpingSignal(
            signal_type=signal_type,
            symbol=symbol,
            timeframe=self.config.fast_timeframe,
            entry_price=fast_close,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            strength=min(buy_score, sell_score) * 10,
            indicators={
                "fast_rsi": float(fast_rsi),
                "slow_rsi": float(slow_rsi),
                "fast_ema_5": float(fast_ema_5),
                "fast_ema_10": float(fast_ema_10),
                "volume": float(fast_volume)
            }
        )

    # ========================================================================
    # POSITION MANAGEMENT
    # ========================================================================

    async def _can_open_position(self) -> bool:
        """Check if we can open a new position.
        
        Returns:
            True if a new position can be opened
        """
        open_positions = await self.position_manager.get_open_positions()
        return len(open_positions) < self.config.max_positions

    async def _close_all_positions(self) -> None:
        """Close all open positions."""
        positions = await self.position_manager.get_open_positions()
        for position in positions:
            try:
                current_price = position.entry_price  # Would use current price
                await self.position_manager.close_position(
                    position_id=position.position_id,
                    exit_price=current_price,
                    exit_reason="ExitReason.MANUAL"
                )
            except Exception as e:
                log.error(f"Failed to close position {position.position_id}: {e}")

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
    # MONITORING
    # ========================================================================

    async def monitor_positions(self, current_prices: Dict[str, float]) -> None:
        """Monitor open positions for exits.
        
        Args:
            current_prices: Dictionary of symbol -> current price
        """
        positions = await self.position_manager.get_open_positions()
        
        for position in positions:
            current_price = current_prices.get(position.symbol)
            if current_price is None:
                continue
            
            # Check stop-loss
            if position.stop_loss and ((position.side.value == "long" and current_price <= position.stop_loss) or
                                    (position.side.value == "short" and current_price >= position.stop_loss)):
                await self._exit_position(position, current_price, "stop_loss")
            
            # Check take-profit
            elif position.take_profit and ((position.side.value == "long" and current_price >= position.take_profit) or
                                         (position.side.value == "short" and current_price <= position.take_profit)):
                await self._exit_position(position, current_price, "take_profit")

    async def _exit_position(self, position: "Position", exit_price: float, reason: str) -> None:
        """Exit a position.
        
        Args:
            position: Position to exit
            exit_price: Exit price
            reason: Exit reason
        """
        try:
            # Determine exit side
            side = "OrderSide.SELL" if position.side.value == "long" else "OrderSide.BUY"
            
            # Create exit order
            order = await self.order_manager.create_order(
                symbol=position.symbol,
                side=side,
                order_type="OrderType.MARKET",
                qty=position.current_qty,
                test=True
            )
            
            # Close position
            await self.position_manager.close_position(
                position_id=position.position_id,
                exit_price=exit_price,
                exit_reason=reason,
                exit_order_id=order.order_id
            )
            
            # Remove from active signals
            if position.symbol in self._active_signals:
                del self._active_signals[position.symbol]
            
            log.info(f"Exited position: {position.symbol} @ {exit_price} ({reason})")
            
        except Exception as e:
            log.error(f"Failed to exit position {position.position_id}: {e}")

    # ========================================================================
    # STATISTICS
    # ========================================================================

    async def get_statistics(self) -> Dict[str, Any]:
        """Get strategy statistics.
        
        Returns:
            Dictionary with strategy statistics
        """
        return {
            "active_signals": len(self._active_signals),
            "active_positions": len(await self.position_manager.get_open_positions()),
            "config": {
                "timeframes": self.config.timeframes,
                "profit_target_pct": self.config.profit_target_pct,
                "stop_loss_pct": self.config.stop_loss_pct,
                "max_positions": self.config.max_positions,
                "mode": self.config.mode.value
            }
        }

    async def get_active_signals(self) -> List[ScalpingSignal]:
        """Get all active signals.
        
        Returns:
            List of active ScalpingSignal objects
        """
        return list(self._active_signals.values())

    async def clear_signals(self) -> None:
        """Clear all active signals."""
        self._active_signals.clear()
        self._last_signal_time.clear()
        log.info("Cleared all active signals")
