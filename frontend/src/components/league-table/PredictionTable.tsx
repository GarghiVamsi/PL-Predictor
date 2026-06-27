import type { PredictionRow } from "@/lib/types"
import { positionColor, pct } from "@/lib/utils"
import { ProbabilityBar } from "./ProbabilityBar"

interface Props {
  table: PredictionRow[]
}

export function PredictionTable({ table }: Props) {
  return (
    <div className="overflow-x-auto rounded-lg border border-white/8">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/8 text-white/40 text-xs">
            <th className="py-2 px-3 text-left w-8">#</th>
            <th className="py-2 px-3 text-left">Club</th>
            <th className="py-2 px-3 text-right">Avg Pts</th>
            <th className="py-2 px-3 text-right">±</th>
            <th className="py-2 px-4 text-left min-w-48">Probabilities</th>
          </tr>
        </thead>
        <tbody>
          {table.map((row) => {
            const posColor = positionColor(row.position)
            return (
              <tr
                key={row.team}
                className="border-b border-white/5 hover:bg-white/3 transition"
              >
                <td className="py-3 px-3">
                  <span className="text-xs font-bold" style={{ color: posColor }}>
                    {row.position}
                  </span>
                </td>
                <td className="py-3 px-3 font-medium whitespace-nowrap">{row.team}</td>
                <td className="py-3 px-3 text-right font-bold">
                  {row.mean_points.toFixed(1)}
                </td>
                <td className="py-3 px-3 text-right text-white/40 text-xs">
                  ±{row.std_points.toFixed(1)}
                </td>
                <td className="py-3 px-4 min-w-48">
                  <div className="flex flex-col gap-1">
                    {row.title_probability > 0.001 && (
                      <ProbabilityBar
                        label="Title"
                        value={row.title_probability}
                        color="#ffd700"
                      />
                    )}
                    <ProbabilityBar
                      label="Top 4"
                      value={row.top4_probability}
                      color="#00d4ff"
                    />
                    {row.relegation_probability > 0.001 && (
                      <ProbabilityBar
                        label="Relegation"
                        value={row.relegation_probability}
                        color="#ef4444"
                      />
                    )}
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
