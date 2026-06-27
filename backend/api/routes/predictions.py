"""Routes for /api/predictions/*"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from ..schemas import (
    AllPredictedScorersResponse,
    AllPredictionsResponse,
    PredictionRow,
    PredictionSeasonResponse,
    PredictionSummary,
    RefreshResponse,
    ScorerOut,
)

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


def _cache(request: Request) -> dict:
    return request.app.state.cache


def _to_row(entry: dict, position: int) -> PredictionRow:
    return PredictionRow(
        position=position,
        team=entry["team"],
        mean_points=entry["mean_points"],
        std_points=entry["std_points"],
        mean_position=entry["mean_position"],
        title_probability=entry["title_probability"],
        top4_probability=entry["top4_probability"],
        relegation_probability=entry["relegation_probability"],
        position_distribution=entry.get("position_distribution", {}),
    )


@router.get("", response_model=AllPredictionsResponse)
def list_predictions(request: Request) -> AllPredictionsResponse:
    cache = _cache(request)
    summaries: list[PredictionSummary] = []
    for season, data in sorted(cache["predictions"].items()):
        table = data["table"]
        if table:
            champ_entry = max(table, key=lambda r: r["title_probability"])
            champ = champ_entry["team"]
            odds = champ_entry["title_probability"]
        else:
            champ, odds = "Unknown", 0.0
        summaries.append(PredictionSummary(
            season=season,
            uncertainty_level=data["uncertainty_level"],
            n_simulations=data.get("n_simulations", 1000),
            champion=champ,
            champion_odds=odds,
        ))
    return AllPredictionsResponse(predictions=summaries)


@router.get("/scorers", response_model=AllPredictedScorersResponse)
def predicted_scorers(request: Request) -> AllPredictedScorersResponse:
    cache = _cache(request)
    out: dict[str, list[ScorerOut]] = {}
    for season, data in cache["predictions"].items():
        out[season] = [ScorerOut(**s) for s in data["top_scorers"]]
    return AllPredictedScorersResponse(scorers=out)


@router.get("/{season}", response_model=PredictionSeasonResponse)
def get_prediction(season: str, request: Request) -> PredictionSeasonResponse:
    cache = _cache(request)
    data = cache["predictions"].get(season)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Prediction for '{season}' not found")
    return PredictionSeasonResponse(
        season=season,
        uncertainty_level=data["uncertainty_level"],
        n_simulations=data.get("n_simulations", 1000),
        table=[_to_row(r, r["position"]) for r in data["table"]],
        top_scorers=[ScorerOut(**s) for s in data["top_scorers"]],
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh(background_tasks: BackgroundTasks, request: Request) -> RefreshResponse:
    """Trigger a background re-run of the precompute pipeline."""
    import subprocess, sys
    from pathlib import Path

    cache = _cache(request)

    def _run() -> None:
        subprocess.run(
            [sys.executable, "-m", "backend.scripts.precompute"],
            cwd=Path(__file__).resolve().parents[3],
            check=False,
        )
        # Reload cache in-place
        import json
        predictions_path = Path(__file__).resolve().parents[3] / "backend" / "data" / "cache" / "predictions.json"
        if predictions_path.exists():
            new_cache = json.loads(predictions_path.read_text(encoding="utf-8"))
            cache.clear()
            cache.update(new_cache)

    background_tasks.add_task(_run)
    return RefreshResponse(status="accepted", message="Precompute pipeline triggered in background")
