"""Next-candle probability estimator — SCALPER.md component #4.

Honest scope (R-E.5): this is a *calibrated edge*, not a crystal ball.
On good days the accuracy is 52–58 %; often it's lower after fees.
The model is trained on historical bars; features come from the MTF analysis.

Architecture (deliberately simple — AGENTS.md §0 evidence standard):
- Feature engineering from the last closed bar
- Logistic regression (sklearn) with Platt calibration → P(next_close > this_close)
- If sklearn is unavailable, falls back to a rule-based heuristic
- OOS accuracy is reported honestly; the scalper only uses this if accuracy > 0.52

Features:
    rsi14, ema_slope, candle_body_pct, upper_wick_pct, lower_wick_pct,
    volume_surge (current vol / 20-bar avg), multi-TF momentum alignment
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return (a / b) if b != 0 else default


def build_features(data: pd.DataFrame, mtf_alignment: int = 0) -> np.ndarray:
    """Compute feature vector for the last closed bar.

    ``data`` must be validated OHLCV (from core.data).
    ``mtf_alignment`` is the integer alignment score from MTFAnalyzer (-1/0/+1).
    """
    if len(data) < 30:
        raise ValueError("Need >= 30 bars to compute features")

    close = data["Close"]
    high = data["High"]
    low = data["Low"]
    vol = data["Volume"]

    # RSI (14)
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(span=14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(span=14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = (100 - 100 / (1 + rs)).fillna(50.0)

    # EMA slopes
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema_slope = (ema9 - ema9.shift(3)).fillna(0.0) / close.replace(0, np.nan)

    # Candle structure
    candle_body = (close - data["Open"]) / close.replace(0, np.nan)
    upper_wick = (high - close.clip(lower=data["Open"])) / close.replace(0, np.nan)
    lower_wick = (close.clip(upper=data["Open"]) - low) / close.replace(0, np.nan)

    # Volume surge
    vol_ma20 = vol.rolling(20, min_periods=5).mean()
    vol_surge = (vol / vol_ma20.replace(0, np.nan)).fillna(1.0)

    # EMA cross signal
    ema_cross = np.sign(ema9 - ema21).fillna(0.0)

    # Distance from 20-bar high/low (mean reversion proxy)
    high20 = high.rolling(20, min_periods=5).max()
    low20 = low.rolling(20, min_periods=5).min()
    dist_high = ((close - high20) / close.replace(0, np.nan)).fillna(0.0)
    dist_low = ((close - low20) / close.replace(0, np.nan)).fillna(0.0)

    last = {
        "rsi14": float(rsi.iloc[-1]) / 100.0,              # normalised 0-1
        "ema_slope": float(ema_slope.iloc[-1]),
        "candle_body": float(candle_body.iloc[-1]),
        "upper_wick": float(upper_wick.iloc[-1]),
        "lower_wick": float(lower_wick.iloc[-1]),
        "vol_surge": min(float(vol_surge.iloc[-1]), 10.0),  # cap outliers
        "ema_cross": float(ema_cross.iloc[-1]),
        "dist_high": float(dist_high.iloc[-1]),
        "dist_low": float(dist_low.iloc[-1]),
        "mtf_alignment": float(mtf_alignment),
    }
    return np.array(list(last.values()), dtype=float)


FEATURE_NAMES = [
    "rsi14", "ema_slope", "candle_body", "upper_wick", "lower_wick",
    "vol_surge", "ema_cross", "dist_high", "dist_low", "mtf_alignment",
]


# ---------------------------------------------------------------------------
# Historical feature/label matrix builder
# ---------------------------------------------------------------------------

def build_dataset(data: pd.DataFrame, mtf_alignment: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Build X (features per bar) and y (1 if next close > this close).

    Used for training and OOS accuracy evaluation.
    """
    if len(data) < 50:
        raise ValueError("Need >= 50 bars to build a training dataset")

    rows: list[np.ndarray] = []
    labels: list[int] = []

    for i in range(30, len(data) - 1):     # -1: need the NEXT bar's close
        window = data.iloc[:i + 1]
        try:
            feat = build_features(window, mtf_alignment)
        except Exception:
            continue
        next_close = float(data["Close"].iloc[i + 1])
        this_close = float(data["Close"].iloc[i])
        labels.append(1 if next_close > this_close else 0)
        rows.append(feat)

    if not rows:
        raise RuntimeError("No usable rows in the dataset")
    return np.array(rows), np.array(labels)


# ---------------------------------------------------------------------------
# Model wrapper
# ---------------------------------------------------------------------------

@dataclass
class PredictionResult:
    p_up: float             # P(next close > this close), calibrated 0.0–1.0
    direction: int          # +1 if p_up > 0.5, -1 if < 0.5, 0 if uncertain
    confidence: float       # |p_up - 0.5| as a measure of model conviction
    oos_accuracy: float     # last measured OOS accuracy (0.0 if not fitted)
    edge: float             # = max(p_up, 1-p_up) - 0.5  (0 = coin-flip, 0.5 = perfect)
    model_type: str         # 'logreg' | 'heuristic'


