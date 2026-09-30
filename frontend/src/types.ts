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
}

export interface Plan {
  version: number
  client: {
    name: string
    date_of_birth: string // YYYY-MM-DD
    state: string
    retirement_age: number
    life_expectancy: number
  }
  income: { annual_income: number; annual_raise: number }
  spending: { current_annual: number; retirement_annual: number; inflation: number }
  accounts: Account[]
}

export interface YearRow {
  year: number
  age: number
  retired: boolean
  income: number
  spending: number
  contributions: number
  withdrawals: number
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
  }
  years: YearRow[]
}
