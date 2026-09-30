// Saving and opening client plan files (one JSON file per client).

import type { Plan } from './types'

export const PLAN_FILE_VERSION = 1

export function samplePlan(): Plan {
  return {
    version: PLAN_FILE_VERSION,
    client: {
      name: 'Sample Client',
      date_of_birth: '1994-04-15',
      state: 'TX',
      retirement_age: 65,
      life_expectancy: 92,
    },
    income: { annual_income: 95000, annual_raise: 0.03 },
    spending: { current_annual: 55000, retirement_annual: 60000, inflation: 0.025 },
    accounts: [
      newAccount({ name: '401(k)', type: 'traditional', balance: 48000, annual_contribution: 11000 }),
      newAccount({ name: 'Roth IRA', type: 'roth', balance: 21000, annual_contribution: 7000 }),
      newAccount({ name: 'Brokerage', type: 'taxable', balance: 12000, annual_contribution: 3000 }),
    ],
  }
}

export function newAccount(fields: Partial<Plan['accounts'][number]> = {}): Plan['accounts'][number] {
  return {
    id: crypto.randomUUID(),
    name: 'New account',
    type: 'taxable',
    balance: 0,
    annual_contribution: 0,
    contribution_start_year: null,
    contribution_stop_year: null,
    expected_return: 0.07,
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

// Parses a plan file. Full validation happens on the backend before it is used.
export async function readPlanFile(file: File): Promise<Plan> {
  let data: unknown
  try {
    data = JSON.parse(await file.text())
  } catch {
    throw new Error(`${file.name} is not a valid plan file (not JSON).`)
  }
  const plan = data as Plan
  if (!plan || typeof plan !== 'object' || !plan.client || !Array.isArray(plan.accounts)) {
    throw new Error(`${file.name} is not a plan file.`)
  }
  if (plan.version > PLAN_FILE_VERSION) {
    throw new Error(`${file.name} was made by a newer version of this app.`)
  }
  return plan
}
