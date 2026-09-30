import { useState } from 'react'
import { fetchComparison } from '../api'
import { money, shortMoney } from '../format'
import type { Comparison, ComparisonKind, Plan } from '../types'

// Side-by-side scenarios, run on request (each is two full projections).
export function StrategyPanel({ plan }: { plan: Plan }) {
  const [result, setResult] = useState<Comparison | null>(null)
  const [running, setRunning] = useState<ComparisonKind | null>(null)
  const [error, setError] = useState<string | null>(null)
  const hasConversion = plan.roth_conversion !== null

  async function run(kind: ComparisonKind) {
    setRunning(kind)
    setError(null)
    try {
      setResult(await fetchComparison(plan, kind))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setRunning(null)
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Strategy check</h2>
        <div className="analysis-actions no-print">
          <button type="button" className="btn btn-small" onClick={() => run('contribution_type')} disabled={running !== null}>
            {running === 'contribution_type' ? 'Comparing…' : 'Roth vs. pre-tax contributions'}
          </button>
          <button
            type="button"
            className="btn btn-small"
            onClick={() => run('roth_conversion')}
            disabled={running !== null || !hasConversion}
            title={hasConversion ? undefined : 'Plan Roth conversions under Taxes & strategy first'}
          >
            {running === 'roth_conversion' ? 'Comparing…' : 'With vs. without Roth conversions'}
          </button>
        </div>
      </div>
      {!result && !error && (
        <p className="empty">
          Compare strategies on what you'd keep after taxes.{' '}
          {!hasConversion && 'To test Roth conversions, plan them under Taxes & strategy.'}
        </p>
      )}
      {error && <p className="error-text">{error}</p>}
      {result && (
        <>
          <div className="compare-grid">
            {result.scenarios.map((s) => (
              <div key={s.name} className={`scenario${s.name === result.better ? ' best' : ''}`}>
                <h3>{s.name}</h3>
                <dl className="figures">
                  <div>
                    <dt>After-tax wealth at the end</dt>
                    <dd>{shortMoney(s.after_tax_final_today_dollars)}</dd>
                  </div>
                  <div>
                    <dt>Lifetime taxes</dt>
                    <dd>{shortMoney(s.lifetime_taxes_today_dollars)}</dd>
                  </div>
                  <div>
                    <dt>At retirement</dt>
                    <dd>{shortMoney(s.balance_at_retirement_today_dollars)}</dd>
                  </div>
                  <div>
                    <dt>Steady returns</dt>
                    <dd>{s.depletion_age === null ? 'lasts' : `runs out at ${s.depletion_age}`}</dd>
                  </div>
                </dl>
              </div>
            ))}
          </div>
          <p className="verdict">
            <strong>{result.better}</strong> leaves {money(result.difference_today_dollars)} more after taxes, in today's
            dollars.
          </p>
          <p className="chart-note">
            Leftover cash is invested in both. Money left in pre-tax accounts at the end is counted after a 24% tax.
          </p>
        </>
      )}
    </section>
  )
}
