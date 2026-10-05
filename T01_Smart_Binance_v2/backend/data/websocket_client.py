"""WebSocket Client for T01 Smart Binance Intelligence v2.

This module provides real-time market data streaming via WebSocket.
It supports multiple exchanges (Binance, Kraken) and handles:

- Connection management with auto-reconnect
- Subscriptions to multiple symbols and channels
- Data buffering and caching
- Message parsing and normalization
- Error handling and recovery
- Rate limiting and throttling

The WebSocket client is essential for scalping strategies that require
sub-second data updates.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set, Tuple, TYPE_CHECKING

import aiohttp
import websockets
from websockets.exceptions import ConnectionClosed

if TYPE_CHECKING:
    from backend.data.database import Database

log = logging.getLogger("data.websocket_client")


# ============================================================================
# ENUMS
# ============================================================================

class WebSocketStatus(Enum):
    """Status of WebSocket connection."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class ExchangeType(Enum):
    """Supported exchange types."""
    BINANCE = "binance"
    KRAKEN = "kraken"
    BYBIT = "bybit"


class ChannelType(Enum):
    """WebSocket channel types."""
    TICKER = "ticker"
    TRADE = "trade"
    ORDER_BOOK = "order_book"
    DEPTH = "depth"
    KLINE = "kline"
    CANDLE = "candle"
    AGG_TRADE = "agg_trade"
    MARK_PRICE = "mark_price"
    INDEX_PRICE = "index_price"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class WebSocketConfig:
    """Configuration for WebSocket connection.
    
    Attributes:
        exchange: Exchange type
        base_url: Base WebSocket URL
        ping_interval: Seconds between ping messages
        pong_timeout: Seconds to wait for pong response
        reconnect_delay: Initial delay between reconnect attempts
        max_reconnect_delay: Maximum delay between reconnect attempts
        max_reconnect_attempts: Maximum reconnect attempts before giving up
        message_buffer_size: Maximum number of messages to buffer
        rate_limit: Maximum messages per second to process
    """
    exchange: ExchangeType = ExchangeType.BINANCE
    base_url: str = ""
    ping_interval: float = 20.0
    pong_timeout: float = 10.0
    reconnect_delay: float = 1.0
    max_reconnect_delay: float = 30.0
    max_reconnect_attempts: int = 10
    message_buffer_size: int = 1000
    rate_limit: int = 100

    @classmethod
    def for_exchange(cls, exchange: ExchangeType) -> "WebSocketConfig":
        """Create config for specific exchange."""
        configs = {
            ExchangeType.BINANCE: cls(
                exchange=ExchangeType.BINANCE,
                base_url="wss://stream.binance.com:9443",
                ping_interval=20.0,
                pong_timeout=10.0
            ),
            ExchangeType.KRAKEN: cls(
                exchange=ExchangeType.KRAKEN,
                base_url="wss://ws.kraken.com",
                ping_interval=30.0,
                pong_timeout=15.0
            ),
            ExchangeType.BYBIT: cls(
                exchange=ExchangeType.BYBIT,
                base_url="wss://stream.bybit.com/v5/public/spot",
                ping_interval=20.0,
                pong_timeout=10.0
            )
        }
        return configs.get(exchange, configs[ExchangeType.BINANCE])


@dataclass
class Subscription:
    """Represents a WebSocket subscription.
    
    Attributes:
        subscription_id: Unique ID for this subscription
        symbol: Trading pair
        channel: Channel type
        params: Additional parameters for the subscription
        callback: Function to call with received data
        active: Whether the subscription is active
        created_at: When the subscription was created
    """
    subscription_id: str = field(default_factory=lambda: f"sub_{time.time()}")
    symbol: str = ""
    channel: ChannelType = ChannelType.TICKER
    params: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable[[Dict[str, Any]], None]] = None
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WebSocketMessage:
    """Represents a received WebSocket message.
    
    Attributes:
        raw_data: Raw message data
        parsed_data: Parsed message data
        symbol: Trading pair (if applicable)
        channel: Channel type (if applicable)
        timestamp: When the message was received
        processed: Whether the message has been processed
    """
    raw_data: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)
    symbol: Optional[str] = None
    channel: Optional[ChannelType] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed: bool = False


# ============================================================================
# WEB SOCKET CLIENT
# ============================================================================

