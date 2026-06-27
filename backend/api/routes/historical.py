"""Routes for /api/historical/*"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..schemas import (
    AllHistoricalScorersResponse,
    HistoricalSeasonResponse,
    HistoricalRow,
    SeasonListResponse,
    ScorerOut,
)

router = APIRouter(prefix="/api/historical", tags=["historical"])


def _cache(request: Request) -> dict:
    return request.app.state.cache


@router.get("/seasons", response_model=SeasonListResponse)
def list_seasons(request: Request) -> SeasonListResponse:
    cache = _cache(request)
    return SeasonListResponse(seasons=sorted(cache["historical"].keys()))


@router.get("/scorers", response_model=AllHistoricalScorersResponse)
def all_scorers(request: Request) -> AllHistoricalScorersResponse:
    cache = _cache(request)
    out: dict[str, list[ScorerOut]] = {}
    for season, data in cache["historical"].items():
        out[season] = [ScorerOut(**s) for s in data["top_scorers"]]
    return AllHistoricalScorersResponse(scorers=out)


@router.get("/{season}", response_model=HistoricalSeasonResponse)
def get_season(season: str, request: Request) -> HistoricalSeasonResponse:
    cache = _cache(request)
    data = cache["historical"].get(season)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Season '{season}' not found")
    return HistoricalSeasonResponse(
        season=season,
        table=[HistoricalRow(**row) for row in data["table"]],
        top_scorers=[ScorerOut(**s) for s in data["top_scorers"]],
    )
