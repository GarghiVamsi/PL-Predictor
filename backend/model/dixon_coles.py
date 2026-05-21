"""
Dixon-Coles Poisson model for Premier League match prediction.

Reference:
  Dixon & Coles (1997) "Modelling association football scores and
  inefficiencies in the football betting market", Applied Statistics 46(2).

Parameters estimated per team:
  alpha  — attack strength   (higher = scores more)
  beta   — defence strength  (higher = concedes less)

Plus two global scalars:
  gamma  — home-field advantage multiplier
  rho    — low-score bivariate correction (captures 0-0 / 1-0 / 0-1 / 1-1 bias)

Fitting uses exponential time-weighting so recent matches carry more weight.
"""

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
XI: float = 0.0018          # time-decay constant (per day)
MAX_GOALS: int = 10         # score matrix is (MAX_GOALS+1) × (MAX_GOALS+1)
_GOALS = np.arange(MAX_GOALS + 1)


# ---------------------------------------------------------------------------
# Model container
# ---------------------------------------------------------------------------

@dataclass
class DCModel:
    """Fitted Dixon-Coles model — immutable snapshot of team strengths."""

    teams: list[str]
    alpha: dict[str, float]       # attack strength per team
    beta: dict[str, float]        # defence strength per team
    gamma: float                   # home advantage multiplier
    rho: float                     # low-score correction
    n_matches: int = 0
    reference_date: pd.Timestamp = field(default_factory=pd.Timestamp.now)

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict_match(self, home: str, away: str) -> np.ndarray:
        """
        Return an (MAX_GOALS+1) × (MAX_GOALS+1) score-probability matrix.
        Entry [i, j] = P(home scores i, away scores j).
        """
        lam, mu = self.expected_goals(home, away)
        return _score_matrix(lam, mu, self.rho)

    def expected_goals(self, home: str, away: str) -> tuple[float, float]:
        """Return (lambda_home, mu_away) expected goals for a fixture."""
        lam = self.alpha[home] * self.beta[away] * self.gamma
        mu = self.alpha[away] * self.beta[home]
        return float(lam), float(mu)

    def win_draw_loss(self, home: str, away: str) -> tuple[float, float, float]:
        """Return (P_home_win, P_draw, P_away_win) from the score matrix."""
        matrix = self.predict_match(home, away)
        p_home = float(np.tril(matrix, -1).sum())
        p_draw = float(np.trace(matrix))
        p_away = float(np.triu(matrix, 1).sum())
        return p_home, p_draw, p_away

    # ------------------------------------------------------------------
    # Introspection helpers used by compound_predictor
    # ------------------------------------------------------------------

    def mean_attack(self) -> float:
        return float(np.mean(list(self.alpha.values())))

    def mean_defence(self) -> float:
        return float(np.mean(list(self.beta.values())))

    def has_team(self, team: str) -> bool:
        return team in self.alpha


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _score_matrix(lam: float, mu: float, rho: float) -> np.ndarray:
    """Build and return the full score-probability matrix."""
    home_pmf = poisson.pmf(_GOALS, max(lam, 1e-6))
    away_pmf = poisson.pmf(_GOALS, max(mu, 1e-6))
    matrix = np.outer(home_pmf, away_pmf)

    # Dixon-Coles bivariate correction for scorelines 0-0, 1-0, 0-1, 1-1
    tau = np.array([
        [1.0 - lam * mu * rho, 1.0 + lam * rho],
        [1.0 + mu * rho,       1.0 - rho       ],
    ])
    matrix[:2, :2] *= tau

    total = matrix.sum()
    if total > 0:
        matrix /= total

    return matrix


