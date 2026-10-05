"""Futures Manager for T01 Smart Binance Intelligence v2.

This module provides comprehensive futures trading management.
It handles all aspects of futures trading including:

1. Futures contract selection and configuration
2. Leverage management
3. Position management for futures
4. Order execution for futures contracts
5. Margin management and monitoring
6. Liquidation risk calculation
7. Funding rate monitoring
8. Integration with spot trading components

The FuturesManager works with the existing OrderManager and PositionManager
but adds futures-specific functionality.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING

import ccxt.async_support as ccxt

if TYPE_CHECKING:
    from backend.trading.order_manager import OrderManager, Order, OrderSide, OrderType
    from backend.trading.position_manager import PositionManager, Position, PositionSide
    from backend.data.database import Database
    from backend.data.collector import DataCollector

log = logging.getLogger("futures.futures_manager")


# ============================================================================
# ENUMS
# ============================================================================

class FuturesType(Enum):
    """Type of futures contract."""
    PERPETUAL = "perpetual"      # Perpetual futures (no expiry)
    QUARTERLY = "quarterly"      # Quarterly futures
    MONTHLY = "monthly"        # Monthly futures


class MarginMode(Enum):
    """Margin mode for futures trading."""
    ISOLATED = "isolated"        # Isolated margin
    CROSSED = "crossed"         # Cross margin


class PositionMode(Enum):
    """Position mode for futures."""
    HEDGE = "hedge"             # Hedge mode (can have both long and short)
    ONE_WAY = "one_way"         # One-way mode (net position only)


class FuturesSide(Enum):
    """Side for futures orders."""
    BUY = "buy"
    SELL = "sell"
    BUY_CLOSE = "buy_close"     # Buy to close short position
    SELL_CLOSE = "sell_close"   # Sell to close long position


class FuturesOrderType(Enum):
    """Order types for futures."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"
    TAKE_PROFIT = "take_profit"
    TAKE_PROFIT_MARKET = "take_profit_market"
    TAKE_PROFIT_LIMIT = "take_profit_limit"
    TRAILING_STOP_MARKET = "trailing_stop_market"
    LIQUIDATION = "liquidation"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class FuturesContract:
    """Represents a futures contract.
    
    Attributes:
        symbol: Contract symbol (e.g., 'BTCUSDT')
        base_asset: Base asset (e.g., 'BTC')
        quote_asset: Quote asset (e.g., 'USDT')
        contract_type: FuturesType
        leverage: Current leverage
        margin_mode: MarginMode
        position_mode: PositionMode
        tick_size: Minimum price increment
        step_size: Minimum quantity increment
        min_notional: Minimum notional value
        max_notional: Maximum notional value
        maintenance_margin_rate: Maintenance margin rate
        liquidation_fee_rate: Liquidation fee rate
        funding_rate: Current funding rate
        next_funding_time: Next funding time
        expiry_time: Expiry time (for non-perpetual contracts)
        index_price: Current index price
        mark_price: Current mark price
        last_price: Last traded price
        price_decimals: Number of price decimals
        quantity_decimals: Number of quantity decimals
    """
    symbol: str = ""
    base_asset: str = ""
    quote_asset: str = ""
    contract_type: FuturesType = FuturesType.PERPETUAL
    leverage: float = 1.0
    margin_mode: MarginMode = MarginMode.ISOLATED
    position_mode: PositionMode = PositionMode.ONE_WAY
    tick_size: float = 0.01
    step_size: float = 0.001
    min_notional: float = 1.0
    max_notional: float = 1000000.0
    maintenance_margin_rate: float = 0.005  # 0.5%
    liquidation_fee_rate: float = 0.005  # 0.5%
    funding_rate: float = 0.0
    next_funding_time: Optional[datetime] = None
    expiry_time: Optional[datetime] = None
    index_price: float = 0.0
    mark_price: float = 0.0
    last_price: float = 0.0
    price_decimals: int = 2
    quantity_decimals: int = 3


