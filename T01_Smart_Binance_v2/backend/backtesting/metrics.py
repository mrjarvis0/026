"""Performance metrics for backtesting.

This module calculates comprehensive performance metrics for
trading strategies during backtesting.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

log = logging.getLogger("backtesting.metrics")


@dataclass
class Trade:
    """Represents a single trade."""
    symbol: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    qty: float
    side: str  # 'long' or 'short'
    pnl: float
    pnl_pct: float
    fee: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_reason: str = "unknown"  # 'stop_loss', 'take_profit', 'signal', 'manual'
    
    @property
    def is_profitable(self) -> bool:
        return self.pnl > 0
    
    @property
    def is_loss(self) -> bool:
        return self.pnl < 0


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for a backtest."""
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # PnL statistics
    total_pnl: float = 0.0
    avg_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    
    # Ratios
    profit_factor: float = 0.0
    expectancy: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Drawdown
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    current_drawdown: float = 0.0
    
    # ROI
    roi: float = 0.0
    roi_pct: float = 0.0
    
    # Additional metrics
    total_fees: float = 0.0
    longest_winning_streak: int = 0
    longest_losing_streak: int = 0
    
    # Time-based metrics
    total_days: float = 0.0
    avg_trades_per_day: float = 0.0
    
    # Metadata
    initial_balance: float = 0.0
    final_balance: float = 0.0
    peak_balance: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': round(self.win_rate, 4),
            'total_pnl': round(self.total_pnl, 4),
            'avg_pnl': round(self.avg_pnl, 4),
            'avg_win': round(self.avg_win, 4),
            'avg_loss': round(self.avg_loss, 4),
            'best_trade': round(self.best_trade, 4),
            'worst_trade': round(self.worst_trade, 4),
            'profit_factor': round(self.profit_factor, 4),
            'expectancy': round(self.expectancy, 4),
            'sharpe_ratio': round(self.sharpe_ratio, 4),
            'sortino_ratio': round(self.sortino_ratio, 4),
            'calmar_ratio': round(self.calmar_ratio, 4),
            'max_drawdown': round(self.max_drawdown, 4),
            'max_drawdown_pct': round(self.max_drawdown_pct, 4),
            'roi': round(self.roi, 4),
            'roi_pct': round(self.roi_pct, 4),
            'total_fees': round(self.total_fees, 4),
            'longest_winning_streak': self.longest_winning_streak,
            'longest_losing_streak': self.longest_losing_streak,
            'total_days': round(self.total_days, 2),
            'avg_trades_per_day': round(self.avg_trades_per_day, 2),
            'initial_balance': self.initial_balance,
            'final_balance': self.final_balance,
            'peak_balance': self.peak_balance,
        }


