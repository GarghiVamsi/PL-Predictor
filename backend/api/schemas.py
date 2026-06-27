"""Pydantic response models for all API endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

class ScorerOut(BaseModel):
    player: str
    goals: int
    team: str
    source: str


class HistoricalRow(BaseModel):
    position: int
    team: str
    played: int
    won: int
    drawn: int
    lost: int
    gf: int
    ga: int
    gd: int
    points: int


class PredictionRow(BaseModel):
    position: int
    team: str
    mean_points: float
    std_points: float
    mean_position: float
    title_probability: float
    top4_probability: float
    relegation_probability: float
    position_distribution: dict[int, float]


# ---------------------------------------------------------------------------
# Historical endpoints
# ---------------------------------------------------------------------------

class SeasonListResponse(BaseModel):
    seasons: list[str]


class HistoricalSeasonResponse(BaseModel):
    season: str
    table: list[HistoricalRow]
    top_scorers: list[ScorerOut]


class AllHistoricalScorersResponse(BaseModel):
    scorers: dict[str, list[ScorerOut]]   # season → scorers


# ---------------------------------------------------------------------------
# Prediction endpoints
# ---------------------------------------------------------------------------

class PredictionSummary(BaseModel):
    """Lightweight summary used in the list-all endpoint."""
    season: str
    uncertainty_level: str
    n_simulations: int
    champion: str        # team with highest title_probability
    champion_odds: float


class AllPredictionsResponse(BaseModel):
    predictions: list[PredictionSummary]


class PredictionSeasonResponse(BaseModel):
    season: str
    uncertainty_level: str
    n_simulations: int
    table: list[PredictionRow]
    top_scorers: list[ScorerOut]


class AllPredictedScorersResponse(BaseModel):
    scorers: dict[str, list[ScorerOut]]   # season → scorers


class RefreshResponse(BaseModel):
    status: str
    message: str
