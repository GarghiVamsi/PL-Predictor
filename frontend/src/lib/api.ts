import type {
  HistoricalSeason,
  PredictionSeason,
  PredictionSummary,
} from "./types"

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { next: { revalidate: 3600 } })
  if (!res.ok) throw new Error(`${path} → ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  historicalSeasons: () =>
    get<{ seasons: string[] }>("/api/historical/seasons").then((r) => r.seasons),

  historicalSeason: (season: string) =>
    get<HistoricalSeason>(`/api/historical/${encodeURIComponent(season)}`),

  allPredictions: () =>
    get<{ predictions: PredictionSummary[] }>("/api/predictions").then(
      (r) => r.predictions,
    ),

  predictionSeason: (season: string) =>
    get<PredictionSeason>(`/api/predictions/${encodeURIComponent(season)}`),
}
