import { useState, type ReactNode } from 'react'
import { money } from '../format'
import { newAccount, newDebt, newGoal, newIncomeStream, newInflow } from '../planFile'
import {
  DEBT_KIND_LABELS,
  GOAL_CATEGORY_LABELS,
  INCOME_KIND_LABELS,
  INFLOW_KIND_LABELS,
  type FilingStatus,
  type Plan,
  type StateOption,
} from '../types'
import { AccountEditor } from './AccountEditor'
import { CheckboxField, NumberField, RemoveButton, SelectField, TextField } from './fields'

interface Props {
  plan: Plan
  onChange: (plan: Plan) => void
  states: StateOption[]
}

type ListKey = 'accounts' | 'income_streams' | 'goals' | 'debts' | 'inflows'
type Item<K extends ListKey> = Plan[K][number]

// set / remove / add for one of the plan's lists
function listOps<K extends ListKey>(plan: Plan, onChange: (p: Plan) => void, key: K, create: () => Item<K>) {
  const items = plan[key] as Item<K>[]
  return {
    set: (id: string, patch: Partial<Item<K>>) =>
      onChange({ ...plan, [key]: items.map((x) => (x.id === id ? { ...x, ...patch } : x)) }),
    remove: (id: string) => onChange({ ...plan, [key]: items.filter((x) => x.id !== id) }),
    add: () => onChange({ ...plan, [key]: [...items, create()] }),
  }
}

const FILING_STATUS_LABELS: Record<FilingStatus, string> = {
  single: 'Single',
  married_joint: 'Married filing jointly',
}

const int = (v: number | null) => Math.round(v ?? 0)

function Section({ title, detail, children }: { title: string; detail: string; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const bodyId = `section-${title.replace(/\W+/g, '-').toLowerCase()}`
  return (
    <div className="accordion-item">
      <button
        type="button"
        className="accordion-trigger"
        aria-expanded={open}
        aria-controls={bodyId}
        onClick={() => setOpen(!open)}
      >
        <span>
          <strong>{title}</strong>
          <small>{detail}</small>
        </span>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
          <path d="M6 3l5 5-5 5" />
        </svg>
      </button>
      {open && (
        <div className="accordion-body" id={bodyId}>
          {children}
        </div>
      )}
    </div>
  )
}

function AddButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button type="button" className="btn btn-small" onClick={onClick} style={{ alignSelf: 'flex-start' }}>
      + {label}
    </button>
  )
}

