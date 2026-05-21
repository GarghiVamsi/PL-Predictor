# PL Predictor

A full-stack web application that uses 32 seasons of Premier League match data (1993–94 to 2025–26) to statistically predict league tables and top goalscorers for the 2026–27 through 2036–37 seasons.

---

## Overview

PL Predictor applies a Dixon-Coles Poisson model to historical match results, running 1,000 Monte Carlo simulations per season to generate per-team probabilities for winning the title, finishing top 4, and relegation. Predictions are chained across 11 future seasons with compounding uncertainty, promotion/relegation logic, and goalscorer projections.

The frontend is built with Next.js 15, shadcn/ui, Tailwind CSS, and Framer Motion for a dark, animated football aesthetic.

---

## Architecture

```
PL-Predictor/
├── backend/
│   ├── main.py                          # FastAPI app with lifespan startup
│   ├── requirements.txt
│   ├── data/
│   │   ├── fetcher.py                   # Downloads football-data.co.uk CSVs
│   │   ├── loader.py                    # Parses CSVs, normalises team names
│   │   ├── historical_scorers.json      # Curated top-scorer data 1993–2016
│   │   └── cache/                       # Downloaded CSVs + predictions.json
│   ├── model/
│   │   ├── dixon_coles.py               # Dixon-Coles parameter estimation
│   │   ├── simulator.py                 # 1000× Poisson season simulation
│   │   ├── scorer_predictor.py          # Top goalscorer projections
│   │   ├── promotion_relegation.py      # Team pool management
│   │   └── compound_predictor.py        # 11-season chained predictions
│   ├── api/
│   │   ├── schemas.py                   # Pydantic response models
│   │   └── routes/
│   │       ├── historical.py            # /api/historical/* endpoints
│   │       └── predictions.py           # /api/predictions/* endpoints
│   └── scripts/
│       └── precompute.py                # CLI: run full prediction pipeline
└── frontend/
    ├── package.json
    ├── next.config.ts
    ├── tailwind.config.ts
    ├── components.json                  # shadcn/ui config
    └── src/
        ├── app/
        │   ├── layout.tsx               # Root layout, dark theme
        │   ├── page.tsx                 # Landing / hero
        │   ├── historical/page.tsx      # Historical season browser
        │   └── predictions/
        │       ├── page.tsx             # All 11 seasons (tabbed)
        │       └── [season]/page.tsx    # Deep-link per season
        ├── components/
        │   ├── ui/                      # shadcn/ui generated components
        │   ├── league-table/
        │   │   ├── LeagueTable.tsx
        │   │   ├── LeagueTableRow.tsx
        │   │   └── ProbabilityBar.tsx
        │   ├── charts/
        │   │   ├── TopScorerBarChart.tsx
        │   │   ├── TitleOddsRadar.tsx
        │   │   └── SeasonTrendLine.tsx
        │   ├── season/
        │   │   ├── SeasonSelector.tsx
        │   │   ├── SeasonHero.tsx
        │   │   └── UncertaintyBadge.tsx
        │   └── hero/
        │       ├── HeroSection.tsx
        │       └── StatCounter.tsx
        └── lib/
            ├── api.ts
            ├── types.ts
            └── utils.ts
```

---

## Data Sources

