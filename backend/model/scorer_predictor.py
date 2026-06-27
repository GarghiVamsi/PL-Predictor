"""
Top-goalscorer projections for future seasons.

Historical seasons (1993-94 → 2025-26): returns actual data from FPL or curated JSON.
Future seasons (2026-27 → 2036-37): projects forward from the most recent season,
applying mild goal-count decay and growing uncertainty with each season.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

_DECAY_RATE: float = 0.03          # ~3% goal decay per season
_NOISE_SIGMA: float = 3.0          # Gaussian noise std (goals) for projections
_MAX_PROJECTED: int = 5            # number of projected top scorers to return
_FLOOR_GOALS: int = 5              # minimum plausible projected goals


@dataclass
class ScorerEntry:
    player: str
    goals: int
    team: str
    source: str   # "curated" | "fpl" | "projected"


def top_scorers_for_season(
    season: str,
    all_scorers: dict[str, list[dict]],
    n: int = 10,
) -> list[ScorerEntry]:
    """Return the top n scorers for a historical season from cached data."""
    records = all_scorers.get(season, [])
    sorted_records = sorted(records, key=lambda r: r.get("goals", 0), reverse=True)
    return [
        ScorerEntry(
            player=r.get("player", "Unknown"),
            goals=int(r.get("goals", 0)),
            team=r.get("team", ""),
            source=r.get("source", "unknown"),
        )
        for r in sorted_records[:n]
    ]


def project_future_scorers(
    base_season_scorers: list[ScorerEntry],
    years_ahead: int,
    rng: np.random.Generator | None = None,
    n: int = _MAX_PROJECTED,
) -> list[ScorerEntry]:
    """
    Project top scorers for a future season.

    Takes the top scorers from the base season and applies:
      - Exponential decay: goals × (1 - decay_rate)^years_ahead
      - Gaussian noise scaled by sqrt(years_ahead)

    Returns a list sorted by projected goals descending.
    """
    if rng is None:
        rng = np.random.default_rng()

    projected: list[ScorerEntry] = []
    for entry in base_season_scorers[:n]:
        decay = (1.0 - _DECAY_RATE) ** years_ahead
        noise_std = _NOISE_SIGMA * math.sqrt(years_ahead)
        raw = entry.goals * decay + rng.normal(0.0, noise_std)
        goals = max(int(round(raw)), _FLOOR_GOALS)
        projected.append(ScorerEntry(
            player=entry.player,
            goals=goals,
            team=entry.team,
            source="projected",
        ))

    projected.sort(key=lambda e: e.goals, reverse=True)
    return projected
