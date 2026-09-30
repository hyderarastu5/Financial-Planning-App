import { useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { compactMoney, money } from '../format'
import type { Plan, Projection, Simulation } from '../types'

type View = 'range' | 'accounts' | 'table'

const SERIES = ['var(--series-1)', 'var(--series-2)', 'var(--series-3)', 'var(--series-4)', 'var(--series-5)']
const axisTick = { fill: 'var(--muted)', fontSize: 12 }
const tooltipStyle = {
  contentStyle: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text)' },
  labelStyle: { color: 'var(--muted)' },
}

interface Props {
  plan: Plan
  projection: Projection
  simulation: Simulation | null
  simulating: boolean
}

export function OutcomesPanel({ plan, projection, simulation, simulating }: Props) {
  const [view, setView] = useState<View>('range')
  const retirementAge = plan.client.retirement_age
  const retireLine = (
    <ReferenceLine
      x={retirementAge}
      stroke="var(--muted)"
      strokeDasharray="4 4"
      label={{ value: `Retirement at ${retirementAge}`, fill: 'var(--muted)', fontSize: 12, position: 'insideTopLeft' }}
    />
  )

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>{view === 'range' ? 'Range of outcomes' : view === 'accounts' ? 'Balances by account' : 'Year by year'}</h2>
        <div className="segmented" role="group" aria-label="Chart view">
          {(
            [
              ['range', 'Range of outcomes'],
              ['accounts', 'By account'],
              ['table', 'Year by year'],
            ] as [View, string][]
          ).map(([v, label]) => (
            <button key={v} type="button" aria-pressed={view === v} onClick={() => setView(v)}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {view === 'range' && <RangeChart projection={projection} simulation={simulation} simulating={simulating} retireLine={retireLine} />}
      {view === 'accounts' && <AccountsChart plan={plan} projection={projection} retireLine={retireLine} />}
      {view === 'table' && <YearTable projection={projection} />}
    </section>
  )
}

// 1, 2, 2.5 or 5 times a power of ten, at least `raw`
function niceStep(raw: number) {
  const power = 10 ** Math.floor(Math.log10(raw))
  return ([1, 2, 2.5, 5, 10].find((m) => m * power >= raw) ?? 10) * power
}

function RangeChart({ projection, simulation, simulating, retireLine }: {
  projection: Projection
  simulation: Simulation | null
  simulating: boolean
  retireLine: React.ReactNode
}) {
  const steadyByAge = new Map(projection.years.map((r) => [r.age, r.total_today_dollars]))
  const data: { age: number; outer?: number[]; inner?: number[]; median?: number; steady?: number }[] = simulation
    ? simulation.bands.map((b) => ({
        age: b.age,
        outer: [b.p10, b.p90],
        inner: [b.p25, b.p75],
        median: b.p50,
        steady: steadyByAge.get(b.age),
      }))
    : projection.years.map((r) => ({ age: r.age, steady: r.total_today_dollars }))
  // The luckiest simulated markets grow huge; size the axis to the typical outcome (about twice the
  // median or steady path) so the middle of the range stays readable, with even ticks.
  const typical = Math.max(
    ...projection.years.map((r) => r.total_today_dollars),
    ...(simulation ? simulation.bands.map((b) => b.p50) : []),
    1,
  )
  const step = niceStep((typical * 2) / 4)
  const ticks = [0, step, 2 * step, 3 * step, 4 * step]

  return (
    <div className={simulating ? 'updating' : ''}>
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="age" tick={axisTick} tickLine={false} axisLine={false} />
          <YAxis domain={[0, ticks[4]]} ticks={ticks} allowDataOverflow tickFormatter={compactMoney} tick={axisTick} tickLine={false} axisLine={false} width={64} />
          <Tooltip
            {...tooltipStyle}
            labelFormatter={(age) => `Age ${age}`}
            formatter={(value, name) => {
              const label = { outer: 'Middle 80%', inner: 'Middle 50%', median: 'Median', steady: 'Steady returns' }[String(name)] ?? name
              const text = Array.isArray(value) ? `${money(Number(value[0]))} – ${money(Number(value[1]))}` : money(Number(value))
              return [text, label]
            }}
          />
          {retireLine}
          {simulation && <Area dataKey="outer" stroke="none" fill="var(--band)" fillOpacity={0.22} isAnimationActive={false} />}
          {simulation && <Area dataKey="inner" stroke="none" fill="var(--band)" fillOpacity={0.42} isAnimationActive={false} />}
          {simulation && <Line dataKey="median" stroke="var(--line)" strokeWidth={3} dot={false} isAnimationActive={false} />}
          <Line dataKey="steady" stroke="var(--muted)" strokeWidth={1.5} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
      <div className="legend">
        {simulation && (
          <>
            <span><i className="line" style={{ background: 'var(--line)' }} />Median</span>
            <span><i style={{ background: 'var(--band)', opacity: 0.6 }} />Middle 50% of outcomes</span>
            <span><i style={{ background: 'var(--band)', opacity: 0.3 }} />Middle 80%</span>
          </>
        )}
        <span><i className="line" style={{ background: 'var(--muted)' }} />Steady returns</span>
      </div>
      <p className="chart-note">
        Portfolio value in today's dollars{simulation ? `, across ${simulation.runs.toLocaleString()} simulated markets` : ''}.
        {simulating && ' Updating simulations…'}
      </p>
    </div>
  )
}

function AccountsChart({ plan, projection, retireLine }: { plan: Plan; projection: Projection; retireLine: React.ReactNode }) {
  const inflation = plan.spending.inflation
  const start = projection.summary.start_year
  const data = projection.years.map((r) => {
    const point: Record<string, number> = { age: r.age }
    const deflate = (1 + inflation) ** (r.year - start)
    for (const a of plan.accounts) point[a.id] = (r.balances[a.id] ?? 0) / deflate
    return point
  })
  return (
    <div>
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="age" tick={axisTick} tickLine={false} axisLine={false} />
          <YAxis tickFormatter={compactMoney} tick={axisTick} tickLine={false} axisLine={false} width={64} />
          <Tooltip
            {...tooltipStyle}
            labelFormatter={(age) => `Age ${age}`}
            formatter={(value, id) => [money(Number(value)), plan.accounts.find((a) => a.id === id)?.name ?? id]}
          />
          {retireLine}
          {plan.accounts.map((a, i) => (
            <Area
              key={a.id}
              dataKey={a.id}
              stackId="1"
              type="monotone"
              stroke={SERIES[i % SERIES.length]}
              fill={SERIES[i % SERIES.length]}
              fillOpacity={0.4}
              isAnimationActive={false}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
      <div className="legend">
        {plan.accounts.map((a, i) => (
          <span key={a.id}>
            <i style={{ background: SERIES[i % SERIES.length] }} />
            {a.name}
          </span>
        ))}
      </div>
      <p className="chart-note">Today's dollars, with steady returns.</p>
    </div>
  )
}

function YearTable({ projection }: { projection: Projection }) {
  const cols: [string, (r: Projection['years'][number]) => number][] = [
    ['Salary', (r) => r.income],
    ['Other income', (r) => r.other_income],
    ['Spending', (r) => r.spending + r.healthcare],
    ['Goals', (r) => r.goals],
    ['Debt', (r) => r.debt_payments],
    ['Saved', (r) => r.contributions],
    ['Withdrawn', (r) => r.withdrawals],
    ['Roth conv.', (r) => r.roth_conversion],
    ['Taxes', (r) => r.income_tax + r.state_tax + r.payroll_tax + r.penalties],
    ['Shortfall', (r) => r.shortfall],
    ['Net worth', (r) => r.net_worth],
  ]
  return (
    <>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Year</th>
              <th>Age</th>
              {cols.map(([label]) => (
                <th key={label}>{label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {projection.years.map((r) => (
              <tr key={r.year} className={r.retired ? 'retired' : ''}>
                <td>{r.year}</td>
                <td>{r.age}</td>
                {cols.map(([label, get]) => (
                  <td key={label} className={label === 'Shortfall' && r.shortfall > 0 ? 'neg' : ''}>
                    {money(get(r))}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="chart-note">Future dollars. Shaded rows are retirement years.</p>
    </>
  )
}