@dataclass
class FuturesPosition:
    """Represents a futures position.
    
    Attributes:
        position_id: Unique position ID
        symbol: Contract symbol
        side: PositionSide (LONG or SHORT)
        entry_price: Average entry price
        current_qty: Current quantity
        leverage: Leverage used
        margin: Margin used
        isolated_margin: Isolated margin (if applicable)
        mark_price: Current mark price
        liquidation_price: Price at which position will be liquidated
        unrealized_pnl: Unrealized P&L
        unrealized_pnl_pct: Unrealized P&L percentage
        margin_mode: MarginMode
        auto_deleveraging: Whether position is in auto-deleveraging
        created_at: When position was created
        updated_at: When position was last updated
    """
    position_id: str = ""
    symbol: str = ""
    side: "PositionSide" = None
    entry_price: float = 0.0
    current_qty: float = 0.0
    leverage: float = 1.0
    margin: float = 0.0
    isolated_margin: float = 0.0
    mark_price: float = 0.0
    liquidation_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    margin_mode: MarginMode = MarginMode.ISOLATED
    auto_deleveraging: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class FuturesOrder:
    """Represents a futures order.
    
    Attributes:
        order_id: Unique order ID
        exchange_order_id: Exchange order ID
        symbol: Contract symbol
        side: FuturesSide
        order_type: FuturesOrderType
        price: Order price
        qty: Order quantity
        filled: Filled quantity
        avg_fill_price: Average fill price
        status: Order status
        reduce_only: Whether this is a reduce-only order
        close_position: Whether this order closes a position
        position_id: Position ID this order affects
        leverage: Leverage for this order
        margin: Margin used for this order
        created_at: When order was created
        updated_at: When order was last updated
    """
    order_id: str = ""
    exchange_order_id: Optional[str] = None
    symbol: str = ""
    side: FuturesSide = FuturesSide.BUY
    order_type: FuturesOrderType = FuturesOrderType.MARKET
    price: Optional[float] = None
    qty: float = 0.0
    filled: float = 0.0
    avg_fill_price: Optional[float] = None
    status: str = "pending"
    reduce_only: bool = False
    close_position: bool = False
    position_id: Optional[str] = None
    leverage: float = 1.0
    margin: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class FundingInfo:
    """Funding rate information.
    
    Attributes:
        symbol: Contract symbol
        funding_rate: Current funding rate
        next_funding_time: Next funding time
        estimated_funding: Estimated funding payment/receipt
        funding_interval: Funding interval in hours
    """
    symbol: str = ""
    funding_rate: float = 0.0
    next_funding_time: Optional[datetime] = None
    estimated_funding: float = 0.0
    funding_interval: int = 8  # Default 8 hours


@dataclass
class LiquidationInfo:
    """Liquidation risk information.
    
    Attributes:
        symbol: Contract symbol
        position_side: PositionSide
        current_price: Current price
        liquidation_price: Liquidation price
        distance_to_liquidation: Distance to liquidation (percentage)
        risk_level: Risk level (low, medium, high, critical)
        estimated_time_to_liquidation: Estimated time to liquidation (in hours)
        margin_ratio: Current margin ratio
        maintenance_margin_ratio: Maintenance margin ratio
    """
    symbol: str = ""
    position_side: "PositionSide" = None
    current_price: float = 0.0
    liquidation_price: float = 0.0
    distance_to_liquidation: float = 0.0
    risk_level: str = "low"
    estimated_time_to_liquidation: Optional[float] = None
    margin_ratio: float = 0.0
    maintenance_margin_ratio: float = 0.0


# ============================================================================
# FUTURES MANAGER
# ============================================================================