export function Sidebar({ plan, onChange, states }: Props) {
  const setClient = (patch: Partial<Plan['client']>) => onChange({ ...plan, client: { ...plan.client, ...patch } })
  const setIncome = (patch: Partial<Plan['income']>) => onChange({ ...plan, income: { ...plan.income, ...patch } })
  const setSpending = (patch: Partial<Plan['spending']>) => onChange({ ...plan, spending: { ...plan.spending, ...patch } })

  const accounts = listOps(plan, onChange, 'accounts', () => newAccount())
  const streams = listOps(plan, onChange, 'income_streams', () => newIncomeStream())
  const goals = listOps(plan, onChange, 'goals', () => newGoal())
  const debts = listOps(plan, onChange, 'debts', () => newDebt())
  const inflows = listOps(plan, onChange, 'inflows', () => newInflow())

  const taxable = plan.accounts.filter((a) => a.type === 'taxable')
  const taxableOptions: Record<string, string> = Object.fromEntries(taxable.map((a) => [a.id, a.name]))
  const stateOptions: Record<string, string> = Object.fromEntries(states.map((s) => [s.code, s.name]))
  if (plan.client.state && !stateOptions[plan.client.state]) stateOptions[plan.client.state] = plan.client.state
  const stateName = stateOptions[plan.client.state] ?? 'No state set'
  const rc = plan.roth_conversion

  // Removing an account also clears references to it.
  const removeAccount = (id: string) =>
    onChange({
      ...plan,
      accounts: plan.accounts.filter((a) => a.id !== id),
      surplus_account_id: plan.surplus_account_id === id ? null : plan.surplus_account_id,
      inflows: plan.inflows.map((f) => (f.account_id === id ? { ...f, account_id: null } : f)),
    })

  const totalBalance = plan.accounts.reduce((s, a) => s + a.balance, 0)
  const totalDebt = plan.debts.reduce((s, d) => s + d.balance, 0)
  const list = (names: string[]) => (names.length ? names.join(', ') : 'None')

  return (
    <aside className="sidebar" aria-label="Plan inputs">
      <h2 className="sidebar-title">Client</h2>
      <div className="grid">
        <TextField label="Name" value={plan.client.name} onChange={(name) => setClient({ name })} />
        <TextField
          label="Date of birth"
          type="date"
          value={plan.client.date_of_birth}
          onChange={(date_of_birth) => setClient({ date_of_birth })}
        />
        <NumberField label="Retirement age" value={plan.client.retirement_age} onChange={(v) => setClient({ retirement_age: int(v) })} />
        <NumberField label="Life expectancy" value={plan.client.life_expectancy} onChange={(v) => setClient({ life_expectancy: int(v) })} />
      </div>

      <div className="accordion">
        <Section
          title="Income & spending"
          detail={`${money(plan.income.annual_income)} salary · spends ${money(plan.spending.current_annual)}`}
        >
          <div className="grid">
            <NumberField label="Annual income" unit="money" value={plan.income.annual_income} onChange={(v) => setIncome({ annual_income: v ?? 0 })} />
            <NumberField label="Yearly raise" unit="percent" value={plan.income.annual_raise} onChange={(v) => setIncome({ annual_raise: v ?? 0 })} />
            <NumberField label="Spends now / yr" unit="money" value={plan.spending.current_annual} onChange={(v) => setSpending({ current_annual: v ?? 0 })} />
            <NumberField
              label="Retirement spending / yr"
              unit="money"
              value={plan.spending.retirement_annual}
              onChange={(v) => setSpending({ retirement_annual: v ?? 0 })}
              hint="Today's dollars"
            />
            <NumberField label="Healthcare / yr" unit="money" value={plan.spending.healthcare_annual} onChange={(v) => setSpending({ healthcare_annual: v ?? 0 })} hint="HSAs pay it first" />
            <NumberField label="Healthcare inflation" unit="percent" value={plan.spending.healthcare_inflation} onChange={(v) => setSpending({ healthcare_inflation: v ?? 0 })} />
            <NumberField label="Inflation" unit="percent" value={plan.spending.inflation} onChange={(v) => setSpending({ inflation: v ?? 0 })} />
          </div>
        </Section>

        <Section title="Accounts" detail={`${plan.accounts.length} accounts · ${money(totalBalance)}`}>
          {plan.accounts.length === 0 && <p className="empty">No accounts yet.</p>}
          {plan.accounts.map((a) => (
            <AccountEditor key={a.id} account={a} onChange={(patch) => accounts.set(a.id, patch)} onRemove={() => removeAccount(a.id)} />
          ))}
          <AddButton label="Add account" onClick={accounts.add} />
        </Section>

        <Section
          title="Other income"
          detail={plan.income_streams.length ? plan.income_streams.map((s) => `${s.name} from ${s.start_age}`).join(', ') : 'None'}
        >
          {plan.income_streams.length === 0 && <p className="empty">Social Security, pensions, annuities, business or rental income.</p>}
          {plan.income_streams.map((s) => (
            <div key={s.id} className="card-item">
              <div className="card-item-head">
                <input className="name-input" aria-label="Income name" value={s.name} onChange={(e) => streams.set(s.id, { name: e.target.value })} />
                <RemoveButton label={`Remove ${s.name}`} onClick={() => streams.remove(s.id)} />
              </div>
              <div className="grid">
                <SelectField label="Kind" value={s.kind} options={INCOME_KIND_LABELS} onChange={(kind) => streams.set(s.id, { kind })} />
                <NumberField label="Amount / yr" unit="money" value={s.annual_amount} onChange={(v) => streams.set(s.id, { annual_amount: v ?? 0 })} hint="Today's dollars" />
                <NumberField label="Starts at age" value={s.start_age} onChange={(v) => streams.set(s.id, { start_age: int(v) })} />
                <NumberField label="Ends at age" optional placeholder="For life" value={s.end_age} onChange={(v) => streams.set(s.id, { end_age: v === null ? null : int(v) })} />
                {s.kind !== 'social_security' && (
                  <NumberField label="Taxable share" unit="percent" value={s.taxable_share} onChange={(v) => streams.set(s.id, { taxable_share: v ?? 0 })} />
                )}
                <CheckboxField label="Rises with inflation" checked={s.inflation_adjusted} onChange={(inflation_adjusted) => streams.set(s.id, { inflation_adjusted })} />
              </div>
            </div>
          ))}
          <AddButton label="Add income" onClick={streams.add} />
        </Section>

        <Section title="Goals" detail={list(plan.goals.map((g) => g.name))}>
          {plan.goals.length === 0 && <p className="empty">A home, college, travel, giving…</p>}
          {plan.goals.map((g) => (
            <div key={g.id} className="card-item">
              <div className="card-item-head">
                <input className="name-input" aria-label="Goal name" value={g.name} onChange={(e) => goals.set(g.id, { name: e.target.value })} />
                <RemoveButton label={`Remove ${g.name}`} onClick={() => goals.remove(g.id)} />
              </div>
              <div className="grid">
                <SelectField label="Category" value={g.category} options={GOAL_CATEGORY_LABELS} onChange={(category) => goals.set(g.id, { category })} />
                <NumberField
                  label={g.financing ? 'Price' : 'Cost / yr'}
                  unit="money"
                  value={g.annual_amount}
                  onChange={(v) => goals.set(g.id, { annual_amount: v ?? 0 })}
                  hint="Today's dollars"
                />
                <NumberField label="Year" value={g.start_year} onChange={(v) => goals.set(g.id, { start_year: int(v) })} />
                {!g.financing && (
                  <NumberField label="For how many years" value={g.years} onChange={(v) => goals.set(g.id, { years: Math.max(1, int(v)) })} />
                )}
                <CheckboxField
                  label="Pay with a loan"
                  checked={g.financing !== null}
                  onChange={(on) =>
                    goals.set(g.id, { financing: on ? { down_payment_share: 0.2, rate: 0.065, years: 30 } : null, years: 1 })
                  }
                />
              </div>
              {g.financing && (
                <div className="grid">
                  <NumberField label="Down payment" unit="percent" value={g.financing.down_payment_share} onChange={(v) => goals.set(g.id, { financing: { ...g.financing!, down_payment_share: v ?? 0 } })} />
                  <NumberField label="Loan rate" unit="percent" value={g.financing.rate} onChange={(v) => goals.set(g.id, { financing: { ...g.financing!, rate: v ?? 0 } })} />
                  <NumberField label="Loan years" value={g.financing.years} onChange={(v) => goals.set(g.id, { financing: { ...g.financing!, years: Math.max(1, int(v)) } })} />
                </div>
              )}
            </div>
          ))}
          <AddButton label="Add goal" onClick={goals.add} />
        </Section>

        <Section title="Debts" detail={plan.debts.length ? `${plan.debts.length} · ${money(totalDebt)} owed` : 'None'}>
          {plan.debts.length === 0 && <p className="empty">Mortgages and loans, paid down by a yearly payment.</p>}
          {plan.debts.map((d) => (
            <div key={d.id} className="card-item">
              <div className="card-item-head">
                <input className="name-input" aria-label="Debt name" value={d.name} onChange={(e) => debts.set(d.id, { name: e.target.value })} />
                <RemoveButton label={`Remove ${d.name}`} onClick={() => debts.remove(d.id)} />
              </div>
              <div className="grid">
                <SelectField label="Kind" value={d.kind} options={DEBT_KIND_LABELS} onChange={(kind) => debts.set(d.id, { kind })} />
                <NumberField label="Balance" unit="money" value={d.balance} onChange={(v) => debts.set(d.id, { balance: v ?? 0 })} />
                <NumberField label="Interest rate" unit="percent" value={d.rate} onChange={(v) => debts.set(d.id, { rate: v ?? 0 })} />
                <NumberField label="Payment / yr" unit="money" value={d.annual_payment} onChange={(v) => debts.set(d.id, { annual_payment: v ?? 0 })} />
              </div>
            </div>
          ))}
          <AddButton label="Add debt" onClick={debts.add} />
        </Section>

        <Section
          title="One-time money"
          detail={plan.inflows.length ? plan.inflows.map((f) => `${f.name} ${f.year}`).join(', ') : 'None'}
        >
          {plan.inflows.length === 0 && <p className="empty">Inheritances, gifts, a home sale. Treated as tax-free.</p>}
          {plan.inflows.map((f) => (
            <div key={f.id} className="card-item">
              <div className="card-item-head">
                <input className="name-input" aria-label="Name" value={f.name} onChange={(e) => inflows.set(f.id, { name: e.target.value })} />
                <RemoveButton label={`Remove ${f.name}`} onClick={() => inflows.remove(f.id)} />
              </div>
              <div className="grid">
                <SelectField label="Kind" value={f.kind} options={INFLOW_KIND_LABELS} onChange={(kind) => inflows.set(f.id, { kind })} />
                <NumberField label="Amount" unit="money" value={f.amount} onChange={(v) => inflows.set(f.id, { amount: v ?? 0 })} hint="Today's dollars" />
                <NumberField label="Year" value={f.year} onChange={(v) => inflows.set(f.id, { year: int(v) })} />
                {taxable.length > 0 && (
                  <SelectField
                    label="Deposit into"
                    value={f.account_id ?? ''}
                    options={{ '': 'First taxable account', ...taxableOptions }}
                    onChange={(v) => inflows.set(f.id, { account_id: v || null })}
                  />
                )}
              </div>
            </div>
          ))}
          <AddButton label="Add money coming in" onClick={inflows.add} />
        </Section>

        <Section
          title="Taxes & strategy"
          detail={`${stateName} · ${FILING_STATUS_LABELS[plan.client.filing_status]} · ${rc ? 'Roth conversions' : 'no Roth conversions'}`}
        >
          <div className="grid">
            <SelectField
              label="Filing status"
              value={plan.client.filing_status}
              options={FILING_STATUS_LABELS}
              onChange={(filing_status) => setClient({ filing_status })}
            />
            <SelectField
              label="State of residence"
              value={plan.client.state}
              options={{ '': 'Choose a state', ...stateOptions }}
              onChange={(state) => setClient({ state })}
            />
            {taxable.length > 0 && (
              <SelectField
                label="Invest leftover cash in"
                value={plan.surplus_account_id ?? ''}
                options={{ '': "Don't invest it while working", ...taxableOptions }}
                onChange={(v) => onChange({ ...plan, surplus_account_id: v || null })}
                wide
              />
            )}
          </div>
          <CheckboxField
            label="Plan Roth conversions"
            checked={rc !== null}
            onChange={(on) => {
              const retire = new Date(plan.client.date_of_birth).getFullYear() + plan.client.retirement_age
              onChange({
                ...plan,
                roth_conversion: on
                  ? { start_year: retire, end_year: retire + 4, mode: 'fill_bracket', annual_amount: 0, bracket_rate: 0.12 }
                  : null,
              })
            }}
          />
          {rc && (
            <div className="grid">
              <NumberField label="From year" value={rc.start_year} onChange={(v) => onChange({ ...plan, roth_conversion: { ...rc, start_year: int(v) } })} />
              <NumberField label="Through year" value={rc.end_year} onChange={(v) => onChange({ ...plan, roth_conversion: { ...rc, end_year: int(v) } })} />
              <SelectField
                label="How much"
                value={rc.mode}
                options={{ fill_bracket: 'Fill a tax bracket', fixed: 'Fixed amount' }}
                onChange={(mode) => onChange({ ...plan, roth_conversion: { ...rc, mode } })}
              />
              {rc.mode === 'fixed' ? (
                <NumberField label="Amount / yr" unit="money" value={rc.annual_amount} onChange={(v) => onChange({ ...plan, roth_conversion: { ...rc, annual_amount: v ?? 0 } })} />
              ) : (
                <SelectField
                  label="Up to the top of"
                  value={String(rc.bracket_rate)}
                  options={{ '0.1': '10% bracket', '0.12': '12% bracket', '0.22': '22% bracket', '0.24': '24% bracket', '0.32': '32% bracket' }}
                  onChange={(v) => onChange({ ...plan, roth_conversion: { ...rc, bracket_rate: Number(v) } })}
                />
              )}
            </div>
          )}
        </Section>
      </div>
    </aside>
  )
}
