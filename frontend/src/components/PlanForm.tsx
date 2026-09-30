import { newAccount } from '../planFile'
import { ACCOUNT_TYPE_LABELS, type Account, type AccountType, type Plan } from '../types'
import { NumberField, TextField } from './fields'

interface Props {
  plan: Plan
  onChange: (plan: Plan) => void
}

export function PlanForm({ plan, onChange }: Props) {
  const setClient = (patch: Partial<Plan['client']>) => onChange({ ...plan, client: { ...plan.client, ...patch } })
  const setIncome = (patch: Partial<Plan['income']>) => onChange({ ...plan, income: { ...plan.income, ...patch } })
  const setSpending = (patch: Partial<Plan['spending']>) =>
    onChange({ ...plan, spending: { ...plan.spending, ...patch } })
  const setAccount = (id: string, patch: Partial<Account>) =>
    onChange({ ...plan, accounts: plan.accounts.map((a) => (a.id === id ? { ...a, ...patch } : a)) })
  const removeAccount = (id: string) => onChange({ ...plan, accounts: plan.accounts.filter((a) => a.id !== id) })
  const addAccount = () => onChange({ ...plan, accounts: [...plan.accounts, newAccount()] })

  const int = (v: number | null) => Math.round(v ?? 0)

  return (
    <div className="form">
      <section>
        <h2>Client</h2>
        <div className="grid">
          <TextField label="Name" value={plan.client.name} onChange={(name) => setClient({ name })} />
          <TextField
            label="Date of birth"
            type="date"
            value={plan.client.date_of_birth}
            onChange={(date_of_birth) => setClient({ date_of_birth })}
          />
          <TextField label="State of residence" value={plan.client.state} onChange={(state) => setClient({ state })} />
          <NumberField
            label="Retirement age"
            value={plan.client.retirement_age}
            onChange={(v) => setClient({ retirement_age: int(v) })}
          />
          <NumberField
            label="Life expectancy"
            value={plan.client.life_expectancy}
            onChange={(v) => setClient({ life_expectancy: int(v) })}
          />
        </div>
      </section>

      <section>
        <h2>Income &amp; spending</h2>
        <div className="grid">
          <NumberField
            label="Annual income"
            unit="money"
            value={plan.income.annual_income}
            onChange={(v) => setIncome({ annual_income: v ?? 0 })}
          />
          <NumberField
            label="Yearly raise"
            unit="percent"
            value={plan.income.annual_raise}
            onChange={(v) => setIncome({ annual_raise: v ?? 0 })}
          />
          <NumberField
            label="Spends now / yr"
            unit="money"
            value={plan.spending.current_annual}
            onChange={(v) => setSpending({ current_annual: v ?? 0 })}
          />
          <NumberField
            label="Wants to spend in retirement / yr"
            unit="money"
            value={plan.spending.retirement_annual}
            onChange={(v) => setSpending({ retirement_annual: v ?? 0 })}
            hint="In today's dollars"
          />
          <NumberField
            label="Inflation"
            unit="percent"
            value={plan.spending.inflation}
            onChange={(v) => setSpending({ inflation: v ?? 0 })}
          />
        </div>
      </section>

      <section>
        <div className="section-head">
          <h2>Accounts</h2>
          <button type="button" className="btn-small" onClick={addAccount}>
            + Add account
          </button>
        </div>
        {plan.accounts.length === 0 && <p className="muted">No accounts yet.</p>}
        {plan.accounts.map((a) => (
          <div key={a.id} className="account">
            <div className="account-head">
              <input
                className="account-name"
                aria-label="Account name"
                value={a.name}
                onChange={(e) => setAccount(a.id, { name: e.target.value })}
              />
              <button type="button" className="btn-icon" aria-label={`Remove ${a.name}`} onClick={() => removeAccount(a.id)}>
                ✕
              </button>
            </div>
            <div className="grid">
              <label className="field">
                <span className="field-label">Type</span>
                <span className="input-wrap">
                  <select value={a.type} onChange={(e) => setAccount(a.id, { type: e.target.value as AccountType })}>
                    {Object.entries(ACCOUNT_TYPE_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </span>
              </label>
              <NumberField
                label="Balance"
                unit="money"
                value={a.balance}
                onChange={(v) => setAccount(a.id, { balance: v ?? 0 })}
              />
              <NumberField
                label="Contribution / yr"
                unit="money"
                value={a.annual_contribution}
                onChange={(v) => setAccount(a.id, { annual_contribution: v ?? 0 })}
              />
              <NumberField
                label="Expected return"
                unit="percent"
                value={a.expected_return}
                onChange={(v) => setAccount(a.id, { expected_return: v ?? 0 })}
              />
              <NumberField
                label="Contributions start"
                optional
                placeholder="This year"
                value={a.contribution_start_year}
                onChange={(v) => setAccount(a.id, { contribution_start_year: v === null ? null : int(v) })}
              />
              <NumberField
                label="Contributions stop"
                optional
                placeholder="At retirement"
                value={a.contribution_stop_year}
                onChange={(v) => setAccount(a.id, { contribution_stop_year: v === null ? null : int(v) })}
              />
            </div>
          </div>
        ))}
      </section>
    </div>
  )
}
