"""Pattern Detector for T01 Smart Binance Intelligence v2.

This module provides comprehensive candlestick pattern detection and analysis.
It identifies 20+ different candlestick patterns across multiple timeframes
and provides pattern-based trading signals.

Features:
- Single candle patterns (Doji, Hammer, Shooting Star, etc.)
- Double candle patterns (Engulfing, Harami, Tweezer, etc.)
- Triple candle patterns (Morning Star, Evening Star, Three White Soldiers, etc.)
- Pattern validation with confirmation rules
- Pattern strength and reliability scoring
- Multi-timeframe pattern confluence
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from backend.data.collector import DataCollector
    from backend.analysis.multitimeframe import Timeframe, MultiTimeframeAnalyzer

log = logging.getLogger("analysis.patterns")


# ============================================================================
# ENUMS
# ============================================================================

class PatternType(Enum):
    DOJI = "doji"
    HAMMER = "hammer"
    INVERTED_HAMMER = "inverted_hammer"
    HANGING_MAN = "hanging_man"
    SHOOTING_STAR = "shooting_star"
    MARUBOZU = "marubozu"
    SPINNING_TOP = "spinning_top"
    BULLISH_ENGULFING = "bullish_engulfing"
    BEARISH_ENGULFING = "bearish_engulfing"
    BULLISH_HARAMI = "bullish_harami"
    BEARISH_HARAMI = "bearish_harami"
    TWEEZER_BOTTOM = "tweezer_bottom"
    TWEEZER_TOP = "tweezer_top"
    PIERCING_LINE = "piercing_line"
    DARK_CLOUD_COVER = "dark_cloud_cover"
    MORNING_STAR = "morning_star"
    EVENING_STAR = "evening_star"
    THREE_WHITE_SOLDIERS = "three_white_soldiers"
    THREE_BLACK_CROWS = "three_black_crows"


class PatternDirection(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class PatternCategory(Enum):
    SINGLE = "single"
    DOUBLE = "double"
    TRIPLE = "triple"


class PatternReliability(Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class Candle:
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    is_bullish: bool = False
    is_bearish: bool = False
    body_size: float = 0.0
    upper_shadow: float = 0.0
    lower_shadow: float = 0.0
    body_ratio: float = 0.0

    def __post_init__(self):
        self.is_bullish = self.close > self.open
        self.is_bearish = self.close < self.open
        self.body_size = abs(self.close - self.open)
        self.upper_shadow = self.high - max(self.open, self.close)
        self.lower_shadow = min(self.open, self.close) - self.low
        total_range = self.high - self.low
        if total_range > 0:
            self.body_ratio = self.body_size / total_range

    @classmethod
    def from_row(cls, row: pd.Series) -> "Candle":
        return cls(
            open=float(row['open']),
            high=float(row['high']),
            low=float(row['low']),
            close=float(row['close']),
            volume=float(row.get('volume', 0))
        )


@dataclass
class Pattern:
    pattern_type: PatternType = PatternType.DOJI
    category: PatternCategory = PatternCategory.SINGLE
    direction: PatternDirection = PatternDirection.NEUTRAL
    reliability: PatternReliability = PatternReliability.MEDIUM
    candles: List[Candle] = field(default_factory=list)
    start_index: int = 0
    end_index: int = 0
    strength: float = 0.0
    confirmation_required: bool = False
    confirmed: bool = False
    signal_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_reward: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PatternSignal:
    pattern: Pattern = field(default_factory=Pattern)
    symbol: str = ""
    timeframe: str = "1h"
    action: str = "hold"
    confidence: float = 0.0
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_reward: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# PATTERN DETECTOR
# ============================================================================

class PatternDetector:
    def __init__(
        self,
        data_collector: Optional["DataCollector"] = None,
        mtf_analyzer: Optional["MultiTimeframeAnalyzer"] = None,
        min_candles: int = 100
    ):
        self.data_collector = data_collector
        self.mtf_analyzer = mtf_analyzer
        self.min_candles = min_candles
        self._doji_threshold = 0.1
        self._long_shadow_threshold = 0.6
        self._engulfing_threshold = 1.0
        self._marubozu_threshold = 0.95
        self._pattern_reliability = self._init_reliability()

    def _init_reliability(self) -> Dict[PatternType, PatternReliability]:
        return {
            PatternType.DOJI: PatternReliability.LOW,
            PatternType.HAMMER: PatternReliability.HIGH,
            PatternType.INVERTED_HAMMER: PatternReliability.MEDIUM,
            PatternType.HANGING_MAN: PatternReliability.HIGH,
            PatternType.SHOOTING_STAR: PatternReliability.HIGH,
            PatternType.MARUBOZU: PatternReliability.MEDIUM,
            PatternType.SPINNING_TOP: PatternReliability.LOW,
            PatternType.BULLISH_ENGULFING: PatternReliability.VERY_HIGH,
            PatternType.BEARISH_ENGULFING: PatternReliability.VERY_HIGH,
            PatternType.BULLISH_HARAMI: PatternReliability.MEDIUM,
            PatternType.BEARISH_HARAMI: PatternReliability.MEDIUM,
            PatternType.TWEEZER_BOTTOM: PatternReliability.HIGH,
            PatternType.TWEEZER_TOP: PatternReliability.HIGH,
            PatternType.PIERCING_LINE: PatternReliability.HIGH,
            PatternType.DARK_CLOUD_COVER: PatternReliability.HIGH,
            PatternType.MORNING_STAR: PatternReliability.VERY_HIGH,
            PatternType.EVENING_STAR: PatternReliability.VERY_HIGH,
            PatternType.THREE_WHITE_SOLDIERS: PatternReliability.HIGH,
            PatternType.THREE_BLACK_CROWS: PatternReliability.HIGH
        }

    async def detect_patterns(
        self, symbol: str, timeframe: str = "1h", limit: int = 100
    ) -> List[Pattern]:
        df = await self._fetch_ohlcv_data(symbol, timeframe, limit)
        if df is None or len(df) < self.min_candles:
            return []
        candles = [Candle.from_row(row) for _, row in df.iterrows()]
        patterns = []
        patterns.extend(self._detect_single_candle_patterns(candles))
        patterns.extend(self._detect_double_candle_patterns(candles))
        patterns.extend(self._detect_triple_candle_patterns(candles))
        patterns = [p for p in patterns if self._validate_pattern(p, candles)]
        patterns.sort(key=lambda p: p.end_index, reverse=True)
        return patterns

    async def detect_recent_patterns(
        self, symbol: str, timeframe: str = "1h", lookback: int = 10
    ) -> List[Pattern]:
        df = await self._fetch_ohlcv_data(symbol, timeframe, lookback * 3)
        if df is None or len(df) < lookback:
            return []
        candles = [Candle.from_row(row) for _, row in df.iterrows()]
        patterns = []
        if len(candles) >= 1:
            patterns.extend(self._detect_single_candle_patterns_on_index(candles, len(candles) - 1))
        if len(candles) >= 2:
            patterns.extend(self._detect_double_candle_patterns_on_index(candles, len(candles) - 2))
        if len(candles) >= 3:
            patterns.extend(self._detect_triple_candle_patterns_on_index(candles, len(candles) - 3))
        patterns = [p for p in patterns if self._validate_pattern(p, candles)]
        return patterns

    async def _fetch_ohlcv_data(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        if self.data_collector:
            try:
                return await self.data_collector.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)
            except Exception as e:
                log.error(f"Failed to fetch OHLCV data: {e}")
        return None

    def _detect_single_candle_patterns(self, candles: List[Candle]) -> List[Pattern]:
        patterns = []
        for i, candle in enumerate(candles):
            patterns.extend(self._detect_single_candle_patterns_on_index(candles, i))
        return patterns

    def _detect_single_candle_patterns_on_index(self, candles: List[Candle], index: int) -> List[Pattern]:
        if index >= len(candles):
            return []
        candle = candles[index]
        patterns = []
        if self._is_doji(candle):
            patterns.append(self._create_pattern(PatternType.DOJI, PatternCategory.SINGLE, PatternDirection.NEUTRAL, [candle], index, index))
        if self._is_hammer(candle):
            patterns.append(self._create_pattern(PatternType.HAMMER, PatternCategory.SINGLE, PatternDirection.BULLISH, [candle], index, index))
        if self._is_inverted_hammer(candle):
            patterns.append(self._create_pattern(PatternType.INVERTED_HAMMER, PatternCategory.SINGLE, PatternDirection.BULLISH, [candle], index, index))
        if self._is_hanging_man(candle):
            patterns.append(self._create_pattern(PatternType.HANGING_MAN, PatternCategory.SINGLE, PatternDirection.BEARISH, [candle], index, index))
        if self._is_shooting_star(candle):
            patterns.append(self._create_pattern(PatternType.SHOOTING_STAR, PatternCategory.SINGLE, PatternDirection.BEARISH, [candle], index, index))
        if self._is_marubozu(candle):
            direction = PatternDirection.BULLISH if candle.is_bullish else PatternDirection.BEARISH
            patterns.append(self._create_pattern(PatternType.MARUBOZU, PatternCategory.SINGLE, direction, [candle], index, index))
        if self._is_spinning_top(candle):
            patterns.append(self._create_pattern(PatternType.SPINNING_TOP, PatternCategory.SINGLE, PatternDirection.NEUTRAL, [candle], index, index))
        return patterns

    def _is_doji(self, candle: Candle) -> bool:
        return candle.body_ratio < self._doji_threshold

    def _is_hammer(self, candle: Candle) -> bool:
        if not candle.is_bullish:
            return False
        return candle.lower_shadow_ratio > 0.66 and candle.upper_shadow_ratio < 0.1 and candle.lower_shadow > candle.body_size * 2

    def _is_inverted_hammer(self, candle: Candle) -> bool:
        if not candle.is_bullish:
            return False
        return candle.upper_shadow_ratio > 0.66 and candle.lower_shadow_ratio < 0.1 and candle.upper_shadow > candle.body_size * 2

    def _is_hanging_man(self, candle: Candle) -> bool:
        if not candle.is_bearish:
            return False
        return candle.lower_shadow_ratio > 0.66 and candle.upper_shadow_ratio < 0.1 and candle.lower_shadow > candle.body_size * 2

    def _is_shooting_star(self, candle: Candle) -> bool:
        if not candle.is_bearish:
            return False
        return candle.upper_shadow_ratio > 0.66 and candle.lower_shadow_ratio < 0.1 and candle.upper_shadow > candle.body_size * 2

    def _is_marubozu(self, candle: Candle) -> bool:
        return candle.body_ratio > self._marubozu_threshold

    def _is_spinning_top(self, candle: Candle) -> bool:
        return candle.body_ratio < 0.4 and candle.upper_shadow_ratio > 0.3 and candle.lower_shadow_ratio > 0.3

    def _detect_double_candle_patterns(self, candles: List[Candle]) -> List[Pattern]:
        patterns = []
        for i in range(len(candles) - 1):
            patterns.extend(self._detect_double_candle_patterns_on_index(candles, i))
        return patterns

    def _detect_double_candle_patterns_on_index(self, candles: List[Candle], index: int) -> List[Pattern]:
        if index >= len(candles) - 1:
            return []
        candle1, candle2 = candles[index], candles[index + 1]
        patterns = []
        if self._is_bullish_engulfing(candle1, candle2):
            patterns.append(self._create_pattern(PatternType.BULLISH_ENGULFING, PatternCategory.DOUBLE, PatternDirection.BULLISH, [candle1, candle2], index, index + 1))
        if self._is_bearish_engulfing(candle1, candle2):
            patterns.append(self._create_pattern(PatternType.BEARISH_ENGULFING, PatternCategory.DOUBLE, PatternDirection.BEARISH, [candle1, candle2], index, index + 1))
        if self._is_bullish_harami(candle1, candle2):
            patterns.append(self._create_pattern(PatternType.BULLISH_HARAMI, PatternCategory.DOUBLE, PatternDirection.BULLISH, [candle1, candle2], index, index + 1))
        if self._is_bearish_harami(candle1, candle2):
            patterns.append(self._create_pattern(PatternType.BEARISH_HARAMI, PatternCategory.DOUBLE, PatternDirection.BEARISH, [candle1, candle2], index, index + 1))
        if self._is_tweezer_bottom(candle1, candle2):
            patterns.append(self._create_pattern(PatternType.TWEEZER_BOTTOM, PatternCategory.DOUBLE, PatternDirection.BULLISH, [candle1, candle2], index, index + 1))
        if self._is_tweezer_top(candle1, candle2):
            patterns.append(self._create_pattern(PatternType.TWEEZER_TOP, PatternCategory.DOUBLE, PatternDirection.BEARISH, [candle1, candle2], index, index + 1))
        if self._is_piercing_line(candle1, candle2):
            patterns.append(self._create_pattern(PatternType.PIERCING_LINE, PatternCategory.DOUBLE, PatternDirection.BULLISH, [candle1, candle2], index, index + 1))
        if self._is_dark_cloud_cover(candle1, candle2):
            patterns.append(self._create_pattern(PatternType.DARK_CLOUD_COVER, PatternCategory.DOUBLE, PatternDirection.BEARISH, [candle1, candle2], index, index + 1))
        return patterns

    def _is_bullish_engulfing(self, candle1: Candle, candle2: Candle) -> bool:
        if not candle1.is_bearish or not candle2.is_bullish:
            return False
        return candle2.open < candle1.low and candle2.close > candle1.high

    def _is_bearish_engulfing(self, candle1: Candle, candle2: Candle) -> bool:
        if not candle1.is_bullish or not candle2.is_bearish:
            return False
        return candle2.open > candle1.high and candle2.close < candle1.low

    def _is_bullish_harami(self, candle1: Candle, candle2: Candle) -> bool:
        if not candle1.is_bearish or not candle2.is_bullish:
            return False
        return candle2.open > candle1.close and candle2.close < candle1.open and candle2.high < candle1.high and candle2.low > candle1.low

    def _is_bearish_harami(self, candle1: Candle, candle2: Candle) -> bool:
        if not candle1.is_bullish or not candle2.is_bearish:
            return False
        return candle2.open < candle1.close and candle2.close > candle1.open and candle2.high < candle1.high and candle2.low > candle1.low

    def _is_tweezer_bottom(self, candle1: Candle, candle2: Candle) -> bool:
        return abs(candle1.low - candle2.low) / candle1.low < 0.001

    def _is_tweezer_top(self, candle1: Candle, candle2: Candle) -> bool:
        return abs(candle1.high - candle2.high) / candle1.high < 0.001

    def _is_piercing_line(self, candle1: Candle, candle2: Candle) -> bool:
        if not candle1.is_bearish or not candle2.is_bullish:
            return False
        midpoint = candle1.open - (candle1.open - candle1.close) / 2
        return candle2.open < candle1.low and candle2.close > midpoint

    def _is_dark_cloud_cover(self, candle1: Candle, candle2: Candle) -> bool:
        if not candle1.is_bullish or not candle2.is_bearish:
            return False
        midpoint = candle1.close - (candle1.open - candle1.close) / 2
        return candle2.open > candle1.high and candle2.close < midpoint

    def _detect_triple_candle_patterns(self, candles: List[Candle]) -> List[Pattern]:
        patterns = []
        for i in range(len(candles) - 2):
            patterns.extend(self._detect_triple_candle_patterns_on_index(candles, i))
        return patterns

    def _detect_triple_candle_patterns_on_index(self, candles: List[Candle], index: int) -> List[Pattern]:
        if index >= len(candles) - 2:
            return []
        candle1, candle2, candle3 = candles[index], candles[index + 1], candles[index + 2]
        patterns = []
        if self._is_morning_star(candle1, candle2, candle3):
            patterns.append(self._create_pattern(PatternType.MORNING_STAR, PatternCategory.TRIPLE, PatternDirection.BULLISH, [candle1, candle2, candle3], index, index + 2))
        if self._is_evening_star(candle1, candle2, candle3):
            patterns.append(self._create_pattern(PatternType.EVENING_STAR, PatternCategory.TRIPLE, PatternDirection.BEARISH, [candle1, candle2, candle3], index, index + 2))
        if self._is_three_white_soldiers(candle1, candle2, candle3):
            patterns.append(self._create_pattern(PatternType.THREE_WHITE_SOLDIERS, PatternCategory.TRIPLE, PatternDirection.BULLISH, [candle1, candle2, candle3], index, index + 2))
        if self._is_three_black_crows(candle1, candle2, candle3):
            patterns.append(self._create_pattern(PatternType.THREE_BLACK_CROWS, PatternCategory.TRIPLE, PatternDirection.BEARISH, [candle1, candle2, candle3], index, index + 2))
        return patterns

    def _is_morning_star(self, candle1: Candle, candle2: Candle, candle3: Candle) -> bool:
        if not candle1.is_bearish or not candle3.is_bullish:
            return False
        if candle2.body_ratio > 0.3:
            return False
        if candle2.open > candle1.close:
            return False
        midpoint = candle1.open - (candle1.open - candle1.close) / 2
        return candle3.close > midpoint

    def _is_evening_star(self, candle1: Candle, candle2: Candle, candle3: Candle) -> bool:
        if not candle1.is_bullish or not candle3.is_bearish:
            return False
        if candle2.body_ratio > 0.3:
            return False
        if candle2.open < candle1.close:
            return False
        midpoint = candle1.close - (candle1.open - candle1.close) / 2
        return candle3.close < midpoint

    def _is_three_white_soldiers(self, candle1: Candle, candle2: Candle, candle3: Candle) -> bool:
        if not (candle1.is_bullish and candle2.is_bullish and candle3.is_bullish):
            return False
        if candle2.open <= candle1.close or candle3.open <= candle2.close:
            return False
        if candle2.close <= candle1.close or candle3.close <= candle2.close:
            return False
        return True

    def _is_three_black_crows(self, candle1: Candle, candle2: Candle, candle3: Candle) -> bool:
        if not (candle1.is_bearish and candle2.is_bearish and candle3.is_bearish):
            return False
        if candle2.open >= candle1.close or candle3.open >= candle2.close:
            return False
        if candle2.close >= candle1.close or candle3.close >= candle2.close:
            return False
        return True

    def _validate_pattern(self, pattern: Pattern, candles: List[Candle]) -> bool:
        if pattern.category == PatternCategory.SINGLE and len(pattern.candles) != 1:
            return False
        elif pattern.category == PatternCategory.DOUBLE and len(pattern.candles) != 2:
            return False
        elif pattern.category == PatternCategory.TRIPLE and len(pattern.candles) != 3:
            return False
        for i, candle in enumerate(pattern.candles):
            candle_index = pattern.start_index + i
            if candle_index >= len(candles):
                return False
        return True

    def _create_pattern(self, pattern_type: PatternType, category: PatternCategory, direction: PatternDirection,
                       candles: List[Candle], start_index: int, end_index: int) -> Pattern:
        reliability = self._pattern_reliability.get(pattern_type, PatternReliability.LOW)
        strength = self._calculate_pattern_strength(pattern_type, candles)
        confirmation_required = self._requires_confirmation(pattern_type)
        signal_price, stop_loss, take_profit, risk_reward = self._calculate_signal_levels(pattern_type, direction, candles)
        return Pattern(
            pattern_type=pattern_type, category=category, direction=direction,
            reliability=reliability, candles=candles, start_index=start_index, end_index=end_index,
            strength=strength, confirmation_required=confirmation_required,
            signal_price=signal_price, stop_loss=stop_loss, take_profit=take_profit, risk_reward=risk_reward
        )

    def _calculate_pattern_strength(self, pattern_type: PatternType, candles: List[Candle]) -> float:
        strength = 50.0
        reliability = self._pattern_reliability.get(pattern_type, PatternReliability.LOW)
        reliability_bonus = {PatternReliability.VERY_LOW: -20, PatternReliability.LOW: -10,
                           PatternReliability.MEDIUM: 0, PatternReliability.HIGH: 10, PatternReliability.VERY_HIGH: 20}.get(reliability, 0)
        strength += reliability_bonus
        if pattern_type.category == PatternCategory.DOUBLE and pattern_type in [PatternType.BULLISH_ENGULFING, PatternType.BEARISH_ENGULFING]:
            body_ratio = candles[1].body_size / candles[0].body_size
            strength += min(body_ratio * 20, 20)
        return max(0, min(100, strength))

    def _requires_confirmation(self, pattern_type: PatternType) -> bool:
        no_confirmation = [PatternType.BULLISH_ENGULFING, PatternType.BEARISH_ENGULFING,
                         PatternType.MORNING_STAR, PatternType.EVENING_STAR,
                         PatternType.THREE_WHITE_SOLDIERS, PatternType.THREE_BLACK_CROWS]
        return pattern_type not in no_confirmation

    def _calculate_signal_levels(self, pattern_type: PatternType, direction: PatternDirection, candles: List[Candle]) -> Tuple[float, float, float, float]:
        last_candle = candles[-1]
        signal_price = last_candle.close
        if direction == PatternDirection.BULLISH:
            pattern_low = min(c.low for c in candles)
            stop_loss = pattern_low * 0.995
            if pattern_type in [PatternType.BULLISH_ENGULFING, PatternType.MORNING_STAR]:
                take_profit = signal_price * 1.03
            elif pattern_type in [PatternType.HAMMER, PatternType.INVERTED_HAMMER]:
                take_profit = signal_price * 1.02
            else:
                take_profit = signal_price * 1.015
        elif direction == PatternDirection.BEARISH:
            pattern_high = max(c.high for c in candles)
            stop_loss = pattern_high * 1.005
            if pattern_type in [PatternType.BEARISH_ENGULFING, PatternType.EVENING_STAR]:
                take_profit = signal_price * 0.97
            elif pattern_type in [PatternType.HANGING_MAN, PatternType.SHOOTING_STAR]:
                take_profit = signal_price * 0.98
            else:
                take_profit = signal_price * 0.985
        else:
            return signal_price, 0.0, 0.0, 0.0
        risk = abs(signal_price - stop_loss)
        reward = abs(take_profit - signal_price)
        risk_reward = reward / risk if risk > 0 else 0.0
        return signal_price, stop_loss, take_profit, risk_reward

    async def generate_signals(self, symbol: str, timeframe: str = "1h", lookback: int = 10) -> List[PatternSignal]:
        patterns = await self.detect_recent_patterns(symbol, timeframe, lookback)
        signals = []
        for pattern in patterns:
            if not pattern.confirmation_required or pattern.confirmed:
                signal = self._create_signal_from_pattern(pattern, symbol, timeframe)
                signals.append(signal)
        signals.sort(key=lambda s: (s.confidence, s.risk_reward), reverse=True)
        return signals

    def _create_signal_from_pattern(self, pattern: Pattern, symbol: str, timeframe: str) -> PatternSignal:
        action = "buy" if pattern.direction == PatternDirection.BULLISH else "sell" if pattern.direction == PatternDirection.BEARISH else "hold"
        confidence = self._calculate_signal_confidence(pattern)
        return PatternSignal(
            pattern=pattern, symbol=symbol, timeframe=timeframe, action=action,
            confidence=confidence, entry_price=pattern.signal_price, stop_loss=pattern.stop_loss,
            take_profit=pattern.take_profit, risk_reward=pattern.risk_reward
        )

    def _calculate_signal_confidence(self, pattern: Pattern) -> float:
        confidence = 0.0
        reliability_weights = {PatternReliability.VERY_LOW: 20, PatternReliability.LOW: 40,
                              PatternReliability.MEDIUM: 60, PatternReliability.HIGH: 80, PatternReliability.VERY_HIGH: 100}
        confidence += reliability_weights.get(pattern.reliability, 50) * 0.4
        confidence += pattern.strength * 0.3
        if pattern.risk_reward > 0:
            confidence += min(pattern.risk_reward * 10, 20) * 0.2
        if pattern.confirmed:
            confidence += 10
        return min(100, confidence)

    async def confirm_pattern(self, pattern: Pattern, confirmation_candle: Candle) -> bool:
        if not pattern.confirmation_required:
            return True
        if pattern.pattern_type == PatternType.HAMMER:
            return confirmation_candle.close > pattern.candles[0].close
        if pattern.pattern_type == PatternType.INVERTED_HAMMER:
            return confirmation_candle.close > pattern.candles[0].close
        if pattern.pattern_type == PatternType.HANGING_MAN:
            return confirmation_candle.close < pattern.candles[0].close
        if pattern.pattern_type == PatternType.SHOOTING_STAR:
            return confirmation_candle.close < pattern.candles[0].close
        return True
