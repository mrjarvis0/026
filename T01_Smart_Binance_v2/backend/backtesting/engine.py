"""Backtesting engine for T01 Smart Binance Intelligence v2.

This module provides the core backtesting functionality, allowing
strategies to be tested on historical data before live trading.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import pandas as pd
import numpy as np

from backend import config
from backend.backtesting.data_loader import data_loader
from backend.backtesting.metrics import BacktestMetrics, Trade, PerformanceMetrics
from backend.analysis.indicators import compute_all
from backend.analysis.signals import generate_signal, Signal

log = logging.getLogger("backtesting.engine")


class OrderType(Enum):
    """Order types for backtesting."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderSide(Enum):
    """Order sides for backtesting."""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """Represents an order in backtesting."""
    id: int
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: float
    price: float
    time: pd.Timestamp
    status: str = "pending"  # pending, filled, canceled
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    
    @property
    def is_filled(self) -> bool:
        return self.status == "filled"
    
    @property
    def is_pending(self) -> bool:
        return self.status == "pending"
    
    @property
    def remaining_qty(self) -> float:
        return self.qty - self.filled_qty


@dataclass
class Position:
    """Represents an open position in backtesting."""
    id: int
    symbol: str
    entry_time: pd.Timestamp
    entry_price: float
    qty: float
    side: str  # 'long' or 'short'
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop: Optional[float] = None
    entry_signal: Optional[Signal] = None
    
    @property
    def is_long(self) -> bool:
        return self.side == 'long'
    
    @property
    def is_short(self) -> bool:
        return self.side == 'short'


@dataclass
class BacktestResult:
    """Result of a backtest."""
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'trades': [self._trade_to_dict(t) for t in self.trades],
            'equity_curve': self.equity_curve,
            'metrics': self.metrics.to_dict(),
            'errors': self.errors,
            'warnings': self.warnings
        }
    
    def _trade_to_dict(self, trade: Trade) -> Dict[str, Any]:
        """Convert trade to dictionary."""
        return {
            'symbol': trade.symbol,
            'entry_time': trade.entry_time.isoformat() if trade.entry_time else None,
            'exit_time': trade.exit_time.isoformat() if trade.exit_time else None,
            'entry_price': trade.entry_price,
            'exit_price': trade.exit_price,
            'qty': trade.qty,
            'side': trade.side,
            'pnl': trade.pnl,
            'pnl_pct': trade.pnl_pct,
            'fee': trade.fee,
            'stop_loss': trade.stop_loss,
            'take_profit': trade.take_profit,
            'exit_reason': trade.exit_reason
        }


