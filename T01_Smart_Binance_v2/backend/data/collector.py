"""Data collector for market data from exchanges.

This module provides REST API-based data collection using ccxt.
It serves as the foundation for all data needs in the trading bot.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import pandas as pd

import ccxt
from backend import config

log = logging.getLogger("data.collector")


# Timeframe to milliseconds mapping for Binance
_TF_MS = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "2h": 7_200_000,
    "4h": 14_400_000,
    "6h": 21_600_000,
    "8h": 28_800_000,
    "12h": 43_200_000,
    "1d": 86_400_000,
}


class DataCollector:
    """Collects market data from exchanges using REST API.
    
    This is the primary data source for the trading bot. It provides:
    - OHLCV (candlestick) data
    - Ticker (24h stats) data
    - Order book data
    - Trade data
    - Symbol information
    
    Uses ccxt library for exchange connectivity.
    """
    
    def __init__(self, exchange_id: str = 'binance'):
        """Initialize the data collector.
        
        Args:
            exchange_id: The exchange to use (default: 'binance')
        """
        self.exchange_id = exchange_id
        self._exchange: Optional[ccxt.Exchange] = None
        self._fallback_exchange: Optional[ccxt.Exchange] = None
        self._initialized = False
        
    @property
    def exchange(self) -> ccxt.Exchange:
        """Get the exchange instance, initializing if necessary."""
        if self._exchange is None:
            self._initialize_exchange()
        return self._exchange
    
    @property
    def fallback_exchange(self) -> Optional[ccxt.Exchange]:
        """Get the fallback exchange (Kraken for geo-block resilience)."""
        if self._fallback_exchange is None and self.exchange_id == 'binance':
            try:
                self._fallback_exchange = self._create_exchange('kraken')
            except Exception as e:
                log.warning(f"Failed to initialize fallback exchange: {e}")
        return self._fallback_exchange
    
    def _initialize_exchange(self) -> None:
        """Initialize the exchange instance."""
        if self._initialized:
            return
        
        try:
            self._exchange = self._create_exchange(self.exchange_id)
            self._initialized = True
            log.info(f"Initialized {self.exchange_id} exchange")
        except Exception as e:
            log.error(f"Failed to initialize {self.exchange_id} exchange: {e}")
            raise
    
    def _create_exchange(self, exchange_id: str) -> ccxt.Exchange:
        """Create an exchange instance.
        
        Args:
            exchange_id: The exchange identifier
            
        Returns:
            Configured exchange instance
        """
        exchange_class = getattr(ccxt, exchange_id)
        
        # Configure exchange
        exchange_config = {
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
            }
        }
        
        # Add credentials if available (for private endpoints)
        if exchange_id == 'binance' and config.BINANCE_API_KEY:
            exchange_config.update({
                'apiKey': config.BINANCE_API_KEY,
                'secret': config.BINANCE_API_SECRET,
                'test': config.BINANCE_TESTNET,
            })
        
        exchange = exchange_class(exchange_config)
        
        # Load markets for symbol validation
        exchange.load_markets()
        
        return exchange
    
    async def fetch_ohlcv(
        self, 
        symbol: str, 
        timeframe: str, 
        limit: int = 250,
        since: Optional[int] = None
    ) -> List[List[Any]]:
        """Fetch OHLCV (candlestick) data.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Timeframe (e.g., '1m', '5m', '1h')
            limit: Number of candles to fetch (default: 250)
            since: Timestamp to fetch from (optional)
            
        Returns:
            List of OHLCV candles: [timestamp, open, high, low, close, volume]
        """
        try:
            # Validate symbol
            if symbol not in self.exchange.symbols:
                raise ValueError(f"Symbol {symbol} not found on {self.exchange_id}")
            
            # Validate timeframe
            if timeframe not in _TF_MS:
                raise ValueError(f"Timeframe {timeframe} not supported")
            
            # Fetch from exchange
            ohlcv = await self._fetch_with_fallback(
                'fetch_ohlcv',
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                since=since
            )
            
            # Validate data
            if not ohlcv or len(ohlcv) == 0:
                log.warning(f"No OHLCV data returned for {symbol} {timeframe}")
                return []
            
            # Ensure we have enough data
            if len(ohlcv) < limit:
                log.info(f"Only {len(ohlcv)} candles returned for {symbol} {timeframe} (requested {limit})")
            
            return ohlcv
            
        except ccxt.NetworkError as e:
            log.error(f"Network error fetching OHLCV for {symbol} {timeframe}: {e}")
            return []
        except ccxt.ExchangeError as e:
            log.error(f"Exchange error fetching OHLCV for {symbol} {timeframe}: {e}")
            # Try fallback for geo-block (HTTP 451)
            if '451' in str(e) and self.fallback_exchange:
                try:
                    ohlcv = await self.fallback_exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                    log.info(f"Successfully fetched OHLCV from fallback exchange for {symbol} {timeframe}")
                    return ohlcv
                except Exception as fallback_error:
                    log.error(f"Fallback also failed: {fallback_error}")
            return []
        except Exception as e:
            log.error(f"Unexpected error fetching OHLCV for {symbol} {timeframe}: {e}")
            return []
    
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch ticker (24h stats) data.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Dictionary with ticker information
        """
        try:
            ticker = await self._fetch_with_fallback('fetch_ticker', symbol=symbol)
            return ticker or {}
        except Exception as e:
            log.error(f"Error fetching ticker for {symbol}: {e}")
            return {}
    
    async def fetch_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """Fetch order book data.
        
        Args:
            symbol: Trading pair
            limit: Depth of order book (default: 20)
            
        Returns:
            Dictionary with bids and asks
        """
        try:
            order_book = await self._fetch_with_fallback(
                'fetch_order_book',
                symbol=symbol,
                limit=limit
            )
            return order_book or {}
        except Exception as e:
            log.error(f"Error fetching order book for {symbol}: {e}")
            return {}
    
    async def fetch_trades(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent trades.
        
        Args:
            symbol: Trading pair
            limit: Number of trades to fetch
            
        Returns:
            List of trade dictionaries
        """
        try:
            trades = await self._fetch_with_fallback(
                'fetch_trades',
                symbol=symbol,
                limit=limit
            )
            return trades or []
        except Exception as e:
            log.error(f"Error fetching trades for {symbol}: {e}")
            return []
    
    async def list_symbols(self, quote: str = 'USDT') -> List[str]:
        """List all symbols with the specified quote currency.
        
        Args:
            quote: Quote currency (default: 'USDT')
            
        Returns:
            List of symbol strings
        """
        try:
            symbols = []
            for symbol in self.exchange.symbols:
                # Check if symbol ends with quote
                if symbol.endswith(f'/{quote}'):
                    symbols.append(symbol)
            return symbols
        except Exception as e:
            log.error(f"Error listing symbols: {e}")
            return []
    
    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get information about a specific symbol.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Dictionary with symbol information
        """
        try:
            if symbol not in self.exchange.markets:
                return {}
            return self.exchange.markets[symbol]
        except Exception as e:
            log.error(f"Error getting info for {symbol}: {e}")
            return {}
    
    async def _fetch_with_fallback(self, method: str, **kwargs) -> Any:
        """Fetch data with fallback to alternative exchange.
        
        Args:
            method: Exchange method to call
            **kwargs: Arguments for the method
            
        Returns:
            Data from exchange or fallback
        """
        try:
            exchange_method = getattr(self.exchange, method)
            return await exchange_method(**kwargs)
        except ccxt.ExchangeError as e:
            # Check for geo-block (HTTP 451)
            if '451' in str(e) and self.fallback_exchange:
                fallback_method = getattr(self.fallback_exchange, method)
                log.info(f"Primary exchange blocked, trying fallback for {method}")
                return await fallback_method(**kwargs)
            raise
    
    def ohlcv_to_dataframe(self, ohlcv: List[List[Any]]) -> pd.DataFrame:
        """Convert OHLCV list to pandas DataFrame.
        
        Args:
            ohlcv: List of OHLCV candles
            
        Returns:
            DataFrame with columns: ts, open, high, low, close, volume
        """
        if not ohlcv:
            return pd.DataFrame()
        
        df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms', utc=True)
        
        # Convert numeric columns
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col])
        
        return df
    
    def get_timeframe_ms(self, timeframe: str) -> int:
        """Get milliseconds for a timeframe.
        
        Args:
            timeframe: Timeframe string (e.g., '1m', '5m', '1h')
            
        Returns:
            Milliseconds
        """
        return _TF_MS.get(timeframe, 0)
    
    def validate_symbol(self, symbol: str) -> bool:
        """Validate if a symbol exists on the exchange.
        
        Args:
            symbol: Trading pair
            
        Returns:
            True if symbol is valid
        """
        return symbol in self.exchange.symbols
    
    def validate_timeframe(self, timeframe: str) -> bool:
        """Validate if a timeframe is supported.
        
        Args:
            timeframe: Timeframe string
            
        Returns:
            True if timeframe is supported
        """
        return timeframe in _TF_MS


# Singleton instance for convenience
collector = DataCollector()