| Source | Usage |
|--------|-------|
| [football-data.co.uk](https://www.football-data.co.uk/mmz4281/{SEASON}/E0.csv) | Match results for all 32 seasons (1993–94 → 2025–26) |
| [vaastav/Fantasy-Premier-League](https://github.com/vaastav/Fantasy-Premier-League) | Player goal data 2016–17 → 2025–26 |
| `historical_scorers.json` | Hand-curated Golden Boot records 1993–94 → 2015–16 |

Season codes follow the format `9394`, `9495`, …, `2526`. Key CSV columns: `HomeTeam`, `AwayTeam`, `FTHG`, `FTAG`.

---

## Prediction Model

### Dixon-Coles (`dixon_coles.py`)
- Fits per-team attack (α) and defence (β) parameters, home advantage (γ), and a low-score correction factor (ρ)
- Uses exponential time-weighting (`xi=0.0018`, ~3-season half-life) via `scipy.optimize.minimize` (L-BFGS-B)
- `predict_match(home, away)` returns an 11×11 score probability matrix

### Season Simulator (`simulator.py`)
- Draws `home_goals ~ Poisson(λ)`, `away_goals ~ Poisson(μ)` across all 380 fixtures
- Runs 1,000 simulations in parallel via `joblib.Parallel(n_jobs=-1)`
- Outputs per-team: `mean_points`, `std_points`, `title_probability`, `top4_probability`, `relegation_probability`, `position_distribution`

### Compound Predictor (`compound_predictor.py`)
- Chains all 11 future seasons; each simulation tracks its own promotion/relegation path
- Each year, parameters shrink 5% toward the league mean to capture transfer uncertainty
- From season 5 onward, adds ±10% random noise per team
- `uncertainty_level` grows from `"low"` (2026–27) → `"very_high"` (2034–37)

### Promoted Teams
- Assigned league-average ratings × 0.90 attack / × 1.10 defence
- Championship pool seeded from relegated teams + known Championship sides

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/historical/seasons` | List of all season strings |
| `GET` | `/api/historical/{season}` | Historical table + top scorer for a season |
| `GET` | `/api/historical/scorers` | All historical top scorers |
| `GET` | `/api/predictions` | All 11 season prediction summaries |
| `GET` | `/api/predictions/{season}` | Full detail for a predicted season |
| `GET` | `/api/predictions/scorers` | Predicted top scorers by season |
| `POST` | `/api/predictions/refresh` | Re-run precompute pipeline (background task) |

All predictions are served from an in-memory cache loaded at startup (<10 ms per request). CORS is enabled for `localhost:3000` in development.

---

## Frontend Pages

| Route | Description |
|-------|-------------|
| `/` | Hero section with animated stat counters and champion probability preview cards for the next 3 seasons |
| `/historical` | Season browser with a 20-team league table and top-10 scorer bar chart |
| `/predictions` | Tabbed hub for all 11 predicted seasons with uncertainty badges |
| `/predictions/[season]` | Full prediction detail: table, probability bars, heatmap, radar chart |

---

## Design Tokens

```
Background:  #080c14    Surface:  #0f1623    Card:  #161e2e
Accent:      #00d4ff    Gold:     #ffd700    Danger: #ef4444    Success: #22c55e
```

---

## Implementation Plan

| Part | Scope |
|------|-------|
| **1 — Data Pipeline** | `fetcher.py`, `loader.py`, `historical_scorers.json` — download and normalise all 32 seasons |
| **2 — Dixon-Coles Model** | `dixon_coles.py` — time-weighted parameter estimation, `predict_match()` score matrix |
| **3 — Season Simulator** | `simulator.py` — 1,000× parallel Poisson simulation, per-team probability output |
| **4 — Promotion & Scorers** | `promotion_relegation.py`, `scorer_predictor.py` — team pool logic, goalscorer projections |
| **5 — Compound Predictor** | `compound_predictor.py` — 11-season chain with shrinkage, noise, and uncertainty levels |
| **6 — Precompute Script** | `scripts/precompute.py` — end-to-end CLI runner, writes `predictions.json` to cache |
| **7 — FastAPI Backend** | `schemas.py`, route files, `main.py` — Pydantic models, all endpoints, lifespan cache load |
| **8 — Frontend Setup** | Next.js 15 + Tailwind 4 + shadcn/ui + Framer Motion, `lib/` types, API wrappers, root layout |
| **9 — Components & Pages** | All React components and the three page routes wired to live API data |
| **10 — Polish & Verification** | Animations, heatmap overlay, mobile layout, full end-to-end verification |

---

## Dependencies

**Backend (`requirements.txt`)**
```
fastapi==0.115.12  uvicorn[standard]==0.34.2  pydantic==2.11.3
pandas==2.2.3  numpy==1.26.4  scipy==1.15.2
requests==2.32.3  joblib==1.4.2  tqdm==4.67.1
```

**Frontend (`package.json`)**
```
next@^15  react@^19  framer-motion@^12  recharts@^3
tailwindcss@^4  shadcn/ui  lucide-react  @radix-ui/*
```

---

## Verification Checklist

- [ ] `python -m backend.scripts.precompute` — outputs `32 seasons loaded, model fitted, 11 predictions cached`
- [ ] `uvicorn backend.main:app` → `GET /api/historical/seasons` and `GET /api/predictions` return valid JSON
- [ ] `GET /api/predictions/2026-27` — table has 20 teams, all `title_probability` values sum to ~1.0
- [ ] `GET /api/historical/1993-94` — returns Alan Shearer / Andy Cole as top scorers
- [ ] `npm run dev` in `frontend/` — all three pages render, tables display, Framer Motion animations play
