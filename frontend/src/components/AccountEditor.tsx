import { useState } from 'react'
import { analyzeHoldings } from '../api'
import { money, pct } from '../format'
import { ACCOUNT_TYPE_LABELS, type Account, type AccountAnalysis } from '../types'
import { NumberField, RemoveButton, SelectField } from './fields'

interface Props {
  account: Account
  onChange: (patch: Partial<Account>) => void
  onRemove: () => void
}

const int = (v: number | null) => (v === null ? null : Math.round(v))

const ASSET_COLORS: Record<string, string> = {
  stock: 'var(--series-1)',
  bond: 'var(--series-3)',
  cash: 'var(--series-2)',
  other: 'var(--series-4)',
}

export function AccountEditor({ account: a, onChange, onRemove }: Props) {
  const [analysis, setAnalysis] = useState<AccountAnalysis | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const setHolding = (i: number, patch: Partial<Account['holdings'][number]>) =>
    onChange({ holdings: a.holdings.map((h, j) => (j === i ? { ...h, ...patch } : h)) })

  async function lookUp() {
    setLoading(true)
    setError(null)
    try {
      setAnalysis(await analyzeHoldings(a.holdings.filter((h) => h.ticker.trim())))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const mix = analysis ? Object.entries(analysis.asset_classes).filter(([, share]) => share >= 0.005) : []

  return (
    <div className="card-item">
      <div className="card-item-head">
        <input className="name-input" aria-label="Account name" value={a.name} onChange={(e) => onChange({ name: e.target.value })} />
        <RemoveButton label={`Remove ${a.name}`} onClick={onRemove} />
      </div>
      <div className="grid">
        <SelectField label="Type" value={a.type} options={ACCOUNT_TYPE_LABELS} onChange={(type) => onChange({ type })} wide />
        <NumberField label="Balance" unit="money" value={a.balance} onChange={(v) => onChange({ balance: v ?? 0 })} />
        <NumberField label="Contribution / yr" unit="money" value={a.annual_contribution} onChange={(v) => onChange({ annual_contribution: v ?? 0 })} />
        <NumberField label="Expected return" unit="percent" value={a.expected_return} onChange={(v) => onChange({ expected_return: v ?? 0 })} />
        <NumberField
          label="Volatility"
          unit="percent"
          optional
          placeholder="15"
          value={a.volatility}
          onChange={(v) => onChange({ volatility: v })}
          hint="Yearly swing, for simulations"
        />
        <NumberField label="Contributions start" optional placeholder="This year" value={a.contribution_start_year} onChange={(v) => onChange({ contribution_start_year: int(v) })} />
        <NumberField label="Contributions stop" optional placeholder="At retirement" value={a.contribution_stop_year} onChange={(v) => onChange({ contribution_stop_year: int(v) })} />
        {(a.type === 'taxable' || a.type === 'roth') && (
          <NumberField
            label={a.type === 'roth' ? 'Contributed so far' : 'Cost basis'}
            unit="money"
            optional
            placeholder="Same as balance"
            value={a.cost_basis}
            onChange={(v) => onChange({ cost_basis: v })}
            hint={a.type === 'roth' ? 'Comes out tax-free first' : 'Gains above this are taxed when sold'}
            wide
          />
        )}
      </div>

      <div className="subhead">Holdings</div>
      {a.holdings.map((h, i) => (
        <div key={i} className="holding-row">
          <label className="field">
            <span className="field-label">Ticker</span>
            <span className="input-wrap">
              <input value={h.ticker} placeholder="VTI" onChange={(e) => setHolding(i, { ticker: e.target.value.toUpperCase() })} />
            </span>
          </label>
          <NumberField label="Shares" value={h.shares} onChange={(v) => setHolding(i, { shares: v ?? 0 })} />
          <RemoveButton label={`Remove ${h.ticker || 'holding'}`} onClick={() => onChange({ holdings: a.holdings.filter((_, j) => j !== i) })} />
        </div>
      ))}
      <div className="analysis-actions">
        <button type="button" className="btn btn-small" onClick={() => onChange({ holdings: [...a.holdings, { ticker: '', shares: 0 }] })}>
          + Add ticker
        </button>
        {a.holdings.length > 0 && (
          <button type="button" className="btn btn-small btn-primary" onClick={lookUp} disabled={loading}>
            {loading ? 'Looking up…' : 'Look up live prices'}
          </button>
        )}
      </div>
      {error && <p className="error-text">{error}</p>}

      {analysis && (
        <div className="analysis" aria-live="polite">
          {analysis.holdings.map((h) => (
            <div key={h.ticker} className="holding-result">
              <span>
                <strong>{h.ticker}</strong> {h.error ? <span className="error-text">{h.error}</span> : <span className="muted">{h.shares} sh · {money(h.price)}</span>}
              </span>
              {!h.error && <strong className="num">{money(h.value)}</strong>}
            </div>
          ))}
          {mix.length > 0 && (
            <>
              <div className="mix" role="img" aria-label={mix.map(([k, v]) => `${k} ${pct(v)}`).join(', ')}>
                {mix.map(([k, v]) => (
                  <span key={k} style={{ width: `${v * 100}%`, background: ASSET_COLORS[k] ?? ASSET_COLORS.other }} />
                ))}
              </div>
              <span className="muted">{mix.map(([k, v]) => `${k[0].toUpperCase()}${k.slice(1)} ${pct(v)}`).join(' · ')}</span>
            </>
          )}
          {analysis.annual_return !== null && analysis.volatility !== null && (
            <span>
              Over the last {analysis.years_of_data} years this mix grew <strong>{pct(analysis.annual_return, 1)} a year</strong> with{' '}
              <strong>{pct(analysis.volatility, 1)} volatility</strong>. Past returns don't predict future ones.
            </span>
          )}
          <div className="analysis-actions">
            <button type="button" className="btn btn-small" onClick={() => onChange({ balance: Math.round(analysis.value) })}>
              Use live value · {money(analysis.value)}
            </button>
            {analysis.volatility !== null && (
              <button type="button" className="btn btn-small" onClick={() => onChange({ volatility: Math.round(analysis.volatility! * 1000) / 1000 })}>
                Use its volatility
              </button>
            )}
            {analysis.annual_return !== null && (
              <button type="button" className="btn btn-small" onClick={() => onChange({ expected_return: Math.round(analysis.annual_return! * 1000) / 1000 })}>
                Use its past return
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
