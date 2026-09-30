import { money, pct, shortMoney, status } from '../format'
import type { Plan, Projection, Simulation, StateOption } from '../types'

interface Props {
  plan: Plan
  projection: Projection
  simulation: Simulation | null
  simulating: boolean
}

export function KpiCards({ plan, projection, simulation, simulating }: Props) {
  const { summary } = projection
  const first = projection.years[0]
  const drawing = !first.retired && first.savings_drawn > 0
  const chance = simulation?.success_probability
  return (
    <div className="kpis">
      <div className={`panel kpi${simulating ? ' updating' : ''}`}>
        <span className="kpi-label">Chance it lasts</span>
        <span className="kpi-value hero">{chance === undefined ? '…' : pct(chance)}</span>
        <div className="meter" role="img" aria-label={chance === undefined ? 'Calculating' : `${pct(chance)} chance`}>
          <span style={{ width: `${(chance ?? 0) * 100}%` }} />
        </div>
        <span className="kpi-sub">
          to age {plan.client.life_expectancy}
          {simulation ? ` · ${simulation.runs.toLocaleString()} simulated markets` : ''}
        </span>
      </div>
      <div className="panel kpi">
        <span className="kpi-label">At retirement</span>
        <span className="kpi-value">{shortMoney(summary.balance_at_retirement_today_dollars)}</span>
        <span className="kpi-sub">age {plan.client.retirement_age} · today's dollars</span>
      </div>
      {first.retired ? (
        <div className={`panel kpi${summary.depletion_age !== null ? ' bad' : ''}`}>
          <span className="kpi-label">Steady returns</span>
          <span className="kpi-value">{summary.depletion_age === null ? 'Lasts' : `Out at ${summary.depletion_age}`}</span>
          <span className="kpi-sub">{shortMoney(summary.final_balance)} left at the end, future $</span>
        </div>
      ) : (
        <div className={`panel kpi${drawing || first.shortfall > 0 ? ' bad' : ''}`}>
          <span className="kpi-label">{drawing ? 'Drawing from savings' : 'Left over this year'}</span>
          <span className="kpi-value">{money(drawing ? first.savings_drawn : first.surplus - first.shortfall)}</span>
          <span className="kpi-sub">{drawing ? 'costs and taxes exceed take-home pay' : 'after taxes and contributions'}</span>
        </div>
      )}
      <div className="panel kpi">
        <span className="kpi-label">Lifetime taxes</span>
        <span className="kpi-value">{shortMoney(summary.lifetime_taxes_today_dollars)}</span>
        <span className="kpi-sub">today's dollars{summary.state ? ` · ${summary.state}` : ''}</span>
      </div>
    </div>
  )
}

export function GoalsPanel({ projection, simulation, simulating }: Omit<Props, 'plan'>) {
  const probability = new Map(simulation?.goals.map((g) => [g.id, g.probability]))
  return (
    <section className="panel wide">
      <div className="panel-head">
        <h2>Goals</h2>
      </div>
      {projection.summary.goals.length === 0 ? (
        <p className="empty">No goals yet. Add them in the sidebar.</p>
      ) : (
        <ul className={`goal-list${simulating ? ' updating' : ''}`}>
          {projection.summary.goals.map((g) => {
            const p = probability.get(g.id)
            const share = p ?? g.funded_share
            const s = status(share)
            return (
              <li key={g.id}>
                <div className="goal-top">
                  <span className="goal-name">{g.name}</span>
                  <span className={`goal-pct ${s === 'bad' ? 'bad-text' : s}`}>{p === undefined ? '…' : `${pct(p)} likely`}</span>
                </div>
                <div className="bar" role="img" aria-label={`${pct(share)}`}>
                  <span className={`fill-${s}`} style={{ width: `${share * 100}%` }} />
                </div>
                <span className="kpi-sub">
                  {money(g.total_cost)} total, future $ · {g.funded_share >= 0.999 ? 'fully funded' : `${pct(g.funded_share)} funded`} with steady returns
                </span>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

function stateLabel(code: string | null, entered: string, states: StateOption[]) {
  if (code === null) return entered ? `${entered} (not recognized)` : 'none set'
  const s = states.find((x) => x.code === code)
  if (!s) return code
  return s.income_tax ? s.name : `${s.name} · no income tax`
}

export function KeyFigures({ plan, projection, simulation, states }: Omit<Props, 'simulating'> & { states: StateOption[] }) {
  const { summary } = projection
  const ss = plan.income_streams.find((s) => s.kind === 'social_security')
  const weakAge = simulation?.bands.find((b) => b.p10 <= 0)?.age
  const lastYear = projection.years[projection.years.length - 1]
  const rows: [string, string][] = [
    ['Portfolio at retirement', `${shortMoney(summary.balance_at_retirement_today_dollars)} today`],
    ...(ss ? [['Social Security', `${money(ss.annual_amount)} / yr at ${ss.start_age}`] as [string, string]] : []),
    [
      `At ${plan.client.life_expectancy}, steady returns`,
      summary.depletion_age === null ? `${shortMoney(lastYear.net_worth)} net worth` : `runs out at ${summary.depletion_age}`,
    ],
    ...(simulation ? [['Weakest 10% of markets', weakAge ? `runs out ~${weakAge}` : 'lasts'] as [string, string]] : []),
    ...summary.debts.map((d) => [d.name, d.payoff_age === null ? 'not paid off' : `paid off at ${d.payoff_age}`] as [string, string]),
    ['State', stateLabel(summary.state, plan.client.state, states)],
  ]
  return (
    <section className="panel narrow">
      <div className="panel-head">
        <h2>Key figures</h2>
      </div>
      <dl className="figures">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
