import Link from "next/link"
import { api } from "@/lib/api"
import { StatCounter } from "@/components/hero/StatCounter"
import { ScorerOddsSection } from "@/components/scorer/ScorerOddsSection"
import { pct } from "@/lib/utils"
import type { ScorerEntry } from "@/lib/types"

export default async function HomePage() {
  let predictions: Awaited<ReturnType<typeof api.allPredictions>> = []
  try {
    predictions = await api.allPredictions()
  } catch {
    // API not running — show static shell
  }

  const first3 = predictions.slice(0, 3)

  // Fetch scorer projections for first 3 seasons in parallel
  const scorerSeasons: Array<{ season: string; scorers: ScorerEntry[] }> = []
  if (first3.length > 0) {
    const results = await Promise.allSettled(
      first3.map((p) => api.predictionSeason(p.season))
    )
    for (let i = 0; i < first3.length; i++) {
      const r = results[i]
      scorerSeasons.push({
        season: first3[i].season,
        scorers: r.status === "fulfilled" ? r.value.top_scorers : [],
      })
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-16">
      {/* Hero */}
      <section className="text-center mb-20">
        <div className="inline-block mb-4 rounded-full border border-[#00d4ff]/30 px-4 py-1 text-xs text-[#00d4ff] bg-[#00d4ff]/5">
          33 seasons · Dixon-Coles · Monte Carlo
        </div>
        <h1 className="text-5xl sm:text-7xl font-extrabold tracking-tight mb-6">
          Premier League
          <br />
          <span className="text-[#00d4ff]">Predicted</span>
        </h1>
        <p className="max-w-xl mx-auto text-lg text-white/60 mb-10">
          32 seasons of match data fed through a Dixon-Coles Poisson model.
          1,000 Monte Carlo simulations per season. Predictions for 2026–37.
        </p>
        <div className="flex justify-center gap-4 flex-wrap">
          <Link
            href="/predictions"
            className="inline-flex items-center gap-2 rounded-full bg-[#00d4ff] px-6 py-3 text-sm font-semibold text-[#080c14] hover:bg-[#00d4ff]/90 transition"
          >
            See Predictions →
          </Link>
          <Link
            href="/historical"
            className="inline-flex items-center gap-2 rounded-full border border-white/20 px-6 py-3 text-sm font-semibold text-white hover:bg-white/5 transition"
          >
            Browse Historical Data
          </Link>
        </div>
      </section>

      {/* Stat counters */}
      <section className="grid grid-cols-2 sm:grid-cols-4 gap-6 mb-20 rounded-2xl border border-white/8 bg-[#0f1623] p-8">
        <StatCounter end={33} label="Seasons of data" />
        <StatCounter end={12604} label="Matches analysed" />
        <StatCounter end={1000} label="Simulations per season" />
        <StatCounter end={11} label="Future seasons predicted" />
      </section>

      {/* Champion cards for first 3 seasons */}
      {first3.length > 0 && (
        <section className="mb-16">
          <h2 className="text-xl font-bold mb-6 text-white/80">
            Predicted Champions
          </h2>
          <div className="grid sm:grid-cols-3 gap-4">
            {first3.map((p) => (
              <Link
                key={p.season}
                href={`/predictions/${encodeURIComponent(p.season)}`}
                className="group rounded-2xl border border-white/8 bg-[#161e2e] p-6 hover:border-[#00d4ff]/40 transition"
              >
                <div className="text-sm text-white/40 mb-1">{p.season}</div>
                <div className="text-2xl font-bold mb-2 group-hover:text-[#00d4ff] transition">
                  {p.champion}
                </div>
                <div className="text-4xl font-extrabold text-[#ffd700]">
                  {pct(p.champion_odds)}
                </div>
                <div className="text-xs text-white/30 mt-1">title probability</div>
                <div className="mt-4 text-xs text-[#00d4ff] opacity-0 group-hover:opacity-100 transition">
                  View full prediction →
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Top Scorer Betting Odds */}
      {scorerSeasons.length > 0 && (
        <ScorerOddsSection seasons={scorerSeasons} />
      )}
    </div>
  )
}
