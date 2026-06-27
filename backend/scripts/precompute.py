"""
Precompute script — runs the full prediction pipeline and writes predictions.json.

Usage:
    python -m backend.scripts.precompute [--output PATH] [--paths N] [--jobs N]

Output JSON structure:
    {
      "generated_at": "<ISO timestamp>",
      "historical": {
        "1993-94": {
          "table": [...],
          "top_scorers": [...]
        },
        ...
      },
      "predictions": {
        "2026-27": {
          "season": "...",
          "uncertainty_level": "...",
          "table": [...],
          "top_scorers": [...]
        },
        ...
      }
    }

Validation:
    - 33 seasons loaded (1993-94 → 2025-26)
    - Model fitted with convergence
    - 11 future season predictions cached
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Resolve package root so this script works as `python -m backend.scripts.precompute`
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
if str(_BACKEND.parent) not in sys.path:
    sys.path.insert(0, str(_BACKEND.parent))

from backend.data.fetcher import MATCH_SEASONS, season_code_to_label
from backend.data.loader import load_all_seasons, load_all_scorers
from backend.model.dixon_coles import fit as dc_fit, DCModel
from backend.model.compound_predictor import predict_all_seasons, FUTURE_SEASONS
from backend.model.promotion_relegation import PromotionPool
from backend.model.scorer_predictor import (
    top_scorers_for_season,
    project_future_scorers,
    ScorerEntry,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_CACHE_DIR = _BACKEND / "data" / "cache"
_SCORERS_JSON = _BACKEND / "data" / "historical_scorers.json"
_DEFAULT_OUTPUT = _CACHE_DIR / "predictions.json"


# ---------------------------------------------------------------------------
# Historical table computation
# ---------------------------------------------------------------------------

def _compute_season_table(df: pd.DataFrame, season: str) -> list[dict]:
    """Build the final league table for a single season from match results."""
    season_df = df[df["season"] == season]
    teams = sorted(set(season_df["HomeTeam"]) | set(season_df["AwayTeam"]))
    stats: dict[str, dict] = {
        t: {"team": t, "played": 0, "won": 0, "drawn": 0, "lost": 0,
            "gf": 0, "ga": 0, "gd": 0, "points": 0}
        for t in teams
    }
    for _, row in season_df.iterrows():
        ht, at = row["HomeTeam"], row["AwayTeam"]
        hg, ag = int(row["FTHG"]), int(row["FTAG"])
        for t in (ht, at):
            stats[t]["played"] += 1
        stats[ht]["gf"] += hg; stats[ht]["ga"] += ag
        stats[at]["gf"] += ag; stats[at]["ga"] += hg
        if hg > ag:
            stats[ht]["won"] += 1; stats[ht]["points"] += 3
            stats[at]["lost"] += 1
        elif hg < ag:
            stats[at]["won"] += 1; stats[at]["points"] += 3
            stats[ht]["lost"] += 1
        else:
            stats[ht]["drawn"] += 1; stats[ht]["points"] += 1
            stats[at]["drawn"] += 1; stats[at]["points"] += 1
    for t in teams:
        stats[t]["gd"] = stats[t]["gf"] - stats[t]["ga"]

    table = sorted(
        stats.values(),
        key=lambda r: (-r["points"], -r["gd"], -r["gf"]),
    )
    for pos, row in enumerate(table, start=1):
        row["position"] = pos
    return table


# ---------------------------------------------------------------------------
# Championship pool bootstrap
# ---------------------------------------------------------------------------

def _bootstrap_pool(df: pd.DataFrame) -> PromotionPool:
    """
    Determine who was relegated from 2025-26 (if data is complete) and seed
    the Championship pool accordingly.
    """
    last_season = "2025-26"
    season_df = df[df["season"] == last_season]

    if len(season_df) < 300:
        # Season data is incomplete — use default pool seeding
        logger.warning(
            "2025-26 match data has only %d rows — Championship pool uses default seed",
            len(season_df),
        )
        return PromotionPool.seed()

    table = _compute_season_table(df, last_season)
    relegated = [row["team"] for row in table[-3:]]
    logger.info("Relegated from 2025-26: %s", relegated)
    return PromotionPool.seed(relegated)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(
    output: Path = _DEFAULT_OUTPUT,
    n_paths: int = 1000,
    n_jobs: int = -1,
) -> None:
    logger.info("=== PL Predictor Precompute ===")

    # ------------------------------------------------------------------
    # 1. Load data
    # ------------------------------------------------------------------
    logger.info("Loading match data …")
    match_df = load_all_seasons(_CACHE_DIR)
    n_seasons_loaded = match_df["season"].nunique()
    logger.info("Loaded %d seasons, %d matches", n_seasons_loaded, len(match_df))

    if n_seasons_loaded < 32:
        logger.warning("Expected 32+ seasons, got %d. Run fetcher first.", n_seasons_loaded)

    all_scorers = load_all_scorers(_CACHE_DIR, _SCORERS_JSON)
    logger.info("Scorer data available for %d seasons", len(all_scorers))

    # ------------------------------------------------------------------
    # 2. Fit Dixon-Coles model on ALL historical data
    # ------------------------------------------------------------------
    logger.info("Fitting Dixon-Coles model …")
    reference_date = pd.Timestamp.now()
    model = dc_fit(match_df, reference_date=reference_date)
    logger.info(
        "Model fitted: %d teams, γ=%.3f, ρ=%.4f",
        len(model.teams), model.gamma, model.rho,
    )

    # ------------------------------------------------------------------
    # 2b. Filter model to the current 20 PL teams (2025-26 season)
    # ------------------------------------------------------------------
    current_teams = sorted(
        set(match_df[match_df["season"] == "2025-26"]["HomeTeam"])
        | set(match_df[match_df["season"] == "2025-26"]["AwayTeam"])
    )
    model = DCModel(
        teams=current_teams,
        alpha={t: model.alpha[t] for t in current_teams},
        beta={t: model.beta[t] for t in current_teams},
        gamma=model.gamma,
        rho=model.rho,
        n_matches=model.n_matches,
        reference_date=model.reference_date,
    )
    logger.info("Model filtered to %d current PL teams", len(current_teams))

    # ------------------------------------------------------------------
    # 3. Bootstrap Championship pool from 2025-26 relegation
    # ------------------------------------------------------------------
    pool = _bootstrap_pool(match_df)
    logger.info("Championship pool seeded: %s …", pool.teams[:5])

    # ------------------------------------------------------------------
    # 4. Historical tables + scorers
    # ------------------------------------------------------------------
    logger.info("Computing historical tables …")
    historical: dict[str, dict] = {}
    all_season_labels = sorted(match_df["season"].unique())

    for season in all_season_labels:
        table = _compute_season_table(match_df, season)
        scorers = [
            {"player": s.player, "goals": s.goals, "team": s.team, "source": s.source}
            for s in top_scorers_for_season(season, all_scorers)
        ]
        historical[season] = {"table": table, "top_scorers": scorers}

    # ------------------------------------------------------------------
    # 5. Compound prediction for 11 future seasons
    # ------------------------------------------------------------------
    logger.info("Running compound predictor (%d paths) …", n_paths)
    season_preds = predict_all_seasons(
        model=model,
        pool=pool,
        seasons=FUTURE_SEASONS,
        n_paths=n_paths,
        n_jobs=n_jobs,
    )
    logger.info("Compound prediction complete: %d seasons", len(season_preds))

    # ------------------------------------------------------------------
    # 6. Project top goalscorers for future seasons
    # ------------------------------------------------------------------
    base_scorers = top_scorers_for_season("2025-26", all_scorers, n=5)
    rng = np.random.default_rng(42)

    predictions: dict[str, dict] = {}
    base_year = 2026
    for pred in season_preds:
        year = int(pred.season[:4])
        years_ahead = year - base_year + 1
        proj_scorers = project_future_scorers(base_scorers, years_ahead, rng=rng)

        table = [
            {
                "position": i + 1,
                "team": s.team,
                "mean_points": s.mean_points,
                "std_points": s.std_points,
                "mean_position": s.mean_position,
                "title_probability": s.title_probability,
                "top4_probability": s.top4_probability,
                "relegation_probability": s.relegation_probability,
                "position_distribution": s.position_distribution,
            }
            for i, s in enumerate(pred.stats)
        ]
        scorers = [
            {"player": s.player, "goals": s.goals, "team": s.team, "source": s.source}
            for s in proj_scorers
        ]
        predictions[pred.season] = {
            "season": pred.season,
            "uncertainty_level": pred.uncertainty_level,
            "n_simulations": pred.n_simulations,
            "table": table,
            "top_scorers": scorers,
        }

    # ------------------------------------------------------------------
    # 7. Write output
    # ------------------------------------------------------------------
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "historical": historical,
        "predictions": predictions,
    }
    output.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    logger.info("Wrote predictions.json to %s", output)

    # ------------------------------------------------------------------
    # 8. Validate
    # ------------------------------------------------------------------
    n_hist = len(historical)
    n_pred = len(predictions)
    logger.info("Validation: %d historical seasons, %d predicted seasons", n_hist, n_pred)
    assert n_hist >= 32, f"Expected ≥32 historical seasons, got {n_hist}"
    assert n_pred == 11, f"Expected 11 predicted seasons, got {n_pred}"
    logger.info("✓ Validation passed")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Precompute PL Predictor predictions")
    p.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT, help="Output JSON path")
    p.add_argument("--paths", type=int, default=1000, help="Number of simulation paths")
    p.add_argument("--jobs", type=int, default=-1, help="Joblib n_jobs (-1 = all cores)")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(output=args.output, n_paths=args.paths, n_jobs=args.jobs)
