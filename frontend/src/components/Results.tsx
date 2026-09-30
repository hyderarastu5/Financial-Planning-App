import { useState } from 'react'
import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Plan, Projection } from '../types'

const SERIES_COLORS = ['var(--series-1)', 'var(--series-2)', 'var(--series-3)', 'var(--series-4)', 'var(--series-5)']

const money = (n: number) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })

const compactMoney = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 1 })

interface Props {
  plan: Plan
  projection: Projection
}

export function Results({ plan, projection }: Props) {
  const [todayDollars, setTodayDollars] = useState(true)
  const { summary, years } = projection
  const retirementAge = plan.client.retirement_age
  const deflator = (year: number) => (todayDollars ? (1 + plan.spending.inflation) ** (year - summary.start_year) : 1)

  const chartData = years.map((r) => {
    const point: Record<string, number> = { age: r.age }
    for (const a of plan.accounts) point[a.id] = (r.balances[a.id] ?? 0) / deflator(r.year)
    return point
  })

  const firstYear = years[0]
  const lasts = summary.depletion_age === null

  return (
    <div className="results">
      <div className="cards">
        <div className="card">
          <span className="card-label">At retirement (age {retirementAge})</span>
          <span className="card-value">{money(summary.balance_at_retirement_today_dollars)}</span>
          <span className="card-sub">today's dollars · {money(summary.balance_at_retirement)} nominal</span>
        </div>
        <div className={`card ${lasts ? 'good' : 'bad'}`}>
          <span className="card-label">Does the money last?</span>
          <span className="card-value">
            {lasts ? `Yes, to ${plan.client.life_expectancy}` : `Runs out at ${summary.depletion_age}`}
          </span>
          <span className="card-sub">
            {lasts ? `${money(summary.final_balance)} left at the end` : 'Spending exceeds savings after this age'}
          </span>
        </div>
        {!firstYear.retired && (
          <div className={`card ${firstYear.surplus >= 0 ? '' : 'bad'}`}>
            <span className="card-label">Left over this year</span>
            <span className="card-value">{money(firstYear.surplus)}</span>
            <span className="card-sub">income − spending − contributions</span>
          </div>
        )}
      </div>

      <div className="panel">
        <div className="panel-head">
          <h2>Account balances</h2>
          <div className="toggle" role="group" aria-label="Dollar basis">
            <button type="button" aria-pressed={todayDollars} onClick={() => setTodayDollars(true)}>
              Today's $
            </button>
            <button type="button" aria-pressed={!todayDollars} onClick={() => setTodayDollars(false)}>
              Future $
            </button>
          </div>
        </div>
        <div className="legend">
          {plan.accounts.map((a, i) => (
            <span key={a.id}>
              <i style={{ background: SERIES_COLORS[i % SERIES_COLORS.length] }} />
              {a.name}
            </span>
          ))}
        </div>
        <div className="chart">
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="age" tick={{ fill: 'var(--muted)', fontSize: 12 }} tickLine={false} axisLine={false} />
              <YAxis
                tickFormatter={compactMoney}
                tick={{ fill: 'var(--muted)', fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                width={64}
              />
              <Tooltip
                formatter={(value, id) => [money(Number(value)), plan.accounts.find((a) => a.id === id)?.name ?? id]}
                labelFormatter={(age) => `Age ${age}`}
                contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }}
              />
              <ReferenceLine
                x={retirementAge}
                stroke="var(--muted)"
                strokeDasharray="4 4"
                label={{ value: 'Retire', fill: 'var(--muted)', fontSize: 12, position: 'insideTopLeft' }}
              />
              {plan.accounts.map((a, i) => (
                <Area
                  key={a.id}
                  dataKey={a.id}
                  stackId="1"
                  type="monotone"
                  stroke={SERIES_COLORS[i % SERIES_COLORS.length]}
                  fill={SERIES_COLORS[i % SERIES_COLORS.length]}
                  fillOpacity={0.35}
                  isAnimationActive={false}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <p className="note">
          Not yet included: taxes, Social Security, pensions and other retirement income (Phase 2). Retirement spending
          is paid entirely from these accounts.
        </p>
      </div>

      <details className="panel">
        <summary>Year-by-year table</summary>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Year</th>
                <th>Age</th>
                <th>Income</th>
                <th>Spending</th>
                <th>Contributions</th>
                <th>Withdrawals</th>
                <th>Shortfall</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {years.map((r) => (
                <tr key={r.year} className={r.retired ? 'retired' : ''}>
                  <td>{r.year}</td>
                  <td>{r.age}</td>
                  <td>{money(r.income)}</td>
                  <td>{money(r.spending)}</td>
                  <td>{money(r.contributions)}</td>
                  <td>{money(r.withdrawals)}</td>
                  <td className={r.shortfall > 0 ? 'neg' : ''}>{money(r.shortfall)}</td>
                  <td>{money(todayDollars ? r.total_today_dollars : r.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="note">Money columns are in future dollars; Total follows the toggle above.</p>
      </details>
    </div>
  )
}
