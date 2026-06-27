"use client"

import type { ScorerEntry } from "@/lib/types"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts"

interface Props {
  scorers: ScorerEntry[]
}

const COLORS = [
  "#ffd700",
  "#00d4ff",
  "#22c55e",
  "#a78bfa",
  "#f97316",
  "#ec4899",
  "#94a3b8",
  "#94a3b8",
  "#94a3b8",
  "#94a3b8",
]

export function TopScorerBarChart({ scorers }: Props) {
  const data = scorers.map((s) => ({
    name: s.player.split(" ").slice(-1)[0],  // last name for brevity
    full: s.player,
    goals: s.goals,
    team: s.team,
  }))

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: -8 }}>
        <XAxis
          dataKey="name"
          tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: "rgba(255,255,255,0.05)" }}
          contentStyle={{
            background: "#161e2e",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 8,
            color: "#fff",
            fontSize: 12,
          }}
          formatter={(v, _, p) => [
            `${String(v)} goals`,
            (p.payload as { full: string }).full,
          ]}
        />
        <Bar dataKey="goals" radius={[4, 4, 0, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i] ?? "#94a3b8"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
