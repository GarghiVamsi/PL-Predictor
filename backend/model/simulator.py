"""
Monte Carlo season simulator using the fitted Dixon-Coles model.

Draws home_goals ~ Poisson(λ), away_goals ~ Poisson(μ) for all 380 fixtures
using fully vectorised numpy operations.  Returns per-team statistics.
"""

import logging
from dataclasses import dataclass, field

import numpy as np

from .dixon_coles import DCModel

logger = logging.getLogger(__name__)

N_SIMULATIONS: int = 1000
TOP4_CUTOFF: int = 4
RELEGATION_SLOTS: int = 3


@dataclass
class TeamStats:
    team: str
    mean_points: float
    std_points: float
    mean_position: float
    title_probability: float
    top4_probability: float
    relegation_probability: float
    position_distribution: dict[int, float]  # position → fraction of sims


@dataclass
class SimulationResult:
    season: str
    teams: list[str]       # sorted by mean_position ascending
    stats: list[TeamStats]
    n_simulations: int = N_SIMULATIONS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fixture_arrays(
    teams: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    """
    Build home_indices and away_indices arrays for all n*(n-1) fixtures.
    Each team plays every other team home and away.
    """
    n = len(teams)
    home_i = np.array([i for i in range(n) for j in range(n) if i != j], dtype=np.int32)
    away_i = np.array([j for i in range(n) for j in range(n) if i != j], dtype=np.int32)
    return home_i, away_i


def _run_simulations(
    lams: np.ndarray,
    mus: np.ndarray,
    home_i: np.ndarray,
    away_i: np.ndarray,
    n_teams: int,
    n_sims: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Simulate n_sims seasons and return (pts, gd, gf) each of shape (n_sims, n_teams).
    Uses matrix multiply to scatter fixture outcomes to team accumulators.
    """
    n_fix = len(lams)

    # Draw all goals at once: shape (n_sims, n_fix)
    hg = rng.poisson(lams, size=(n_sims, n_fix)).astype(np.float32)
    ag = rng.poisson(mus,  size=(n_sims, n_fix)).astype(np.float32)

    # One-hot fixture→team mappings: shape (n_fix, n_teams)
    home_oh = np.zeros((n_fix, n_teams), dtype=np.float32)
    away_oh = np.zeros((n_fix, n_teams), dtype=np.float32)
    home_oh[np.arange(n_fix), home_i] = 1.0
    away_oh[np.arange(n_fix), away_i] = 1.0

    # Points per fixture per sim
    home_pts = (hg > ag) * 3.0 + (hg == ag)   # (n_sims, n_fix)
    away_pts = (ag > hg) * 3.0 + (ag == hg)

    pts = home_pts @ home_oh + away_pts @ away_oh   # (n_sims, n_teams)
    gd  = (hg - ag) @ home_oh + (ag - hg) @ away_oh
    gf  = hg @ home_oh + ag @ away_oh

    return pts.astype(np.float64), gd.astype(np.float64), gf.astype(np.float64)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def simulate(
    model: DCModel,
    season: str,
    n_sims: int = N_SIMULATIONS,
    rng: np.random.Generator | None = None,
) -> SimulationResult:
    """
    Run n_sims Monte Carlo simulations of a Premier League season.

    Parameters
    ----------
    model   : Fitted DCModel with 20 teams.
    season  : Human-readable label, e.g. '2025-26'.
    n_sims  : Number of simulations (default 1 000).
    rng     : Optional generator for reproducibility.

    Returns
    -------
    SimulationResult with per-team statistics sorted by mean position.
    """
    if rng is None:
        rng = np.random.default_rng()

    teams = model.teams
    n_teams = len(teams)

    home_i, away_i = _make_fixture_arrays(teams)

    # Pre-compute expected goals for every fixture
    lams = np.array([model.alpha[teams[h]] * model.beta[teams[a]] * model.gamma
                     for h, a in zip(home_i, away_i)], dtype=np.float64)
    mus  = np.array([model.alpha[teams[a]] * model.beta[teams[h]]
                     for h, a in zip(home_i, away_i)], dtype=np.float64)

    pts, gd, gf = _run_simulations(lams, mus, home_i, away_i, n_teams, n_sims, rng)

    # Composite rank score — vectorised double-argsort gives position (1 = best)
    score = pts * 1e6 + gd * 1e3 + gf                             # (n_sims, n_teams)
    positions = np.argsort(np.argsort(-score, axis=1), axis=1) + 1  # (n_sims, n_teams)

    n_pl = n_teams
    stats: list[TeamStats] = []
    for t_idx, team in enumerate(teams):
        t_pts = pts[:, t_idx]
        t_pos = positions[:, t_idx]

        pos_dist: dict[int, float] = {}
        for p in range(1, n_pl + 1):
            f = float(np.mean(t_pos == p))
            if f > 0.0:
                pos_dist[p] = round(f, 4)

        stats.append(TeamStats(
            team=team,
            mean_points=round(float(np.mean(t_pts)), 2),
            std_points=round(float(np.std(t_pts)), 2),
            mean_position=round(float(np.mean(t_pos)), 2),
            title_probability=round(float(np.mean(t_pos == 1)), 4),
            top4_probability=round(float(np.mean(t_pos <= TOP4_CUTOFF)), 4),
            relegation_probability=round(float(np.mean(t_pos > n_pl - RELEGATION_SLOTS)), 4),
            position_distribution=pos_dist,
        ))

    stats.sort(key=lambda s: s.mean_position)

    logger.info(
        "Simulated %s: %d teams, %d sims. Top: %s (title %.1f%%)",
        season, n_teams, n_sims,
        stats[0].team if stats else "?",
        (stats[0].title_probability * 100) if stats else 0.0,
    )

    return SimulationResult(
        season=season,
        teams=[s.team for s in stats],
        stats=stats,
        n_simulations=n_sims,
    )
