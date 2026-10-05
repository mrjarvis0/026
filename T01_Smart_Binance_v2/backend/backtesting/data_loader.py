"""Historical data loader for backtesting.

This module provides functionality to load and cache historical
OHLCV data from exchanges for backtesting purposes.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
import pandas as pd
import aiofiles

import ccxt
from backend import config
from backend.data.collector import DataCollector

log = logging.getLogger("backtesting.data_loader")


class HistoricalDataLoader:
    """Loads and caches historical OHLCV data for backtesting.
    
    Features:
    - Load from Binance API
    - Local caching for faster reloads
    - Multiple timeframe support
    - Data validation and cleaning
    - Rate limit handling
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize the historical data loader.
        
        Args:
            cache_dir: Directory for caching data (default: config.HISTORICAL_DATA_DIR)
        """
        self.cache_dir = cache_dir or config.HISTORICAL_DATA_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.collector = DataCollector()
        self._rate_limit_delay = 0.1  # seconds between requests
    
    async def load_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """Load OHLCV data for a symbol and timeframe.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Timeframe (e.g., '1h', '4h')
            start_date: Start date (optional)
            end_date: End date (optional)
            limit: Maximum number of candles (optional)
            
        Returns:
            DataFrame with OHLCV data
        """
        # Generate cache filename
        cache_file = self._get_cache_path(symbol, timeframe)
        
        # Try to load from cache first
        cached_data = self._load_from_cache(cache_file)
        if cached_data is not None and self._is_cache_valid(cached_data, start_date, end_date):
            log.debug(f"Loaded {symbol} {timeframe} from cache")
            return cached_data
        
        # Fetch from exchange
        log.info(f"Fetching {symbol} {timeframe} from exchange...")
        ohlcv = await self._fetch_from_exchange(symbol, timeframe, limit)
        
        if not ohlcv or len(ohlcv) == 0:
            log.warning(f"No data returned for {symbol} {timeframe}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = self.collector.ohlcv_to_dataframe(ohlcv)
        
        if df.empty:
            log.warning(f"Empty DataFrame for {symbol} {timeframe}")
            return df
        
        # Filter by date range if specified
        if start_date or end_date:
            df = self._filter_by_date(df, start_date, end_date)
        
        # Limit if specified
        if limit:
            df = df.tail(limit)
        
        # Save to cache
        self._save_to_cache(cache_file, df)
        
        return df
    
    async def load_multiple(
        self,
        symbols: List[str],
        timeframe: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> Dict[str, pd.DataFrame]:
        """Load OHLCV data for multiple symbols.
        
        Args:
            symbols: List of trading pairs
            timeframe: Timeframe
            start_date: Start date (optional)
            end_date: End date (optional)
            limit: Maximum candles per symbol (optional)
            
        Returns:
            Dictionary mapping symbol to DataFrame
        """
        results = {}
        
        # Process symbols concurrently with rate limiting
        for symbol in symbols:
            try:
                df = await self.load_ohlcv(symbol, timeframe, start_date, end_date, limit)
                if not df.empty:
                    results[symbol] = df
                else:
                    log.warning(f"No data loaded for {symbol}")
            except Exception as e:
                log.error(f"Error loading data for {symbol}: {e}")
            
            # Rate limiting
            await asyncio.sleep(self._rate_limit_delay)
        
        return results
    
    async def load_all_timeframes(
        self,
        symbol: str,
        timeframes: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> Dict[str, pd.DataFrame]:
        """Load OHLCV data for multiple timeframes.
        
        Args:
            symbol: Trading pair
            timeframes: List of timeframes
            start_date: Start date (optional)
            end_date: End date (optional)
            limit: Maximum candles per timeframe (optional)
            
        Returns:
            Dictionary mapping timeframe to DataFrame
        """
        results = {}
        
        for tf in timeframes:
            try:
                df = await self.load_ohlcv(symbol, tf, start_date, end_date, limit)
                if not df.empty:
                    results[tf] = df
                else:
                    log.warning(f"No data loaded for {symbol} {tf}")
            except Exception as e:
                log.error(f"Error loading data for {symbol} {tf}: {e}")
            
            await asyncio.sleep(self._rate_limit_delay)
        
        return results
    
    def _get_cache_path(self, symbol: str, timeframe: str) -> Path:
        """Generate cache file path.
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe
            
        Returns:
            Path to cache file
        """
        # Sanitize symbol for filename
        safe_symbol = symbol.replace('/', '_')
        filename = f"{safe_symbol}_{timeframe}.csv"
        return self.cache_dir / filename
    
    def _load_from_cache(self, cache_file: Path) -> Optional[pd.DataFrame]:
        """Load data from cache file.
        
        Args:
            cache_file: Path to cache file
            
        Returns:
            DataFrame if cache exists and is valid, None otherwise
        """
        if not cache_file.exists():
            return None
        
        try:
            df = pd.read_csv(cache_file, parse_dates=['ts'], index_col=None)
            
            # Validate data
            if df.empty or len(df) < 10:
                log.warning(f"Cache file {cache_file} has insufficient data")
                return None
            
            return df
            
        except Exception as e:
            log.error(f"Error loading cache from {cache_file}: {e}")
            return None
    
    def _is_cache_valid(
        self,
        df: pd.DataFrame,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> bool:
        """Check if cached data is valid for the requested date range.
        
        Args:
            df: Cached DataFrame
            start_date: Requested start date
            end_date: Requested end date
            
        Returns:
            True if cache is valid
        """
        if df.empty:
            return False
        
        # If no date range specified, cache is valid
        if start_date is None and end_date is None:
            return True
        
        # Check if cache covers the requested range
        min_date = df['ts'].min()
        max_date = df['ts'].max()
        
        if start_date and min_date > start_date:
            return False
        if end_date and max_date < end_date:
            return False
        
        return True
    
    async def _fetch_from_exchange(
        self,
        symbol: str,
        timeframe: str,
        limit: Optional[int] = None
    ) -> List[List[Any]]:
        """Fetch OHLCV data from exchange.
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe
            limit: Maximum candles to fetch
            
        Returns:
            List of OHLCV candles
        """
        max_limit = limit or config.BACKTEST_LIMIT
        
        try:
            # Fetch from exchange
            ohlcv = await self.collector.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=max_limit
            )
            
            if not ohlcv:
                log.warning(f"No data from exchange for {symbol} {timeframe}")
                return []
            
            # Validate data
            if len(ohlcv) < 10:
                log.warning(f"Insufficient data from exchange: {len(ohlcv)} candles")
                return []
            
            return ohlcv
            
        except ccxt.RateLimitExceeded as e:
            log.warning(f"Rate limit exceeded: {e}")
            await asyncio.sleep(1.0)
            return await self._fetch_from_exchange(symbol, timeframe, limit)
        except Exception as e:
            log.error(f"Error fetching from exchange: {e}")
            return []
    
    def _save_to_cache(self, cache_file: Path, df: pd.DataFrame) -> None:
        """Save data to cache file.
        
        Args:
            cache_file: Path to cache file
            df: DataFrame to save
        """
        try:
            df.to_csv(cache_file, index=False)
            log.debug(f"Saved cache to {cache_file}")
        except Exception as e:
            log.error(f"Error saving cache to {cache_file}: {e}")
    
    def _filter_by_date(
        self,
        df: pd.DataFrame,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> pd.DataFrame:
        """Filter DataFrame by date range.
        
        Args:
            df: DataFrame to filter
            start_date: Start date
            end_date: End date
            
        Returns:
            Filtered DataFrame
        """
        if start_date is None and end_date is None:
            return df
        
        filtered = df.copy()
        
        if start_date:
            # Convert to timezone-aware if needed
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            filtered = filtered[filtered['ts'] >= start_date]
        
        if end_date:
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            filtered = filtered[filtered['ts'] <= end_date]
        
        return filtered
    
    def clear_cache(self, symbol: Optional[str] = None, timeframe: Optional[str] = None) -> int:
        """Clear cached data.
        
        Args:
            symbol: Specific symbol to clear (optional)
            timeframe: Specific timeframe to clear (optional)
            
        Returns:
            Number of files deleted
        """
        count = 0
        
        if symbol and timeframe:
            # Clear specific file
            cache_file = self._get_cache_path(symbol, timeframe)
            if cache_file.exists():
                cache_file.unlink()
                count += 1
        elif symbol:
            # Clear all files for symbol
            pattern = f"{symbol.replace('/', '_')}_*.csv"
            for file in self.cache_dir.glob(pattern):
                file.unlink()
                count += 1
        elif timeframe:
            # Clear all files for timeframe
            pattern = f"*_{timeframe}.csv"
            for file in self.cache_dir.glob(pattern):
                file.unlink()
                count += 1
        else:
            # Clear all cache files
            for file in self.cache_dir.glob("*.csv"):
                file.unlink()
                count += 1
        
        log.info(f"Cleared {count} cache files")
        return count
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached data.
        
        Returns:
            Dictionary with cache statistics
        """
        cache_files = list(self.cache_dir.glob("*.csv"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'total_files': len(cache_files),
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'cache_dir': str(self.cache_dir)
        }


# Singleton instance for convenience
data_loader = HistoricalDataLoader()