class BacktestMetrics:
    """Calculates performance metrics for backtesting."""
    
    def __init__(self, fee_pct: float = 0.001, slippage_pct: float = 0.0):
        """Initialize metrics calculator.
        
        Args:
            fee_pct: Trading fee percentage (default: 0.1%)
            slippage_pct: Slippage percentage (default: 0%)
        """
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct
    
    def calculate_all(
        self,
        trades: List[Trade],
        equity_curve: List[Dict[str, Any]],
        initial_balance: float
    ) -> PerformanceMetrics:
        """Calculate all performance metrics.
        
        Args:
            trades: List of Trade objects
            equity_curve: List of equity curve points
            initial_balance: Starting balance
            
        Returns:
            PerformanceMetrics object with all metrics
        """
        metrics = PerformanceMetrics()
        metrics.initial_balance = initial_balance
        
        # Calculate trade statistics
        self._calculate_trade_stats(trades, metrics)
        
        # Calculate PnL statistics
        self._calculate_pnl_stats(trades, metrics)
        
        # Calculate ratios
        self._calculate_ratios(trades, metrics)
        
        # Calculate drawdown
        self._calculate_drawdown(equity_curve, metrics)
        
        # Calculate ROI
        self._calculate_roi(equity_curve, metrics, initial_balance)
        
        # Calculate time-based metrics
        self._calculate_time_metrics(trades, equity_curve, metrics)
        
        # Calculate streak metrics
        self._calculate_streaks(trades, metrics)
        
        return metrics
    
    def _calculate_trade_stats(self, trades: List[Trade], metrics: PerformanceMetrics) -> None:
        """Calculate basic trade statistics."""
        metrics.total_trades = len(trades)
        
        if metrics.total_trades == 0:
            return
        
        winning_trades = [t for t in trades if t.is_profitable]
        losing_trades = [t for t in trades if t.is_loss]
        
        metrics.winning_trades = len(winning_trades)
        metrics.losing_trades = len(losing_trades)
        metrics.win_rate = metrics.winning_trades / metrics.total_trades if metrics.total_trades > 0 else 0.0
        
        metrics.total_fees = sum(t.fee for t in trades)
    
    def _calculate_pnl_stats(self, trades: List[Trade], metrics: PerformanceMetrics) -> None:
        """Calculate PnL statistics."""
        if not trades:
            return
        
        pnls = [t.pnl for t in trades]
        winning_pnls = [t.pnl for t in trades if t.is_profitable]
        losing_pnls = [t.pnl for t in trades if t.is_loss]
        
        metrics.total_pnl = sum(pnls)
        metrics.avg_pnl = np.mean(pnls) if pnls else 0.0
        
        metrics.best_trade = max(pnls) if pnls else 0.0
        metrics.worst_trade = min(pnls) if pnls else 0.0
        
        metrics.avg_win = np.mean(winning_pnls) if winning_pnls else 0.0
        metrics.avg_loss = np.mean(losing_pnls) if losing_pnls else 0.0
    
    def _calculate_ratios(self, trades: List[Trade], metrics: PerformanceMetrics) -> None:
        """Calculate performance ratios."""
        if not trades:
            return
        
        winning_pnls = [t.pnl for t in trades if t.is_profitable]
        losing_pnls = [abs(t.pnl) for t in trades if t.is_loss]
        
        # Profit Factor = Gross Profit / Gross Loss
        gross_profit = sum(winning_pnls)
        gross_loss = sum(losing_pnls)
        
        if gross_loss > 0:
            metrics.profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            metrics.profit_factor = float('inf')
        else:
            metrics.profit_factor = 0.0
        
        # Expectancy = (Win Rate * Avg Win) - ((1 - Win Rate) * Avg Loss)
        if metrics.winning_trades > 0 and metrics.losing_trades > 0:
            metrics.expectancy = (metrics.win_rate * metrics.avg_win) - ((1 - metrics.win_rate) * abs(metrics.avg_loss))
        elif metrics.winning_trades > 0:
            metrics.expectancy = metrics.avg_win
        elif metrics.losing_trades > 0:
            metrics.expectancy = -abs(metrics.avg_loss)
        else:
            metrics.expectancy = 0.0
    
    def _calculate_drawdown(self, equity_curve: List[Dict[str, Any]], metrics: PerformanceMetrics) -> None:
        """Calculate drawdown metrics."""
        if not equity_curve:
            return
        
        # Extract equity values
        equities = [point['equity'] for point in equity_curve]
        
        if not equities:
            return
        
        # Calculate running max
        running_max = []
        current_max = equities[0]
        for equity in equities:
            current_max = max(current_max, equity)
            running_max.append(current_max)
        
        # Calculate drawdown at each point
        drawdowns = []
        for i, equity in enumerate(equities):
            dd = (running_max[i] - equity) / running_max[i] if running_max[i] > 0 else 0
            drawdowns.append(dd)
        
        # Max drawdown
        max_dd_idx = np.argmax(drawdowns)
        metrics.max_drawdown = equities[max_dd_idx] - running_max[max_dd_idx]
        metrics.max_drawdown_pct = drawdowns[max_dd_idx] * 100
        
        # Current drawdown
        if equity_curve:
            current_dd = (running_max[-1] - equities[-1]) / running_max[-1] if running_max[-1] > 0 else 0
            metrics.current_drawdown = equities[-1] - running_max[-1]
    
    def _calculate_roi(self, equity_curve: List[Dict[str, Any]], metrics: PerformanceMetrics, initial_balance: float) -> None:
        """Calculate ROI metrics."""
        if not equity_curve:
            return
        
        # Final balance
        final_balance = equity_curve[-1]['equity']
        metrics.final_balance = final_balance
        
        # Peak balance
        peak_balance = max(point['equity'] for point in equity_curve)
        metrics.peak_balance = peak_balance
        
        # ROI
        if initial_balance > 0:
            metrics.roi = final_balance - initial_balance
            metrics.roi_pct = ((final_balance - initial_balance) / initial_balance) * 100
    
    def _calculate_time_metrics(self, trades: List[Trade], equity_curve: List[Dict[str, Any]], metrics: PerformanceMetrics) -> None:
        """Calculate time-based metrics."""
        if not equity_curve:
            return
        
        # Calculate total days
        if len(equity_curve) >= 2:
            start_time = equity_curve[0]['timestamp']
            end_time = equity_curve[-1]['timestamp']
            
            if isinstance(start_time, str):
                start_time = pd.to_datetime(start_time)
            if isinstance(end_time, str):
                end_time = pd.to_datetime(end_time)
            
            delta = end_time - start_time
            metrics.total_days = delta.total_seconds() / (24 * 3600)
        
        # Average trades per day
        if metrics.total_days > 0:
            metrics.avg_trades_per_day = metrics.total_trades / metrics.total_days
    
    def _calculate_streaks(self, trades: List[Trade], metrics: PerformanceMetrics) -> None:
        """Calculate winning/losing streak metrics."""
        if not trades:
            return
        
        current_winning_streak = 0
        current_losing_streak = 0
        max_winning_streak = 0
        max_losing_streak = 0
        
        for trade in trades:
            if trade.is_profitable:
                current_winning_streak += 1
                current_losing_streak = 0
                max_winning_streak = max(max_winning_streak, current_winning_streak)
            elif trade.is_loss:
                current_losing_streak += 1
                current_winning_streak = 0
                max_losing_streak = max(max_losing_streak, current_losing_streak)
            else:
                current_winning_streak = 0
                current_losing_streak = 0
        
        metrics.longest_winning_streak = max_winning_streak
        metrics.longest_losing_streak = max_losing_streak
    
    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.0,
        annualize: bool = False
    ) -> float:
        """Calculate Sharpe ratio.
        
        Args:
            returns: List of period returns
            risk_free_rate: Risk-free rate (default: 0)
            annualize: Whether to annualize the ratio
            
        Returns:
            Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        # Calculate mean return
        mean_return = np.mean(returns)
        
        # Calculate standard deviation
        std_return = np.std(returns, ddof=1)
        
        if std_return == 0:
            return 0.0
        
        # Sharpe ratio = (Mean Return - Risk Free Rate) / Std Dev
        sharpe = (mean_return - risk_free_rate) / std_return
        
        # Annualize if requested
        if annualize:
            n = len(returns)
            sharpe *= np.sqrt(n)
        
        return sharpe
    
    def calculate_sortino_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.0,
        target_return: float = 0.0
    ) -> float:
        """Calculate Sortino ratio (only downside deviation).
        
        Args:
            returns: List of period returns
            risk_free_rate: Risk-free rate (default: 0)
            target_return: Target return (default: 0)
            
        Returns:
            Sortino ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        # Calculate mean return
        mean_return = np.mean(returns)
        
        # Calculate downside deviation
        downside_returns = [r for r in returns if r < target_return]
        
        if not downside_returns:
            return 0.0
        
        downside_std = np.std(downside_returns, ddof=1)
        
        if downside_std == 0:
            return 0.0
        
        # Sortino ratio = (Mean Return - Target) / Downside Std Dev
        sortino = (mean_return - target_return) / downside_std
        
        return sortino
    
    def calculate_calmar_ratio(
        self,
        total_return: float,
        max_drawdown: float
    ) -> float:
        """Calculate Calmar ratio.
        
        Args:
            total_return: Total return over period
            max_drawdown: Maximum drawdown over period
            
        Returns:
            Calmar ratio
        """
        if max_drawdown == 0:
            return 0.0
        
        return total_return / abs(max_drawdown)
    
    def calculate_equity_curve(
        self,
        initial_balance: float,
        trades: List[Trade],
        equity_points: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate equity curve from trades.
        
        Args:
            initial_balance: Starting balance
            trades: List of Trade objects
            equity_points: Existing equity points (optional)
            
        Returns:
            List of equity curve points
        """
        equity_curve = []
        balance = initial_balance
        
        # Add initial point
        equity_curve.append({
            'timestamp': trades[0].entry_time if trades else pd.Timestamp.now(tz='UTC'),
            'balance': balance,
            'equity': balance,
            'pnl': 0.0
        })
        
        # Process each trade
        for trade in trades:
            balance += trade.pnl - trade.fee
            equity = balance
            
            equity_curve.append({
                'timestamp': trade.exit_time,
                'balance': balance,
                'equity': equity,
                'pnl': trade.pnl
            })
        
        return equity_curve


# Singleton instance for convenience
metrics_calculator = BacktestMetrics()
