"""
AETHERTRADE-SWARM — Portfolio Optimizer
Black-Litterman + Half-Kelly position sizing.

Black-Litterman:
  - Starts from market equilibrium (reverse-optimised from cap weights)
  - Incorporates strategy views (from signal engine)
  - Produces posterior expected returns

Half-Kelly:
  - Computes Kelly fraction per position from signal confidence + win rate
  - Halves it for robustness (full Kelly overbets in practice)
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger("oracle.portfolio_optimizer")


class BlackLittermanOptimizer:
    """
    Simplified Black-Litterman implementation for strategy allocation.

    Reference: He & Litterman (1999).
    """

    def __init__(self, risk_aversion: float = 2.5, tau: float = 0.05) -> None:
        # Risk aversion coefficient (lambda)
        self.risk_aversion = risk_aversion
        # Scaling factor for uncertainty in prior
        self.tau = tau

    def compute_equilibrium_returns(
        self,
        cov_matrix: np.ndarray,
        market_weights: np.ndarray,
    ) -> np.ndarray:
        """
        Pi = lambda * Sigma * w_market
        Equilibrium (implied) excess returns.
        """
        return self.risk_aversion * cov_matrix @ market_weights

    def combine_views(
        self,
        cov_matrix: np.ndarray,
        equilibrium_returns: np.ndarray,
        view_matrix: np.ndarray,   # P — link matrix (k x n)
        view_returns: np.ndarray,  # q — view excess returns (k,)
        view_confidence: np.ndarray,  # Omega diagonal (k,) — view uncertainty
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Posterior returns: mu_BL = [(tau*Sigma)^-1 + P'*Omega^-1*P]^-1 * [(tau*Sigma)^-1*pi + P'*Omega^-1*q]
        Returns (posterior_mu, posterior_cov).
        """
        n = len(equilibrium_returns)
        tau_sigma = self.tau * cov_matrix
        tau_sigma_inv = np.linalg.pinv(tau_sigma)

        omega = np.diag(view_confidence)
        omega_inv = np.diag(1.0 / view_confidence)

        # Posterior precision
        posterior_prec = tau_sigma_inv + view_matrix.T @ omega_inv @ view_matrix

        # Posterior mean
        prior_term = tau_sigma_inv @ equilibrium_returns
        view_term = view_matrix.T @ omega_inv @ view_returns
        posterior_mu = np.linalg.solve(posterior_prec, prior_term + view_term)

        # Posterior covariance = Sigma + (tau*Sigma)^-1 posterior
        posterior_cov = cov_matrix + np.linalg.pinv(posterior_prec)

        return posterior_mu, posterior_cov

    def mean_variance_weights(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        constraints: dict[str, float] | None = None,
    ) -> np.ndarray:
        """
        Compute mean-variance optimal weights.
        w* = (lambda * Sigma)^-1 * mu_adjusted
        With simple box constraints.
        """
        inv_sigma = np.linalg.pinv(self.risk_aversion * cov_matrix)
        raw_weights = inv_sigma @ expected_returns

        # Normalise to long-only sum=1 (simplified)
        raw_weights = np.maximum(raw_weights, 0.0)
        total = raw_weights.sum()
        if total <= 0:
            n = len(raw_weights)
            return np.ones(n) / n

        weights = raw_weights / total

        # Apply box constraints
        if constraints:
            min_w = constraints.get("min_weight", 0.02)
            max_w = constraints.get("max_weight", 0.35)
            weights = np.clip(weights, min_w, max_w)
            weights = weights / weights.sum()

        return weights


class HalfKellyPositionSizer:
    """
    Half-Kelly criterion for position sizing.
    f* = (W * R - L) / R / 2
    where W = win rate, R = win/loss ratio, L = loss rate.
    """

    def compute_kelly_fraction(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
    ) -> float:
        """
        Standard Kelly fraction (half-Kelly applied after).
        f = (W*R - (1-W)) / R  where R = avg_win / avg_loss
        """
        if avg_loss <= 0 or avg_win <= 0:
            return 0.0
        R = avg_win / avg_loss
        loss_rate = 1.0 - win_rate
        kelly = (win_rate * R - loss_rate) / R
        return max(0.0, kelly * 0.5)  # Half-Kelly

    def size_positions(
        self,
        signals: list[dict[str, Any]],
        portfolio_constraints: dict[str, float] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Apply Half-Kelly sizing to a list of signals.
        Each signal should have: strength, confidence, expected_win_rate (optional).
        """
        constraints = portfolio_constraints or {
            "max_single_position": 0.15,
            "min_single_position": 0.01,
            "max_gross_leverage": 1.5,
        }

        sized = []
        for sig in signals:
            confidence = float(sig.get("confidence", 0.6))
            strength = abs(float(sig.get("strength", 0.0)))

            # Proxy win_rate from confidence
            win_rate = 0.5 + (confidence - 0.5) * 0.6
            avg_win = strength * 1.5
            avg_loss = strength * 1.0

            kelly = self.compute_kelly_fraction(win_rate, max(avg_win, 0.001), max(avg_loss, 0.001))

            # Scale by signal strength
            position_size = kelly * strength
            position_size = max(
                constraints["min_single_position"],
                min(constraints["max_single_position"], position_size),
            )

            sized.append({**sig, "kelly_fraction": round(kelly, 4), "position_size": round(position_size, 4)})

        return sized


# Singletons
_bl_optimizer: BlackLittermanOptimizer | None = None
_kelly_sizer: HalfKellyPositionSizer | None = None


def get_bl_optimizer() -> BlackLittermanOptimizer:
    global _bl_optimizer
    if _bl_optimizer is None:
        _bl_optimizer = BlackLittermanOptimizer()
    return _bl_optimizer


def get_kelly_sizer() -> HalfKellyPositionSizer:
    global _kelly_sizer
    if _kelly_sizer is None:
        _kelly_sizer = HalfKellyPositionSizer()
    return _kelly_sizer
