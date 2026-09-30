// Mirrors backend/app/models.py. Rates are decimals: 0.07 means 7%.

export type AccountType = 'taxable' | 'traditional' | 'roth' | '529' | 'hsa'

export const ACCOUNT_TYPE_LABELS: Record<AccountType, string> = {
  taxable: 'Taxable brokerage',
  traditional: 'Traditional IRA / 401(k)',
  roth: 'Roth IRA / 401(k)',
  '529': '529 education',
  hsa: 'HSA',
}

export interface Holding {
  ticker: string
  shares: number
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
  volatility: number | null
  holdings: Holding[]
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

export interface Financing {
  down_payment_share: number
  rate: number
  years: number
}

export interface Goal {
  id: string
  name: string
  category: GoalCategory
  annual_amount: number // today's dollars, per year (the price, for a financed goal)
  start_year: number
  years: number
  financing: Financing | null
}

export type DebtKind = 'mortgage' | 'auto' | 'student' | 'credit_card' | 'other'

export const DEBT_KIND_LABELS: Record<DebtKind, string> = {
  mortgage: 'Mortgage',
  auto: 'Auto loan',
  student: 'Student loan',
  credit_card: 'Credit card',
  other: 'Other',
}

export interface Debt {
  id: string
  name: string
  kind: DebtKind
  balance: number
  rate: number
  annual_payment: number
}

export type InflowKind = 'inheritance' | 'home_sale' | 'gift' | 'other'

export const INFLOW_KIND_LABELS: Record<InflowKind, string> = {
  inheritance: 'Inheritance',
  home_sale: 'Home sale',
  gift: 'Gift',
  other: 'Other',
}

export interface Inflow {
  id: string
  name: string
  kind: InflowKind
  amount: number // today's dollars
  year: number
  account_id: string | null
}

export interface RothConversion {
  start_year: number
  end_year: number
  mode: 'fixed' | 'fill_bracket'
  annual_amount: number
  bracket_rate: number
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
  debts: Debt[]
  inflows: Inflow[]
  surplus_account_id: string | null
  roth_conversion: RothConversion | null
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
  state_tax: number
  debt_payments: number
  inflows: number
  roth_conversion: number
  shortfall: number
  surplus: number
  balances: Record<string, number>
  total: number
  total_today_dollars: number
  debt: number
  property: number
  net_worth: number
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
    lifetime_taxes_today_dollars: number
    goals: { id: string; name: string; total_cost: number; funded_share: number }[]
    debts: { id: string; name: string; payoff_age: number | null }[]
    state: string | null
  }
  years: YearRow[]
}

export interface Simulation {
  runs: number
  success_probability: number
  goals: { id: string; name: string; probability: number }[]
  bands: { age: number; p10: number; p25: number; p50: number; p75: number; p90: number }[]
}

export interface ScenarioResult {
  name: string
  lifetime_taxes: number
  lifetime_taxes_today_dollars: number
  balance_at_retirement_today_dollars: number
  final_net_worth_today_dollars: number
  after_tax_final_today_dollars: number
  depletion_age: number | null
}

export type ComparisonKind = 'contribution_type' | 'roth_conversion'

export interface Comparison {
  kind: ComparisonKind
  scenarios: ScenarioResult[]
  better: string
  difference_today_dollars: number
}

export interface HoldingAnalysis {
  ticker: string
  name: string
  kind: string
  shares: number
  price: number
  value: number
  weight: number
  annual_return: number | null
  volatility: number | null
  years_of_data: number | null
  asset_classes: Record<string, number>
  error: string | null
}

export interface AccountAnalysis {
  value: number
  holdings: HoldingAnalysis[]
  annual_return: number | null
  volatility: number | null
  years_of_data: number | null
  asset_classes: Record<string, number>
  sectors: Record<string, number>
}

export interface StateOption {
  code: string
  name: string
  income_tax: boolean
}
