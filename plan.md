The README has a detailed implementation plan. Here are the 10 parts I'm breaking it into, following the sequence laid out:

Part 1 — Data Pipeline
fetcher.py + loader.py + historical_scorers.json
Download all 32 seasons of CSVs from football-data.co.uk, parse and normalize team names, curate the ~230-record goalscorer JSON for 1993–2016.

Part 2 — Dixon-Coles Model
model/dixon_coles.py
Fit per-team attack (α) / defense (β) parameters, home advantage (γ), low-score correction (ρ) using time-weighted L-BFGS-B via scipy. Output: predict_match() returning an 11×11 score probability matrix.

Part 3 — Season Simulator
model/simulator.py
Run 1000 Poisson-draw simulations of all 380 matches in parallel (joblib). Produce per-team title/top4/relegation probabilities and position distributions.

Part 4 — Promotion, Relegation & Scorer Predictor
model/promotion_relegation.py + model/scorer_predictor.py
Manage the Championship pool, assign promoted-team ratings (×0.90 attack / ×1.10 defense), project top goalscorers using FPL data and fallback curated records.

Part 5 — Compound Predictor (11-season chain)
model/compound_predictor.py
Chain all 11 future seasons: shrink parameters 5% toward mean each year, add ±10% noise from season 5 onward, grow uncertainty_level from "low" → "very_high".

Part 6 — Precompute Script
scripts/precompute.py
CLI entry point that runs the full pipeline end-to-end and writes predictions.json to cache. Validates output: 32 seasons loaded, model fitted, 11 predictions cached.

Part 7 — FastAPI Backend
api/schemas.py + api/routes/ + main.py
Pydantic models for all response types, route handlers for /api/historical/* and /api/predictions/*, lifespan startup that loads cache into memory (<10ms per request), CORS for localhost:3000.

Part 8 — Frontend Setup & Types
Next.js 15 init, Tailwind 4, shadcn/ui, Framer Motion, lib/types.ts, lib/api.ts, lib/utils.ts, root layout with dark theme tokens (#080c14 bg etc.).

Part 9 — Frontend Components & Pages
LeagueTable + ProbabilityBar, TopScorerBarChart, SeasonSelector, SeasonHero, UncertaintyBadge, TitleOddsRadar, SeasonTrendLine, HeroSection + StatCounter. Then wire up all three pages: /, /historical, /predictions/[season].

Part 10 — Polish & Verification
Framer Motion layout animations, position-probability heatmap overlay, mobile-responsive layout, full end-to-end verification (precompute → API → UI), edge cases (promoted teams, sum-to-1 probabilities, 1993-94 Shearer/Cole check).

