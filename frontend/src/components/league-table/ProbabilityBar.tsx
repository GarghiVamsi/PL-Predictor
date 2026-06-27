"use client"

interface Props {
  label: string
  value: number  // 0–1
  color: string
}

export function ProbabilityBar({ label, value, color }: Props) {
  const pct = Math.round(value * 100)
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-16 shrink-0 text-white/50">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="w-9 text-right text-white/70">{pct}%</span>
    </div>
  )
}
