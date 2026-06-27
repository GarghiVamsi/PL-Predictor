"use client"

import type { UncertaintyLevel } from "@/lib/types"
import { uncertaintyColor, uncertaintyLabel } from "@/lib/utils"

interface Props {
  level: UncertaintyLevel
  className?: string
}

export function UncertaintyBadge({ level, className = "" }: Props) {
  const color = uncertaintyColor(level)
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium border ${className}`}
      style={{ borderColor: color, color }}
    >
      <span
        className="size-1.5 rounded-full"
        style={{ background: color }}
      />
      {uncertaintyLabel(level)} Uncertainty
    </span>
  )
}