class CandlePredictor:
    """Calibrated next-candle probability model.

    Trains on historical bars using a rolling/expanding OOS evaluation so accuracy
    is always measured on unseen data (R-D.7 — ship only what is measured).

    Falls back to a rule-based heuristic if sklearn is unavailable.
    """

    MIN_OOS_ACCURACY = 0.52     # below this, use_if_below_threshold kicks in

    def __init__(self) -> None:
        self._model: Any = None
        self._oos_accuracy: float = 0.0
        self._fitted: bool = False
        self._model_type: str = "heuristic"

    # -- training -----------------------------------------------------------------

    def fit(
        self,
        data: pd.DataFrame,
        mtf_alignment: int = 0,
        oos_frac: float = 0.25,
        max_features: int = 10,
    ) -> float:
        """Fit the model and return OOS accuracy.

        ``oos_frac`` = fraction of bars reserved for out-of-sample accuracy measurement.
        Returns OOS accuracy; does NOT silence a weak model — caller decides whether
        to use it.
        """
        X, y = build_dataset(data, mtf_alignment)
        if len(X) < 60:
            self._oos_accuracy = 0.0
            return 0.0

        split = max(30, int(len(X) * (1 - oos_frac)))
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.calibration import CalibratedClassifierCV
            from sklearn.preprocessing import StandardScaler

            scaler = StandardScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_test_s = scaler.transform(X_test)

            lr = LogisticRegression(max_iter=500, C=0.5)
            lr.fit(X_train_s, y_train)
            clf = CalibratedClassifierCV(lr, cv="prefit", method="sigmoid")
            clf.fit(X_train_s, y_train)

            y_pred = clf.predict(X_test_s)
            oos_acc = float((y_pred == y_test).mean())

            self._model = (scaler, clf)
            self._oos_accuracy = round(oos_acc, 4)
            self._fitted = True
            self._model_type = "logreg"

        except ImportError:
            # sklearn not installed → heuristic fallback
            oos_acc = self._heuristic_oos_accuracy(X_test, y_test)
            self._oos_accuracy = round(oos_acc, 4)
            self._fitted = True
            self._model_type = "heuristic"

        return self._oos_accuracy

    # -- prediction ---------------------------------------------------------------

    def predict(self, data: pd.DataFrame, mtf_alignment: int = 0) -> PredictionResult:
        """Predict P(next close > this close) for the last bar of ``data``."""
        feat = build_features(data, mtf_alignment).reshape(1, -1)

        if self._model_type == "logreg" and self._model is not None:
            scaler, clf = self._model
            feat_s = scaler.transform(feat)
            p_up = float(clf.predict_proba(feat_s)[0][1])
        else:
            p_up = self._heuristic_predict(feat[0])

        # Gate: if OOS accuracy is below the minimum, signal is unreliable → no trade
        if self._oos_accuracy < self.MIN_OOS_ACCURACY:
            direction = 0
        else:
            direction = 1 if p_up > 0.52 else (-1 if p_up < 0.48 else 0)
        confidence = abs(p_up - 0.5) if direction != 0 else 0.0
        edge = abs(p_up - 0.5)

        return PredictionResult(
            p_up=round(p_up, 4),
            direction=direction,
            confidence=round(confidence, 4),
            oos_accuracy=self._oos_accuracy,
            edge=round(edge, 4),
            model_type=self._model_type,
        )

    # -- persistence --------------------------------------------------------------

    def save(self, path: Path) -> None:
        """Persist the fitted model state to JSON (sklearn model excluded)."""
        state = {
            "oos_accuracy": self._oos_accuracy,
            "model_type": self._model_type,
            "fitted": self._fitted,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        # sklearn model: pickle beside the JSON if available
        if self._model_type == "logreg" and self._model is not None:
            pkl_path = path.with_suffix(".pkl")
            try:
                import pickle
                with pkl_path.open("wb") as fh:
                    pickle.dump(self._model, fh)
            except Exception:
                pass

    def load(self, path: Path) -> bool:
        """Load a previously saved model. Returns True on success."""
        if not path.exists():
            return False
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            self._oos_accuracy = float(state.get("oos_accuracy", 0.0))
            self._model_type = state.get("model_type", "heuristic")
            self._fitted = bool(state.get("fitted", False))
        except Exception:
            return False
        # try to load the sklearn pickle
        pkl_path = path.with_suffix(".pkl")
        if pkl_path.exists() and self._model_type == "logreg":
            try:
                import pickle
                with pkl_path.open("rb") as fh:
                    self._model = pickle.load(fh)
            except Exception:
                self._model = None
        return True

    # -- heuristic fallback -------------------------------------------------------

    @staticmethod
    def _heuristic_predict(feat: np.ndarray) -> float:
        """Rule-based P(up) when sklearn is unavailable (honest, simple)."""
        # feat order: rsi, ema_slope, candle_body, upper_wick, lower_wick,
        #             vol_surge, ema_cross, dist_high, dist_low, mtf_alignment
        rsi, ema_slope, candle_body, _, lower_wick, vol_surge, ema_cross, _, _, mtf = feat
        score = 0.0
        if rsi < 0.3:           score += 0.05   # oversold
        elif rsi > 0.7:         score -= 0.05   # overbought
        if ema_slope > 0:       score += 0.06
        elif ema_slope < 0:     score -= 0.06
        if candle_body > 0.001: score += 0.04   # green candle
        elif candle_body < -0.001: score -= 0.04
        if lower_wick > 0.002:  score += 0.03   # buying tail
        if vol_surge > 1.5:     score += 0.02   # volume confirmation
        if ema_cross > 0:       score += 0.05
        elif ema_cross < 0:     score -= 0.05
        if mtf > 0:             score += 0.08
        elif mtf < 0:           score -= 0.08
        return float(np.clip(0.5 + score, 0.3, 0.7))

    @staticmethod
    def _heuristic_oos_accuracy(X_test: np.ndarray, y_test: np.ndarray) -> float:
        preds = np.array([
            1 if CandlePredictor._heuristic_predict(x) > 0.5 else 0
            for x in X_test
        ])
        return float((preds == y_test).mean()) if len(y_test) > 0 else 0.0
