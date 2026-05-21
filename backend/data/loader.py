"""
Parses cached CSVs and the curated scorer JSON into clean DataFrames / dicts
consumed by the model layer.

Public API:
  load_all_seasons(cache_dir)     → pd.DataFrame  (all match results)
  load_all_scorers(cache_dir, json_path) → dict[season_label, list[scorer_dict]]
"""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from .fetcher import FPL_SEASONS, MATCH_SEASONS, season_code_to_label

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Team-name normalisation
# Canonical names are the ones we use throughout the model and UI.
# football-data.co.uk uses slightly different spellings across seasons.
# ---------------------------------------------------------------------------
TEAM_NAME_MAP: dict[str, str] = {
    # Manchester
    "Man United": "Manchester United",
    "Man Utd": "Manchester United",
    "Man City": "Manchester City",
    # Tottenham
    "Tottenham Hotspur": "Tottenham",
    "Spurs": "Tottenham",
    # Wolverhampton
    "Wolves": "Wolverhampton",
    "Wolverhampton Wanderers": "Wolverhampton",
    # West Ham
    "West Ham United": "West Ham",
    # Nottingham Forest
    "Nott'm Forest": "Nottingham Forest",
    # Sheffield
    "Sheffield Weds": "Sheffield Wednesday",
    # Leeds
    "Leeds United": "Leeds",
    # Newcastle
    "Newcastle United": "Newcastle",
    # Blackburn
    "Blackburn Rovers": "Blackburn",
    # Charlton
    "Charlton Ath": "Charlton",
    # Bournemouth
    "AFC Bournemouth": "Bournemouth",
    # Derby
    "Derby Co": "Derby County",
    # West Brom
    "West Bromwich Albion": "West Brom",
    # Ipswich
    "Ipswich Town": "Ipswich",
    # QPR
    "Queens Park Rangers": "QPR",
    # Middlesbrough
    "Middlesbro": "Middlesbrough",
    # Bradford
    "Bradford City": "Bradford",
    # Swindon
    "Swindon Town": "Swindon",
    # Oldham
    "Oldham Ath": "Oldham",
    "Oldham Athletic": "Oldham",
    # Coventry
    "Coventry City": "Coventry",
    # Birmingham
    "Birmingham City": "Birmingham",
    # Hull
    "Hull City": "Hull",
    # Swansea
    "Swansea City": "Swansea",
    # Brighton
    "Brighton & Hove Albion": "Brighton",
    # Luton
    "Luton Town": "Luton",
    # Stoke
    "Stoke City": "Stoke",
    # Wigan
    "Wigan Athletic": "Wigan",
    # Bolton
    "Bolton Wanderers": "Bolton",
    # Norwich
    "Norwich City": "Norwich",
    # Huddersfield
    "Huddersfield Town": "Huddersfield",
    # Cardiff
    "Cardiff City": "Cardiff",
    # Leicester — football-data uses both forms across eras
    "Leicester": "Leicester City",
}

_REQUIRED_COLS = {"HomeTeam", "AwayTeam", "FTHG", "FTAG"}
_OPTIONAL_COLS = {"Date", "Referee", "HS", "AS", "HST", "AST"}  # kept when present


def normalize_team(name: str) -> str:
    if not isinstance(name, str):
        return name
    return TEAM_NAME_MAP.get(name.strip(), name.strip())


# ---------------------------------------------------------------------------
# Match data
# ---------------------------------------------------------------------------

def _load_season_csv(csv_path: Path, season: str) -> pd.DataFrame | None:
    try:
        df = pd.read_csv(csv_path, encoding="latin-1", low_memory=False, on_bad_lines="skip")
    except Exception as exc:
        logger.error("Cannot read %s: %s", csv_path, exc)
        return None

    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        logger.warning("Season %s missing columns %s — skipped", season, missing)
        return None

    keep = list(_REQUIRED_COLS) + [c for c in _OPTIONAL_COLS if c in df.columns]
    df = df[keep].copy()
    df = df.dropna(subset=list(_REQUIRED_COLS))

    df["FTHG"] = df["FTHG"].astype(int)
    df["FTAG"] = df["FTAG"].astype(int)
    df["HomeTeam"] = df["HomeTeam"].map(normalize_team)
    df["AwayTeam"] = df["AwayTeam"].map(normalize_team)
    df["season"] = season

    df["result"] = np.where(
        df["FTHG"] > df["FTAG"], "H",
        np.where(df["FTHG"] < df["FTAG"], "A", "D"),
    )

    return df


