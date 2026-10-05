"""Walk-forward optimization for backtesting.

This module provides walk-forward optimization capabilities,
allowing strategies to be optimized and validated across different
time periods to prevent overfitting.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import itertools
import pandas as pd
import numpy as np

from backend import config
from backend.backtesting.data_loader import HistoricalDataLoader
from backend.backtesting.engine import BacktestingEngine, BacktestResult
from backend.backtesting.metrics import PerformanceMetrics

log = logging.getLogger("backtesting.walkforward")


@dataclass
class OptimizationResult:
    """Result of parameter optimization."""
    params: Dict[str, Any]
    metrics: PerformanceMetrics
    in_sample_result: BacktestResult
    out_sample_result: Optional[BacktestResult] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'params': self.params,
            'metrics': self.metrics.to_dict(),
            'in_sample': self.in_sample_result.to_dict(),
            'out_sample': self.out_sample_result.to_dict() if self.out_sample_result else None
        }


@dataclass
class WalkForwardResult:
    """Result of walk-forward optimization."""
    all_results: List[OptimizationResult] = field(default_factory=list)
    best_params: Dict[str, Any] = field(default_factory=dict)
    best_in_sample_score: float = 0.0
    best_out_sample_score: float = 0.0
    best_metric: str = "sharpe_ratio"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'all_results': [r.to_dict() for r in self.all_results],
            'best_params': self.best_params,
            'best_in_sample_score': self.best_in_sample_score,
            'best_out_sample_score': self.best_out_sample_score,
            'best_metric': self.best_metric
        }


class WalkForwardOptimizer:
    """Walk-forward optimization for trading strategies.
    
    This class implements walk-forward optimization, which:
    1. Splits data into in-sample and out-of-sample periods
    2. Optimizes parameters on in-sample data
    3. Validates on out-of-sample data
    4. Rolls forward through time
    
    This helps prevent overfitting by ensuring the strategy
    performs well on unseen data.
    """
    
    def __init__(
        self,
        engine: Optional[BacktestingEngine] = None,
        data_loader: Optional[HistoricalDataLoader] = None
    ):
        """Initialize the walk-forward optimizer.
        
        Args:
            engine: Backtesting engine (optional)
            data_loader: Historical data loader (optional)
        """
        self.engine = engine or BacktestingEngine()
        self.data_loader = data_loader or HistoricalDataLoader()
        self._window_size = 0
        self._roll_forward = 0
    
    async def optimize(
        self,
        symbol: str,
        timeframe: str,
        param_grid: Dict[str, List[Any]],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        in_sample_periods: int = 30,
        out_sample_periods: int = 10,
        metric: str = "sharpe_ratio",
        maximize: bool = True,
        signal_generator: Optional[Callable] = None
    ) -> WalkForwardResult:
        """Run walk-forward optimization.
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe
            param_grid: Dictionary of parameter names to possible values
            start_date: Start date (optional)
            end_date: End date (optional)
            in_sample_periods: Number of periods for in-sample optimization
            out_sample_periods: Number of periods for out-of-sample validation
            metric: Metric to optimize (default: 'sharpe_ratio')
            maximize: Whether to maximize or minimize the metric
            signal_generator: Custom signal generator (optional)
            
        Returns:
            WalkForwardResult with optimization results
        """
        result = WalkForwardResult()
        result.best_metric = metric
        
        # Load full dataset
        df = await self.data_loader.load_ohlcv(symbol, timeframe, start_date, end_date)
        
        if df.empty or len(df) < in_sample_periods + out_sample_periods:
            log.error(f"Insufficient data: {len(df)} candles, need at least {in_sample_periods + out_sample_periods}")
            return result
        
        # Calculate window size in candles
        self._window_size = in_sample_periods + out_sample_periods
        self._roll_forward = out_sample_periods
        
        # Generate all parameter combinations
        param_combinations = self._generate_param_combinations(param_grid)
        
        if not param_combinations:
            log.error("No parameter combinations to test")
            return result
        
        log.info(f"Starting walk-forward optimization with {len(param_combinations)} parameter combinations")
        log.info(f"In-sample: {in_sample_periods} periods, Out-sample: {out_sample_periods} periods")
        
        # Run walk-forward
        all_results = await self._run_walk_forward(
            df, symbol, timeframe, param_combinations, 
            in_sample_periods, out_sample_periods, metric, maximize, signal_generator
        )
        
        result.all_results = all_results
        
        # Find best parameters
        self._find_best_parameters(result, metric, maximize)
        
        log.info(f"Walk-forward optimization completed")
        log.info(f"Best in-sample {metric}: {result.best_in_sample_score:.4f}")
        log.info(f"Best out-sample {metric}: {result.best_out_sample_score:.4f}")
        log.info(f"Best parameters: {result.best_params}")
        
        return result
    
    def _generate_param_combinations(self, param_grid: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """Generate all parameter combinations from grid.
        
        Args:
            param_grid: Dictionary of parameter names to possible values
            
        Returns:
            List of parameter combination dictionaries
        """
        # Get parameter names and values
        param_names = list(param_grid.keys())
        param_values = [param_grid[name] for name in param_names]
        
        # Generate all combinations
        combinations = list(itertools.product(*param_values))
        
        # Convert to dictionaries
        param_combinations = []
        for combo in combinations:
            param_dict = dict(zip(param_names, combo))
            param_combinations.append(param_dict)
        
        log.info(f"Generated {len(param_combinations)} parameter combinations")
        
        return param_combinations
    
    async def _run_walk_forward(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        param_combinations: List[Dict[str, Any]],
        in_sample_periods: int,
        out_sample_periods: int,
        metric: str,
        maximize: bool,
        signal_generator: Optional[Callable]
    ) -> List[OptimizationResult]:
        """Run walk-forward optimization across data.
        
        Args:
            df: Full dataset
            symbol: Trading pair
            timeframe: Timeframe
            param_combinations: List of parameter combinations
            in_sample_periods: In-sample periods
            out_sample_periods: Out-sample periods
            metric: Metric to optimize
            maximize: Whether to maximize or minimize
            signal_generator: Custom signal generator
            
        Returns:
            List of optimization results
        """
        all_results = []
        
        # Split data into windows
        windows = self._split_into_windows(df, in_sample_periods, out_sample_periods)
        
        if not windows:
            return all_results
        
        log.info(f"Processing {len(windows)} windows")
        
        # Process each window
        for window_idx, (is_data, oos_data) in enumerate(windows):
            log.info(f"Processing window {window_idx + 1}/{len(windows)}")
            
            # Find best parameters for this window
            best_result = await self._optimize_window(
                is_data, oos_data, symbol, timeframe,
                param_combinations, metric, maximize, signal_generator
            )
            
            if best_result:
                all_results.append(best_result)
        
        return all_results
    
    def _split_into_windows(
        self,
        df: pd.DataFrame,
        in_sample_periods: int,
        out_sample_periods: int
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """Split data into rolling windows for walk-forward.
        
        Args:
            df: Full dataset
            in_sample_periods: In-sample periods
            out_sample_periods: Out-sample periods
            
        Returns:
            List of (in_sample_data, out_sample_data) tuples
        """
        windows = []
        total_periods = in_sample_periods + out_sample_periods
        
        # Check if we have enough data
        if len(df) < total_periods:
            return windows
        
        # Create rolling windows
        for start_idx in range(0, len(df) - total_periods + 1, out_sample_periods):
            is_end_idx = start_idx + in_sample_periods
            oos_end_idx = start_idx + total_periods
            
            is_data = df.iloc[start_idx:is_end_idx]
            oos_data = df.iloc[is_end_idx:oos_end_idx]
            
            windows.append((is_data, oos_data))
        
        return windows
    
    async def _optimize_window(
        self,
        is_data: pd.DataFrame,
        oos_data: pd.DataFrame,
        symbol: str,
        timeframe: str,
        param_combinations: List[Dict[str, Any]],
        metric: str,
        maximize: bool,
        signal_generator: Optional[Callable]
    ) -> Optional[OptimizationResult]:
        """Optimize parameters for a single window.
        
        Args:
            is_data: In-sample data
            oos_data: Out-of-sample data
            symbol: Trading pair
            timeframe: Timeframe
            param_combinations: Parameter combinations to test
            metric: Metric to optimize
            maximize: Whether to maximize or minimize
            signal_generator: Custom signal generator
            
        Returns:
            Best optimization result for this window
        """
        best_result = None
        best_score = -float('inf') if maximize else float('inf')
        
        # Test each parameter combination
        for params in param_combinations:
            try:
                # Run in-sample backtest
                is_result = await self._run_backtest(
                    is_data, symbol, timeframe, params, signal_generator
                )
                
                # Get metric value
                metric_value = self._get_metric_value(is_result.metrics, metric)
                
                # Check if this is the best so far
                if (maximize and metric_value > best_score) or (not maximize and metric_value < best_score):
                    best_score = metric_value
                    best_result = OptimizationResult(
                        params=params,
                        metrics=is_result.metrics,
                        in_sample_result=is_result
                    )
                    
                    # Run out-of-sample validation
                    if oos_data is not None and len(oos_data) > 0:
                        oos_result = await self._run_backtest(
                            oos_data, symbol, timeframe, params, signal_generator
                        )
                        best_result.out_sample_result = oos_result
                        best_result.metrics = oos_result.metrics
                
            except Exception as e:
                log.error(f"Error testing parameters {params}: {e}")
                continue
        
        return best_result
    
    async def _run_backtest(
        self,
        data: pd.DataFrame,
        symbol: str,
        timeframe: str,
        params: Dict[str, Any],
        signal_generator: Optional[Callable]
    ) -> BacktestResult:
        """Run a backtest with specific parameters.
        
        Args:
            data: Historical data
            symbol: Trading pair
            timeframe: Timeframe
            params: Parameters for the signal generator
            signal_generator: Custom signal generator
            
        Returns:
            BacktestResult
        """
        # Create a custom signal generator if params are provided
        if params and signal_generator is None:
            # Use default signal generator with custom parameters
            def custom_signal_generator(df):
                from backend.analysis.signals import generate_signal
                return generate_signal(df, params)
            signal_gen = custom_signal_generator
        else:
            signal_gen = signal_generator
        
        # Create temporary engine for this backtest
        temp_engine = BacktestingEngine(
            initial_balance=self.engine.initial_balance,
            fee_pct=self.engine.fee_pct,
            slippage_pct=self.engine.slippage_pct
        )
        
        # Convert DataFrame to list of candles for the engine
        # The engine expects to load data itself, so we need to adapt
        # For now, we'll use a simplified approach
        
        # Run backtest
        result = await temp_engine.run(
            symbol=symbol,
            timeframe=timeframe,
            limit=len(data),
            signal_generator=signal_gen
        )
        
        return result
    
    def _get_metric_value(self, metrics: PerformanceMetrics, metric_name: str) -> float:
        """Get metric value from PerformanceMetrics.
        
        Args:
            metrics: PerformanceMetrics object
            metric_name: Name of the metric
            
        Returns:
            Metric value
        """
        metric_mapping = {
            'sharpe_ratio': metrics.sharpe_ratio,
            'sortino_ratio': metrics.sortino_ratio,
            'profit_factor': metrics.profit_factor,
            'expectancy': metrics.expectancy,
            'win_rate': metrics.win_rate,
            'total_pnl': metrics.total_pnl,
            'roi': metrics.roi,
            'roi_pct': metrics.roi_pct,
            'max_drawdown': metrics.max_drawdown,
            'calmar_ratio': metrics.calmar_ratio,
        }
        
        return metric_mapping.get(metric_name, 0.0)
    
    def _find_best_parameters(
        self,
        result: WalkForwardResult,
        metric: str,
        maximize: bool
    ) -> None:
        """Find the best parameters across all windows.
        
        Args:
            result: WalkForwardResult to update
            metric: Metric to optimize
            maximize: Whether to maximize or minimize
        """
        if not result.all_results:
            return
        
        # Calculate average out-of-sample score for each parameter set
        param_scores = {}
        
        for opt_result in result.all_results:
            if opt_result.out_sample_result:
                metric_value = self._get_metric_value(opt_result.out_sample_result.metrics, metric)
                param_key = self._params_to_key(opt_result.params)
                
                if param_key not in param_scores:
                    param_scores[param_key] = []
                param_scores[param_key].append(metric_value)
        
        # Find best parameter set
        best_score = -float('inf') if maximize else float('inf')
        best_params = None
        
        for param_key, scores in param_scores.items():
            avg_score = np.mean(scores)
            
            if (maximize and avg_score > best_score) or (not maximize and avg_score < best_score):
                best_score = avg_score
                # Find the params corresponding to this key
                for opt_result in result.all_results:
                    if self._params_to_key(opt_result.params) == param_key:
                        best_params = opt_result.params
                        break
        
        if best_params:
            result.best_params = best_params
            result.best_out_sample_score = best_score
            
            # Find best in-sample score for the best params
            for opt_result in result.all_results:
                if self._params_to_key(opt_result.params) == self._params_to_key(best_params):
                    in_sample_metric = self._get_metric_value(opt_result.in_sample_result.metrics, metric)
                    if (maximize and in_sample_metric > result.best_in_sample_score) or \
                       (not maximize and in_sample_metric < result.best_in_sample_score):
                        result.best_in_sample_score = in_sample_metric
                    break
    
    def _params_to_key(self, params: Dict[str, Any]) -> str:
        """Convert parameters dictionary to string key.
        
        Args:
            params: Parameters dictionary
            
        Returns:
            String key representing the parameters
        """
        # Sort parameters for consistent key
        sorted_params = sorted(params.items())
        param_str = ",".join(f"{k}={v}" for k, v in sorted_params)
        return param_str
    
    async def grid_search(
        self,
        symbol: str,
        timeframe: str,
        param_grid: Dict[str, List[Any]],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        metric: str = "sharpe_ratio",
        maximize: bool = True,
        cv: int = 3
    ) -> WalkForwardResult:
        """Run grid search with cross-validation.
        
        This is a simpler alternative to walk-forward that uses
        k-fold cross-validation.
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe
            param_grid: Parameter grid to search
            start_date: Start date (optional)
            end_date: End date (optional)
            metric: Metric to optimize
            maximize: Whether to maximize or minimize
            cv: Number of cross-validation folds
            
        Returns:
            WalkForwardResult with best parameters
        """
        result = WalkForwardResult()
        result.best_metric = metric
        
        # Load data
        df = await self.data_loader.load_ohlcv(symbol, timeframe, start_date, end_date)
        
        if df.empty:
            return result
        
        # Split into folds
        folds = self._split_into_folds(df, cv)
        
        if not folds:
            return result
        
        # Generate parameter combinations
        param_combinations = self._generate_param_combinations(param_grid)
        
        if not param_combinations:
            return result
        
        # Test each parameter combination with cross-validation
        for params in param_combinations:
            fold_scores = []
            
            for fold_idx, (train_data, test_data) in enumerate(folds):
                try:
                    # Train on training fold
                    train_result = await self._run_backtest(
                        train_data, symbol, timeframe, params, None
                    )
                    
                    # Test on test fold
                    test_result = await self._run_backtest(
                        test_data, symbol, timeframe, params, None
                    )
                    
                    # Get metric value
                    metric_value = self._get_metric_value(test_result.metrics, metric)
                    fold_scores.append(metric_value)
                    
                except Exception as e:
                    log.error(f"Error in fold {fold_idx} for params {params}: {e}")
                    continue
            
            if fold_scores:
                avg_score = np.mean(fold_scores)
                
                # Create optimization result
                opt_result = OptimizationResult(
                    params=params,
                    metrics=test_result.metrics,
                    in_sample_result=train_result
                )
                result.all_results.append(opt_result)
                
                # Update best if this is better
                if (maximize and avg_score > result.best_out_sample_score) or \
                   (not maximize and avg_score < result.best_out_sample_score):
                    result.best_out_sample_score = avg_score
                    result.best_params = params
        
        return result
    
    def _split_into_folds(self, df: pd.DataFrame, cv: int) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """Split data into k folds for cross-validation.
        
        Args:
            df: Dataset to split
            cv: Number of folds
            
        Returns:
            List of (train_data, test_data) tuples
        """
        if cv <= 1 or len(df) < cv:
            return []
        
        folds = []
        fold_size = len(df) // cv
        
        for i in range(cv):
            start_idx = i * fold_size
            test_start = start_idx + fold_size if i < cv - 1 else len(df)
            
            # Training data is everything except this fold
            train_indices = list(range(0, start_idx)) + list(range(test_start, len(df)))
            train_data = df.iloc[train_indices]
            
            # Test data is this fold
            test_data = df.iloc[start_idx:test_start]
            
            folds.append((train_data, test_data))
        
        return folds


# Singleton instance for convenience
walkforward_optimizer = WalkForwardOptimizer()
