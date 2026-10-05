"""Multi-Timeframe Analyzer for T01 Smart Binance Intelligence v2.

This module provides comprehensive multi-timeframe analysis capabilities.
It analyzes price action across multiple timeframes to identify:

1. Trend confluence (higher timeframes confirming lower timeframe trends)
2. Support and resistance levels across timeframes
3. Divergences between timeframes
4. Breakout confirmations
5. Multi-timeframe momentum alignment

The analyzer works with the data collector to fetch and cache OHLCV data
for multiple timeframes, then performs analysis to generate trading signals.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from backend.data.collector import DataCollector
    from backend.data.database import Database

log = logging.getLogger("analysis.multitimeframe")


# ============================================================================
# ENUMS
# ============================================================================

class Timeframe(Enum):
    """Supported timeframes for analysis."""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H2 = "2h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


class TrendDirection(Enum):
    """Trend direction."""
    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"


class ConfluenceType(Enum):
    """Type of timeframe confluence."""
    TREND = "trend"              # Higher TF confirms lower TF trend
    REVERSAL = "reversal"        # Higher TF suggests reversal of lower TF
    BREAKOUT = "breakout"        # Breakout confirmed across timeframes
    SUPPORT = "support"          # Support level across timeframes
    RESISTANCE = "resistance"    # Resistance level across timeframes
    DIVERGENCE = "divergence"    # Divergence between timeframes


class MTFSignalType(Enum):
    """Multi-timeframe signal types."""
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
class TimeframeData:
    """Data for a single timeframe.
    
    Attributes:
        timeframe: Timeframe
        df: DataFrame with OHLCV data
        indicators: Dictionary of calculated indicators
        trend: Current trend direction
        trend_strength: Strength of trend (0-100)
        support_levels: List of support levels
        resistance_levels: List of resistance levels
        last_close: Last closing price
        last_open: Last opening price
        last_high: Last high price
        last_low: Last low price
        last_volume: Last volume
    """
    timeframe: Timeframe = Timeframe.M15
    df: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    indicators: Dict[str, pd.Series] = field(default_factory=dict)
    trend: TrendDirection = TrendDirection.SIDEWAYS
    trend_strength: float = 0.0
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)
    last_close: float = 0.0
    last_open: float = 0.0
    last_high: float = 0.0
    last_low: float = 0.0
    last_volume: float = 0.0


@dataclass
class ConfluencePoint:
    """Represents a confluence point across timeframes.
    
    Attributes:
        confluence_type: Type of confluence
        timeframes: List of timeframes involved
        price: Price level of confluence
        strength: Strength of confluence (0-100)
        description: Human-readable description
        timestamp: When the confluence was detected
    """
    confluence_type: ConfluenceType = ConfluenceType.TREND
    timeframes: List[Timeframe] = field(default_factory=list)
    price: float = 0.0
    strength: float = 0.0
    description: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MTFSignal:
    """Multi-timeframe trading signal.
    
    Attributes:
        signal_type: Type of signal
        symbol: Trading pair
        timeframes: List of timeframes analyzed
        base_timeframe: Primary timeframe for the signal
        confluence_points: List of confluence points
        strength: Signal strength (0-100)
        confidence: Signal confidence (0-100)
        direction: Recommended trade direction
        entry_price: Suggested entry price
        stop_loss: Suggested stop-loss price
        take_profit: Suggested take-profit price
        risk_reward: Risk/reward ratio
        timestamp: When the signal was generated
    """
    signal_type: MTFSignalType = MTFSignalType.NEUTRAL
    symbol: str = ""
    timeframes: List[Timeframe] = field(default_factory=list)
    base_timeframe: Timeframe = Timeframe.M15
    confluence_points: List[ConfluencePoint] = field(default_factory=list)
    strength: float = 0.0
    confidence: float = 0.0
    direction: TrendDirection = TrendDirection.SIDEWAYS
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_reward: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary."""
        return {
            "signal_type": self.signal_type.value,
            "symbol": self.symbol,
            "timeframes": [tf.value for tf in self.timeframes],
            "base_timeframe": self.base_timeframe.value,
            "confluence_points": [
                {
                    "type": cp.confluence_type.value,
                    "timeframes": [tf.value for tf in cp.timeframes],
                    "price": cp.price,
                    "strength": cp.strength,
                    "description": cp.description
                }
                for cp in self.confluence_points
            ],
            "strength": self.strength,
            "confidence": self.confidence,
            "direction": self.direction.value,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_reward": self.risk_reward,
            "timestamp": self.timestamp.isoformat()
        }


