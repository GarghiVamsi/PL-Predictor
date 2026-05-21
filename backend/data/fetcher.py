"""
Downloads all source data to backend/data/cache/:
  - Premier League match CSVs from football-data.co.uk (1993-94 → 2025-26)
  - FPL player_raw CSVs from vaastav/Fantasy-Premier-League (2016-17 → 2025-26)
"""

import logging
import sys
import time
from pathlib import Path

import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)

_MATCH_BASE = "https://www.football-data.co.uk/mmz4281"
_FPL_BASE = (
    "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"
)

# All 33 Premier League seasons from 1993-94 to 2025-26
MATCH_SEASONS: list[str] = [
    "9394", "9495", "9596", "9697", "9798", "9899",
    "9900", "0001", "0102", "0203", "0304", "0405",
    "0506", "0607", "0708", "0809", "0910", "1011",
    "1112", "1213", "1314", "1415", "1516", "1617",
    "1718", "1819", "1920", "2021", "2122", "2223",
    "2324", "2425", "2526",
]

# FPL repo only goes back to 2016-17
FPL_SEASONS: list[str] = [
    "2016-17", "2017-18", "2018-19", "2019-20", "2020-21",
    "2021-22", "2022-23", "2023-24", "2024-25", "2025-26",
]

_CRAWL_DELAY = 0.3  # seconds between requests — be polite


def season_code_to_label(code: str) -> str:
    """Convert a raw season code to a human-readable label.

    Examples: '9394' → '1993-94', '0506' → '2005-06', '2526' → '2025-26'
    """
    yy_start = int(code[:2])
    yy_end = int(code[2:])
    century_s = 1900 if yy_start >= 93 else 2000
    century_e = 1900 if yy_end >= 93 else 2000
    return f"{century_s + yy_start}-{str(century_e + yy_end)[2:]}"


def _get(url: str, timeout: int = 30) -> bytes | None:
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.content
    except requests.HTTPError as exc:
        logger.warning("HTTP %s — %s", exc.response.status_code, url)
    except requests.RequestException as exc:
        logger.error("Network error — %s: %s", url, exc)
    return None


def fetch_match_csv(code: str, cache_dir: Path, force: bool = False) -> Path | None:
    """Download one season's match CSV. Returns the cached path or None on failure."""
    dest = cache_dir / f"E0_{code}.csv"
    if dest.exists() and not force:
        return dest

    url = f"{_MATCH_BASE}/{code}/E0.csv"
    data = _get(url)
    if not data or len(data) < 200:  # sanity-check: real CSVs are several KB
        logger.warning("Empty or missing response for season code %s", code)
        return None

    dest.write_bytes(data)
    return dest


def fetch_fpl_csv(season: str, cache_dir: Path, force: bool = False) -> Path | None:
    """Download one FPL season's players_raw.csv. Returns the cached path or None."""
    safe = season.replace("-", "_")
    dest = cache_dir / f"fpl_{safe}.csv"
    if dest.exists() and not force:
        return dest

    url = f"{_FPL_BASE}/{season}/players_raw.csv"
    data = _get(url)
    if not data or len(data) < 200:
        logger.warning("Empty or missing FPL response for season %s", season)
        return None

    dest.write_bytes(data)
    return dest


def fetch_all(cache_dir: Path, force: bool = False) -> dict:
    """
    Download all match CSVs and FPL player files into cache_dir.

    Returns a summary dict with keys:
      match_csvs  — {season_label: Path}
      fpl_csvs    — {season_label: Path}
      errors      — list of failed identifiers
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    results: dict = {"match_csvs": {}, "fpl_csvs": {}, "errors": []}

    print("Fetching match CSVs from football-data.co.uk …")
    for code in tqdm(MATCH_SEASONS, unit="season"):
        label = season_code_to_label(code)
        path = fetch_match_csv(code, cache_dir, force)
        if path:
            results["match_csvs"][label] = path
        else:
            results["errors"].append(f"match:{label}")
        time.sleep(_CRAWL_DELAY)

    print("Fetching FPL player data from GitHub …")
    for season in tqdm(FPL_SEASONS, unit="season"):
        path = fetch_fpl_csv(season, cache_dir, force)
        if path:
            results["fpl_csvs"][season] = path
        else:
            results["errors"].append(f"fpl:{season}")
        time.sleep(_CRAWL_DELAY)

    n_m = len(results["match_csvs"])
    n_f = len(results["fpl_csvs"])
    n_e = len(results["errors"])
    print(f"\nComplete — {n_m} match seasons, {n_f} FPL seasons cached. {n_e} error(s).")
    if results["errors"]:
        print("Failed:", results["errors"])

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    cache = Path(__file__).parent / "cache"
    fetch_all(cache, force="--force" in sys.argv)
