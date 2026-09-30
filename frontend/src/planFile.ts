// Saving and opening client plan files (one JSON file per client).

import type { Account, Goal, IncomeStream, Plan } from './types'

// 2: filing status, healthcare, cost basis, income streams, goals. 3: holdings, volatility.
// 4: debts, goal financing, one-time inflows, surplus account, Roth conversions.
// Fields from versions 3-4 have no editing screens yet; they're kept as-is when a file is opened and saved.
export const PLAN_FILE_VERSION = 4

export function samplePlan(): Plan {
  return {
    version: PLAN_FILE_VERSION,
    client: {
      name: 'Sample Client',
      date_of_birth: '1994-04-15',
      filing_status: 'single',
      state: 'TX',
      retirement_age: 65,
      life_expectancy: 92,
    },
    income: { annual_income: 95000, annual_raise: 0.03 },
    spending: {
      current_annual: 48000,
      retirement_annual: 60000,
      inflation: 0.025,
      healthcare_annual: 4000,
      healthcare_inflation: 0.05,
    },
    accounts: [
      newAccount({ name: '401(k)', type: 'traditional', balance: 48000, annual_contribution: 11000 }),
      newAccount({ name: 'Roth IRA', type: 'roth', balance: 21000, annual_contribution: 7000, cost_basis: 18000 }),
      newAccount({ name: 'Brokerage', type: 'taxable', balance: 12000, annual_contribution: 3000, cost_basis: 10000 }),
      newAccount({ name: "Kid's 529", type: '529', balance: 5000, annual_contribution: 2400, contribution_stop_year: 2043 }),
    ],
    income_streams: [
      newIncomeStream({ name: 'Social Security', kind: 'social_security', annual_amount: 30000, start_age: 67 }),
    ],
    goals: [
      newGoal({ name: 'Kitchen remodel', category: 'home_improvement', annual_amount: 30000, start_year: 2032 }),
      newGoal({ name: "Kid's college", category: 'college', annual_amount: 25000, start_year: 2044, years: 4 }),
      newGoal({ name: 'Retirement travel', category: 'travel', annual_amount: 8000, start_year: 2059, years: 10 }),
    ],
  }
}

export function newAccount(fields: Partial<Account> = {}): Account {
  return {
    id: crypto.randomUUID(),
    name: 'New account',
    type: 'taxable',
    balance: 0,
    annual_contribution: 0,
    contribution_start_year: null,
    contribution_stop_year: null,
    expected_return: 0.07,
    cost_basis: null,
    ...fields,
  }
}

export function newIncomeStream(fields: Partial<IncomeStream> = {}): IncomeStream {
  return {
    id: crypto.randomUUID(),
    name: 'New income',
    kind: 'other',
    annual_amount: 0,
    start_age: 65,
    end_age: null,
    inflation_adjusted: true,
    taxable_share: 1,
    ...fields,
  }
}

export function newGoal(fields: Partial<Goal> = {}): Goal {
  return {
    id: crypto.randomUUID(),
    name: 'New goal',
    category: 'other',
    annual_amount: 0,
    start_year: new Date().getFullYear() + 1,
    years: 1,
    ...fields,
  }
}

export function downloadPlan(plan: Plan) {
  const slug = (plan.client.name || 'client').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-')
  const blob = new Blob([JSON.stringify(plan, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${slug}-plan.json`
  a.click()
  URL.revokeObjectURL(url)
}

// Fills in fields added since older file versions, so older plans open with the same defaults the backend uses.
function upgrade(plan: Plan): Plan {
  return {
    ...plan,
    version: PLAN_FILE_VERSION,
    client: { ...plan.client, filing_status: plan.client.filing_status ?? 'single' },
    spending: {
      ...plan.spending,
      healthcare_annual: plan.spending.healthcare_annual ?? 0,
      healthcare_inflation: plan.spending.healthcare_inflation ?? 0.05,
    },
    accounts: plan.accounts.map((a) => ({ ...a, cost_basis: a.cost_basis ?? null })),
    income_streams: plan.income_streams ?? [],
    goals: plan.goals ?? [],
  }
}

// Parses a plan file. Full validation happens on the backend before it is used.
export async function readPlanFile(file: File): Promise<Plan> {
  let data: unknown
  try {
    data = JSON.parse(await file.text())
  } catch {
    throw new Error(`${file.name} is not a valid plan file (not JSON).`)
  }
  const plan = data as Plan
  if (!plan || typeof plan !== 'object' || !plan.client || !plan.spending || !Array.isArray(plan.accounts)) {
    throw new Error(`${file.name} is not a plan file.`)
  }
  if (plan.version > PLAN_FILE_VERSION) {
    throw new Error(`${file.name} was made by a newer version of this app.`)
  }
  return upgrade(plan)
}
