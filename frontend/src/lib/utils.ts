import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import type { UncertaintyLevel } from "./types"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function pct(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`
}

export function uncertaintyColor(level: UncertaintyLevel): string {
  const map: Record<UncertaintyLevel, string> = {
    low: "#22c55e",
    medium: "#ffd700",
    high: "#f97316",
    very_high: "#ef4444",
  }
  return map[level] ?? "#94a3b8"
}

export function uncertaintyLabel(level: UncertaintyLevel): string {
  const map: Record<UncertaintyLevel, string> = {
    low: "Low",
    medium: "Medium",
    high: "High",
    very_high: "Very High",
  }
  return map[level] ?? level
}

export function positionColor(pos: number, total = 20): string {
  if (pos === 1) return "#ffd700"
  if (pos <= 4) return "#00d4ff"
  if (pos > total - 3) return "#ef4444"
  return "#94a3b8"
}