def load_all_seasons(cache_dir: Path) -> pd.DataFrame:
    """
    Load every available match CSV from cache_dir into one DataFrame.

    Columns: HomeTeam, AwayTeam, FTHG, FTAG, season, result
             (+ Date, HS, AS, HST, AST when present in source CSV)
    """
    frames: list[pd.DataFrame] = []
    missing_seasons: list[str] = []

    for code in MATCH_SEASONS:
        label = season_code_to_label(code)
        path = cache_dir / f"E0_{code}.csv"
        if not path.exists():
            missing_seasons.append(label)
            continue
        df = _load_season_csv(path, label)
        if df is not None:
            frames.append(df)

    if missing_seasons:
        logger.warning(
            "%d season(s) not found in cache (run fetcher): %s",
            len(missing_seasons),
            missing_seasons,
        )

    if not frames:
        raise RuntimeError(
            "No match data loaded. Run `python -m backend.data.fetcher` first."
        )

    combined = pd.concat(frames, ignore_index=True)
    logger.info(
        "Loaded %d matches across %d seasons", len(combined), len(frames)
    )
    return combined


# ---------------------------------------------------------------------------
# Scorer data
# ---------------------------------------------------------------------------

def _load_fpl_scorers(cache_dir: Path, season: str) -> list[dict]:
    """Return top-10 scorers for a single FPL season (from players_raw.csv)."""
    safe = season.replace("-", "_")
    path = cache_dir / f"fpl_{safe}.csv"
    if not path.exists():
        return []

    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        logger.error("Cannot read FPL CSV for %s: %s", season, exc)
        return []

    if "goals_scored" not in df.columns:
        logger.warning("FPL CSV for %s has no goals_scored column", season)
        return []

    # Build display name from first_name + second_name when available
    if {"first_name", "second_name"}.issubset(df.columns):
        df["player"] = (df["first_name"] + " " + df["second_name"]).str.strip()
    elif "web_name" in df.columns:
        df["player"] = df["web_name"]
    else:
        return []

    top = (
        df[["player", "goals_scored"]]
        .sort_values("goals_scored", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )

    return [
        {
            "season": season,
            "player": row["player"],
            "goals": int(row["goals_scored"]),
            "source": "fpl",
        }
        for _, row in top.iterrows()
        if int(row["goals_scored"]) > 0
    ]


def load_historical_scorers(json_path: Path) -> list[dict]:
    """Load curated 1993-94 → 2015-16 scorer records from JSON."""
    if not json_path.exists():
        logger.warning("historical_scorers.json not found at %s", json_path)
        return []

    with json_path.open(encoding="utf-8") as fh:
        data: dict[str, list[dict]] = json.load(fh)

    records: list[dict] = []
    for season, scorers in data.items():
        for entry in scorers:
            records.append({**entry, "season": season, "source": "curated"})
    return records


def load_all_scorers(cache_dir: Path, json_path: Path) -> dict[str, list[dict]]:
    """
    Merge curated historical data (1993-94 → 2015-16) with FPL data
    (2016-17 → 2025-26).

    Returns a dict keyed by season label, e.g. '1993-94', '2023-24'.
    Each value is a list of scorer dicts with keys:
      season, player, team (may be absent in FPL data), goals, source
    """
    by_season: dict[str, list[dict]] = {}

    for record in load_historical_scorers(json_path):
        by_season.setdefault(record["season"], []).append(record)

    for season in FPL_SEASONS:
        fpl_records = _load_fpl_scorers(cache_dir, season)
        if fpl_records:
            by_season[season] = fpl_records

    return by_season