class BacktestingEngine:
    """Main backtesting engine.
    
    This engine simulates trading on historical data, allowing
    strategies to be validated before live trading.
    
    Features:
    - Realistic trade execution with fees and slippage
    - Position management
    - Stop-loss and take-profit handling
    - Multiple timeframe support
    - Comprehensive metrics calculation
    """
    
    def __init__(
        self,
        initial_balance: float = 10000.0,
        fee_pct: float = 0.001,
        slippage_pct: float = 0.0005
    ):
        """Initialize the backtesting engine.
        
        Args:
            initial_balance: Starting balance (default: 10000 USDT)
            fee_pct: Trading fee percentage (default: 0.1%)
            slippage_pct: Slippage percentage (default: 0.05%)
        """
        self.initial_balance = initial_balance
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct
        
        self.balance = initial_balance
        self.positions: Dict[int, Position] = {}
        self.closed_positions: List[Position] = []
        self.trades: List[Trade] = []
        self.orders: Dict[int, Order] = {}
        self.equity_curve: List[Dict[str, Any]] = []
        
        self._order_id = 0
        self._position_id = 0
        self._trade_id = 0
        
        self.metrics_calculator = BacktestMetrics(fee_pct, slippage_pct)
        
        log.info(f"Initialized backtesting engine with balance: {initial_balance}")
    
    async def run(
        self,
        symbol: str,
        timeframe: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None,
        signal_generator: Optional[Callable] = None
    ) -> BacktestResult:
        """Run a backtest.
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe
            start_date: Start date (optional)
            end_date: End date (optional)
            limit: Maximum candles to process (optional)
            signal_generator: Custom signal generator (optional)
            
        Returns:
            BacktestResult with trades, equity curve, and metrics
        """
        # Reset engine state
        self._reset()
        
        result = BacktestResult()
        
        try:
            # Load historical data
            log.info(f"Loading data for {symbol} {timeframe}...")
            df = await data_loader.load_ohlcv(symbol, timeframe, start_date, end_date, limit)
            
            if df.empty:
                result.errors.append(f"No data loaded for {symbol} {timeframe}")
                return result
            
            log.info(f"Loaded {len(df)} candles")
            
            # Add initial equity point
            self._add_equity_point(df.iloc[0]['ts'])
            
            # Process each candle
            for i, candle in df.iterrows():
                candle_df = df.iloc[:i+1]  # All data up to current candle
                
                # Check and close positions
                self._check_exits(candle_df, candle['ts'])
                
                # Generate signal
                if signal_generator:
                    signal = signal_generator(candle_df)
                else:
                    signal = generate_signal(candle_df)
                
                # Execute trades based on signal
                self._execute_signal(signal, candle, symbol, timeframe)
                
                # Add equity point
                self._add_equity_point(candle['ts'])
            
            # Close all open positions at end
            self._close_all_positions(df.iloc[-1]['ts'], "backtest_end")
            
            # Calculate metrics
            result.trades = self.trades
            result.equity_curve = self.equity_curve
            result.metrics = self.metrics_calculator.calculate_all(
                self.trades, 
                self.equity_curve, 
                self.initial_balance
            )
            result.errors = self._get_errors()
            result.warnings = self._get_warnings()
            
            log.info(f"Backtest completed: {result.metrics.total_trades} trades, "
                    f"PnL: {result.metrics.total_pnl:.2f}, "
                    f"Win Rate: {result.metrics.win_rate:.1%}")
            
        except Exception as e:
            result.errors.append(f"Backtest failed: {str(e)}")
            log.error(f"Backtest error: {e}", exc_info=True)
        
        return result
    
    def _reset(self) -> None:
        """Reset engine state."""
        self.balance = self.initial_balance
        self.positions = {}
        self.closed_positions = []
        self.trades = []
        self.orders = {}
        self.equity_curve = []
        self._order_id = 0
        self._position_id = 0
        self._trade_id = 0
    
    def _check_exits(self, df: pd.DataFrame, current_time: pd.Timestamp) -> None:
        """Check and close positions that hit stop-loss or take-profit.
        
        Args:
            df: Current DataFrame with all data
            current_time: Current timestamp
        """
        current_price = df.iloc[-1]['close']
        
        positions_to_close = []
        
        for pos_id, position in self.positions.items():
            # Check stop-loss
            if position.stop_loss and self._should_close(position, current_price, position.stop_loss, 'stop_loss'):
                positions_to_close.append((pos_id, 'stop_loss'))
                continue
            
            # Check take-profit
            if position.take_profit and self._should_close(position, current_price, position.take_profit, 'take_profit'):
                positions_to_close.append((pos_id, 'take_profit'))
                continue
            
            # Check trailing stop
            if position.trailing_stop:
                if self._check_trailing_stop(position, current_price):
                    positions_to_close.append((pos_id, 'trailing_stop'))
        
        # Close positions
        for pos_id, reason in positions_to_close:
            self._close_position(pos_id, current_time, current_price, reason)
    
    def _should_close(self, position: Position, current_price: float, level: float, reason: str) -> bool:
        """Check if position should be closed.
        
        Args:
            position: Position to check
            current_price: Current market price
            level: Price level to check (stop-loss or take-profit)
            reason: Reason for closing
            
        Returns:
            True if position should be closed
        """
        if position.is_long:
            # Long position: close if price <= stop-loss or >= take-profit
            if reason == 'stop_loss' and current_price <= level:
                return True
            if reason == 'take_profit' and current_price >= level:
                return True
        else:
            # Short position: close if price >= stop-loss or <= take-profit
            if reason == 'stop_loss' and current_price >= level:
                return True
            if reason == 'take_profit' and current_price <= level:
                return True
        
        return False
    
    def _check_trailing_stop(self, position: Position, current_price: float) -> bool:
        """Check trailing stop for position.
        
        Args:
            position: Position to check
            current_price: Current market price
            
        Returns:
            True if trailing stop is hit
        """
        if not position.trailing_stop:
            return False
        
        if position.is_long:
            # For long: trailing stop moves up, close if price <= trailing stop
            if current_price <= position.trailing_stop:
                return True
            # Update trailing stop if price makes new high
            if current_price > position.entry_price:
                position.trailing_stop = current_price * (1 - config.TRAIL_PCT)
        else:
            # For short: trailing stop moves down, close if price >= trailing stop
            if current_price >= position.trailing_stop:
                return True
            # Update trailing stop if price makes new low
            if current_price < position.entry_price:
                position.trailing_stop = current_price * (1 + config.TRAIL_PCT)
        
        return False
    
    def _execute_signal(self, signal: Signal, candle: pd.Series, symbol: str, timeframe: str) -> None:
        """Execute trades based on signal.
        
        Args:
            signal: Trading signal
            candle: Current candle data
            symbol: Trading pair
            timeframe: Timeframe
        """
        current_time = candle['ts']
        current_price = candle['close']
        
        # Only act on buy/sell signals (not hold)
        if signal.action == 'buy':
            self._execute_buy(signal, current_time, current_price, symbol)
        elif signal.action == 'sell':
            self._execute_sell(signal, current_time, current_price, symbol)
    
    def _execute_buy(self, signal: Signal, current_time: pd.Timestamp, current_price: float, symbol: str) -> None:
        """Execute buy trade.
        
        Args:
            signal: Buy signal
            current_time: Current timestamp
            current_price: Current price
            symbol: Trading pair
        """
        # Check if we already have a position on this symbol
        for pos_id, position in self.positions.items():
            if position.symbol == symbol:
                # Already have a position, don't open another
                return
        
        # Calculate position size
        qty = self._calculate_position_size(current_price, signal.confidence)
        
        if qty <= 0:
            return
        
        # Apply slippage
        fill_price = current_price * (1 + self.slippage_pct)
        
        # Calculate fees
        fee = fill_price * qty * self.fee_pct
        
        # Calculate stop-loss and take-profit
        stop_loss, take_profit = self._calculate_sl_tp(current_price, 'long')
        
        # Create position
        self._position_id += 1
        position = Position(
            id=self._position_id,
            symbol=symbol,
            entry_time=current_time,
            entry_price=fill_price,
            qty=qty,
            side='long',
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=fill_price * (1 - config.TRAIL_PCT) if config.TRAIL_ENABLED else None,
            entry_signal=signal
        )
        
        self.positions[position.id] = position
        
        log.debug(f"Opened long position: {symbol} @ {fill_price} ({qty})")
    
    def _execute_sell(self, signal: Signal, current_time: pd.Timestamp, current_price: float, symbol: str) -> None:
        """Execute sell trade.
        
        Args:
            signal: Sell signal
            current_time: Current timestamp
            current_price: Current price
            symbol: Trading pair
        """
        # Check if we have a long position on this symbol
        for pos_id, position in self.positions.items():
            if position.symbol == symbol and position.is_long:
                self._close_position(pos_id, current_time, current_price, 'signal')
                return
        
        # If no long position, this is a short sell
        # Calculate position size
        qty = self._calculate_position_size(current_price, signal.confidence)
        
        if qty <= 0:
            return
        
        # Apply slippage
        fill_price = current_price * (1 - self.slippage_pct)
        
        # Calculate fees
        fee = fill_price * qty * self.fee_pct
        
        # Calculate stop-loss and take-profit
        stop_loss, take_profit = self._calculate_sl_tp(current_price, 'short')
        
        # Create position
        self._position_id += 1
        position = Position(
            id=self._position_id,
            symbol=symbol,
            entry_time=current_time,
            entry_price=fill_price,
            qty=qty,
            side='short',
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=fill_price * (1 + config.TRAIL_PCT) if config.TRAIL_ENABLED else None,
            entry_signal=signal
        )
        
        self.positions[position.id] = position
        
        log.debug(f"Opened short position: {symbol} @ {fill_price} ({qty})")
    
    def _calculate_position_size(self, price: float, confidence: float) -> float:
        """Calculate position size based on risk settings.
        
        Args:
            price: Current price
            confidence: Signal confidence (0-1)
            
        Returns:
            Position size in quantity
        """
        # Use risk per trade setting
        risk_per_trade = config.RISK_PER_TRADE_PAPER
        
        # Calculate capital at risk
        capital_at_risk = self.balance * risk_per_trade
        
        # For now, use fixed percentage stop-loss
        stop_loss_pct = config.STOP_LOSS_PCT
        stop_distance = price * stop_loss_pct
        
        if stop_distance == 0:
            return 0
        
        # Calculate quantity
        qty = capital_at_risk / stop_distance
        
        # Limit by available balance
        max_qty = self.balance / price
        qty = min(qty, max_qty)
        
        # Limit by max concurrent positions
        if len(self.positions) >= config.MAX_CONCURRENT_POSITIONS:
            return 0
        
        return qty
    
    def _calculate_sl_tp(self, entry_price: float, side: str) -> Tuple[Optional[float], Optional[float]]:
        """Calculate stop-loss and take-profit levels.
        
        Args:
            entry_price: Entry price
            side: Position side ('long' or 'short')
            
        Returns:
            Tuple of (stop_loss, take_profit)
        """
        if config.USE_ATR_STOPS:
            # ATR-based stops (not implemented in backtest yet)
            # For now, use fixed percentages
            stop_loss_pct = config.STOP_LOSS_PCT
            take_profit_pct = config.TAKE_PROFIT_PCT
        else:
            stop_loss_pct = config.STOP_LOSS_PCT
            take_profit_pct = config.TAKE_PROFIT_PCT
        
        if side == 'long':
            stop_loss = entry_price * (1 - stop_loss_pct)
            take_profit = entry_price * (1 + take_profit_pct)
        else:  # short
            stop_loss = entry_price * (1 + stop_loss_pct)
            take_profit = entry_price * (1 - take_profit_pct)
        
        return stop_loss, take_profit
    
    def _close_position(self, pos_id: int, exit_time: pd.Timestamp, exit_price: float, reason: str) -> None:
        """Close a position.
        
        Args:
            pos_id: Position ID
            exit_time: Exit timestamp
            exit_price: Exit price
            reason: Reason for closing
        """
        if pos_id not in self.positions:
            return
        
        position = self.positions[pos_id]
        
        # Apply slippage
        if position.is_long:
            fill_price = exit_price * (1 - self.slippage_pct)
        else:
            fill_price = exit_price * (1 + self.slippage_pct)
        
        # Calculate PnL
        if position.is_long:
            pnl = (fill_price - position.entry_price) * position.qty
        else:
            pnl = (position.entry_price - fill_price) * position.qty
        
        # Calculate PnL percentage
        pnl_pct = (pnl / (position.entry_price * position.qty)) * 100 if (position.entry_price * position.qty) > 0 else 0
        
        # Calculate fee
        fee = fill_price * position.qty * self.fee_pct
        
        # Create trade record
        self._trade_id += 1
        trade = Trade(
            symbol=position.symbol,
            entry_time=position.entry_time,
            exit_time=exit_time,
            entry_price=position.entry_price,
            exit_price=fill_price,
            qty=position.qty,
            side=position.side,
            pnl=pnl - fee,
            pnl_pct=pnl_pct,
            fee=fee,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            exit_reason=reason
        )
        
        self.trades.append(trade)
        self.closed_positions.append(position)
        del self.positions[pos_id]
        
        # Update balance
        self.balance += trade.pnl
        
        log.debug(f"Closed {position.side} position: {position.symbol} @ {fill_price}, "
                 f"PnL: {trade.pnl:.2f} ({trade.pnl_pct:.2f}%)")
    
    def _close_all_positions(self, exit_time: pd.Timestamp, reason: str) -> None:
        """Close all open positions.
        
        Args:
            exit_time: Exit timestamp
            reason: Reason for closing
        """
        # Use the last candle's close price
        # In practice, we'd need to fetch current price
        # For backtesting, we use the last available price
        if not self.positions:
            return
        
        # Get current price from last candle
        # This is a simplification - in real backtesting, we'd need to track this
        current_price = None
        for trade in reversed(self.trades):
            current_price = trade.exit_price
            break
        
        if current_price is None:
            current_price = self.initial_balance  # Fallback
        
        # Close all positions
        for pos_id in list(self.positions.keys()):
            self._close_position(pos_id, exit_time, current_price, reason)
    
    def _add_equity_point(self, timestamp: pd.Timestamp) -> None:
        """Add equity curve point.
        
        Args:
            timestamp: Current timestamp
        """
        # Calculate current equity
        equity = self.balance
        
        # Add open position values
        for position in self.positions.values():
            # For simplicity, use entry price (in real implementation, use mark price)
            if position.is_long:
                equity += (position.entry_price - position.entry_price) * position.qty
            else:
                equity += (position.entry_price - position.entry_price) * position.qty
        
        self.equity_curve.append({
            'timestamp': timestamp,
            'balance': self.balance,
            'equity': equity,
            'open_positions': len(self.positions)
        })
    
    def _get_errors(self) -> List[str]:
        """Get list of errors."""
        # For now, return empty list
        # In future, track errors during backtest
        return []
    
    def _get_warnings(self) -> List[str]:
        """Get list of warnings."""
        warnings = []
        
        # Check for no trades
        if len(self.trades) == 0:
            warnings.append("No trades executed during backtest")
        
        # Check for low win rate
        if len(self.trades) > 0:
            winning_trades = sum(1 for t in self.trades if t.pnl > 0)
            win_rate = winning_trades / len(self.trades)
            if win_rate < 0.4:
                warnings.append(f"Low win rate: {win_rate:.1%}")
        
        return warnings


# Singleton instance for convenience
backtest_engine = BacktestingEngine()
