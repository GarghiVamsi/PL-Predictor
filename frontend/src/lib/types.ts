export interface HistoricalRow {
  position: number
  team: string
  played: number
  won: number
  drawn: number
  lost: number
  gf: number
  ga: number
  gd: number
  points: number
}

export interface ScorerEntry {
  player: string
  goals: number
  team: string
  source: string
}

export interface HistoricalSeason {
  season: string
  table: HistoricalRow[]
  top_scorers: ScorerEntry[]
}

export interface PredictionRow {
  position: number
  team: string
  mean_points: number
  std_points: number
  mean_position: number
  title_probability: number
  top4_probability: number
  relegation_probability: number
  position_distribution: Record<string, number>
}

export interface PredictionSummary {
  season: string
  uncertainty_level: string
  n_simulations: number
  champion: string
  champion_odds: number
}

export interface PredictionSeason {
  season: string
  uncertainty_level: string
  n_simulations: number
  table: PredictionRow[]
  top_scorers: ScorerEntry[]
}

export type UncertaintyLevel = "low" | "medium" | "high" | "very_high"
