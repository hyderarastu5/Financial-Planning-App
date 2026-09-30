// Mirrors backend/app/models.py. Rates are decimals: 0.07 means 7%.

export type AccountType = 'taxable' | 'traditional' | 'roth' | '529' | 'hsa'

export const ACCOUNT_TYPE_LABELS: Record<AccountType, string> = {
  taxable: 'Taxable brokerage',
  traditional: 'Traditional IRA / 401(k)',
  roth: 'Roth IRA / 401(k)',
  '529': '529 education',
  hsa: 'HSA',
}

export interface Account {
  id: string
  name: string
  type: AccountType
  balance: number
  annual_contribution: number
  contribution_start_year: number | null
  contribution_stop_year: number | null
  expected_return: number
  cost_basis: number | null
}

export type IncomeKind = 'social_security' | 'pension' | 'annuity' | 'business' | 'rental' | 'other'

export const INCOME_KIND_LABELS: Record<IncomeKind, string> = {
  social_security: 'Social Security',
  pension: 'Pension',
  annuity: 'Annuity',
  business: 'Business income',
  rental: 'Rental income',
  other: 'Other',
}

export interface IncomeStream {
  id: string
  name: string
  kind: IncomeKind
  annual_amount: number // today's dollars
  start_age: number
  end_age: number | null
  inflation_adjusted: boolean
  taxable_share: number
}

export type GoalCategory =
  | 'home'
  | 'college'
  | 'home_improvement'
  | 'travel'
  | 'charity'
  | 'healthcare'
  | 'family'
  | 'other'

export const GOAL_CATEGORY_LABELS: Record<GoalCategory, string> = {
  home: 'Home purchase',
  college: 'College (529 pays first)',
  home_improvement: 'Home improvement',
  travel: 'Travel',
  charity: 'Charitable giving',
  healthcare: 'Healthcare',
  family: 'Kids / grandkids',
  other: 'Other',
}

export interface Goal {
  id: string
  name: string
  category: GoalCategory
  annual_amount: number // today's dollars, per year
  start_year: number
  years: number
}

export type FilingStatus = 'single' | 'married_joint'

export interface Plan {
  version: number
  client: {
    name: string
    date_of_birth: string // YYYY-MM-DD
    filing_status: FilingStatus
    state: string
    retirement_age: number
    life_expectancy: number
  }
  income: { annual_income: number; annual_raise: number }
  spending: {
    current_annual: number
    retirement_annual: number
    inflation: number
    healthcare_annual: number
    healthcare_inflation: number
  }
  accounts: Account[]
  income_streams: IncomeStream[]
  goals: Goal[]
}

export interface YearRow {
  year: number
  age: number
  retired: boolean
  income: number
  other_income: number
  spending: number
  healthcare: number
  goals: number
  contributions: number
  withdrawals: number
  savings_drawn: number
  rmd: number
  income_tax: number
  payroll_tax: number
  penalties: number
  shortfall: number
  surplus: number
  balances: Record<string, number>
  total: number
  total_today_dollars: number
}

export interface Projection {
  summary: {
    start_year: number
    retirement_year: number
    balance_at_retirement: number
    balance_at_retirement_today_dollars: number
    final_balance: number
    depletion_age: number | null
    lifetime_taxes: number
    goals: { id: string; name: string; total_cost: number; funded_share: number }[]
  }
  years: YearRow[]
}
