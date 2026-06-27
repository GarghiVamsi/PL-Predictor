import type { HistoricalRow } from "@/lib/types"
import { positionColor } from "@/lib/utils"

interface Props {
  table: HistoricalRow[]
}

export function LeagueTable({ table }: Props) {
  return (
    <div className="overflow-x-auto rounded-lg border border-white/8">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/8 text-white/40 text-xs">
            <th className="py-2 px-3 text-left w-8">#</th>
            <th className="py-2 px-3 text-left">Club</th>
            <th className="py-2 px-3 text-right">P</th>
            <th className="py-2 px-3 text-right">W</th>
            <th className="py-2 px-3 text-right">D</th>
            <th className="py-2 px-3 text-right">L</th>
            <th className="py-2 px-3 text-right">GD</th>
            <th className="py-2 px-3 text-right font-bold text-white/60">Pts</th>
          </tr>
        </thead>
        <tbody>
          {table.map((row) => {
            const color = positionColor(row.position)
            return (
              <tr
                key={row.team}
                className="border-b border-white/5 hover:bg-white/3 transition"
              >
                <td className="py-2 px-3">
                  <span
                    className="text-xs font-bold"
                    style={{ color }}
                  >
                    {row.position}
                  </span>
                </td>
                <td className="py-2 px-3 font-medium">{row.team}</td>
                <td className="py-2 px-3 text-right text-white/60">{row.played}</td>
                <td className="py-2 px-3 text-right text-white/60">{row.won}</td>
                <td className="py-2 px-3 text-right text-white/60">{row.drawn}</td>
                <td className="py-2 px-3 text-right text-white/60">{row.lost}</td>
                <td className="py-2 px-3 text-right text-white/60">
                  {row.gd > 0 ? `+${row.gd}` : row.gd}
                </td>
                <td className="py-2 px-3 text-right font-bold">{row.points}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
