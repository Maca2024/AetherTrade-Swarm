"""
AETHERTRADE-SWARM — HMM-Based 4-State Regime Detector
Uses Gaussian HMM from hmmlearn to identify market regimes:
  State 0: Bull     — positive drift, low vol
  State 1: Range    — near-zero drift, moderate vol
  State 2: Bear     — negative drift, elevated vol
  State 3: Crisis   — large negative drift, extreme vol
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

from models.schemas import RegimeState

logger = logging.getLogger("oracle.regime_detector")


# Regime label assignment by (mean_rank, vol_rank)
# After fitting, we identify states by their emission parameters.
_STATE_LABELS = [RegimeState.BULL, RegimeState.RANGE, RegimeState.BEAR, RegimeState.CRISIS]


class RegimeDetector:
    """
    Wrapper around hmmlearn's GaussianHMM for 4-state regime detection.

    The model is fitted on a sliding window of returns. State identity
    is preserved across fits via a label-assignment heuristic based on
    (emission mean, emission std) ordering.
    """

    N_STATES = 4

    def __init__(self, n_iter: int = 200, random_state: int = 42) -> None:
        self._n_iter = n_iter
        self._random_state = random_state
        self._model = None
        self._state_mapping: dict[int, RegimeState] = {
            0: RegimeState.BULL,
            1: RegimeState.RANGE,
            2: RegimeState.BEAR,
            3: RegimeState.CRISIS,
        }
        self._fitted = False
        self._last_fit_returns: np.ndarray | None = None

    def fit(self, returns: np.ndarray) -> None:
        """Fit HMM on a 1-D array of daily returns."""
        try:
            from hmmlearn.hmm import GaussianHMM  # type: ignore
        except ImportError:
            logger.warning("hmmlearn not installed — using simplified regime detection.")
            self._fitted = False
            self._last_fit_returns = returns
            return

        if len(returns) < 60:
            logger.warning("Insufficient data for HMM fit (need >= 60 obs, got %d)", len(returns))
            return

        X = returns.reshape(-1, 1)

        model = GaussianHMM(
            n_components=self.N_STATES,
            covariance_type="diag",
            n_iter=self._n_iter,
            random_state=self._random_state,
            tol=1e-4,
        )
        try:
            model.fit(X)
        except Exception as exc:
            logger.error("HMM fit failed: %s", exc)
            return

        self._model = model
        self._fitted = True
        self._last_fit_returns = returns
        self._assign_state_labels()

    def _assign_state_labels(self) -> None:
        """
        Assign regime labels to HMM states by sorting on emission mean.
        State with highest mean → BULL, lowest → CRISIS.
        """
        if self._model is None:
            return
        means = self._model.means_.flatten()
        order = np.argsort(means)[::-1]  # Descending by mean
        # order[0] = highest mean state (Bull)
        # order[1] = second (Range)
        # order[2] = third (Bear)
        # order[3] = lowest mean (Crisis)
        labels = [RegimeState.BULL, RegimeState.RANGE, RegimeState.BEAR, RegimeState.CRISIS]
        self._state_mapping = {int(order[i]): labels[i] for i in range(self.N_STATES)}

    def predict(self, returns: np.ndarray) -> tuple[RegimeState, float, dict[str, float]]:
        """
        Returns (current_regime, confidence, state_probabilities).
        Falls back to heuristic if model not fitted.
        """
        if not self._fitted or self._model is None:
            return self._heuristic_regime(returns)

        X = returns.reshape(-1, 1)
        try:
            # Get posterior state probabilities for the last observation
            _, posteriors = self._model.decode(X, algorithm="viterbi")
            state_probs = self._model.predict_proba(X)
            current_state_idx = int(posteriors[-1])
            current_probs = state_probs[-1]

            regime = self._state_mapping.get(current_state_idx, RegimeState.BULL)
            confidence = float(current_probs[current_state_idx])

            probs_by_label = {
                label: float(current_probs[state_idx])
                for state_idx, label in self._state_mapping.items()
            }
            return regime, confidence, probs_by_label

        except Exception as exc:
            logger.error("HMM predict failed: %s", exc)
            return self._heuristic_regime(returns)

    def _heuristic_regime(self, returns: np.ndarray) -> tuple[RegimeState, float, dict[str, float]]:
        """Simple volatility/momentum heuristic fallback."""
        if len(returns) < 20:
            return RegimeState.BULL, 0.70, {
                RegimeState.BULL: 0.70, RegimeState.RANGE: 0.15,
                RegimeState.BEAR: 0.10, RegimeState.CRISIS: 0.05,
            }

        recent = returns[-20:]
        mean = float(np.mean(recent))
        vol = float(np.std(recent))
        momentum = float(np.sum(returns[-10:]))

        # Classify by vol and momentum thresholds
        if vol > 0.025:
            regime = RegimeState.CRISIS
            conf = min(0.90, 0.60 + vol * 10)
        elif mean < -0.002 or momentum < -0.05:
            regime = RegimeState.BEAR
            conf = 0.72
        elif abs(mean) < 0.0005 and vol > 0.008:
            regime = RegimeState.RANGE
            conf = 0.68
        else:
            regime = RegimeState.BULL
            conf = 0.75

        remaining = 1.0 - conf
        others = {r: remaining / 3 for r in RegimeState if r != regime}
        probs = {regime: conf, **others}
        return regime, conf, probs

    def transition_matrix(self) -> np.ndarray | None:
        if self._model is None:
            return None
        return self._model.transmat_

    @property
    def is_fitted(self) -> bool:
        return self._fitted


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_detector: RegimeDetector | None = None


def get_regime_detector() -> RegimeDetector:
    global _detector
    if _detector is None:
        _detector = RegimeDetector()
    return _detector


def init_regime_detector(returns: np.ndarray) -> RegimeDetector:
    global _detector
    _detector = RegimeDetector()
    _detector.fit(returns)
    return _detector


def init_regime_detector_from_market() -> RegimeDetector:
    """Initialize regime detector using real SPY returns from yfinance."""
    global _detector
    _detector = RegimeDetector()
    try:
        from data.market_data import get_market_data_service
        mds = get_market_data_service()
        spy_returns = mds.get_returns("SPY", "2y")
        if len(spy_returns) >= 60:
            _detector.fit(spy_returns)
            regime, conf, probs = _detector.predict(spy_returns)
            logger.info(
                "Regime detector initialized from real SPY data: %s (%.0f%% confidence, %d observations)",
                regime.value, conf * 100, len(spy_returns),
            )
        else:
            logger.warning("Insufficient SPY data (%d obs), regime detector unfitted", len(spy_returns))
    except Exception as exc:
        logger.error("Failed to init regime from market data: %s", exc)
    return _detector
