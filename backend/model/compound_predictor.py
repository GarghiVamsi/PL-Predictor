"""
11-season compound predictor.

Runs N_PATHS independent Monte Carlo paths, each covering 2026-27 through
2036-37.  Within each path:

  1. Simulate the season (one Poisson draw per fixture).
  2. Relegate the bottom 3 teams; promote 3 from the Championship pool.
  3. Shrink all team parameters 5 % toward the league mean.
  4. From path-season 5 onward, add ±10 % multiplicative noise per team.

After all paths finish, aggregate across paths per season to produce
per-team statistics (title / top-4 / relegation probabilities, mean points,
position distribution).

Parallelised over paths with joblib.Parallel(n_jobs=-1).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
from joblib import Parallel, delayed

from .dixon_coles import DCModel
from .promotion_relegation import (
    PromotionPool,
    RELEGATED_PER_SEASON,
    PROMOTED_PER_SEASON,
    assign_promoted_ratings,
)
from .simulator import TeamStats, N_SIMULATIONS

logger = logging.getLogger(__name__)

FUTURE_SEASONS: list[str] = [
    "2026-27", "2027-28", "2028-29", "2029-30", "2030-31",
    "2031-32", "2032-33", "2033-34", "2034-35", "2035-36", "2036-37",
]

_SHRINK_RATE: float = 0.05    # shrink parameters 5 % toward mean each season
_NOISE_FROM: int = 4          # 0-indexed season index at which noise starts (season 5)
_NOISE_FACTOR: float = 0.10   # ±10 % multiplicative noise
_TOP4: int = 4
_REL_SLOTS: int = 3

_UNCERTAINTY_MAP: list[str] = [
    "low",       # 2026-27 (index 0)
    "low",       # 2027-28
    "medium",    # 2028-29
    "medium",    # 2029-30
    "high",      # 2030-31
    "high",      # 2031-32
    "high",      # 2032-33
    "very_high", # 2033-34
    "very_high", # 2034-35
    "very_high", # 2035-36
    "very_high", # 2036-37
]


@dataclass
class SeasonPrediction:
    season: str
    uncertainty_level: str
    teams: list[str]         # ordered by mean_position ascending
    stats: list[TeamStats]   # parallel to teams
    n_simulations: int


# ---------------------------------------------------------------------------
# Single-path helpers
# ---------------------------------------------------------------------------

def _sim_one_season(
    alpha: dict[str, float],
    beta: dict[str, float],
    gamma: float,
    rng: np.random.Generator,
) -> tuple[list[str], np.ndarray, np.ndarray]:
    """
    Simulate a single season (one Poisson draw per fixture).

    Returns (ordered_teams, points_array, gd_array) with teams sorted by
    (points desc, gd desc).
    """
    teams = sorted(alpha.keys())
    n = len(teams)
    tidx = {t: i for i, t in enumerate(teams)}

    home_i = np.array([i for i in range(n) for j in range(n) if i != j], dtype=np.int32)
    away_i = np.array([j for i in range(n) for j in range(n) if i != j], dtype=np.int32)
    n_fix = len(home_i)

    lams = np.array([alpha[teams[h]] * beta[teams[a]] * gamma for h, a in zip(home_i, away_i)])
    mus  = np.array([alpha[teams[a]] * beta[teams[h]] for h, a in zip(home_i, away_i)])

    hg = rng.poisson(lams).astype(np.float32)
    ag = rng.poisson(mus).astype(np.float32)

    home_oh = np.zeros((n_fix, n), dtype=np.float32)
    away_oh = np.zeros((n_fix, n), dtype=np.float32)
    home_oh[np.arange(n_fix), home_i] = 1.0
    away_oh[np.arange(n_fix), away_i] = 1.0

    pts = ((hg > ag) * 3.0 + (hg == ag)) @ home_oh + ((ag > hg) * 3.0 + (ag == hg)) @ away_oh
    gd  = (hg - ag) @ home_oh + (ag - hg) @ away_oh

    score = pts * 1e4 + gd
    order = np.argsort(-score)
    return [teams[i] for i in order], pts, gd


def _run_path(
    base_alpha: dict[str, float],
    base_beta: dict[str, float],
    gamma: float,
    rho: float,
    pool_teams: list[str],
    seasons: list[str],
    seed: int,
) -> list[dict]:
    """
    Run one independent compound simulation path.

    Returns a list of dicts (one per season) with:
      season, positions {team: rank}, points {team: float}
    """
    rng = np.random.default_rng(seed)

    alpha = dict(base_alpha)
    beta  = dict(base_beta)
    pool  = PromotionPool()
    pool.teams = list(pool_teams)

    path_results: list[dict] = []

    for s_idx, season in enumerate(seasons):
        ranked, pts_arr, _ = _sim_one_season(alpha, beta, gamma, rng)
        n_in = len(ranked)

        pts_by_team = {ranked[i]: float(pts_arr[i]) if i < len(pts_arr) else 0.0
                       for i in range(n_in)}
        # pts_arr is not aligned with ranked — recompute alignment
        # ranked is sorted by score; pts_arr is in original team order
        # we need pts for each ranked team
        teams_orig = sorted(alpha.keys())
        tidx = {t: i for i, t in enumerate(teams_orig)}
        pts_by_team = {t: float(pts_arr[tidx[t]]) for t in teams_orig}

        positions = {t: pos + 1 for pos, t in enumerate(ranked)}

        path_results.append({
            "season": season,
            "positions": positions,
            "points": pts_by_team,
        })

        # Relegate bottom 3
        relegated = ranked[-RELEGATED_PER_SEASON:]
        pool.relegate(relegated)
        for t in relegated:
            alpha.pop(t, None)
            beta.pop(t, None)

        # Promote 3 from pool
        promoted = pool.promote(PROMOTED_PER_SEASON)
        a_up, b_up = assign_promoted_ratings(promoted, alpha, beta)
        alpha.update(a_up)
        beta.update(b_up)

        # Shrink parameters toward league mean
        mean_a = float(np.mean(list(alpha.values())))
        mean_b = float(np.mean(list(beta.values())))
        for t in list(alpha):
            alpha[t] += _SHRINK_RATE * (mean_a - alpha[t])
            beta[t]  += _SHRINK_RATE * (mean_b - beta[t])

        # Add noise from season 5 onward
        if s_idx >= _NOISE_FROM:
            for t in list(alpha):
                alpha[t] *= float(rng.uniform(1.0 - _NOISE_FACTOR, 1.0 + _NOISE_FACTOR))
                beta[t]  *= float(rng.uniform(1.0 - _NOISE_FACTOR, 1.0 + _NOISE_FACTOR))

    return path_results


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _aggregate(
    all_paths: list[list[dict]],
    seasons: list[str],
    n_paths: int,
) -> list[SeasonPrediction]:
    """Aggregate N paths into SeasonPrediction objects (one per season)."""
    season_predictions: list[SeasonPrediction] = []

    for s_idx, season in enumerate(seasons):
        # Collect all teams seen in at least one path for this season
        team_positions: dict[str, list[int]] = {}
        team_points: dict[str, list[float]] = {}

        for path in all_paths:
            entry = path[s_idx]
            for team, pos in entry["positions"].items():
                team_positions.setdefault(team, []).append(pos)
                team_points.setdefault(team, []).append(entry["points"].get(team, 0.0))

        stats: list[TeamStats] = []
        n_pl = 20  # league size

        for team, positions in team_positions.items():
            pos_arr = np.array(positions)
            pts_arr = np.array(team_points[team])

            pos_dist: dict[int, float] = {}
            for p in range(1, n_pl + 1):
                f = float(np.mean(pos_arr == p))
                if f > 0.0:
                    pos_dist[p] = round(f, 4)

            stats.append(TeamStats(
                team=team,
                mean_points=round(float(np.mean(pts_arr)), 2),
                std_points=round(float(np.std(pts_arr)), 2),
                mean_position=round(float(np.mean(pos_arr)), 2),
                title_probability=round(float(np.mean(pos_arr == 1)), 4),
                top4_probability=round(float(np.mean(pos_arr <= _TOP4)), 4),
                relegation_probability=round(float(np.mean(pos_arr > n_pl - _REL_SLOTS)), 4),
                position_distribution=pos_dist,
            ))

        # Sort by mean_position; teams appearing in more paths rank higher when tied
        stats.sort(key=lambda s: (s.mean_position, -len(team_positions[s.team])))

        # Keep top 20 (most frequently in-league teams)
        freq_sorted = sorted(
            stats,
            key=lambda s: (-len(team_positions[s.team]), s.mean_position),
        )
        top20 = freq_sorted[:20]
        top20.sort(key=lambda s: s.mean_position)

        season_predictions.append(SeasonPrediction(
            season=season,
            uncertainty_level=_UNCERTAINTY_MAP[s_idx],
            teams=[s.team for s in top20],
            stats=top20,
            n_simulations=n_paths,
        ))

    return season_predictions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def predict_all_seasons(
    model: DCModel,
    pool: PromotionPool,
    seasons: list[str] = FUTURE_SEASONS,
    n_paths: int = N_SIMULATIONS,
    n_jobs: int = -1,
) -> list[SeasonPrediction]:
    """
    Run n_paths independent compound simulation paths and return predictions
    for each of the 11 future seasons.

    Parameters
    ----------
    model   : Fitted DCModel (used as the base for season 2026-27).
    pool    : Initial Championship pool.
    seasons : List of season labels to predict (default: FUTURE_SEASONS).
    n_paths : Number of independent simulation paths (default 1 000).
    n_jobs  : Joblib parallelism (-1 = all cores).

    Returns
    -------
    List of SeasonPrediction objects, one per season.
    """
    logger.info("Starting compound prediction: %d paths × %d seasons", n_paths, len(seasons))

    all_paths: list[list[dict]] = Parallel(n_jobs=n_jobs, prefer="threads")(
        delayed(_run_path)(
            model.alpha,
            model.beta,
            model.gamma,
            model.rho,
            pool.teams,
            seasons,
            seed,
        )
        for seed in range(n_paths)
    )

    logger.info("All paths complete — aggregating")
    return _aggregate(all_paths, seasons, n_paths)
