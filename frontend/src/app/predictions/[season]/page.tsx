export const dynamic = "force-dynamic"

import { Suspense } from "react"
import { notFound } from "next/navigation"
import { api } from "@/lib/api"
import { PredictionTable } from "@/components/league-table/PredictionTable"
import { TopScorerBarChart } from "@/components/charts/TopScorerBarChart"
import { UncertaintyBadge } from "@/components/season/UncertaintyBadge"
import type { UncertaintyLevel } from "@/lib/types"

interface Props {
  params: Promise<{ season: string }>
}

export default async function PredictionSeasonPage({ params }: Props) {
  const { season } = await params
  const decodedSeason = decodeURIComponent(season)

  let data: Awaited<ReturnType<typeof api.predictionSeason>>
  try {
    data = await api.predictionSeason(decodedSeason)
  } catch {
    notFound()
  }

  const topTeam = data.table[0]

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-12">
      {/* Header */}
      <div className="mb-10">
        <div className="flex flex-wrap items-start gap-4 mb-4">
          <div>
            <h1 className="text-4xl font-extrabold">{data.season}</h1>
            <p className="text-white/40 text-sm mt-1">
              {data.n_simulations.toLocaleString()} compound simulation paths
            </p>
          </div>
          <UncertaintyBadge
            level={data.uncertainty_level as UncertaintyLevel}
            className="mt-1"
          />
        </div>

        {/* Top team highlight */}
        {topTeam && (
          <div className="rounded-2xl border border-[#ffd700]/20 bg-[#ffd700]/5 p-6 mb-8">
            <div className="text-sm text-[#ffd700]/60 mb-1">Predicted Champion</div>
            <div className="text-3xl font-extrabold text-[#ffd700]">{topTeam.team}</div>
            <div className="flex gap-6 mt-3 text-sm">
              <div>
                <span className="text-white/40">Title odds </span>
                <span className="font-bold text-[#ffd700]">
                  {(topTeam.title_probability * 100).toFixed(1)}%
                </span>
              </div>
              <div>
                <span className="text-white/40">Avg points </span>
                <span className="font-bold">{topTeam.mean_points.toFixed(1)}</span>
              </div>
              <div>
                <span className="text-white/40">Top-4 </span>
                <span className="font-bold text-[#00d4ff]">
                  {(topTeam.top4_probability * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Main table */}
        <div className="lg:col-span-2">
          <h2 className="text-sm font-semibold text-white/50 mb-3 uppercase tracking-wider">
            Predicted Table
          </h2>
          <PredictionTable table={data.table} />
        </div>

        {/* Scorer sidebar */}
        <div className="bg-[#161e2e] rounded-xl border border-white/8 p-5">
          <h2 className="text-sm font-semibold text-white/50 mb-4 uppercase tracking-wider">
            Projected Top Scorers
          </h2>
          {data.top_scorers.length > 0 ? (
            <>
              <Suspense fallback={<div className="h-56 animate-pulse bg-white/5 rounded" />}>
                <TopScorerBarChart scorers={data.top_scorers} />
              </Suspense>
              <div className="mt-4 space-y-2">
                {data.top_scorers.map((s, i) => (
                  <div key={i} className="flex justify-between text-sm">
                    <span className="text-white/70">{s.player}</span>
                    <span className="font-bold text-[#ffd700]">~{s.goals}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="text-white/30 text-sm">No projection available</p>
          )}
        </div>
      </div>
    </div>
  )
}