class FuturesManager:
    """Manages futures trading operations.
    
    The FuturesManager provides:
    
    1. Futures contract management
    2. Leverage configuration
    3. Position management for futures
    4. Order execution for futures
    5. Margin monitoring
    6. Liquidation risk management
    7. Funding rate monitoring
    
    The manager works with the exchange's futures API and integrates
    with the existing OrderManager and PositionManager.
    """

    def __init__(
        self,
        exchange: ccxt.Exchange,
        order_manager: "OrderManager",
        position_manager: "PositionManager",
        db: "Database",
        data_collector: Optional["DataCollector"] = None,
        test: bool = True
    ):
        """Initialize FuturesManager.
        
        Args:
            exchange: CCXT exchange instance (futures)
            order_manager: OrderManager instance
            position_manager: PositionManager instance
            db: Database instance
            data_collector: Optional DataCollector instance
            test: Whether to use testnet
        """
        self.exchange = exchange
        self.order_manager = order_manager
        self.position_manager = position_manager
        self.db = db
        self.data_collector = data_collector
        self.test = test
        
        # Contract information
        self._contracts: Dict[str, FuturesContract] = {}
        
        # Futures positions (separate from spot positions)
        self._futures_positions: Dict[str, FuturesPosition] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        log.info(f"FuturesManager initialized (test={self.test})")

    # ========================================================================
    # CONTRACT MANAGEMENT
    # ========================================================================

    async def load_contracts(self, symbols: Optional[List[str]] = None) -> None:
        """Load futures contract information.
        
        Args:
            symbols: Optional list of symbols to load
        """
        try:
            # Fetch all contracts from exchange
            contracts = await self.exchange.fetch_contracts()
            
            for contract in contracts:
                symbol = contract.get("symbol", "")
                if symbols and symbol not in symbols:
                    continue
                
                # Create FuturesContract
                fc = FuturesContract(
                    symbol=symbol,
                    base_asset=contract.get("baseAsset", ""),
                    quote_asset=contract.get("quoteAsset", ""),
                    contract_type=FuturesType.PERPETUAL if contract.get("contractType", "").upper() == "PERPETUAL" else FuturesType.QUARTERLY,
                    leverage=float(contract.get("leverage", 1)),
                    margin_mode=MarginMode.ISOLATED if contract.get("marginMode", "").upper() == "ISOLATED" else MarginMode.CROSSED,
                    position_mode=PositionMode.ONE_WAY if contract.get("positionMode", "").upper() == "ONE_WAY" else PositionMode.HEDGE,
                    tick_size=float(contract.get("tickSize", 0.01)),
                    step_size=float(contract.get("stepSize", 0.001)),
                    min_notional=float(contract.get("minNotional", 1.0)),
                    max_notional=float(contract.get("maxNotional", 1000000.0)),
                    maintenance_margin_rate=float(contract.get("maintenanceMarginRate", 0.005)),
                    liquidation_fee_rate=float(contract.get("liquidationFeeRate", 0.005)),
                    price_decimals=int(contract.get("pricePrecision", 2)),
                    quantity_decimals=int(contract.get("quantityPrecision", 3))
                )
                
                self._contracts[symbol] = fc
            
            log.info(f"Loaded {len(self._contracts)} futures contracts")
            
        except Exception as e:
            log.error(f"Failed to load contracts: {e}")

    async def get_contract(self, symbol: str) -> Optional[FuturesContract]:
        """Get contract information for a symbol.
        
        Args:
            symbol: Contract symbol
            
        Returns:
            FuturesContract or None
        """
        if symbol not in self._contracts:
            await self.load_contracts([symbol])
        return self._contracts.get(symbol)

    async def get_all_contracts(self) -> List[FuturesContract]:
        """Get all loaded contracts.
        
        Returns:
            List of FuturesContract objects
        """
        return list(self._contracts.values())

    # ========================================================================
    # LEVERAGE MANAGEMENT
    # ========================================================================

    async def set_leverage(
        self,
        symbol: str,
        leverage: float
    ) -> bool:
        """Set leverage for a contract.
        
        Args:
            symbol: Contract symbol
            leverage: Leverage to set (e.g., 10 for 10x)
            
        Returns:
            True if leverage was set successfully
        """
        try:
            # Check if leverage is valid
            contract = await self.get_contract(symbol)
            if not contract:
                log.error(f"Contract not found: {symbol}")
                return False
            
            # Set leverage on exchange
            if not self.test:
                await self.exchange.set_leverage(leverage, symbol)
            
            # Update contract
            contract.leverage = leverage
            
            log.info(f"Set leverage for {symbol}: {leverage}x")
            return True
            
        except Exception as e:
            log.error(f"Failed to set leverage for {symbol}: {e}")
            return False

    async def get_leverage(self, symbol: str) -> float:
        """Get current leverage for a contract.
        
        Args:
            symbol: Contract symbol
            
        Returns:
            Current leverage
        """
        contract = await self.get_contract(symbol)
        if contract:
            return contract.leverage
        return 1.0

    # ========================================================================
    # POSITION MANAGEMENT
    # ========================================================================

    async def open_futures_position(
        self,
        symbol: str,
        side: "PositionSide",
        qty: float,
        leverage: Optional[float] = None,
        margin_mode: MarginMode = MarginMode.ISOLATED
    ) -> Optional[FuturesPosition]:
        """Open a futures position.
        
        Args:
            symbol: Contract symbol
            side: Position side (LONG or SHORT)
            qty: Quantity
            leverage: Optional leverage (uses contract default if None)
            margin_mode: Margin mode
            
        Returns:
            FuturesPosition or None
        """
        async with self._lock:
            try:
                # Get contract
                contract = await self.get_contract(symbol)
                if not contract:
                    log.error(f"Contract not found: {symbol}")
                    return None
                
                # Set leverage if specified
                if leverage:
                    await self.set_leverage(symbol, leverage)
                    contract.leverage = leverage
                
                # Get current price
                ticker = await self.exchange.fetch_ticker(symbol)
                current_price = float(ticker.get("last", ticker.get("close", 0)))
                
                # Calculate margin
                margin = self._calculate_margin(
                    current_price,
                    qty,
                    contract.leverage,
                    margin_mode
                )
                
                # Create position
                position = FuturesPosition(
                    symbol=symbol,
                    side=side,
                    entry_price=current_price,
                    current_qty=qty,
                    leverage=contract.leverage,
                    margin=margin,
                    margin_mode=margin_mode,
                    mark_price=current_price
                )
                
                # Calculate liquidation price
                position.liquidation_price = self._calculate_liquidation_price(
                    position,
                    contract.maintenance_margin_rate
                )
                
                # Store position
                self._futures_positions[position.position_id] = position
                
                # Save to database
                await self._save_position(position)
                
                log.info(f"Opened futures position: {position.symbol} {side.value} {qty} @ {current_price}")
                return position
                
            except Exception as e:
                log.error(f"Failed to open futures position: {e}")
                return None

    async def close_futures_position(
        self,
        position_id: str,
        exit_price: Optional[float] = None
    ) -> Optional[FuturesPosition]:
        """Close a futures position.
        
        Args:
            position_id: ID of position to close
            exit_price: Optional exit price (uses mark price if None)
            
        Returns:
            Closed FuturesPosition or None
        """
        async with self._lock:
            position = self._futures_positions.get(position_id)
            if not position:
                log.error(f"Position not found: {position_id}")
                return None
            
            try:
                # Get exit price
                if exit_price is None:
                    ticker = await self.exchange.fetch_ticker(position.symbol)
                    exit_price = float(ticker.get("last", position.mark_price))
                
                # Calculate P&L
                pnl = self._calculate_pnl(position, exit_price)
                position.unrealized_pnl = pnl
                
                # Close position
                position.current_qty = 0
                position.updated_at = datetime.now(timezone.utc)
                
                # Save to database
                await self._save_position(position)
                
                log.info(f"Closed futures position: {position.symbol} P&L: {pnl:.4f}")
                return position
                
            except Exception as e:
                log.error(f"Failed to close futures position: {e}")
                return None

    async def update_futures_positions(self) -> None:
        """Update all futures positions with current prices."""
        for position in self._futures_positions.values():
            try:
                ticker = await self.exchange.fetch_ticker(position.symbol)
                current_price = float(ticker.get("last", 0))
                
                position.mark_price = current_price
                position.unrealized_pnl = self._calculate_pnl(position, current_price)
                position.liquidation_price = self._calculate_liquidation_price(
                    position,
                    (await self.get_contract(position.symbol)).maintenance_margin_rate
                )
                
                position.updated_at = datetime.now(timezone.utc)
                
            except Exception as e:
                log.error(f"Failed to update position {position.position_id}: {e}")

    def _calculate_margin(
        self,
        price: float,
        qty: float,
        leverage: float,
        margin_mode: MarginMode
    ) -> float:
        """Calculate required margin for a position.
        
        Args:
            price: Current price
            qty: Quantity
            leverage: Leverage
            margin_mode: Margin mode
            
        Returns:
            Required margin
        """
        notional = price * qty
        return notional / leverage

    def _calculate_pnl(
        self,
        position: FuturesPosition,
        current_price: float
    ) -> float:
        """Calculate P&L for a position.
        
        Args:
            position: FuturesPosition
            current_price: Current price
            
        Returns:
            P&L amount
        """
        if position.side.value == "long":
            return (current_price - position.entry_price) * position.current_qty * position.leverage
        else:
            return (position.entry_price - current_price) * position.current_qty * position.leverage

    def _calculate_liquidation_price(
        self,
        position: FuturesPosition,
        maintenance_margin_rate: float
    ) -> float:
        """Calculate liquidation price for a position.
        
        Args:
            position: FuturesPosition
            maintenance_margin_rate: Maintenance margin rate
            
        Returns:
            Liquidation price
        """
        # Simplified calculation
        if position.side.value == "long":
            # Long position: liquidation when price drops too much
            return position.entry_price * (1 - maintenance_margin_rate * position.leverage)
        else:
            # Short position: liquidation when price rises too much
            return position.entry_price * (1 + maintenance_margin_rate * position.leverage)

    # ========================================================================
    # ORDER EXECUTION
    # ========================================================================

    async def create_futures_order(
        self,
        symbol: str,
        side: FuturesSide,
        order_type: FuturesOrderType,
        qty: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        reduce_only: bool = False,
        leverage: Optional[float] = None
    ) -> Optional[FuturesOrder]:
        """Create a futures order.
        
        Args:
            symbol: Contract symbol
            side: Order side
            order_type: Order type
            qty: Quantity
            price: Price for limit orders
            stop_price: Stop price for stop orders
            reduce_only: Whether this is a reduce-only order
            leverage: Optional leverage
            
        Returns:
            FuturesOrder or None
        """
        try:
            # Set leverage if specified
            if leverage:
                await self.set_leverage(symbol, leverage)
            
            # Create order on exchange
            exchange_order = await self._submit_futures_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                qty=qty,
                price=price,
                stop_price=stop_price,
                reduce_only=reduce_only
            )
            
            # Create FuturesOrder
            order = FuturesOrder(
                order_id=f"fut_{datetime.now(timezone.utc).timestamp()}",
                exchange_order_id=str(exchange_order.get("id", "")),
                symbol=symbol,
                side=side,
                order_type=order_type,
                price=price,
                qty=qty,
                filled=float(exchange_order.get("filled", 0)),
                avg_fill_price=float(exchange_order.get("average", 0)) if exchange_order.get("average") else None,
                status=exchange_order.get("status", "pending"),
                reduce_only=reduce_only
            )
            
            # Save to database
            await self._save_order(order)
            
            log.info(f"Created futures order: {order.order_id} {symbol} {side.value} {qty}")
            return order
            
        except Exception as e:
            log.error(f"Failed to create futures order: {e}")
            return None

    async def _submit_futures_order(
        self,
        symbol: str,
        side: FuturesSide,
        order_type: FuturesOrderType,
        qty: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        reduce_only: bool = False
    ) -> Dict[str, Any]:
        """Submit order to futures exchange.
        
        Args:
            symbol: Contract symbol
            side: Order side
            order_type: Order type
            qty: Quantity
            price: Price for limit orders
            stop_price: Stop price for stop orders
            reduce_only: Whether this is a reduce-only order
            
        Returns:
            Exchange order response
        """
        params = {
            "symbol": symbol,
            "side": side.value,
            "type": order_type.value,
            "amount": qty,
            "reduceOnly": reduce_only
        }
        
        if price:
            params["price"] = price
        if stop_price:
            params["stopPrice"] = stop_price
        
        # Submit to exchange
        if not self.test:
            return await self.exchange.create_order(**params)
        else:
            # Test mode: return mock response
            return {
                "id": f"test_{datetime.now(timezone.utc).timestamp()}",
                "symbol": symbol,
                "side": side.value,
                "type": order_type.value,
                "amount": qty,
                "price": price or 0,
                "stopPrice": stop_price or 0,
                "status": "open",
                "filled": 0,
                "average": 0
            }

    # ========================================================================
    # MARGIN MANAGEMENT
    # ========================================================================

    async def get_margin_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get margin information.
        
        Args:
            symbol: Optional contract symbol (all symbols if None)
            
        Returns:
            Dictionary with margin information
        """
        info = {}
        
        try:
            if symbol:
                # Get margin for specific symbol
                margin = await self.exchange.fetch_margin_mode(symbol)
                info[symbol] = margin
            else:
                # Get margin for all positions
                for position in self._futures_positions.values():
                    margin = await self.exchange.fetch_margin_mode(position.symbol)
                    info[position.symbol] = margin
            
        except Exception as e:
            log.error(f"Failed to get margin info: {e}")
        
        return info

    async def set_margin_mode(
        self,
        symbol: str,
        margin_mode: MarginMode
    ) -> bool:
        """Set margin mode for a contract.
        
        Args:
            symbol: Contract symbol
            margin_mode: Margin mode to set
            
        Returns:
            True if margin mode was set successfully
        """
        try:
            if not self.test:
                await self.exchange.set_margin_mode(
                    margin_mode.value,
                    symbol
                )
            
            # Update contract
            contract = await self.get_contract(symbol)
            if contract:
                contract.margin_mode = margin_mode
            
            log.info(f"Set margin mode for {symbol}: {margin_mode.value}")
            return True
            
        except Exception as e:
            log.error(f"Failed to set margin mode for {symbol}: {e}")
            return False

    # ========================================================================
    # LIQUIDATION MONITORING
    # ========================================================================

    async def check_liquidation_risk(self) -> List[LiquidationInfo]:
        """Check liquidation risk for all positions.
        
        Returns:
            List of LiquidationInfo for at-risk positions
        """
        at_risk = []
        
        for position in self._futures_positions.values():
            if position.current_qty == 0:
                continue
            
            # Get contract
            contract = await self.get_contract(position.symbol)
            if not contract:
                continue
            
            # Calculate liquidation info
            liquidation_info = self._calculate_liquidation_info(position, contract)
            
            # Check if at risk (within 5% of liquidation)
            if liquidation_info.distance_to_liquidation < 5.0:
                at_risk.append(liquidation_info)
        
        return at_risk

    def _calculate_liquidation_info(
        self,
        position: FuturesPosition,
        contract: FuturesContract
    ) -> LiquidationInfo:
        """Calculate liquidation risk information.
        
        Args:
            position: FuturesPosition
            contract: FuturesContract
            
        Returns:
            LiquidationInfo
        """
        # Calculate distance to liquidation
        if position.side.value == "long":
            distance = ((position.liquidation_price - position.mark_price) / position.mark_price) * 100
        else:
            distance = ((position.mark_price - position.liquidation_price) / position.mark_price) * 100
        
        # Determine risk level
        if distance < 1.0:
            risk_level = "critical"
        elif distance < 3.0:
            risk_level = "high"
        elif distance < 5.0:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Calculate margin ratio
        notional = position.mark_price * position.current_qty
        margin_used = notional / position.leverage
        margin_ratio = (position.margin / margin_used) * 100 if margin_used > 0 else 0
        
        return LiquidationInfo(
            symbol=position.symbol,
            position_side=position.side,
            current_price=position.mark_price,
            liquidation_price=position.liquidation_price,
            distance_to_liquidation=distance,
            risk_level=risk_level,
            margin_ratio=margin_ratio,
            maintenance_margin_ratio=contract.maintenance_margin_rate * 100
        )

    # ========================================================================
    # FUNDING RATE MONITORING
    # ========================================================================

    async def get_funding_info(self, symbol: Optional[str] = None) -> List[FundingInfo]:
        """Get funding rate information.
        
        Args:
            symbol: Optional contract symbol (all symbols if None)
            
        Returns:
            List of FundingInfo
        """
        funding_infos = []
        
        try:
            symbols = [symbol] if symbol else list(self._contracts.keys())
            
            for sym in symbols:
                # Get funding rate
                funding_rate = await self.exchange.fetch_funding_rate(sym)
                
                # Get next funding time
                next_funding = await self.exchange.fetch_funding_rate_history(sym, limit=1)
                next_funding_time = None
                if next_funding:
                    next_funding_time = datetime.fromtimestamp(next_funding[0].get("timestamp", 0) / 1000)
                
                # Calculate estimated funding
                contract = await self.get_contract(sym)
                estimated_funding = 0.0
                if contract:
                    position = self._futures_positions.get(sym)
                    if position:
                        notional = position.mark_price * position.current_qty
                        estimated_funding = notional * funding_rate
                
                funding_infos.append(FundingInfo(
                    symbol=sym,
                    funding_rate=funding_rate,
                    next_funding_time=next_funding_time,
                    estimated_funding=estimated_funding
                ))
                
        except Exception as e:
            log.error(f"Failed to get funding info: {e}")
        
        return funding_infos

    # ========================================================================
    # DATABASE INTEGRATION
    # ========================================================================

    async def _save_position(self, position: FuturesPosition) -> None:
        """Save position to database.
        
        Args:
            position: FuturesPosition to save
        """
        try:
            await self.db.create_futures_position(
                position_id=position.position_id,
                symbol=position.symbol,
                side=position.side.value,
                entry_price=position.entry_price,
                current_qty=position.current_qty,
                leverage=position.leverage,
                margin=position.margin,
                isolated_margin=position.isolated_margin,
                mark_price=position.mark_price,
                liquidation_price=position.liquidation_price,
                unrealized_pnl=position.unrealized_pnl,
                unrealized_pnl_pct=position.unrealized_pnl_pct,
                margin_mode=position.margin_mode.value,
                auto_deleveraging=position.auto_deleveraging,
                created_at=position.created_at,
                updated_at=position.updated_at
            )
        except Exception as e:
            log.error(f"Failed to save futures position: {e}")

    async def _save_order(self, order: FuturesOrder) -> None:
        """Save order to database.
        
        Args:
            order: FuturesOrder to save
        """
        try:
            await self.db.create_futures_order(
                order_id=order.order_id,
                exchange_order_id=order.exchange_order_id,
                symbol=order.symbol,
                side=order.side.value,
                order_type=order.order_type.value,
                price=order.price,
                qty=order.qty,
                filled=order.filled,
                avg_fill_price=order.avg_fill_price,
                status=order.status,
                reduce_only=order.reduce_only,
                close_position=order.close_position,
                position_id=order.position_id,
                leverage=order.leverage,
                margin=order.margin,
                created_at=order.created_at,
                updated_at=order.updated_at
            )
        except Exception as e:
            log.error(f"Failed to save futures order: {e}")

    async def load_positions(self) -> None:
        """Load futures positions from database."""
        try:
            positions = await self.db.get_all_futures_positions()
            
            for pos in positions:
                position = FuturesPosition(
                    position_id=pos["position_id"],
                    symbol=pos["symbol"],
                    side=pos["side"],
                    entry_price=pos["entry_price"],
                    current_qty=pos["current_qty"],
                    leverage=pos["leverage"],
                    margin=pos["margin"],
                    isolated_margin=pos["isolated_margin"],
                    mark_price=pos["mark_price"],
                    liquidation_price=pos["liquidation_price"],
                    unrealized_pnl=pos["unrealized_pnl"],
                    unrealized_pnl_pct=pos["unrealized_pnl_pct"],
                    margin_mode=pos["margin_mode"],
                    auto_deleveraging=pos["auto_deleveraging"],
                    created_at=datetime.fromisoformat(pos["created_at"]),
                    updated_at=datetime.fromisoformat(pos["updated_at"])
                )
                
                self._futures_positions[position.position_id] = position
            
            log.info(f"Loaded {len(self._futures_positions)} futures positions")
            
        except Exception as e:
            log.error(f"Failed to load futures positions: {e}")

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def get_all_positions(self) -> List[FuturesPosition]:
        """Get all futures positions.
        
        Returns:
            List of FuturesPosition objects
        """
        return list(self._futures_positions.values())

    async def get_position(self, position_id: str) -> Optional[FuturesPosition]:
        """Get a specific futures position.
        
        Args:
            position_id: Position ID
            
        Returns:
            FuturesPosition or None
        """
        return self._futures_positions.get(position_id)

    async def get_position_for_symbol(self, symbol: str) -> Optional[FuturesPosition]:
        """Get position for a specific symbol.
        
        Args:
            symbol: Contract symbol
            
        Returns:
            FuturesPosition or None
        """
        for position in self._futures_positions.values():
            if position.symbol == symbol and position.current_qty > 0:
                return position
        return None

    async def get_statistics(self) -> Dict[str, Any]:
        """Get futures trading statistics.
        
        Returns:
            Dictionary with statistics
        """
        open_positions = sum(1 for p in self._futures_positions.values() if p.current_qty > 0)
        total_pnl = sum(p.unrealized_pnl for p in self._futures_positions.values())
        
        return {
            "total_contracts": len(self._contracts),
            "open_positions": open_positions,
            "total_pnl": total_pnl,
            "total_margin": sum(p.margin for p in self._futures_positions.values())
        }

    async def close_all_positions(self) -> List[FuturesPosition]:
        """Close all open futures positions.
        
        Returns:
            List of closed positions
        """
        closed = []
        
        for position in list(self._futures_positions.values()):
            if position.current_qty > 0:
                result = await self.close_futures_position(position.position_id)
                if result:
                    closed.append(result)
        
        return closed

    async def clear(self) -> None:
        """Clear all futures data."""
        self._contracts.clear()
        self._futures_positions.clear()
        log.info("Cleared all futures data")
