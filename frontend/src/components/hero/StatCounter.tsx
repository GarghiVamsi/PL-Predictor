"use client"

import { useEffect, useRef, useState } from "react"

interface Props {
  end: number
  label: string
  suffix?: string
  duration?: number
}

export function StatCounter({ end, label, suffix = "", duration = 1500 }: Props) {
  const [count, setCount] = useState(0)
  const ref = useRef<HTMLDivElement>(null)
  const started = useRef(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !started.current) {
        started.current = true
        const start = performance.now()
        const tick = (now: number) => {
          const elapsed = now - start
          const progress = Math.min(elapsed / duration, 1)
          setCount(Math.round(progress * end))
          if (progress < 1) requestAnimationFrame(tick)
        }
        requestAnimationFrame(tick)
      }
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [end, duration])

  return (
    <div ref={ref} className="text-center">
      <div className="text-4xl font-bold text-[#00d4ff] tabular-nums">
        {count.toLocaleString()}{suffix}
      </div>
      <div className="mt-1 text-sm text-white/50">{label}</div>
    </div>
  )
}
