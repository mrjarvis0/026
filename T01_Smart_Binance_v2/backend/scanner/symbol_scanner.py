"""Symbol Scanner for T01 Smart Binance Intelligence v2.

This module provides comprehensive symbol scanning capabilities.
It screens multiple symbols based on technical criteria to identify
trading opportunities.

Features:
- Multi-symbol technical analysis
- Custom filter definitions
- Performance-based ranking
- Volume and liquidity analysis
- Trend strength analysis
- Integration with data collector
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Callable, TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from backend.data.collector import DataCollector
    from backend.data.database import Database

log = logging.getLogger("scanner.symbol_scanner")


# ============================================================================
# ENUMS
# ============================================================================

class ScanMode(Enum):
    """Scanning mode."""
    FULL = "full"              # Scan all symbols
    QUICK = "quick"            # Quick scan with limited data
    DEEP = "deep"              # Deep scan with full analysis


class SortBy(Enum):
    """Sorting criteria for scan results."""
    PERFORMANCE = "performance"    # Sort by performance score
    VOLUME = "volume"            # Sort by volume
    VOLATILITY = "volatility"    # Sort by volatility
    TREND = "trend"              # Sort by trend strength
    PRICE = "price"              # Sort by price
    NAME = "name"                # Sort by symbol name


class FilterOperator(Enum):
    """Filter comparison operators."""
    GT = "gt"      # Greater than
    LT = "lt"      # Less than
    GTE = "gte"    # Greater than or equal
    LTE = "lte"    # Less than or equal
    EQ = "eq"      # Equal
    NEQ = "neq"    # Not equal
    IN = "in"      # In list
    NOT_IN = "not_in"  # Not in list


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class ScanFilter:
    """Filter definition for symbol scanning.
    
    Attributes:
        name: Filter name
        field: Field to filter on
        operator: Comparison operator
        value: Value to compare against
        weight: Weight for scoring (0-100)
    """
    name: str = ""
    field: str = ""
    operator: FilterOperator = FilterOperator.GT
    value: Any = None
    weight: float = 1.0


@dataclass
class ScanResult:
    """Result of a symbol scan.
    
    Attributes:
        symbol: Trading pair
        rank: Rank in scan results
        score: Overall score (0-100)
        data: Dictionary of symbol data
        filters_passed: Number of filters passed
        filters_total: Total number of filters
        timestamp: When the scan was performed
    """
    symbol: str = ""
    rank: int = 0
    score: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)
    filters_passed: int = 0
    filters_total: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert scan result to dictionary."""
        return {
            "symbol": self.symbol,
            "rank": self.rank,
            "score": self.score,
            "data": self.data,
            "filters_passed": self.filters_passed,
            "filters_total": self.filters_total,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class SymbolData:
    """Data for a single symbol.
    
    Attributes:
        symbol: Trading pair
        price: Current price
        volume_24h: 24-hour volume
        volume_1h: 1-hour volume
        price_change_24h: 24-hour price change percentage
        price_change_1h: 1-hour price change percentage
        high_24h: 24-hour high
        low_24h: 24-hour low
        trend: Current trend
        trend_strength: Trend strength (0-100)
        volatility: Volatility (0-100)
        rsi: RSI value
        macd: MACD value
        signal_line: MACD signal line
        histogram: MACD histogram
        atr: ATR value
        bollinger_upper: Bollinger Band upper
        bollinger_lower: Bollinger Band lower
        last_update: When data was last updated
    """
    symbol: str = ""
    price: float = 0.0
    volume_24h: float = 0.0
    volume_1h: float = 0.0
    price_change_24h: float = 0.0
    price_change_1h: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    trend: str = "sideways"
    trend_strength: float = 0.0
    volatility: float = 0.0
    rsi: float = 50.0
    macd: float = 0.0
    signal_line: float = 0.0
    histogram: float = 0.0
    atr: float = 0.0
    bollinger_upper: float = 0.0
    bollinger_lower: float = 0.0
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# SYMBOL SCANNER
# ============================================================================

class SymbolScanner:
    """Scans multiple symbols based on technical criteria.
    
    The SymbolScanner provides:
    
    1. Multi-symbol data collection
    2. Custom filter definitions
    3. Technical indicator calculations
    4. Performance-based ranking
    5. Real-time scanning capabilities
    
    The scanner works by:
    - Fetching data for multiple symbols
    - Calculating technical indicators
    - Applying filters to each symbol
    - Ranking symbols by score
    - Returning sorted results
    """

    def __init__(
        self,
        data_collector: "DataCollector",
        db: Optional["Database"] = None,
        symbols: Optional[List[str]] = None,
        timeframe: str = "1h"
    ):
        """Initialize SymbolScanner.
        
        Args:
            data_collector: DataCollector instance for fetching data
            db: Optional database for persistence
            symbols: List of symbols to scan (default: top Binance symbols)
            timeframe: Default timeframe for analysis
        """
        self.data_collector = data_collector
        self.db = db
        self.timeframe = timeframe
        
        # Default symbols (top Binance pairs)
        self.symbols = symbols or [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "DOT/USDT", "SHIB/USDT", "AVAX/USDT",
            "MATIC/USDT", "LINK/USDT", "UNI/USDT", "ATOM/USDT", "LTC/USDT",
            "BCH/USDT", "ALGO/USDT", "VET/USDT", "TRX/USDT", "XLM/USDT"
        ]
        
        # Default filters
        self._default_filters = self._create_default_filters()
        
        # Custom filters
        self._custom_filters: List[ScanFilter] = []
        
        # Symbol data cache
        self._symbol_data: Dict[str, SymbolData] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        log.info(f"SymbolScanner initialized with {len(self.symbols)} symbols")

    def _create_default_filters(self) -> List[ScanFilter]:
        """Create default scan filters.
        
        Returns:
            List of default ScanFilter objects
        """
        return [
            ScanFilter(
                name="volume_24h_min",
                field="volume_24h",
                operator=FilterOperator.GT,
                value=1000000,  # Minimum $1M volume
                weight=1.0
            ),
            ScanFilter(
                name="volatility_min",
                field="volatility",
                operator=FilterOperator.GT,
                value=10,  # Minimum 10% volatility
                weight=0.8
            ),
            ScanFilter(
                name="rsi_range",
                field="rsi",
                operator=FilterOperator.IN,
                value=[20, 30, 70, 80],  # RSI in overbought/oversold zones
                weight=0.5
            ),
            ScanFilter(
                name="trend_strength_min",
                field="trend_strength",
                operator=FilterOperator.GT,
                value=50,  # Minimum 50% trend strength
                weight=0.7
            )
        ]

    # ========================================================================
    # SCANNING METHODS
    # ========================================================================

    async def scan(
        self,
        symbols: Optional[List[str]] = None,
        filters: Optional[List[ScanFilter]] = None,
        timeframe: Optional[str] = None,
        sort_by: SortBy = SortBy.PERFORMANCE,
        limit: int = 20,
        scan_mode: ScanMode = ScanMode.FULL
    ) -> List[ScanResult]:
        """Scan symbols based on filters and criteria.
        
        Args:
            symbols: List of symbols to scan (default: all configured symbols)
            filters: List of filters to apply (default: default filters)
            timeframe: Timeframe for analysis (default: configured timeframe)
            sort_by: Sorting criteria
            limit: Maximum number of results to return
            scan_mode: Scanning mode (FULL, QUICK, DEEP)
            
        Returns:
            List of ScanResult objects sorted by criteria
        """
        async with self._lock:
            log.info(f"Starting scan: {len(symbols or self.symbols)} symbols, mode={scan_mode.value}")
            
            # Use provided symbols or default
            scan_symbols = symbols or self.symbols
            
            # Use provided filters or default
            scan_filters = filters or self._default_filters
            
            # Use provided timeframe or default
            tf = timeframe or self.timeframe
            
            # Collect data for all symbols
            await self._collect_symbol_data(scan_symbols, tf, scan_mode)
            
            # Apply filters and calculate scores
            results = []
            for symbol in scan_symbols:
                symbol_data = self._symbol_data.get(symbol)
                if symbol_data:
                    result = await self._evaluate_symbol(symbol_data, scan_filters)
                    results.append(result)
            
            # Sort results
            results = self._sort_results(results, sort_by)
            
            # Limit results
            return results[:limit]

    async def _collect_symbol_data(
        self,
        symbols: List[str],
        timeframe: str,
        scan_mode: ScanMode
    ) -> None:
        """Collect data for multiple symbols.
        
        Args:
            symbols: List of symbols to collect data for
            timeframe: Timeframe for analysis
            scan_mode: Scanning mode
        """
        tasks = []
        
        for symbol in symbols:
            task = asyncio.create_task(
                self._fetch_symbol_data(symbol, timeframe, scan_mode)
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _fetch_symbol_data(
        self,
        symbol: str,
        timeframe: str,
        scan_mode: ScanMode
    ) -> None:
        """Fetch data for a single symbol.
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe for analysis
            scan_mode: Scanning mode
        """
        try:
            # Fetch OHLCV data
            limit = 100 if scan_mode == ScanMode.FULL else 50 if scan_mode == ScanMode.QUICK else 200
            df = await self.data_collector.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit
            )
            
            if df is None or len(df) < 10:
                log.warning(f"Insufficient data for {symbol}")
                return
            
            # Calculate indicators
            symbol_data = await self._calculate_symbol_data(df, symbol)
            
            # Cache data
            self._symbol_data[symbol] = symbol_data
            
        except Exception as e:
            log.error(f"Failed to fetch data for {symbol}: {e}")

    async def _calculate_symbol_data(
        self,
        df: pd.DataFrame,
        symbol: str
    ) -> SymbolData:
        """Calculate all data for a symbol.
        
        Args:
            df: OHLCV DataFrame
            symbol: Trading pair
            
        Returns:
            SymbolData object
        """
        # Get last row
        last_row = df.iloc[-1]
        
        # Calculate basic data
        price = float(last_row['close'])
        high_24h = float(df['high'].max())
        low_24h = float(df['low'].min())
        
        # Calculate volume
        volume_24h = float(df['volume'].sum())
        volume_1h = float(df['volume'].iloc[-1])
        
        # Calculate price changes
        price_change_24h = ((price - float(df['open'].iloc[0])) / float(df['open'].iloc[0])) * 100
        price_change_1h = ((price - float(df['open'].iloc[-1])) / float(df['open'].iloc[-1])) * 100
        
        # Calculate indicators
        rsi = self._calculate_rsi(df)
        macd, signal_line, histogram = self._calculate_macd(df)
        atr = self._calculate_atr(df)
        bollinger_upper, bollinger_lower = self._calculate_bollinger_bands(df)
        
        # Calculate trend
        trend, trend_strength = self._calculate_trend(df)
        
        # Calculate volatility
        volatility = self._calculate_volatility(df)
        
        return SymbolData(
            symbol=symbol,
            price=price,
            volume_24h=volume_24h,
            volume_1h=volume_1h,
            price_change_24h=price_change_24h,
            price_change_1h=price_change_1h,
            high_24h=high_24h,
            low_24h=low_24h,
            trend=trend,
            trend_strength=trend_strength,
            volatility=volatility,
            rsi=rsi,
            macd=macd,
            signal_line=signal_line,
            histogram=histogram,
            atr=atr,
            bollinger_upper=bollinger_upper,
            bollinger_lower=bollinger_lower
        )

    def _calculate_rsi(self, df: pd.DataFrame) -> float:
        """Calculate RSI.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            RSI value
        """
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(com=13, min_periods=13).mean()
        avg_loss = loss.ewm(com=13, min_periods=13).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])

    def _calculate_macd(self, df: pd.DataFrame) -> Tuple[float, float, float]:
        """Calculate MACD.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Tuple of (macd, signal_line, histogram)
        """
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        macd = ema_12 - ema_26
        signal_line = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal_line
        return float(macd.iloc[-1]), float(signal_line.iloc[-1]), float(histogram.iloc[-1])

    def _calculate_atr(self, df: pd.DataFrame) -> float:
        """Calculate ATR.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            ATR value
        """
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift(1))
        low_close = abs(df['low'] - df['close'].shift(1))
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.ewm(span=14, adjust=False).mean()
        return float(atr.iloc[-1])

    def _calculate_bollinger_bands(self, df: pd.DataFrame) -> Tuple[float, float]:
        """Calculate Bollinger Bands.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Tuple of (upper_band, lower_band)
        """
        sma_20 = df['close'].rolling(window=20).mean()
        std_20 = df['close'].rolling(window=20).std()
        upper = sma_20 + (std_20 * 2)
        lower = sma_20 - (std_20 * 2)
        return float(upper.iloc[-1]), float(lower.iloc[-1])

    def _calculate_trend(self, df: pd.DataFrame) -> Tuple[str, float]:
        """Calculate trend direction and strength.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Tuple of (trend, strength)
        """
        close = df['close']
        sma_20 = close.rolling(window=20).mean()
        sma_50 = close.rolling(window=50).mean()
        
        if sma_20.iloc[-1] is None or sma_50.iloc[-1] is None:
            return "sideways", 0.0
        
        # Price vs SMA
        price_above_sma_20 = close.iloc[-1] > sma_20.iloc[-1]
        price_above_sma_50 = close.iloc[-1] > sma_50.iloc[-1]
        sma_20_above_sma_50 = sma_20.iloc[-1] > sma_50.iloc[-1]
        
        bullish = sum([price_above_sma_20, price_above_sma_50, sma_20_above_sma_50])
        bearish = 3 - bullish
        
        total = bullish + bearish
        if total == 0:
            return "sideways", 0.0
        
        score = bullish / total
        
        if score >= 0.7:
            return "up", score * 100
        elif score <= 0.3:
            return "down", (1 - score) * 100
        else:
            return "sideways", 50.0

    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Calculate volatility as percentage.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Volatility percentage
        """
        returns = df['close'].pct_change().dropna()
        std = returns.std()
        return float(std * 100)

    async def _evaluate_symbol(
        self,
        symbol_data: SymbolData,
        filters: List[ScanFilter]
    ) -> ScanResult:
        """Evaluate a symbol against filters.
        
        Args:
            symbol_data: SymbolData for the symbol
            filters: List of filters to apply
            
        Returns:
            ScanResult for the symbol
        """
        score = 0.0
        passed = 0
        total = len(filters)
        
        # Convert SymbolData to dictionary
        data = {
            "symbol": symbol_data.symbol,
            "price": symbol_data.price,
            "volume_24h": symbol_data.volume_24h,
            "volume_1h": symbol_data.volume_1h,
            "price_change_24h": symbol_data.price_change_24h,
            "price_change_1h": symbol_data.price_change_1h,
            "high_24h": symbol_data.high_24h,
            "low_24h": symbol_data.low_24h,
            "trend": symbol_data.trend,
            "trend_strength": symbol_data.trend_strength,
            "volatility": symbol_data.volatility,
            "rsi": symbol_data.rsi,
            "macd": symbol_data.macd,
            "signal_line": symbol_data.signal_line,
            "histogram": symbol_data.histogram,
            "atr": symbol_data.atr,
            "bollinger_upper": symbol_data.bollinger_upper,
            "bollinger_lower": symbol_data.bollinger_lower
        }
        
        # Apply filters
        for filter_obj in filters:
            if self._apply_filter(symbol_data, filter_obj):
                passed += 1
                score += filter_obj.weight * 100
        
        # Normalize score
        if total > 0:
            score = (score / (total * 100)) * 100
        
        return ScanResult(
            symbol=symbol_data.symbol,
            score=score,
            data=data,
            filters_passed=passed,
            filters_total=total
        )

    def _apply_filter(self, symbol_data: SymbolData, filter_obj: ScanFilter) -> bool:
        """Apply a single filter to symbol data.
        
        Args:
            symbol_data: SymbolData for the symbol
            filter_obj: Filter to apply
            
        Returns:
            True if symbol passes the filter
        """
        # Get field value
        field_value = getattr(symbol_data, filter_obj.field, None)
        
        if field_value is None:
            return False
        
        # Apply operator
        if filter_obj.operator == FilterOperator.GT:
            return field_value > filter_obj.value
        elif filter_obj.operator == FilterOperator.LT:
            return field_value < filter_obj.value
        elif filter_obj.operator == FilterOperator.GTE:
            return field_value >= filter_obj.value
        elif filter_obj.operator == FilterOperator.LTE:
            return field_value <= filter_obj.value
        elif filter_obj.operator == FilterOperator.EQ:
            return field_value == filter_obj.value
        elif filter_obj.operator == FilterOperator.NEQ:
            return field_value != filter_obj.value
        elif filter_obj.operator == FilterOperator.IN:
            return field_value in filter_obj.value
        elif filter_obj.operator == FilterOperator.NOT_IN:
            return field_value not in filter_obj.value
        
        return False

    def _sort_results(self, results: List[ScanResult], sort_by: SortBy) -> List[ScanResult]:
        """Sort scan results.
        
        Args:
            results: List of ScanResult objects
            sort_by: Sorting criteria
            
        Returns:
            Sorted list of ScanResult objects
        """
        if sort_by == SortBy.PERFORMANCE:
            results.sort(key=lambda r: r.score, reverse=True)
        elif sort_by == SortBy.VOLUME:
            results.sort(key=lambda r: r.data.get("volume_24h", 0), reverse=True)
        elif sort_by == SortBy.VOLATILITY:
            results.sort(key=lambda r: r.data.get("volatility", 0), reverse=True)
        elif sort_by == SortBy.TREND:
            results.sort(key=lambda r: r.data.get("trend_strength", 0), reverse=True)
        elif sort_by == SortBy.PRICE:
            results.sort(key=lambda r: r.data.get("price", 0), reverse=True)
        elif sort_by == SortBy.NAME:
            results.sort(key=lambda r: r.symbol)
        
        # Update ranks
        for i, result in enumerate(results):
            result.rank = i + 1
        
        return results

    # ========================================================================
    # FILTER MANAGEMENT
    # ========================================================================

    def add_filter(self, filter_obj: ScanFilter) -> None:
        """Add a custom filter.
        
        Args:
            filter_obj: Filter to add
        """
        self._custom_filters.append(filter_obj)
        log.info(f"Added filter: {filter_obj.name}")

    def remove_filter(self, filter_name: str) -> bool:
        """Remove a custom filter.
        
        Args:
            filter_name: Name of filter to remove
            
        Returns:
            True if filter was removed
        """
        for i, filter_obj in enumerate(self._custom_filters):
            if filter_obj.name == filter_name:
                self._custom_filters.pop(i)
                log.info(f"Removed filter: {filter_name}")
                return True
        return False

    def get_filters(self) -> List[ScanFilter]:
        """Get all custom filters.
        
        Returns:
            List of custom filters
        """
        return self._custom_filters.copy()

    def clear_filters(self) -> None:
        """Clear all custom filters."""
        self._custom_filters.clear()
        log.info("Cleared all custom filters")

    # ========================================================================
    # SYMBOL MANAGEMENT
    # ========================================================================

    def add_symbol(self, symbol: str) -> None:
        """Add a symbol to scan.
        
        Args:
            symbol: Symbol to add
        """
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            log.info(f"Added symbol: {symbol}")

    def remove_symbol(self, symbol: str) -> bool:
        """Remove a symbol from scan.
        
        Args:
            symbol: Symbol to remove
            
        Returns:
            True if symbol was removed
        """
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            log.info(f"Removed symbol: {symbol}")
            return True
        return False

    def get_symbols(self) -> List[str]:
        """Get all symbols.
        
        Returns:
            List of symbols
        """
        return self.symbols.copy()

    def set_symbols(self, symbols: List[str]) -> None:
        """Set the list of symbols to scan.
        
        Args:
            symbols: List of symbols
        """
        self.symbols = symbols.copy()
        log.info(f"Set {len(symbols)} symbols")

    # ========================================================================
    # CACHE MANAGEMENT
    # ========================================================================

    async def refresh_data(self) -> None:
        """Refresh data for all symbols."""
        await self._collect_symbol_data(self.symbols, self.timeframe, ScanMode.FULL)
        log.info(f"Refreshed data for {len(self.symbols)} symbols")

    async def refresh_symbol_data(self, symbol: str) -> None:
        """Refresh data for a specific symbol.
        
        Args:
            symbol: Symbol to refresh
        """
        await self._fetch_symbol_data(symbol, self.timeframe, ScanMode.FULL)
        log.info(f"Refreshed data for {symbol}")

    def clear_cache(self) -> None:
        """Clear symbol data cache."""
        self._symbol_data.clear()
        log.info("Cleared symbol data cache")

    def get_symbol_data(self, symbol: str) -> Optional[SymbolData]:
        """Get cached data for a symbol.
        
        Args:
            symbol: Symbol to get data for
            
        Returns:
            SymbolData or None
        """
        return self._symbol_data.get(symbol)

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def get_top_symbols(
        self,
        limit: int = 10,
        sort_by: SortBy = SortBy.PERFORMANCE
    ) -> List[ScanResult]:
        """Get top symbols based on criteria.
        
        Args:
            limit: Maximum number of symbols to return
            sort_by: Sorting criteria
            
        Returns:
            List of top ScanResult objects
        """
        results = await self.scan(sort_by=sort_by, limit=limit)
        return results

    async def find_symbols_by_filter(
        self,
        filters: List[ScanFilter],
        limit: int = 20
    ) -> List[ScanResult]:
        """Find symbols matching specific filters.
        
        Args:
            filters: List of filters to apply
            limit: Maximum number of results to return
            
        Returns:
            List of matching ScanResult objects
        """
        return await self.scan(filters=filters, limit=limit)

    async def get_symbol_stats(self, symbol: str) -> Dict[str, Any]:
        """Get detailed statistics for a symbol.
        
        Args:
            symbol: Symbol to get stats for
            
        Returns:
            Dictionary of symbol statistics
        """
        symbol_data = await self.get_symbol_data(symbol)
        if symbol_data:
            return {
                "symbol": symbol_data.symbol,
                "price": symbol_data.price,
                "volume_24h": symbol_data.volume_24h,
                "volume_1h": symbol_data.volume_1h,
                "price_change_24h": symbol_data.price_change_24h,
                "price_change_1h": symbol_data.price_change_1h,
                "high_24h": symbol_data.high_24h,
                "low_24h": symbol_data.low_24h,
                "trend": symbol_data.trend,
                "trend_strength": symbol_data.trend_strength,
                "volatility": symbol_data.volatility,
                "rsi": symbol_data.rsi,
                "macd": symbol_data.macd,
                "signal_line": symbol_data.signal_line,
                "histogram": symbol_data.histogram,
                "atr": symbol_data.atr,
                "bollinger_upper": symbol_data.bollinger_upper,
                "bollinger_lower": symbol_data.bollinger_lower
            }
        return {}
