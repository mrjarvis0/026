import ccxt
import time

_exchange = None

def get_exchange():
    global _exchange
    if _exchange is None:
        _exchange = ccxt.binance({
            'enableRateLimit': True,
        })
    return _exchange

def fetch_ohlcv(symbol: str, timeframe: str, limit: int = 250):
    ex = get_exchange()
    return ex.fetch_ohlcv(symbol, timeframe, limit=limit)

def fetch_ticker(symbol: str):
    ex = get_exchange()
    return ex.fetch_ticker(symbol)

def fetch_order_book(symbol: str, limit: int = 12):
    ex = get_exchange()
    return ex.fetch_order_book(symbol, limit=limit)
