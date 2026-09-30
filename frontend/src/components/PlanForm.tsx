import { newAccount, newGoal, newIncomeStream } from '../planFile'
import {
  ACCOUNT_TYPE_LABELS,
  GOAL_CATEGORY_LABELS,
  INCOME_KIND_LABELS,
  type Account,
  type FilingStatus,
  type Goal,
  type IncomeStream,
  type Plan,
} from '../types'
import { CheckboxField, NumberField, SelectField, TextField } from './fields'

const FILING_STATUS_LABELS: Record<FilingStatus, string> = {
  single: 'Single',
  married_joint: 'Married filing jointly',
}

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
  const setStream = (id: string, patch: Partial<IncomeStream>) =>
    onChange({ ...plan, income_streams: plan.income_streams.map((s) => (s.id === id ? { ...s, ...patch } : s)) })
  const removeStream = (id: string) =>
    onChange({ ...plan, income_streams: plan.income_streams.filter((s) => s.id !== id) })
  const addStream = () => onChange({ ...plan, income_streams: [...plan.income_streams, newIncomeStream()] })
  const setGoal = (id: string, patch: Partial<Goal>) =>
    onChange({ ...plan, goals: plan.goals.map((g) => (g.id === id ? { ...g, ...patch } : g)) })
  const removeGoal = (id: string) => onChange({ ...plan, goals: plan.goals.filter((g) => g.id !== id) })
  const addGoal = () => onChange({ ...plan, goals: [...plan.goals, newGoal()] })

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
          <SelectField
            label="Filing status"
            value={plan.client.filing_status}
            options={FILING_STATUS_LABELS}
            onChange={(filing_status) => setClient({ filing_status })}
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
          <NumberField
            label="Healthcare / yr"
            unit="money"
            value={plan.spending.healthcare_annual}
            onChange={(v) => setSpending({ healthcare_annual: v ?? 0 })}
            hint="On top of spending; HSAs pay it first"
          />
          <NumberField
            label="Healthcare inflation"
            unit="percent"
            value={plan.spending.healthcare_inflation}
            onChange={(v) => setSpending({ healthcare_inflation: v ?? 0 })}
          />
        </div>
      </section>

      <section>
        <div className="section-head">
          <h2>Other income</h2>
          <button type="button" className="btn-small" onClick={addStream}>
            + Add income
          </button>
        </div>
        {plan.income_streams.length === 0 && (
          <p className="muted">Social Security, pensions, annuities, business or rental income.</p>
        )}
        {plan.income_streams.map((s) => (
          <div key={s.id} className="account">
            <div className="account-head">
              <input
                className="account-name"
                aria-label="Income name"
                value={s.name}
                onChange={(e) => setStream(s.id, { name: e.target.value })}
              />
              <button type="button" className="btn-icon" aria-label={`Remove ${s.name}`} onClick={() => removeStream(s.id)}>
                ✕
              </button>
            </div>
            <div className="grid">
              <SelectField
                label="Kind"
                value={s.kind}
                options={INCOME_KIND_LABELS}
                onChange={(kind) => setStream(s.id, { kind })}
              />
              <NumberField
                label="Amount / yr"
                unit="money"
                value={s.annual_amount}
                onChange={(v) => setStream(s.id, { annual_amount: v ?? 0 })}
                hint="In today's dollars"
              />
              <NumberField label="Starts at age" value={s.start_age} onChange={(v) => setStream(s.id, { start_age: int(v) })} />
              <NumberField
                label="Ends at age"
                optional
                placeholder="For life"
                value={s.end_age}
                onChange={(v) => setStream(s.id, { end_age: v === null ? null : int(v) })}
              />
              {s.kind !== 'social_security' && (
                <NumberField
                  label="Taxable share"
                  unit="percent"
                  value={s.taxable_share}
                  onChange={(v) => setStream(s.id, { taxable_share: v ?? 0 })}
                />
              )}
              <CheckboxField
                label="Rises with inflation"
                checked={s.inflation_adjusted}
                onChange={(inflation_adjusted) => setStream(s.id, { inflation_adjusted })}
              />
            </div>
          </div>
        ))}
      </section>

      <section>
        <div className="section-head">
          <h2>Goals</h2>
          <button type="button" className="btn-small" onClick={addGoal}>
            + Add goal
          </button>
        </div>
        {plan.goals.length === 0 && <p className="muted">A home, college, travel, giving…</p>}
        {plan.goals.map((g) => (
          <div key={g.id} className="account">
            <div className="account-head">
              <input
                className="account-name"
                aria-label="Goal name"
                value={g.name}
                onChange={(e) => setGoal(g.id, { name: e.target.value })}
              />
              <button type="button" className="btn-icon" aria-label={`Remove ${g.name}`} onClick={() => removeGoal(g.id)}>
                ✕
              </button>
            </div>
            <div className="grid">
              <SelectField
                label="Category"
                value={g.category}
                options={GOAL_CATEGORY_LABELS}
                onChange={(category) => setGoal(g.id, { category })}
              />
              <NumberField
                label="Cost / yr"
                unit="money"
                value={g.annual_amount}
                onChange={(v) => setGoal(g.id, { annual_amount: v ?? 0 })}
                hint="In today's dollars"
              />
              <NumberField label="Year" value={g.start_year} onChange={(v) => setGoal(g.id, { start_year: int(v) })} />
              <NumberField
                label="For how many years"
                value={g.years}
                onChange={(v) => setGoal(g.id, { years: Math.max(1, int(v)) })}
              />
            </div>
          </div>
        ))}
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
              <SelectField
                label="Type"
                value={a.type}
                options={ACCOUNT_TYPE_LABELS}
                onChange={(type) => setAccount(a.id, { type })}
              />
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
              {(a.type === 'taxable' || a.type === 'roth') && (
                <NumberField
                  label={a.type === 'roth' ? 'Contributed so far' : 'Cost basis'}
                  unit="money"
                  optional
                  placeholder="Same as balance"
                  value={a.cost_basis}
                  onChange={(v) => setAccount(a.id, { cost_basis: v })}
                  hint={a.type === 'roth' ? 'Comes out tax-free first' : 'Gains above this are taxed when sold'}
                />
              )}
            </div>
          </div>
        ))}
      </section>
    </div>
  )
}