# ============================================================================
# MULTI-TIMEFRAME ANALYZER
# ============================================================================

class MultiTimeframeAnalyzer:
    """Analyzes price action across multiple timeframes.
    
    The MultiTimeframeAnalyzer provides:
    
    1. Data collection and caching for multiple timeframes
    2. Trend analysis across timeframes
    3. Confluence detection (trend, support, resistance, breakouts)
    4. Divergence detection between timeframes
    5. Signal generation based on multi-timeframe analysis
    6. Integration with trading bot for signal execution
    
    The analyzer works by:
    - Fetching OHLCV data for configured timeframes
    - Calculating indicators for each timeframe
    - Detecting trends and key levels
    - Finding confluence points where multiple timeframes agree
    - Generating trading signals based on confluence
    """

    def __init__(
        self,
        data_collector: "DataCollector",
        db: Optional["Database"] = None,
        timeframes: Optional[List[Timeframe]] = None,
        symbol: str = "BTC/USDT"
    ):
        """Initialize MultiTimeframeAnalyzer.
        
        Args:
            data_collector: DataCollector instance for fetching data
            db: Optional database for persistence
            timeframes: List of timeframes to analyze
            symbol: Default symbol to analyze
        """
        self.data_collector = data_collector
        self.db = db
        self.symbol = symbol
        
        # Configure timeframes (default: 1m, 5m, 15m, 1h, 4h)
        self.timeframes = timeframes or [
            Timeframe.M1,
            Timeframe.M5,
            Timeframe.M15,
            Timeframe.H1,
            Timeframe.H4
        ]
        
        # Data cache: symbol -> timeframe -> TimeframeData
        self._data_cache: Dict[str, Dict[Timeframe, TimeframeData]] = {}
        
        # Last analysis timestamp
        self._last_analysis: Optional[datetime] = None
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Analysis parameters
        self._min_candles = 50  # Minimum candles required for analysis
        self._trend_period = 20  # Period for trend detection
        self._support_lookback = 5  # Candles to look back for support
        self._resistance_lookback = 5  # Candles to look back for resistance
        
        log.info(f"MultiTimeframeAnalyzer initialized for {symbol}")

    # ========================================================================
    # DATA MANAGEMENT
    # ========================================================================

    async def fetch_data(
        self,
        symbol: str,
        timeframes: Optional[List[Timeframe]] = None,
        limit: int = 100
    ) -> Dict[Timeframe, TimeframeData]:
        """Fetch OHLCV data for multiple timeframes.
        
        Args:
            symbol: Trading pair
            timeframes: List of timeframes to fetch (default: all configured)
            limit: Number of candles to fetch per timeframe
            
        Returns:
            Dictionary of timeframe -> TimeframeData
        """
        async with self._lock:
            tf_data = {}
            
            for tf in timeframes or self.timeframes:
                try:
                    # Fetch OHLCV data
                    df = await self.data_collector.fetch_ohlcv(
                        symbol=symbol,
                        timeframe=tf.value,
                        limit=limit
                    )
                    
                    if df is None or len(df) < self._min_candles:
                        log.warning(f"Insufficient data for {symbol}/{tf.value}: {len(df) if df is not None else 0} candles")
                        continue
                    
                    # Create TimeframeData
                    tf_data[tf] = await self._process_timeframe_data(df, tf)
                    
                except Exception as e:
                    log.error(f"Failed to fetch data for {symbol}/{tf.value}: {e}")
            
            # Cache data
            if symbol not in self._data_cache:
                self._data_cache[symbol] = {}
            self._data_cache[symbol].update(tf_data)
            
            return tf_data

    async def _process_timeframe_data(
        self,
        df: pd.DataFrame,
        tf: Timeframe
    ) -> TimeframeData:
        """Process OHLCV data for a timeframe.
        
        Args:
            df: OHLCV DataFrame
            tf: Timeframe
            
        Returns:
            Processed TimeframeData
        """
        # Ensure we have required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                log.error(f"Missing column {col} in OHLCV data")
                raise ValueError(f"Missing column {col}")
        
        # Calculate indicators
        indicators = self._calculate_indicators(df)
        
        # Detect trend
        trend, trend_strength = self._detect_trend(df, indicators)
        
        # Detect support and resistance
        support_levels = self._detect_support_levels(df)
        resistance_levels = self._detect_resistance_levels(df)
        
        # Get last values
        last_row = df.iloc[-1]
        
        return TimeframeData(
            timeframe=tf,
            df=df,
            indicators=indicators,
            trend=trend,
            trend_strength=trend_strength,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            last_close=float(last_row['close']),
            last_open=float(last_row['open']),
            last_high=float(last_row['high']),
            last_low=float(last_row['low']),
            last_volume=float(last_row['volume'])
        )

    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate technical indicators for a DataFrame.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Dictionary of indicator name -> Series
        """
        indicators = {}
        
        # Simple Moving Averages
        for period in [9, 20, 50, 100, 200]:
            indicators[f'sma_{period}'] = df['close'].rolling(window=period).mean()
        
        # Exponential Moving Averages
        for period in [9, 20, 50]:
            indicators[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(com=13, min_periods=13).mean()
        avg_loss = loss.ewm(com=13, min_periods=13).mean()
        rs = avg_gain / avg_loss
        indicators['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        indicators['macd'] = ema_12 - ema_26
        signal_line = indicators['macd'].ewm(span=9, adjust=False).mean()
        indicators['macd_signal'] = signal_line
        indicators['macd_histogram'] = indicators['macd'] - signal_line
        
        # Bollinger Bands
        sma_20 = df['close'].rolling(window=20).mean()
        std_20 = df['close'].rolling(window=20).std()
        indicators['bb_upper'] = sma_20 + (std_20 * 2)
        indicators['bb_middle'] = sma_20
        indicators['bb_lower'] = sma_20 - (std_20 * 2)
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift(1))
        low_close = abs(df['low'] - df['close'].shift(1))
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        indicators['atr'] = true_range.ewm(span=14, adjust=False).mean()
        
        # Volume indicators
        indicators['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        
        return indicators

    def _detect_trend(
        self,
        df: pd.DataFrame,
        indicators: Dict[str, pd.Series]
    ) -> Tuple[TrendDirection, float]:
        """Detect trend direction and strength.
        
        Args:
            df: OHLCV DataFrame
            indicators: Calculated indicators
            
        Returns:
            Tuple of (trend_direction, trend_strength)
        """
        # Use multiple indicators to detect trend
        close = df['close']
        sma_20 = indicators.get('sma_20')
        sma_50 = indicators.get('sma_50')
        ema_20 = indicators.get('ema_20')
        ema_50 = indicators.get('ema_50')
        rsi = indicators.get('rsi')
        macd = indicators.get('macd')
        
        if sma_20 is None or sma_50 is None:
            return TrendDirection.SIDEWAYS, 0.0
        
        # Price vs SMA
        price_above_sma_20 = close.iloc[-1] > sma_20.iloc[-1]
        price_above_sma_50 = close.iloc[-1] > sma_50.iloc[-1]
        sma_20_above_sma_50 = sma_20.iloc[-1] > sma_50.iloc[-1]
        
        # RSI
        rsi_value = rsi.iloc[-1] if rsi is not None else 50
        
        # MACD
        macd_value = macd.iloc[-1] if macd is not None else 0
        macd_signal = indicators.get('macd_signal')
        macd_signal_value = macd_signal.iloc[-1] if macd_signal is not None else 0
        
        # Count bullish and bearish signals
        bullish = 0
        bearish = 0
        
        if price_above_sma_20:
            bullish += 1
        else:
            bearish += 1
            
        if price_above_sma_50:
            bullish += 1
        else:
            bearish += 1
            
        if sma_20_above_sma_50:
            bullish += 1
        else:
            bearish += 1
            
        if rsi_value > 50:
            bullish += 1
        else:
            bearish += 1
            
        if macd_value > macd_signal_value:
            bullish += 1
        else:
            bearish += 1
        
        total = bullish + bearish
        if total == 0:
            return TrendDirection.SIDEWAYS, 0.0
        
        score = bullish / total
        
        if score >= 0.7:
            return TrendDirection.UP, score * 100
        elif score <= 0.3:
            return TrendDirection.DOWN, (1 - score) * 100
        else:
            return TrendDirection.SIDEWAYS, 50.0

    def _detect_support_levels(self, df: pd.DataFrame) -> List[float]:
        """Detect support levels.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            List of support price levels
        """
        levels = []
        lookback = min(self._support_lookback, len(df))
        
        for i in range(-lookback, 0):
            row = df.iloc[i]
            
            # Check if this low was followed by a bounce
            if i + 1 < len(df):
                next_row = df.iloc[i + 1]
                if next_row['close'] > row['low']:
                    # Potential support
                    levels.append(float(row['low']))
        
        # Cluster nearby levels
        if levels:
            levels = self._cluster_levels(levels, threshold=0.005)
        
        return sorted(levels, reverse=True)

    def _detect_resistance_levels(self, df: pd.DataFrame) -> List[float]:
        """Detect resistance levels.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            List of resistance price levels
        """
        levels = []
        lookback = min(self._resistance_lookback, len(df))
        
        for i in range(-lookback, 0):
            row = df.iloc[i]
            
            # Check if this high was followed by a rejection
            if i + 1 < len(df):
                next_row = df.iloc[i + 1]
                if next_row['close'] < row['high']:
                    # Potential resistance
                    levels.append(float(row['high']))
        
        # Cluster nearby levels
        if levels:
            levels = self._cluster_levels(levels, threshold=0.005)
        
        return sorted(levels)

    def _cluster_levels(self, levels: List[float], threshold: float = 0.005) -> List[float]:
        """Cluster nearby price levels.
        
        Args:
            levels: List of price levels
            threshold: Percentage threshold for clustering
            
        Returns:
            List of clustered levels
        """
        if not levels:
            return []
        
        # Sort levels
        levels = sorted(levels)
        
        # Cluster
        clustered = []
        current_cluster = [levels[0]]
        
        for level in levels[1:]:
            if abs(level - current_cluster[-1]) / current_cluster[-1] <= threshold:
                current_cluster.append(level)
            else:
                # Add average of cluster
                clustered.append(sum(current_cluster) / len(current_cluster))
                current_cluster = [level]
        
        # Add last cluster
        clustered.append(sum(current_cluster) / len(current_cluster))
        
        return clustered

    # ========================================================================
    # CONFLUENCE ANALYSIS
    # ========================================================================

    async def analyze_confluence(
        self,
        symbol: str,
        timeframes: Optional[List[Timeframe]] = None
    ) -> List[ConfluencePoint]:
        """Analyze confluence across timeframes.
        
        Args:
            symbol: Trading pair
            timeframes: List of timeframes to analyze (default: all configured)
            
        Returns:
            List of detected confluence points
        """
        # Fetch data
        tf_data = await self.fetch_data(symbol, timeframes)
        
        if len(tf_data) < 2:
            return []
        
        confluence_points = []
        
        # Check for trend confluence
        confluence_points.extend(self._analyze_trend_confluence(tf_data))
        
        # Check for support/resistance confluence
        confluence_points.extend(self._analyze_support_confluence(tf_data))
        
        # Check for breakout confluence
        confluence_points.extend(self._analyze_breakout_confluence(tf_data))
        
        # Check for divergences
        confluence_points.extend(self._analyze_divergences(tf_data))
        
        return confluence_points

    def _analyze_trend_confluence(
        self,
        tf_data: Dict[Timeframe, TimeframeData]
    ) -> List[ConfluencePoint]:
        """Analyze trend confluence across timeframes.
        
        Args:
            tf_data: Dictionary of timeframe data
            
        Returns:
            List of trend confluence points
        """
        points = []
        
        # Get sorted timeframes by period (smallest to largest)
        sorted_tfs = sorted(
            tf_data.keys(),
            key=lambda tf: self._timeframe_to_minutes(tf)
        )
        
        # Check for trend agreement
        for i in range(len(sorted_tfs)):
            for j in range(i + 1, len(sorted_tfs)):
                tf1 = sorted_tfs[i]
                tf2 = sorted_tfs[j]
                
                data1 = tf_data[tf1]
                data2 = tf_data[tf2]
                
                # If both trends agree
                if data1.trend == data2.trend and data1.trend != TrendDirection.SIDEWAYS:
                    strength = (data1.trend_strength + data2.trend_strength) / 2
                    
                    # Higher timeframe confirms lower timeframe
                    points.append(ConfluencePoint(
                        confluence_type=ConfluenceType.TREND,
                        timeframes=[tf1, tf2],
                        price=data2.last_close,  # Use higher TF close
                        strength=strength,
                        description=f"{tf2.value} confirms {tf1.value} {data1.trend.value} trend"
                    ))
                
                # If trends disagree (potential reversal)
                elif data1.trend != TrendDirection.SIDEWAYS and data2.trend != TrendDirection.SIDEWAYS:
                    if (data1.trend == TrendDirection.UP and data2.trend == TrendDirection.DOWN) or \
                       (data1.trend == TrendDirection.DOWN and data2.trend == TrendDirection.UP):
                        
                        strength = (data1.trend_strength + data2.trend_strength) / 2
                        
                        points.append(ConfluencePoint(
                            confluence_type=ConfluenceType.REVERSAL,
                            timeframes=[tf1, tf2],
                            price=data2.last_close,
                            strength=strength,
                            description=f"{tf2.value} suggests reversal of {tf1.value} {data1.trend.value} trend"
                        ))
        
        return points

    def _analyze_support_confluence(
        self,
        tf_data: Dict[Timeframe, TimeframeData]
    ) -> List[ConfluencePoint]:
        """Analyze support level confluence across timeframes.
        
        Args:
            tf_data: Dictionary of timeframe data
            
        Returns:
            List of support confluence points
        """
        points = []
        
        # Collect all support levels
        all_support = {}
        for tf, data in tf_data.items():
            for level in data.support_levels:
                if level not in all_support:
                    all_support[level] = []
                all_support[level].append(tf)
        
        # Find levels that appear in multiple timeframes
        for level, tfs in all_support.items():
            if len(tfs) >= 2:
                strength = min(len(tfs) * 20, 100)  # 2 TFs = 40, 3 TFs = 60, etc.
                
                points.append(ConfluencePoint(
                    confluence_type=ConfluenceType.SUPPORT,
                    timeframes=tfs,
                    price=level,
                    strength=strength,
                    description=f"Support at {level} across {len(tfs)} timeframes"
                ))
        
        return points

    def _analyze_breakout_confluence(
        self,
        tf_data: Dict[Timeframe, TimeframeData]
    ) -> List[ConfluencePoint]:
        """Analyze breakout confluence across timeframes.
        
        Args:
            tf_data: Dictionary of timeframe data
            
        Returns:
            List of breakout confluence points
        """
        points = []
        
        # Get sorted timeframes
        sorted_tfs = sorted(
            tf_data.keys(),
            key=lambda tf: self._timeframe_to_minutes(tf)
        )
        
        # Check if price broke above resistance or below support
        for i in range(len(sorted_tfs)):
            tf = sorted_tfs[i]
            data = tf_data[tf]
            
            # Check for break above resistance
            if data.resistance_levels:
                highest_resistance = max(data.resistance_levels)
                if data.last_close > highest_resistance:
                    # Check if higher timeframes also show breakout
                    for j in range(i + 1, len(sorted_tfs)):
                        higher_tf = sorted_tfs[j]
                        higher_data = tf_data[higher_tf]
                        
                        if higher_data.last_close > highest_resistance:
                            strength = (data.trend_strength + higher_data.trend_strength) / 2
                            
                            points.append(ConfluencePoint(
                                confluence_type=ConfluenceType.BREAKOUT,
                                timeframes=[tf, higher_tf],
                                price=data.last_close,
                                strength=strength,
                                description=f"Breakout above {highest_resistance} confirmed on {higher_tf.value}"
                            ))
            
            # Check for break below support
            if data.support_levels:
                lowest_support = min(data.support_levels)
                if data.last_close < lowest_support:
                    # Check if higher timeframes also show breakdown
                    for j in range(i + 1, len(sorted_tfs)):
                        higher_tf = sorted_tfs[j]
                        higher_data = tf_data[higher_tf]
                        
                        if higher_data.last_close < lowest_support:
                            strength = (data.trend_strength + higher_data.trend_strength) / 2
                            
                            points.append(ConfluencePoint(
                                confluence_type=ConfluenceType.BREAKOUT,
                                timeframes=[tf, higher_tf],
                                price=data.last_close,
                                strength=strength,
                                description=f"Breakdown below {lowest_support} confirmed on {higher_tf.value}"
                            ))
        
        return points

    def _analyze_divergences(
        self,
        tf_data: Dict[Timeframe, TimeframeData]
    ) -> List[ConfluencePoint]:
        """Analyze divergences between timeframes.
        
        Args:
            tf_data: Dictionary of timeframe data
            
        Returns:
            List of divergence confluence points
        """
        points = []
        
        # Get sorted timeframes
        sorted_tfs = sorted(
            tf_data.keys(),
            key=lambda tf: self._timeframe_to_minutes(tf)
        )
        
        # Compare each pair of timeframes
        for i in range(len(sorted_tfs)):
            for j in range(i + 1, len(sorted_tfs)):
                tf1 = sorted_tfs[i]
                tf2 = sorted_tfs[j]
                
                data1 = tf_data[tf1]
                data2 = tf_data[tf2]
                
                # Check for bullish divergence (lower TF making higher lows while higher TF making lower lows)
                if self._is_bullish_divergence(data1, data2):
                    strength = (data1.trend_strength + data2.trend_strength) / 2
                    
                    points.append(ConfluencePoint(
                        confluence_type=ConfluenceType.DIVERGENCE,
                        timeframes=[tf1, tf2],
                        price=data1.last_close,
                        strength=strength,
                        description=f"Bullish divergence: {tf1.value} vs {tf2.value}"
                    ))
                
                # Check for bearish divergence (lower TF making lower highs while higher TF making higher highs)
                elif self._is_bearish_divergence(data1, data2):
                    strength = (data1.trend_strength + data2.trend_strength) / 2
                    
                    points.append(ConfluencePoint(
                        confluence_type=ConfluenceType.DIVERGENCE,
                        timeframes=[tf1, tf2],
                        price=data1.last_close,
                        strength=strength,
                        description=f"Bearish divergence: {tf1.value} vs {tf2.value}"
                    ))
        
        return points

    def _is_bullish_divergence(
        self,
        data1: TimeframeData,
        data2: TimeframeData
    ) -> bool:
        """Check for bullish divergence between two timeframes.
        
        Args:
            data1: Lower timeframe data
            data2: Higher timeframe data
            
        Returns:
            True if bullish divergence detected
        """
        # Lower TF making higher lows
        if len(data1.df) >= 2:
            lower_lows = data1.df['low'].iloc[-2:].values
            if lower_lows[1] > lower_lows[0]:  # Higher low
                # Higher TF making lower lows
                if len(data2.df) >= 2:
                    higher_lows = data2.df['low'].iloc[-2:].values
                    if higher_lows[1] < higher_lows[0]:  # Lower low
                        return True
        
        return False

    def _is_bearish_divergence(
        self,
        data1: TimeframeData,
        data2: TimeframeData
    ) -> bool:
        """Check for bearish divergence between two timeframes.
        
        Args:
            data1: Lower timeframe data
            data2: Higher timeframe data
            
        Returns:
            True if bearish divergence detected
        """
        # Lower TF making lower highs
        if len(data1.df) >= 2:
            lower_highs = data1.df['high'].iloc[-2:].values
            if lower_highs[1] < lower_highs[0]:  # Lower high
                # Higher TF making higher highs
                if len(data2.df) >= 2:
                    higher_highs = data2.df['high'].iloc[-2:].values
                    if higher_highs[1] > higher_highs[0]:  # Higher high
                        return True
        
        return False

    # ========================================================================
    # SIGNAL GENERATION
    # ========================================================================

    async def generate_signal(
        self,
        symbol: str,
        timeframes: Optional[List[Timeframe]] = None,
        base_timeframe: Optional[Timeframe] = None
    ) -> MTFSignal:
        """Generate a multi-timeframe trading signal.
        
        Args:
            symbol: Trading pair
            timeframes: List of timeframes to analyze
            base_timeframe: Primary timeframe for the signal
            
        Returns:
            MTFSignal with trading recommendation
        """
        # Fetch and analyze data
        tf_data = await self.fetch_data(symbol, timeframes)
        
        if not tf_data:
            return MTFSignal(
                signal_type=MTFSignalType.NEUTRAL,
                symbol=symbol,
                timeframes=timeframes or self.timeframes,
                base_timeframe=base_timeframe or self.timeframes[len(self.timeframes) // 2]
            )
        
        # Analyze confluence
        confluence_points = await self.analyze_confluence(symbol, timeframes)
        
        # Determine base timeframe
        bt = base_timeframe or self.timeframes[len(self.timeframes) // 2]
        base_data = tf_data.get(bt)
        
        if not base_data:
            bt = list(tf_data.keys())[len(tf_data) // 2]
            base_data = tf_data[bt]
        
        # Analyze signal based on confluence
        signal_type, direction, strength, confidence = self._analyze_signal(
            tf_data, confluence_points, bt
        )
        
        # Calculate entry, stop-loss, take-profit
        entry_price, stop_loss, take_profit, risk_reward = self._calculate_levels(
            base_data, direction, signal_type
        )
        
        return MTFSignal(
            signal_type=signal_type,
            symbol=symbol,
            timeframes=list(tf_data.keys()),
            base_timeframe=bt,
            confluence_points=confluence_points,
            strength=strength,
            confidence=confidence,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=risk_reward
        )

    def _analyze_signal(
        self,
        tf_data: Dict[Timeframe, TimeframeData],
        confluence_points: List[ConfluencePoint],
        base_timeframe: Timeframe
    ) -> Tuple[MTFSignalType, TrendDirection, float, float]:
        """Analyze confluence points to determine signal.
        
        Args:
            tf_data: Timeframe data
            confluence_points: Detected confluence points
            base_timeframe: Base timeframe
            
        Returns:
            Tuple of (signal_type, direction, strength, confidence)
        """
        base_data = tf_data.get(base_timeframe)
        if not base_data:
            return MTFSignalType.NEUTRAL, TrendDirection.SIDEWAYS, 0.0, 0.0
        
        # Count confluence types
        trend_count = 0
        reversal_count = 0
        breakout_count = 0
        support_count = 0
        resistance_count = 0
        divergence_count = 0
        
        for cp in confluence_points:
            if cp.confluence_type == ConfluenceType.TREND:
                trend_count += 1
            elif cp.confluence_type == ConfluenceType.REVERSAL:
                reversal_count += 1
            elif cp.confluence_type == ConfluenceType.BREAKOUT:
                breakout_count += 1
            elif cp.confluence_type == ConfluenceType.SUPPORT:
                support_count += 1
            elif cp.confluence_type == ConfluenceType.RESISTANCE:
                resistance_count += 1
            elif cp.confluence_type == ConfluenceType.DIVERGENCE:
                divergence_count += 1
        
        # Determine direction from base timeframe
        direction = base_data.trend
        
        # Calculate strength and confidence
        total_confluence = len(confluence_points)
        
        if total_confluence == 0:
            # No confluence, use base trend
            if direction == TrendDirection.UP:
                return MTFSignalType.WEAK_BUY, direction, 30.0, 40.0
            elif direction == TrendDirection.DOWN:
                return MTFSignalType.WEAK_SELL, direction, 30.0, 40.0
            else:
                return MTFSignalType.NEUTRAL, direction, 0.0, 0.0
        
        # Calculate signal strength
        strength = min(total_confluence * 20, 100)  # Max 100 for 5+ confluence points
        
        # Calculate confidence based on confluence types
        confidence = 0.0
        
        if trend_count > 0:
            confidence += trend_count * 25
        if breakout_count > 0:
            confidence += breakout_count * 20
        if divergence_count > 0:
            confidence += divergence_count * 15
        
        confidence = min(confidence, 100)
        
        # Adjust based on direction
        if direction == TrendDirection.UP:
            if trend_count >= 2:
                signal_type = MTFSignalType.STRONG_BUY
            elif trend_count == 1:
                signal_type = MTFSignalType.BUY
            else:
                signal_type = MTFSignalType.WEAK_BUY
        elif direction == TrendDirection.DOWN:
            if trend_count >= 2:
                signal_type = MTFSignalType.STRONG_SELL
            elif trend_count == 1:
                signal_type = MTFSignalType.SELL
            else:
                signal_type = MTFSignalType.WEAK_SELL
        else:
            signal_type = MTFSignalType.NEUTRAL
        
        # If reversal confluence, reduce signal strength
        if reversal_count > 0:
            strength *= 0.7
            confidence *= 0.8
        
        return signal_type, direction, strength, confidence

    def _calculate_levels(
        self,
        base_data: TimeframeData,
        direction: TrendDirection,
        signal_type: MTFSignalType
    ) -> Tuple[float, float, float, float]:
        """Calculate entry, stop-loss, and take-profit levels.
        
        Args:
            base_data: Base timeframe data
            direction: Signal direction
            signal_type: Signal type
            
        Returns:
            Tuple of (entry_price, stop_loss, take_profit, risk_reward)
        """
        current_price = base_data.last_close
        atr = base_data.indicators.get('atr')
        atr_value = atr.iloc[-1] if atr is not None else 0
        
        if atr_value == 0:
            atr_value = current_price * 0.02  # 2% as fallback
        
        if direction == TrendDirection.UP:
            # Entry at current price (or slightly above for breakout)
            entry_price = current_price
            
            # Stop-loss based on ATR
            stop_loss = current_price - (atr_value * 1.5)
            
            # Take-profit based on signal strength
            if signal_type in [MTFSignalType.STRONG_BUY, MTFSignalType.BUY]:
                take_profit = current_price + (atr_value * 3)
            else:
                take_profit = current_price + (atr_value * 2)
            
        elif direction == TrendDirection.DOWN:
            entry_price = current_price
            stop_loss = current_price + (atr_value * 1.5)
            
            if signal_type in [MTFSignalType.STRONG_SELL, MTFSignalType.SELL]:
                take_profit = current_price - (atr_value * 3)
            else:
                take_profit = current_price - (atr_value * 2)
        else:
            return current_price, 0.0, 0.0, 0.0
        
        # Calculate risk/reward
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        risk_reward = reward / risk if risk > 0 else 0.0
        
        return entry_price, stop_loss, take_profit, risk_reward

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def _timeframe_to_minutes(self, tf: Timeframe) -> int:
        """Convert timeframe to minutes.
        
        Args:
            tf: Timeframe enum
            
        Returns:
            Number of minutes
        """
        tf_str = tf.value
        if tf_str.endswith('m'):
            return int(tf_str[:-1])
        elif tf_str.endswith('h'):
            return int(tf_str[:-1]) * 60
        elif tf_str.endswith('d'):
            return int(tf_str[:-1]) * 60 * 24
        elif tf_str.endswith('w'):
            return int(tf_str[:-1]) * 60 * 24 * 7
        return 1

    def get_timeframe_data(
        self,
        symbol: str,
        timeframe: Timeframe
    ) -> Optional[TimeframeData]:
        """Get cached timeframe data.
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe
            
        Returns:
            TimeframeData or None
        """
        if symbol in self._data_cache:
            return self._data_cache[symbol].get(timeframe)
        return None

    async def refresh_data(self, symbol: str) -> None:
        """Refresh data for a symbol.
        
        Args:
            symbol: Trading pair to refresh
        """
        await self.fetch_data(symbol)

    async def clear_cache(self) -> None:
        """Clear all cached data."""
        async with self._lock:
            self._data_cache.clear()
            log.info("Multi-timeframe data cache cleared")
