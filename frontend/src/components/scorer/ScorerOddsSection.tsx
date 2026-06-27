import type { ScorerEntry } from "@/lib/types"

interface ScorerWithOdds extends ScorerEntry {
  probability: number
  decimal_odds: number
  fractional: string
  tag?: string
}

function softmaxOdds(scorers: ScorerEntry[], temperature = 8): ScorerWithOdds[] {
  if (scorers.length === 0) return []
  const expVals = scorers.map((s) => Math.exp(s.goals / temperature))
  const total = expVals.reduce((a, b) => a + b, 0)
  const probs = expVals.map((e) => e / total)

  return scorers.map((s, i) => {
    const prob = probs[i]
    const decimal = Math.round((1 / prob) * 100) / 100
    // Fractional: simplify ratio closest to decimal-1
    const num = Math.round((decimal - 1) * 4)
    const fractional = `${num}/4`
    const tag =
      i === 0
        ? "Favourite"
        : prob > 0.18
        ? "Strong Pick"
        : prob > 0.1
        ? "Each-Way"
        : "Outsider"
    return { ...s, probability: prob, decimal_odds: decimal, fractional, tag }
  })
}

const RANK_COLORS = ["#ffd700", "#94a3b8", "#cd7f32", "#64748b", "#475569"]
const RANK_LABELS = ["1st", "2nd", "3rd", "4th", "5th"]

const TAG_STYLES: Record<string, string> = {
  Favourite: "bg-[#ffd700]/10 text-[#ffd700] border-[#ffd700]/30",
  "Strong Pick": "bg-[#00d4ff]/10 text-[#00d4ff] border-[#00d4ff]/30",
  "Each-Way": "bg-[#22c55e]/10 text-[#22c55e] border-[#22c55e]/30",
  Outsider: "bg-white/5 text-white/40 border-white/10",
}

interface SeasonScorerCardProps {
  season: string
  scorers: ScorerEntry[]
}

function SeasonScorerCard({ season, scorers }: SeasonScorerCardProps) {
  const withOdds = softmaxOdds(scorers.slice(0, 5))

  return (
    <div className="rounded-2xl border border-white/8 bg-[#161e2e] p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">
          {season}
        </h3>
        <span className="text-[10px] text-white/20 uppercase tracking-widest">
          Implied odds
        </span>
      </div>

      {withOdds.map((scorer, i) => (
        <div
          key={scorer.player}
          className="flex items-center gap-3 group"
        >
          {/* Rank */}
          <div
            className="w-8 text-center text-xs font-bold shrink-0"
            style={{ color: RANK_COLORS[i] }}
          >
            {RANK_LABELS[i]}
          </div>

          {/* Player info */}
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold truncate">{scorer.player}</div>
            <div className="text-xs text-white/30 truncate">{scorer.team}</div>
          </div>

          {/* Goals projection */}
          <div className="text-right shrink-0">
            <div className="text-xs text-white/30">~{scorer.goals} goals</div>
            <div
              className="text-base font-extrabold"
              style={{ color: RANK_COLORS[i] }}
            >
              {scorer.decimal_odds.toFixed(2)}
            </div>
          </div>
        </div>
      ))}

      {/* Probability bar strip */}
      <div className="mt-1">
        <div className="flex h-2 rounded-full overflow-hidden gap-px">
          {withOdds.map((scorer, i) => (
            <div
              key={scorer.player}
              style={{
                width: `${(scorer.probability * 100).toFixed(1)}%`,
                backgroundColor: RANK_COLORS[i],
                opacity: i === 0 ? 1 : 0.4 + i * -0.05,
              }}
              title={`${scorer.player}: ${(scorer.probability * 100).toFixed(0)}%`}
            />
          ))}
        </div>
        <div className="flex justify-between text-[10px] text-white/20 mt-1">
          <span>{(withOdds[0]?.probability ?? 0) > 0 ? `${(withOdds[0].probability * 100).toFixed(0)}% fav` : ""}</span>
          <span>field {((1 - (withOdds[0]?.probability ?? 0)) * 100).toFixed(0)}%</span>
        </div>
      </div>

      {/* Best bet callout */}
      {withOdds[0] && (
        <div className="rounded-xl border border-[#ffd700]/15 bg-[#ffd700]/5 px-4 py-3 flex items-center justify-between">
          <div>
            <div className="text-[10px] text-[#ffd700]/50 uppercase tracking-wider mb-0.5">
              Best bet
            </div>
            <div className="text-sm font-bold text-[#ffd700]">
              {withOdds[0].player.split(" ").slice(-1)[0]}
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-extrabold text-[#ffd700]">
              {withOdds[0].decimal_odds.toFixed(2)}
            </div>
            <div className="text-[10px] text-white/30">decimal</div>
          </div>
        </div>
      )}

      {/* Value pick (highest prob / odds ratio after favourite) */}
      {withOdds[1] && withOdds[1].probability > 0.12 && (
        <div className="rounded-xl border border-[#00d4ff]/15 bg-[#00d4ff]/5 px-4 py-3 flex items-center justify-between">
          <div>
            <div className="text-[10px] text-[#00d4ff]/50 uppercase tracking-wider mb-0.5">
              Each-way value
            </div>
            <div className="text-sm font-bold text-[#00d4ff]">
              {withOdds[1].player.split(" ").slice(-1)[0]}
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-extrabold text-[#00d4ff]">
              {withOdds[1].decimal_odds.toFixed(2)}
            </div>
            <div className="text-[10px] text-white/30">decimal</div>
          </div>
        </div>
      )}
    </div>
  )
}

interface Props {
  seasons: Array<{ season: string; scorers: ScorerEntry[] }>
}

export function ScorerOddsSection({ seasons }: Props) {
  return (
    <section>
      <div className="mb-6 flex flex-wrap items-end gap-4 justify-between">
        <div>
          <h2 className="text-xl font-bold text-white/80">Top Scorer Betting Odds</h2>
          <p className="text-sm text-white/30 mt-1">
            Implied probabilities derived from Monte Carlo goal projections via softmax.
            Decimal odds = 1 ÷ probability. Not financial advice.
          </p>
        </div>
        <span className="text-[10px] text-white/20 uppercase tracking-widest border border-white/10 rounded px-2 py-1">
          Model output · for entertainment
        </span>
      </div>

      <div className="grid sm:grid-cols-3 gap-4">
        {seasons.map(({ season, scorers }) => (
          <SeasonScorerCard key={season} season={season} scorers={scorers} />
        ))}
      </div>

      {/* Legend */}
      <div className="mt-4 rounded-xl border border-white/5 bg-[#0f1623] px-5 py-4 grid sm:grid-cols-3 gap-3 text-xs text-white/40">
        <div>
          <span className="font-semibold text-white/60">Decimal odds</span> — how much
          you get back per £1 staked including your stake (e.g. 2.50 = £2.50 return on £1).
        </div>
        <div>
          <span className="font-semibold text-white/60">Probability strip</span> — gold
          is the favourite&apos;s share; remaining colours are the rest of the field.
        </div>
        <div>
          <span className="font-semibold text-white/60">Each-way value</span> — a player
          with {">"}15% implied probability at {">"}5.00 odds is typically good each-way
          value on most bookmakers&apos; top-scorer markets.
        </div>
      </div>
    </section>
  )
}