class WebSocketClient:
    """WebSocket client for real-time market data streaming.
    
    The WebSocketClient provides:
    
    - Connection management with automatic reconnection
    - Multiple symbol and channel subscriptions
    - Data buffering and rate limiting
    - Message parsing and normalization
    - Error handling and recovery
    - Integration with database for persistence
    
    The client supports Binance, Kraken, and Bybit exchanges out of the box.
    """

    def __init__(
        self,
        exchange: ExchangeType = ExchangeType.BINANCE,
        db: Optional["Database"] = None,
        config: Optional[WebSocketConfig] = None
    ):
        """Initialize WebSocketClient.
        
        Args:
            exchange: Exchange to connect to
            db: Optional database for persistence
            config: Optional WebSocket configuration
        """
        self.exchange = exchange
        self.db = db
        self.config = config or WebSocketConfig.for_exchange(exchange)
        
        # Connection state
        self._status = WebSocketStatus.DISCONNECTED
        self._connection: Optional[websockets.WebSocketClientProtocol] = None
        self._connected_at: Optional[datetime] = None
        self._last_message_at: Optional[datetime] = None
        
        # Subscriptions
        self._subscriptions: Dict[str, Subscription] = {}
        self._subscription_map: Dict[str, List[str]] = {}  # channel_key -> [subscription_ids]
        
        # Message handling
        self._message_buffer: asyncio.Queue = asyncio.Queue(
            maxsize=self.config.message_buffer_size
        )
        self._message_handlers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._last_message_id: int = 0
        self._messages_processed: int = 0
        self._messages_received: int = 0
        
        # Reconnection
        self._reconnect_attempt: int = 0
        self._reconnect_delay: float = self.config.reconnect_delay
        self._reconnect_task: Optional[asyncio.Task] = None
        
        # Ping/pong
        self._ping_task: Optional[asyncio.Task] = None
        self._last_ping: Optional[datetime] = None
        self._last_pong: Optional[datetime] = None
        self._pong_received: bool = True
        
        # Rate limiting
        self._last_process_time: float = 0.0
        self._rate_limit_counter: int = 0
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Shutdown flag
        self._shutdown_flag: bool = False
        
        log.info(f"WebSocketClient initialized for {exchange.value}")

    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================

    async def start(self) -> None:
        """Start the WebSocket client."""
        if self._status != WebSocketStatus.DISCONNECTED:
            log.warning(f"WebSocket is already {self._status.value}, cannot start")
            return
        
        self._shutdown_flag = False
        self._status = WebSocketStatus.CONNECTING
        
        log.info(f"Starting WebSocket client for {self.exchange.value}")
        
        try:
            # Connect to WebSocket
            await self._connect()
            
            # Start background tasks
            self._ping_task = asyncio.create_task(self._ping_loop())
            
            # Process existing subscriptions
            await self._resubscribe()
            
            self._status = WebSocketStatus.CONNECTED
            self._connected_at = datetime.now(timezone.utc)
            
            log.info(f"WebSocket client started and connected to {self.config.base_url}")
            
        except Exception as e:
            self._status = WebSocketStatus.ERROR
            log.error(f"Failed to start WebSocket client: {e}")
            raise

    async def stop(self) -> None:
        """Stop the WebSocket client."""
        if self._status == WebSocketStatus.DISCONNECTED:
            return
        
        self._shutdown_flag = True
        self._status = WebSocketStatus.DISCONNECTED
        
        log.info("Stopping WebSocket client")
        
        try:
            # Cancel ping task
            if self._ping_task:
                self._ping_task.cancel()
                try:
                    await self._ping_task
                except asyncio.CancelledError:
                    pass
            
            # Cancel reconnect task
            if self._reconnect_task:
                self._reconnect_task.cancel()
                try:
                    await self._reconnect_task
                except asyncio.CancelledError:
                    pass
            
            # Close connection
            if self._connection:
                await self._connection.close()
                self._connection = None
            
            log.info("WebSocket client stopped")
            
        except Exception as e:
            log.error(f"Error stopping WebSocket client: {e}")

    async def reconnect(self) -> None:
        """Reconnect to WebSocket."""
        if self._status == WebSocketStatus.CONNECTED:
            return
        
        if self._reconnect_task and not self._reconnect_task.done():
            return
        
        self._reconnect_attempt = 0
        self._reconnect_delay = self.config.reconnect_delay
        self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    # ========================================================================
    # CONNECTION MANAGEMENT
    # ========================================================================

    async def _connect(self) -> None:
        """Establish WebSocket connection."""
        try:
            # Close existing connection if any
            if self._connection:
                await self._connection.close()
                self._connection = None
            
            # Connect to WebSocket
            self._connection = await websockets.connect(
                self.config.base_url,
                extra_headers=self._get_headers(),
                ping_interval=self.config.ping_interval,
                ping_timeout=self.config.pong_timeout
            )
            
            self._status = WebSocketStatus.CONNECTED
            self._connected_at = datetime.now(timezone.utc)
            self._reconnect_attempt = 0
            
            log.info(f"WebSocket connected to {self.config.base_url}")
            
            # Start message listener
            asyncio.create_task(self._listen_for_messages())
            
        except Exception as e:
            self._status = WebSocketStatus.ERROR
            log.error(f"WebSocket connection failed: {e}")
            raise

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for WebSocket connection.
        
        Returns:
            Dictionary of headers
        """
        headers = {}
        
        # Add exchange-specific headers if needed
        if self.exchange == ExchangeType.KRAKEN:
            headers["User-Agent"] = "T01-Smart-Binance-v2"
        
        return headers

    async def _reconnect_loop(self) -> None:
        """Reconnect loop with exponential backoff."""
        self._status = WebSocketStatus.RECONNECTING
        
        while not self._shutdown_flag and self._reconnect_attempt < self.config.max_reconnect_attempts:
            self._reconnect_attempt += 1
            
            try:
                log.info(f"Reconnect attempt {self._reconnect_attempt}/{self.config.max_reconnect_attempts} "
                        f"(delay: {self._reconnect_delay:.1f}s)")
                
                await asyncio.sleep(self._reconnect_delay)
                
                await self._connect()
                
                # Resubscribe after reconnection
                await self._resubscribe()
                
                # Reset reconnect state
                self._reconnect_attempt = 0
                self._reconnect_delay = self.config.reconnect_delay
                self._status = WebSocketStatus.CONNECTED
                
                break
                
            except Exception as e:
                log.error(f"Reconnect attempt {self._reconnect_attempt} failed: {e}")
                
                # Exponential backoff
                self._reconnect_delay = min(
                    self._reconnect_delay * 2,
                    self.config.max_reconnect_delay
                )
        
        if self._reconnect_attempt >= self.config.max_reconnect_attempts:
            self._status = WebSocketStatus.ERROR
            log.error("Max reconnect attempts reached, giving up")

    async def _listen_for_messages(self) -> None:
        """Listen for incoming WebSocket messages."""
        try:
            async for message in self._connection:
                self._last_message_at = datetime.now(timezone.utc)
                self._messages_received += 1
                
                # Put message in buffer
                await self._message_buffer.put(message)
                
                # Process message immediately if not rate limited
                await self._process_message(message)
                
        except ConnectionClosed:
            log.info("WebSocket connection closed")
            self._status = WebSocketStatus.DISCONNECTED
            self._connection = None
            
            # Auto-reconnect
            if not self._shutdown_flag:
                await self.reconnect()
                
        except Exception as e:
            log.error(f"WebSocket message listener error: {e}")
            self._status = WebSocketStatus.ERROR
            self._connection = None

    # ========================================================================
    # SUBSCRIPTION MANAGEMENT
    # ========================================================================

    async def subscribe(
        self,
        symbol: str,
        channel: ChannelType,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """Subscribe to a WebSocket channel.
        
        Args:
            symbol: Trading pair
            channel: Channel type to subscribe to
            callback: Optional callback function for received data
            params: Optional additional parameters
            
        Returns:
            Subscription ID
        """
        async with self._lock:
            # Create subscription
            subscription = Subscription(
                symbol=symbol,
                channel=channel,
                callback=callback,
                params=params or {}
            )
            
            self._subscriptions[subscription.subscription_id] = subscription
            
            # Add to subscription map
            channel_key = self._get_channel_key(symbol, channel, params)
            if channel_key not in self._subscription_map:
                self._subscription_map[channel_key] = []
            self._subscription_map[channel_key].append(subscription.subscription_id)
            
            # If connected, send subscription message
            if self._status == WebSocketStatus.CONNECTED:
                await self._send_subscription_message(subscription)
            
            log.info(f"Subscribed to {channel.value} for {symbol}: {subscription.subscription_id}")
            return subscription.subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a WebSocket channel.
        
        Args:
            subscription_id: ID of subscription to remove
            
        Returns:
            True if unsubscribed successfully
        """
        async with self._lock:
            subscription = self._subscriptions.get(subscription_id)
            if not subscription:
                log.warning(f"Subscription not found: {subscription_id}")
                return False
            
            subscription.active = False
            del self._subscriptions[subscription_id]
            
            # Remove from subscription map
            channel_key = self._get_channel_key(
                subscription.symbol,
                subscription.channel,
                subscription.params
            )
            if channel_key in self._subscription_map:
                if subscription_id in self._subscription_map[channel_key]:
                    self._subscription_map[channel_key].remove(subscription_id)
                if not self._subscription_map[channel_key]:
                    del self._subscription_map[channel_key]
                    
                    # If connected, send unsubscribe message
                    if self._status == WebSocketStatus.CONNECTED:
                        await self._send_unsubscribe_message(subscription)
            
            log.info(f"Unsubscribed: {subscription_id}")
            return True

    async def unsubscribe_all(self) -> None:
        """Unsubscribe from all channels."""
        async with self._lock:
            subscription_ids = list(self._subscriptions.keys())
            for sub_id in subscription_ids:
                await self.unsubscribe(sub_id)
            
            log.info("Unsubscribed from all channels")

    async def _resubscribe(self) -> None:
        """Resubscribe to all active subscriptions after reconnection."""
        async with self._lock:
            for subscription in self._subscriptions.values():
                if subscription.active:
                    await self._send_subscription_message(subscription)
            
            log.info(f"Resubscribed to {len(self._subscriptions)} subscriptions")

    def _get_channel_key(
        self,
        symbol: str,
        channel: ChannelType,
        params: Dict[str, Any]
    ) -> str:
        """Generate a unique key for a channel subscription.
        
        Args:
            symbol: Trading pair
            channel: Channel type
            params: Additional parameters
            
        Returns:
            Unique channel key
        """
        # Sort params for consistent key
        sorted_params = json.dumps(params, sort_keys=True) if params else "{}"
        return f"{symbol}|{channel.value}|{sorted_params}"

    async def _send_subscription_message(self, subscription: Subscription) -> None:
        """Send subscription message to WebSocket.
        
        Args:
            subscription: Subscription to send
        """
        if not self._connection or self._status != WebSocketStatus.CONNECTED:
            return
        
        try:
            message = self._build_subscription_message(subscription)
            if message:
                await self._connection.send(message)
                log.debug(f"Sent subscription: {message}")
        except Exception as e:
            log.error(f"Failed to send subscription message: {e}")

    async def _send_unsubscribe_message(self, subscription: Subscription) -> None:
        """Send unsubscribe message to WebSocket.
        
        Args:
            subscription: Subscription to remove
        """
        if not self._connection or self._status != WebSocketStatus.CONNECTED:
            return
        
        try:
            message = self._build_unsubscribe_message(subscription)
            if message:
                await self._connection.send(message)
                log.debug(f"Sent unsubscribe: {message}")
        except Exception as e:
            log.error(f"Failed to send unsubscribe message: {e}")

    def _build_subscription_message(self, subscription: Subscription) -> Optional[str]:
        """Build subscription message for specific exchange.
        
        Args:
            subscription: Subscription to build message for
            
        Returns:
            Subscription message string or None
        """
        if self.exchange == ExchangeType.BINANCE:
            return self._build_binance_subscription(subscription)
        elif self.exchange == ExchangeType.KRAKEN:
            return self._build_kraken_subscription(subscription)
        elif self.exchange == ExchangeType.BYBIT:
            return self._build_bybit_subscription(subscription)
        return None

    def _build_unsubscribe_message(self, subscription: Subscription) -> Optional[str]:
        """Build unsubscribe message for specific exchange.
        
        Args:
            subscription: Subscription to build message for
            
        Returns:
            Unsubscribe message string or None
        """
        if self.exchange == ExchangeType.BINANCE:
            return self._build_binance_unsubscribe(subscription)
        elif self.exchange == ExchangeType.KRAKEN:
            return self._build_kraken_unsubscribe(subscription)
        elif self.exchange == ExchangeType.BYBIT:
            return self._build_bybit_unsubscribe(subscription)
        return None

    # ========================================================================
    # EXCHANGE-SPECIFIC MESSAGE BUILDERS
    # ========================================================================

    def _build_binance_subscription(self, subscription: Subscription) -> str:
        """Build Binance subscription message."""
        symbol = subscription.symbol.replace("/", "").lower()
        
        channel_map = {
            ChannelType.TICKER: f"{symbol}@ticker",
            ChannelType.TRADE: f"{symbol}@trade",
            ChannelType.ORDER_BOOK: f"{symbol}@depth",
            ChannelType.DEPTH: f"{symbol}@depth",
            ChannelType.KLINE: f"{symbol}@kline_{subscription.params.get('interval', '1m')}",
            ChannelType.CANDLE: f"{symbol}@kline_{subscription.params.get('interval', '1m')}",
            ChannelType.AGG_TRADE: f"{symbol}@aggTrade",
            ChannelType.MARK_PRICE: f"{symbol}@markPrice",
            ChannelType.INDEX_PRICE: f"{symbol}@indexPrice"
        }
        
        channel_str = channel_map.get(subscription.channel, f"{symbol}@ticker")
        
        return json.dumps({
            "method": "SUBSCRIBE",
            "params": [channel_str],
            "id": self._get_next_message_id()
        })

    def _build_binance_unsubscribe(self, subscription: Subscription) -> str:
        """Build Binance unsubscribe message."""
        symbol = subscription.symbol.replace("/", "").lower()
        
        channel_map = {
            ChannelType.TICKER: f"{symbol}@ticker",
            ChannelType.TRADE: f"{symbol}@trade",
            ChannelType.ORDER_BOOK: f"{symbol}@depth",
            ChannelType.DEPTH: f"{symbol}@depth",
            ChannelType.KLINE: f"{symbol}@kline_{subscription.params.get('interval', '1m')}",
            ChannelType.CANDLE: f"{symbol}@kline_{subscription.params.get('interval', '1m')}",
            ChannelType.AGG_TRADE: f"{symbol}@aggTrade",
            ChannelType.MARK_PRICE: f"{symbol}@markPrice",
            ChannelType.INDEX_PRICE: f"{symbol}@indexPrice"
        }
        
        channel_str = channel_map.get(subscription.channel, f"{symbol}@ticker")
        
        return json.dumps({
            "method": "UNSUBSCRIBE",
            "params": [channel_str],
            "id": self._get_next_message_id()
        })

    def _build_kraken_subscription(self, subscription: Subscription) -> str:
        """Build Kraken subscription message."""
        symbol = subscription.symbol
        
        channel_map = {
            ChannelType.TICKER: "ticker",
            ChannelType.TRADE: "trade",
            ChannelType.ORDER_BOOK: "book",
            ChannelType.DEPTH: "book"
        }
        
        channel_name = channel_map.get(subscription.channel, "ticker")
        
        return json.dumps({
            "event": "subscribe",
            "subscription": {
                "name": channel_name,
                "symbol": [symbol]
            },
            "reqid": self._get_next_message_id()
        })

    def _build_kraken_unsubscribe(self, subscription: Subscription) -> str:
        """Build Kraken unsubscribe message."""
        symbol = subscription.symbol
        
        channel_map = {
            ChannelType.TICKER: "ticker",
            ChannelType.TRADE: "trade",
            ChannelType.ORDER_BOOK: "book",
            ChannelType.DEPTH: "book"
        }
        
        channel_name = channel_map.get(subscription.channel, "ticker")
        
        return json.dumps({
            "event": "unsubscribe",
            "subscription": {
                "name": channel_name,
                "symbol": [symbol]
            },
            "reqid": self._get_next_message_id()
        })

    def _build_bybit_subscription(self, subscription: Subscription) -> str:
        """Build Bybit subscription message."""
        symbol = subscription.symbol
        
        channel_map = {
            ChannelType.TICKER: "tickers.V2",
            ChannelType.TRADE: "publicTrade.V2",
            ChannelType.ORDER_BOOK: "orderbook.50.V2",
            ChannelType.DEPTH: "orderbook.50.V2"
        }
        
        channel_name = channel_map.get(subscription.channel, "tickers.V2")
        
        return json.dumps({
            "op": "sub",
            "args": [f"{channel_name}.{symbol}"]
        })

    def _build_bybit_unsubscribe(self, subscription: Subscription) -> str:
        """Build Bybit unsubscribe message."""
        symbol = subscription.symbol
        
        channel_map = {
            ChannelType.TICKER: "tickers.V2",
            ChannelType.TRADE: "publicTrade.V2",
            ChannelType.ORDER_BOOK: "orderbook.50.V2",
            ChannelType.DEPTH: "orderbook.50.V2"
        }
        
        channel_name = channel_map.get(subscription.channel, "tickers.V2")
        
        return json.dumps({
            "op": "unsub",
            "args": [f"{channel_name}.{symbol}"]
        })

    def _get_next_message_id(self) -> int:
        """Get next message ID.
        
        Returns:
            Next message ID
        """
        self._last_message_id += 1
        return self._last_message_id

    # ========================================================================
    # MESSAGE PROCESSING
    # ========================================================================

    async def _process_message(self, message: str) -> None:
        """Process a received WebSocket message.
        
        Args:
            message: Raw message string
        """
        # Rate limiting
        now = time.time()
        if now - self._last_process_time < 1.0:
            self._rate_limit_counter += 1
        else:
            self._rate_limit_counter = 0
            self._last_process_time = now
        
        if self._rate_limit_counter > self.config.rate_limit:
            log.warning(f"Rate limit exceeded: {self._rate_limit_counter} messages/sec")
            return
        
        try:
            # Parse message
            parsed = self._parse_message(message)
            if not parsed:
                return
            
            # Create message object
            ws_message = WebSocketMessage(
                raw_data=message,
                parsed_data=parsed,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Extract symbol and channel
            self._extract_metadata(ws_message)
            
            # Handle ping/pong
            if ws_message.channel == "ping":
                await self._handle_ping(ws_message)
                return
            elif ws_message.channel == "pong":
                await self._handle_pong(ws_message)
                return
            
            # Handle subscription responses
            if self._is_subscription_response(ws_message):
                await self._handle_subscription_response(ws_message)
                return
            
            # Handle error responses
            if self._is_error_response(ws_message):
                await self._handle_error_response(ws_message)
                return
            
            # Process data message
            await self._process_data_message(ws_message)
            
            # Mark as processed
            ws_message.processed = True
            self._messages_processed += 1
            
            # Save to database if configured
            if self.db:
                await self._save_message_to_db(ws_message)
            
        except Exception as e:
            log.error(f"Failed to process message: {e}")

    def _parse_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse raw WebSocket message.
        
        Args:
            message: Raw message string
            
        Returns:
            Parsed message dictionary or None
        """
        try:
            return json.loads(message)
        except json.JSONDecodeError:
            log.debug(f"Failed to parse JSON message: {message[:100]}...")
            return None

    def _extract_metadata(self, message: WebSocketMessage) -> None:
        """Extract symbol and channel metadata from message.
        
        Args:
            message: WebSocketMessage to update
        """
        if self.exchange == ExchangeType.BINANCE:
            self._extract_binance_metadata(message)
        elif self.exchange == ExchangeType.KRAKEN:
            self._extract_kraken_metadata(message)
        elif self.exchange == ExchangeType.BYBIT:
            self._extract_bybit_metadata(message)

    def _extract_binance_metadata(self, message: WebSocketMessage) -> None:
        """Extract metadata from Binance message."""
        data = message.parsed_data
        
        if isinstance(data, dict):
            # Handle result messages
            if "result" in data:
                message.channel = "subscription"
                return
            
            # Handle stream messages
            if "stream" in data:
                stream = data.get("stream", "")
                if "@" in stream:
                    parts = stream.split("@")
                    message.symbol = parts[0].upper().replace("", "/")
                    message.channel = ChannelType(parts[1].split("_")[0])
            
            # Handle kline/candle messages
            if "e" in data:
                event_type = data.get("e")
                if event_type == "kline":
                    message.channel = ChannelType.KLINE
                    message.symbol = data.get("s", "").upper().replace("", "/")
                elif event_type == "trade":
                    message.channel = ChannelType.TRADE
                    message.symbol = data.get("s", "").upper().replace("", "/")
                elif event_type == "aggTrade":
                    message.channel = ChannelType.AGG_TRADE
                    message.symbol = data.get("s", "").upper().replace("", "/")
                elif event_type == "24hrTicker":
                    message.channel = ChannelType.TICKER
                    message.symbol = data.get("s", "").upper().replace("", "/")
                elif event_type == "depthUpdate":
                    message.channel = ChannelType.DEPTH
                    message.symbol = data.get("s", "").upper().replace("", "/")

    def _extract_kraken_metadata(self, message: WebSocketMessage) -> None:
        """Extract metadata from Kraken message."""
        data = message.parsed_data
        
        if isinstance(data, list) and len(data) > 0:
            # Kraken sends arrays: [channel_id, data, ...]
            if isinstance(data[0], int):
                # Channel ID
                message.channel = ChannelType.TICKER
            elif isinstance(data[0], str):
                # Channel name
                message.channel = ChannelType(data[0])
        elif isinstance(data, dict):
            if "event" in data:
                message.channel = data.get("event", "unknown")

    def _extract_bybit_metadata(self, message: WebSocketMessage) -> None:
        """Extract metadata from Bybit message."""
        data = message.parsed_data
        
        if isinstance(data, dict):
            if "topic" in data:
                topic = data.get("topic", "")
                if "tickers" in topic:
                    message.channel = ChannelType.TICKER
                elif "publicTrade" in topic:
                    message.channel = ChannelType.TRADE
                elif "orderbook" in topic:
                    message.channel = ChannelType.ORDER_BOOK

    def _is_subscription_response(self, message: WebSocketMessage) -> bool:
        """Check if message is a subscription response.
        
        Args:
            message: WebSocketMessage to check
            
        Returns:
            True if message is a subscription response
        """
        data = message.parsed_data
        
        if self.exchange == ExchangeType.BINANCE:
            return isinstance(data, dict) and "result" in data and "method" in data
        elif self.exchange == ExchangeType.KRAKEN:
            return isinstance(data, dict) and "event" in data and data.get("event") == "subscriptionStatus"
        elif self.exchange == ExchangeType.BYBIT:
            return isinstance(data, dict) and "success" in data
        
        return False

    def _is_error_response(self, message: WebSocketMessage) -> bool:
        """Check if message is an error response.
        
        Args:
            message: WebSocketMessage to check
            
        Returns:
            True if message is an error response
        """
        data = message.parsed_data
        
        if isinstance(data, dict):
            if "error" in data:
                return True
            if "code" in data and "msg" in data:
                return True
        
        return False

    async def _handle_ping(self, message: WebSocketMessage) -> None:
        """Handle ping message.
        
        Args:
            message: Ping message
        """
        self._last_ping = datetime.now(timezone.utc)
        self._pong_received = False
        
        try:
            if self._connection:
                await self._connection.pong()
                self._pong_received = True
                self._last_pong = datetime.now(timezone.utc)
        except Exception as e:
            log.error(f"Failed to send pong: {e}")

    async def _handle_pong(self, message: WebSocketMessage) -> None:
        """Handle pong message.
        
        Args:
            message: Pong message
        """
        self._last_pong = datetime.now(timezone.utc)
        self._pong_received = True

    async def _handle_subscription_response(self, message: WebSocketMessage) -> None:
        """Handle subscription response message.
        
        Args:
            message: Subscription response message
        """
        data = message.parsed_data
        
        if self.exchange == ExchangeType.BINANCE:
            if isinstance(data, dict) and data.get("result") is not None:
                log.info(f"Subscription response: {data.get('result')}")
        elif self.exchange == ExchangeType.KRAKEN:
            log.info(f"Subscription response: {data}")
        elif self.exchange == ExchangeType.BYBIT:
            if isinstance(data, dict) and data.get("success"):
                log.info("Subscription successful")

    async def _handle_error_response(self, message: WebSocketMessage) -> None:
        """Handle error response message.
        
        Args:
            message: Error response message
        """
        data = message.parsed_data
        
        if isinstance(data, dict):
            error_msg = data.get("error", data.get("msg", str(data)))
            log.error(f"WebSocket error: {error_msg}")

    async def _process_data_message(self, message: WebSocketMessage) -> None:
        """Process a data message (not ping/pong/subscription/error).
        
        Args:
            message: Data message to process
        """
        if not message.symbol or not message.channel:
            log.debug(f"Message without symbol/channel: {message.raw_data[:100]}")
            return
        
        # Find matching subscriptions
        channel_key = self._get_channel_key(
            message.symbol,
            message.channel,
            {}
        )
        
        subscription_ids = self._subscription_map.get(channel_key, [])
        
        for sub_id in subscription_ids:
            subscription = self._subscriptions.get(sub_id)
            if subscription and subscription.active:
                # Normalize data for consistent format
                normalized = self._normalize_data(message)
                
                # Call subscription callback
                if subscription.callback:
                    try:
                        subscription.callback(normalized)
                    except Exception as e:
                        log.error(f"Callback error for {sub_id}: {e}")
                
                # Call channel-specific handlers
                await self._call_channel_handlers(message.channel, normalized)

    def _normalize_data(self, message: WebSocketMessage) -> Dict[str, Any]:
        """Normalize message data to consistent format.
        
        Args:
            message: WebSocketMessage to normalize
            
        Returns:
            Normalized data dictionary
        """
        data = message.parsed_data
        normalized = {
            "symbol": message.symbol,
            "channel": message.channel.value if message.channel else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "exchange": self.exchange.value,
            "raw": data
        }
        
        if message.channel == ChannelType.TICKER:
            normalized.update(self._normalize_ticker(data))
        elif message.channel == ChannelType.TRADE:
            normalized.update(self._normalize_trade(data))
        elif message.channel == ChannelType.ORDER_BOOK:
            normalized.update(self._normalize_order_book(data))
        elif message.channel == ChannelType.KLINE or message.channel == ChannelType.CANDLE:
            normalized.update(self._normalize_kline(data))
        
        return normalized

    def _normalize_ticker(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize ticker data."""
        if self.exchange == ExchangeType.BINANCE:
            return {
                "price": float(data.get("c", data.get("lastPrice", 0))),
                "volume": float(data.get("v", data.get("volume", 0))),
                "bid": float(data.get("b", data.get("bestBid", 0))),
                "ask": float(data.get("a", data.get("bestAsk", 0))),
                "high": float(data.get("h", data.get("highPrice", 0))),
                "low": float(data.get("l", data.get("lowPrice", 0))),
                "change_pct": float(data.get("P", data.get("priceChangePercent", 0)))
            }
        elif self.exchange == ExchangeType.KRAKEN:
            return {
                "price": float(data.get("c", [0])[0]),
                "volume": float(data.get("v", [0])[0]),
                "bid": float(data.get("b", [0])[0]),
                "ask": float(data.get("a", [0])[0]),
                "high": float(data.get("h", [0])[0]),
                "low": float(data.get("l", [0])[0])
            }
        elif self.exchange == ExchangeType.BYBIT:
            return {
                "price": float(data.get("lastPrice", 0)),
                "volume": float(data.get("volume24h", 0)),
                "bid": float(data.get("bid1Price", 0)),
                "ask": float(data.get("ask1Price", 0)),
                "high": float(data.get("high24h", 0)),
                "low": float(data.get("low24h", 0))
            }
        
        return {}

    def _normalize_trade(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize trade data."""
        if self.exchange == ExchangeType.BINANCE:
            return {
                "price": float(data.get("p", 0)),
                "qty": float(data.get("q", 0)),
                "side": data.get("m", ""),  # True = buyer is market maker
                "time": data.get("T", 0)
            }
        elif self.exchange == ExchangeType.KRAKEN:
            return {
                "price": float(data.get("price", [0])[0]),
                "qty": float(data.get("volume", [0])[0]),
                "side": data.get("type", ""),
                "time": data.get("time", 0)
            }
        elif self.exchange == ExchangeType.BYBIT:
            return {
                "price": float(data.get("price", 0)),
                "qty": float(data.get("qty", 0)),
                "side": data.get("side", ""),
                "time": data.get("time", 0)
            }
        
        return {}

    def _normalize_order_book(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize order book data."""
        if self.exchange == ExchangeType.BINANCE:
            return {
                "bids": [[float(b[0]), float(b[1])] for b in data.get("b", [])],
                "asks": [[float(a[0]), float(a[1])] for a in data.get("a", [])],
                "last_update_id": data.get("lastUpdateId", 0)
            }
        elif self.exchange == ExchangeType.KRAKEN:
            return {
                "bids": [[float(b[0]), float(b[1])] for b in data.get("b", [])],
                "asks": [[float(a[0]), float(a[1])] for a in data.get("a", [])]
            }
        elif self.exchange == ExchangeType.BYBIT:
            return {
                "bids": [[float(b["price"]), float(b["qty"])] for b in data.get("b", [])],
                "asks": [[float(a["price"]), float(a["qty"])] for a in data.get("a", [])]
            }
        
        return {}

    def _normalize_kline(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize kline/candle data."""
        if self.exchange == ExchangeType.BINANCE:
            kline = data.get("k", {})
            return {
                "open_time": kline.get("t", 0),
                "close_time": kline.get("T", 0),
                "open": float(kline.get("o", 0)),
                "high": float(kline.get("h", 0)),
                "low": float(kline.get("l", 0)),
                "close": float(kline.get("c", 0)),
                "volume": float(kline.get("v", 0)),
                "is_closed": kline.get("x", False)
            }
        elif self.exchange == ExchangeType.BYBIT:
            return {
                "open_time": data.get("start", 0),
                "close_time": data.get("end", 0),
                "open": float(data.get("open", 0)),
                "high": float(data.get("high", 0)),
                "low": float(data.get("low", 0)),
                "close": float(data.get("close", 0)),
                "volume": float(data.get("volume", 0)),
                "is_closed": data.get("confirm", False)
            }
        
        return {}

    # ========================================================================
    # HANDLER MANAGEMENT
    # ========================================================================

    def add_channel_handler(
        self,
        channel: ChannelType,
        handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Add a handler for a specific channel type.
        
        Args:
            channel: Channel type to handle
            handler: Function to call with received data
        """
        if channel.value not in self._message_handlers:
            self._message_handlers[channel.value] = []
        
        self._message_handlers[channel.value].append(handler)
        log.debug(f"Added handler for {channel.value}")

    def remove_channel_handler(
        self,
        channel: ChannelType,
        handler: Callable[[Dict[str, Any]], None]
    ) -> bool:
        """Remove a handler for a specific channel type.
        
        Args:
            channel: Channel type
            handler: Handler function to remove
            
        Returns:
            True if handler was removed
        """
        if channel.value in self._message_handlers:
            handlers = self._message_handlers[channel.value]
            if handler in handlers:
                handlers.remove(handler)
                log.debug(f"Removed handler for {channel.value}")
                return True
        
        return False

    async def _call_channel_handlers(
        self,
        channel: ChannelType,
        data: Dict[str, Any]
    ) -> None:
        """Call all handlers for a channel type.
        
        Args:
            channel: Channel type
            data: Data to pass to handlers
        """
        handlers = self._message_handlers.get(channel.value, [])
        
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                log.error(f"Channel handler error for {channel.value}: {e}")

    # ========================================================================
    # PING/PONG MANAGEMENT
    # ========================================================================

    async def _ping_loop(self) -> None:
        """Background ping loop to keep connection alive."""
        try:
            while not self._shutdown_flag:
                await asyncio.sleep(self.config.ping_interval)
                
                if self._status == WebSocketStatus.CONNECTED:
                    # Check if we need to ping
                    if self._connection:
                        try:
                            await self._connection.ping()
                            self._last_ping = datetime.now(timezone.utc)
                        except Exception as e:
                            log.error(f"Ping failed: {e}")
                            self._status = WebSocketStatus.ERROR
                            await self.reconnect()
                
                # Check pong timeout
                if self._last_ping and not self._pong_received:
                    timeout = (datetime.now(timezone.utc) - self._last_ping).total_seconds()
                    if timeout > self.config.pong_timeout:
                        log.error(f"Pong timeout after {timeout:.1f}s")
                        self._status = WebSocketStatus.ERROR
                        await self.reconnect()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"Ping loop error: {e}")

    # ========================================================================
    # DATABASE INTEGRATION
    # ========================================================================

    async def _save_message_to_db(self, message: WebSocketMessage) -> None:
        """Save message to database.
        
        Args:
            message: Message to save
        """
        if not self.db:
            return
        
        try:
            await self.db.create_websocket_message(
                message_id=f"ws_{self._messages_received}",
                exchange=self.exchange.value,
                symbol=message.symbol or "",
                channel=message.channel.value if message.channel else "",
                raw_data=message.raw_data,
                parsed_data=json.dumps(message.parsed_data),
                timestamp=message.timestamp
            )
        except Exception as e:
            log.error(f"Failed to save message to DB: {e}")

    # ========================================================================
    # STATISTICS & MONITORING
    # ========================================================================

    async def get_statistics(self) -> Dict[str, Any]:
        """Get WebSocket client statistics.
        
        Returns:
            Dictionary with client statistics
        """
        return {
            "status": self._status.value,
            "exchange": self.exchange.value,
            "connected_at": self._connected_at.isoformat() if self._connected_at else None,
            "last_message_at": self._last_message_at.isoformat() if self._last_message_at else None,
            "messages_received": self._messages_received,
            "messages_processed": self._messages_processed,
            "subscriptions": len(self._subscriptions),
            "active_subscriptions": sum(
                1 for s in self._subscriptions.values() if s.active
            ),
            "reconnect_attempts": self._reconnect_attempt,
            "reconnect_delay": self._reconnect_delay,
            "rate_limit_counter": self._rate_limit_counter,
            "ping_pong": {
                "last_ping": self._last_ping.isoformat() if self._last_ping else None,
                "last_pong": self._last_pong.isoformat() if self._last_pong else None,
                "pong_received": self._pong_received
            }
        }

    def get_subscriptions(self) -> List[Subscription]:
        """Get all subscriptions.
        
        Returns:
            List of all subscriptions
        """
        return list(self._subscriptions.values())

    def get_active_subscriptions(self) -> List[Subscription]:
        """Get all active subscriptions.
        
        Returns:
            List of active subscriptions
        """
        return [s for s in self._subscriptions.values() if s.active]
