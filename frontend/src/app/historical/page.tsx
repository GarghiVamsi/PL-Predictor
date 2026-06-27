export const dynamic = "force-dynamic"

import { Suspense } from "react"
import { api } from "@/lib/api"
import { LeagueTable } from "@/components/league-table/LeagueTable"
import { TopScorerBarChart } from "@/components/charts/TopScorerBarChart"
import { SeasonSelector } from "@/components/season/SeasonSelector"

interface Props {
  searchParams: Promise<{ s?: string }>
}

export default async function HistoricalPage({ searchParams }: Props) {
  const { s } = await searchParams
  const seasons = await api.historicalSeasons()
  const defaultSeason = seasons[seasons.length - 1] ?? "2025-26"
  const season = s && seasons.includes(s) ? s : defaultSeason

  const data = await api.historicalSeason(season)

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-12">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold">{season} Season</h1>
          <p className="text-white/40 text-sm mt-1">Final league table</p>
        </div>
        <SeasonSelector seasons={[...seasons].reverse()} current={season} basePath="/historical" />
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <LeagueTable table={data.table} />
        </div>
        <div className="bg-[#161e2e] rounded-xl border border-white/8 p-5">
          <h2 className="text-sm font-semibold text-white/50 mb-4 uppercase tracking-wider">
            Top Scorers
          </h2>
          {data.top_scorers.length > 0 ? (
            <Suspense fallback={<div className="h-64 animate-pulse bg-white/5 rounded" />}>
              <TopScorerBarChart scorers={data.top_scorers.slice(0, 10)} />
            </Suspense>
          ) : (
            <p className="text-white/30 text-sm">No scorer data available</p>
          )}
          <div className="mt-4 space-y-2">
            {data.top_scorers.slice(0, 5).map((s, i) => (
              <div key={i} className="flex justify-between text-sm">
                <span className="text-white/70">{s.player}</span>
                <span className="font-bold text-[#ffd700]">{s.goals}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
