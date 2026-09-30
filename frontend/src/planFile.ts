// Client plan files: one JSON file per client, optionally password-protected.

import type { Account, Debt, Goal, IncomeStream, Inflow, Plan } from './types'

// 2: filing status, healthcare, cost basis, income streams, goals. 3: holdings, volatility.
// 4: debts, goal financing, one-time inflows, surplus account, Roth conversions.
export const PLAN_FILE_VERSION = 4

const id = () => crypto.randomUUID()
const nextYear = () => new Date().getFullYear() + 1

export function newAccount(fields: Partial<Account> = {}): Account {
  return {
    id: id(),
    name: 'New account',
    type: 'taxable',
    balance: 0,
    annual_contribution: 0,
    contribution_start_year: null,
    contribution_stop_year: null,
    expected_return: 0.07,
    cost_basis: null,
    volatility: null,
    holdings: [],
    ...fields,
  }
}

export function newIncomeStream(fields: Partial<IncomeStream> = {}): IncomeStream {
  return {
    id: id(),
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
    id: id(),
    name: 'New goal',
    category: 'other',
    annual_amount: 0,
    start_year: nextYear(),
    years: 1,
    financing: null,
    ...fields,
  }
}

export function newDebt(fields: Partial<Debt> = {}): Debt {
  return { id: id(), name: 'New debt', kind: 'other', balance: 0, rate: 0.06, annual_payment: 0, ...fields }
}

export function newInflow(fields: Partial<Inflow> = {}): Inflow {
  return { id: id(), name: 'Inheritance', kind: 'inheritance', amount: 0, year: nextYear(), account_id: null, ...fields }
}

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
      newAccount({
        name: 'Brokerage',
        type: 'taxable',
        balance: 12000,
        annual_contribution: 3000,
        cost_basis: 10000,
        holdings: [
          { ticker: 'VTI', shares: 22 },
          { ticker: 'BND', shares: 53 },
        ],
      }),
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
    debts: [],
    inflows: [],
    surplus_account_id: null,
    roth_conversion: null,
  }
}

// Fills in fields added since older file versions, with the same defaults the backend uses.
export function upgrade(plan: Plan): Plan {
  return {
    ...plan,
    version: PLAN_FILE_VERSION,
    client: { ...plan.client, filing_status: plan.client.filing_status ?? 'single' },
    spending: {
      ...plan.spending,
      healthcare_annual: plan.spending.healthcare_annual ?? 0,
      healthcare_inflation: plan.spending.healthcare_inflation ?? 0.05,
    },
    accounts: plan.accounts.map((a) => ({
      ...a,
      cost_basis: a.cost_basis ?? null,
      volatility: a.volatility ?? null,
      holdings: a.holdings ?? [],
    })),
    income_streams: plan.income_streams ?? [],
    goals: (plan.goals ?? []).map((g) => ({ ...g, financing: g.financing ?? null })),
    debts: plan.debts ?? [],
    inflows: plan.inflows ?? [],
    surplus_account_id: plan.surplus_account_id ?? null,
    roth_conversion: plan.roth_conversion ?? null,
  }
}

// --- password protection ---------------------------------------------------------------------
// AES-GCM with a key derived from the password by PBKDF2-SHA256. Without the password the file
// can't be read; there is no recovery.

const ENCRYPTED_FORMAT = 'financial-planner-encrypted'
const PBKDF2_ITERATIONS = 600_000

interface EncryptedFile {
  format: typeof ENCRYPTED_FORMAT
  version: 1
  iterations: number
  salt: string
  iv: string
  ciphertext: string
}

const toBase64 = (bytes: Uint8Array) => btoa(String.fromCharCode(...bytes))
const fromBase64 = (text: string) => Uint8Array.from(atob(text), (ch) => ch.charCodeAt(0))

async function deriveKey(password: string, salt: Uint8Array, iterations: number) {
  const material = await crypto.subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, [
    'deriveKey',
  ])
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt: salt as BufferSource, iterations, hash: 'SHA-256' },
    material,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  )
}

export async function encryptPlan(plan: Plan, password: string): Promise<EncryptedFile> {
  const salt = crypto.getRandomValues(new Uint8Array(16))
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const key = await deriveKey(password, salt, PBKDF2_ITERATIONS)
  const data = new TextEncoder().encode(JSON.stringify(plan))
  const ciphertext = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, data))
  return {
    format: ENCRYPTED_FORMAT,
    version: 1,
    iterations: PBKDF2_ITERATIONS,
    salt: toBase64(salt),
    iv: toBase64(iv),
    ciphertext: toBase64(ciphertext),
  }
}

async function decryptPlan(file: EncryptedFile, password: string): Promise<unknown> {
  const key = await deriveKey(password, fromBase64(file.salt), file.iterations)
  try {
    const data = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: fromBase64(file.iv) as BufferSource },
      key,
      fromBase64(file.ciphertext) as BufferSource,
    )
    return JSON.parse(new TextDecoder().decode(data))
  } catch {
    throw new Error('Wrong password.')
  }
}

// --- files ---------------------------------------------------------------------------------------

export function planFileName(plan: Plan) {
  const slug = (plan.client.name || 'client').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-')
  return `${slug}-plan.json`
}

export async function downloadPlan(plan: Plan, password?: string) {
  const content = password ? await encryptPlan(plan, password) : plan
  const blob = new Blob([JSON.stringify(content, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = planFileName(plan)
  a.click()
  URL.revokeObjectURL(url)
}

export type ParsedFile = { kind: 'plan'; plan: Plan } | { kind: 'locked'; open: (password: string) => Promise<Plan> }

function toPlan(data: unknown, fileName: string): Plan {
  const plan = data as Plan
  if (!plan || typeof plan !== 'object' || !plan.client || !plan.spending || !Array.isArray(plan.accounts)) {
    throw new Error(`${fileName} is not a plan file.`)
  }
  if (plan.version > PLAN_FILE_VERSION) {
    throw new Error(`${fileName} was made by a newer version of this app.`)
  }
  return upgrade(plan)
}

// Reads a plan file. A password-protected file comes back locked, to be opened with its password.
// Full validation happens on the backend before the plan is used.
export async function readPlanFile(file: File): Promise<ParsedFile> {
  let data: unknown
  try {
    data = JSON.parse(await file.text())
  } catch {
    throw new Error(`${file.name} is not a valid plan file (not JSON).`)
  }
  if ((data as EncryptedFile)?.format === ENCRYPTED_FORMAT) {
    return {
      kind: 'locked',
      open: async (password) => toPlan(await decryptPlan(data as EncryptedFile, password), file.name),
    }
  }
  return { kind: 'plan', plan: toPlan(data, file.name) }
}