def _neg_log_likelihood(
    params: np.ndarray,
    n_teams: int,
    home_idx: np.ndarray,
    away_idx: np.ndarray,
    home_goals: np.ndarray,
    away_goals: np.ndarray,
    weights: np.ndarray,
) -> float:
    """Vectorised weighted negative log-likelihood for L-BFGS-B."""
    alpha = np.exp(params[:n_teams])
    beta = np.exp(params[n_teams: 2 * n_teams])
    gamma = np.exp(params[2 * n_teams])
    rho = params[2 * n_teams + 1]

    lam = alpha[home_idx] * beta[away_idx] * gamma   # home expected goals
    mu = alpha[away_idx] * beta[home_idx]             # away expected goals

    # Low-score bivariate correction τ(x, y, λ, μ, ρ)
    tau = np.ones(len(home_goals))
    m00 = (home_goals == 0) & (away_goals == 0)
    m10 = (home_goals == 1) & (away_goals == 0)
    m01 = (home_goals == 0) & (away_goals == 1)
    m11 = (home_goals == 1) & (away_goals == 1)
    tau[m00] = 1.0 - lam[m00] * mu[m00] * rho
    tau[m10] = 1.0 + mu[m10] * rho
    tau[m01] = 1.0 + lam[m01] * rho
    tau[m11] = 1.0 - rho

    # Guard against invalid tau (can occur at extreme rho values)
    if np.any(tau <= 0):
        return 1e10

    log_ll = (
        np.log(tau)
        + poisson.logpmf(home_goals, lam)
        + poisson.logpmf(away_goals, mu)
    )
    return -float(np.dot(weights, log_ll))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fit(df: pd.DataFrame, reference_date: pd.Timestamp | None = None) -> DCModel:
    """
    Fit a Dixon-Coles model to historical match data.

    Parameters
    ----------
    df : DataFrame with columns HomeTeam, AwayTeam, FTHG, FTAG
         and optionally a Date column (used for time-weighting).
    reference_date : the "present" date for computing time weights.
                     Defaults to today.

    Returns
    -------
    DCModel with fitted alpha, beta, gamma, rho.
    """
    if reference_date is None:
        reference_date = pd.Timestamp.now()

    df = df.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"]).copy()

    # ------------------------------------------------------------------
    # Time weights
    # ------------------------------------------------------------------
    if "Date" in df.columns:
        dates = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce", format="mixed")
        days_ago = (reference_date - dates).dt.days.clip(lower=0)
        # Fill unparseable dates with the median age so they still contribute
        days_ago = days_ago.fillna(days_ago.median()).astype(float)
    else:
        days_ago = pd.Series(730.0, index=df.index)  # 2-year fallback

    weights = np.exp(-XI * days_ago.values).astype(np.float64)

    # ------------------------------------------------------------------
    # Index teams
    # ------------------------------------------------------------------
    teams = sorted(set(df["HomeTeam"]) | set(df["AwayTeam"]))
    n_teams = len(teams)
    team_idx = {t: i for i, t in enumerate(teams)}

    home_idx = df["HomeTeam"].map(team_idx).values.astype(np.int32)
    away_idx = df["AwayTeam"].map(team_idx).values.astype(np.int32)
    home_goals = df["FTHG"].values.astype(np.int32)
    away_goals = df["FTAG"].values.astype(np.int32)

    # ------------------------------------------------------------------
    # Optimisation
    # Initial values: log(alpha)=log(beta)=0, gamma≈1.3, rho≈-0.13
    # rho is bounded to keep τ valid; gamma is log-transformed (>0 always)
    # ------------------------------------------------------------------
    x0 = np.zeros(2 * n_teams + 2)
    x0[2 * n_teams] = np.log(1.3)     # gamma start
    x0[2 * n_teams + 1] = -0.13       # rho start (matches Dixon-Coles paper)

    bounds = [(None, None)] * (2 * n_teams + 1) + [(-0.99, 0.99)]

    logger.info(
        "Fitting Dixon-Coles model: %d teams, %d matches", n_teams, len(df)
    )

    result = minimize(
        _neg_log_likelihood,
        x0,
        args=(n_teams, home_idx, away_idx, home_goals, away_goals, weights),
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": 5000, "maxfun": 100_000, "ftol": 1e-10, "gtol": 1e-4},
    )

    if not result.success:
        logger.warning("Optimisation did not fully converge: %s", result.message)

    p = result.x
    alpha_vals = np.exp(p[:n_teams])
    beta_vals = np.exp(p[n_teams: 2 * n_teams])
    gamma = float(np.exp(p[2 * n_teams]))
    rho = float(p[2 * n_teams + 1])

    logger.info(
        "Fitted: gamma=%.3f  rho=%.3f  converged=%s",
        gamma, rho, result.success,
    )

    return DCModel(
        teams=teams,
        alpha={t: float(alpha_vals[i]) for i, t in enumerate(teams)},
        beta={t: float(beta_vals[i]) for i, t in enumerate(teams)},
        gamma=gamma,
        rho=rho,
        n_matches=len(df),
        reference_date=reference_date,
    )
