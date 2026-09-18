from unittest.mock import patch
from unittest.mock import MagicMock
import sys

# Mock the missing database module since it was seemingly not carried over or is structurally mocked
sys.modules["backend.data"] = MagicMock()
sys.modules["backend.data.database"] = MagicMock()

from backend.strategy import engine

def test_feedback_tuning():
    """
    Test that the self_tune engine adjusts the net_threshold correctly based on sharpe ratio.
    """
    engine.db.get_state.side_effect = lambda k, default=None: "0" if k == "tune_last_trades" else None

    with patch("backend.strategy.engine.performance.compute_metrics") as mock_metrics:
        # Simulate poor performance
        mock_metrics.return_value = {
            "total_trades": 20,
            "sharpe": 0.2,
            "profit_factor": 0.8
        }

        # Run self tune
        updated_params = engine.self_tune()

        # Verify it tightened the threshold
        assert updated_params["net_threshold"] > 1.0

        # Verify it called db to save the state
        engine.db.set_state.assert_any_call("tune_last_trades", "20")
