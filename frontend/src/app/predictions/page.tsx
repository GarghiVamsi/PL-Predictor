export const dynamic = "force-dynamic"

import Link from "next/link"
import { api } from "@/lib/api"
import { UncertaintyBadge } from "@/components/season/UncertaintyBadge"
import { pct } from "@/lib/utils"
import type { UncertaintyLevel } from "@/lib/types"

export default async function PredictionsPage() {
  const predictions = await api.allPredictions()

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-12">
      <div className="mb-10">
        <h1 className="text-3xl font-bold mb-2">Future Season Predictions</h1>
        <p className="text-white/40">
          11 seasons predicted via 1,000 compound Monte Carlo paths. Each path
          tracks independent promotion/relegation chains.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {predictions.map((p) => (
          <Link
            key={p.season}
            href={`/predictions/${encodeURIComponent(p.season)}`}
            className="group rounded-2xl border border-white/8 bg-[#161e2e] p-6 hover:border-[#00d4ff]/40 transition"
          >
            <div className="flex items-start justify-between mb-4">
              <span className="text-sm text-white/40">{p.season}</span>
              <UncertaintyBadge level={p.uncertainty_level as UncertaintyLevel} />
            </div>
            <div className="text-xl font-bold mb-1 group-hover:text-[#00d4ff] transition">
              {p.champion}
            </div>
            <div className="text-3xl font-extrabold text-[#ffd700]">
              {pct(p.champion_odds)}
            </div>
            <div className="text-xs text-white/30 mt-0.5">title probability</div>
            <div className="mt-5 text-xs text-[#00d4ff] opacity-0 group-hover:opacity-100 transition">
              Full table →
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
