"use client"

import { useRouter } from "next/navigation"

interface Props {
  seasons: string[]
  current: string
  basePath: string  // e.g. "/historical" or "/predictions"
}

export function SeasonSelector({ seasons, current, basePath }: Props) {
  const router = useRouter()
  return (
    <div className="flex items-center gap-3">
      <label htmlFor="season-select" className="text-sm text-white/50 shrink-0">
        Season
      </label>
      <select
        id="season-select"
        value={current}
        onChange={(e) => router.push(`${basePath}?s=${encodeURIComponent(e.target.value)}`)}
        className="rounded border border-white/8 bg-[#0f1623] px-3 py-1.5 text-sm text-white outline-none focus:ring-1 focus:ring-[#00d4ff]"
      >
        {seasons.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>
    </div>
  )
}
