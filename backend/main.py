"""
FastAPI application for PL Predictor.

Startup: loads predictions.json from cache into app.state.cache so every
request is served from memory with < 10 ms latency.

CORS is enabled for http://localhost:3000 (Next.js dev server).
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.historical import router as historical_router
from backend.api.routes.predictions import router as predictions_router

logger = logging.getLogger(__name__)

_CACHE_PATH = Path(__file__).parent / "data" / "cache" / "predictions.json"


def _load_cache() -> dict:
    if not _CACHE_PATH.exists():
        logger.warning(
            "predictions.json not found at %s — run `python -m backend.scripts.precompute` first",
            _CACHE_PATH,
        )
        return {"historical": {}, "predictions": {}, "generated_at": None}
    data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    n_hist = len(data.get("historical", {}))
    n_pred = len(data.get("predictions", {}))
    logger.info("Cache loaded: %d historical seasons, %d predictions", n_hist, n_pred)
    return data


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.cache = _load_cache()
    yield


app = FastAPI(
    title="PL Predictor API",
    description="Premier League table and goalscorer predictions via Dixon-Coles + Monte Carlo",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(historical_router)
app.include_router(predictions_router)


@app.get("/", tags=["health"])
def health() -> dict:
    cache = app.state.cache
    return {
        "status": "ok",
        "generated_at": cache.get("generated_at"),
        "historical_seasons": len(cache.get("historical", {})),
        "predicted_seasons": len(cache.get("predictions", {})),
    }
