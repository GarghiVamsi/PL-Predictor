"""
Promotion, relegation, and Championship pool management.

Rules:
  - Bottom 3 Premier League teams are relegated each season.
  - 3 teams are promoted from the Championship (2 automatic + 1 play-off).
  - Promoted teams receive league-average parameters × ATTACK_FACTOR / DEFENCE_FACTOR.
  - Pool is seeded from recently relegated sides + a curated list of Championship clubs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

ATTACK_FACTOR: float = 0.90    # promoted teams are weaker in attack
DEFENCE_FACTOR: float = 1.10   # promoted teams concede more (higher β = weaker defence)
RELEGATED_PER_SEASON: int = 3
PROMOTED_PER_SEASON: int = 3

# Clubs likely to be in the Championship pool for 2026-27 onwards
_CHAMPIONSHIP_SEED: list[str] = [
    "Burnley", "Southampton", "Leicester City",
    "Sunderland", "Leeds", "Sheffield United",
    "Middlesbrough", "Millwall", "Watford",
    "Coventry", "Stoke", "QPR",
    "West Brom", "Norwich", "Swansea",
    "Bristol City", "Preston", "Cardiff",
    "Hull", "Derby County",
]


@dataclass
class PromotionPool:
    """Ordered list of Championship clubs available for promotion."""

    teams: list[str] = field(default_factory=list)

    @classmethod
    def seed(cls, relegated: list[str] | None = None) -> "PromotionPool":
        """
        Construct the initial pool.

        Starts with the curated seed list and prepends any recently relegated
        teams (who are more likely to bounce straight back up).
        """
        pool = cls()
        seed = list(_CHAMPIONSHIP_SEED)
        if relegated:
            for t in relegated:
                if t not in seed:
                    seed.insert(0, t)
        pool.teams = seed
        return pool

    def relegate(self, teams: list[str]) -> None:
        """Add relegated teams to the front of the pool."""
        for t in reversed(teams):
            if t in self.teams:
                self.teams.remove(t)
            self.teams.insert(0, t)

    def promote(self, n: int = PROMOTED_PER_SEASON) -> list[str]:
        """Remove and return the first n teams from the pool."""
        n = min(n, len(self.teams))
        promoted, self.teams = self.teams[:n], self.teams[n:]
        return promoted

    def copy(self) -> "PromotionPool":
        new = PromotionPool()
        new.teams = list(self.teams)
        return new


def assign_promoted_ratings(
    promoted: list[str],
    current_alpha: dict[str, float],
    current_beta: dict[str, float],
) -> tuple[dict[str, float], dict[str, float]]:
    """
    Return alpha and beta updates for the promoted teams.

    Uses the mean of the current PL clubs, not including the promoted teams,
    scaled by ATTACK_FACTOR and DEFENCE_FACTOR.
    """
    mean_a = float(np.mean(list(current_alpha.values()))) if current_alpha else 1.0
    mean_b = float(np.mean(list(current_beta.values()))) if current_beta else 1.0
    alpha_up = {t: mean_a * ATTACK_FACTOR  for t in promoted}
    beta_up  = {t: mean_b * DEFENCE_FACTOR for t in promoted}
    return alpha_up, beta_up
