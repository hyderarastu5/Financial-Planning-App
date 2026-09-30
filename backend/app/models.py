"""Data shapes for a client plan (input) and its projection (output).

A Plan is exactly what gets saved to and loaded from a client's plan file.
Rates are decimals: 0.07 means 7%. Money is in nominal dollars unless a
field says otherwise.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

# 2: filing status, healthcare, cost basis, income streams, goals. 3: holdings, volatility.
# 4: debts, goal financing, one-time inflows, surplus account, Roth conversions.
PLAN_FILE_VERSION = 4


class AccountType(str, Enum):
    taxable = "taxable"
    traditional = "traditional"  # Traditional IRA / 401(k)
    roth = "roth"  # Roth IRA / Roth 401(k)
    education_529 = "529"
    hsa = "hsa"


class Client(BaseModel):
    name: str = ""
    date_of_birth: date
    filing_status: Literal["single", "married_joint"] = "single"  # joint assumes spouse is the same age
    state: str = ""  # residence; used for state tax in a later phase
    retirement_age: int = Field(ge=18, le=100)
    life_expectancy: int = Field(ge=18, le=120)

    @model_validator(mode="after")
    def _retire_before_death(self) -> "Client":
        if self.life_expectancy <= self.retirement_age:
            raise ValueError("life_expectancy must be greater than retirement_age")
        return self


class Income(BaseModel):
    annual_income: float = Field(ge=0)
    annual_raise: float = Field(default=0.03, ge=-0.5, le=0.5)


class Spending(BaseModel):
    current_annual: float = Field(ge=0)  # what they spend now
    retirement_annual: float = Field(ge=0)  # what they want to spend in retirement, today's dollars
    inflation: float = Field(default=0.025, ge=-0.1, le=0.2)
    healthcare_annual: float = Field(default=0, ge=0)  # on top of the above, today's dollars
    healthcare_inflation: float = Field(default=0.05, ge=-0.1, le=0.3)


class Holding(BaseModel):
    ticker: str = Field(min_length=1, max_length=15)
    shares: float = Field(ge=0)


DEFAULT_VOLATILITY = 0.15  # roughly a stock-heavy portfolio


class Account(BaseModel):
    id: str
    name: str
    type: AccountType = AccountType.taxable
    balance: float = Field(ge=0)
    annual_contribution: float = Field(default=0, ge=0)
    contribution_start_year: Optional[int] = None  # default: this year
    contribution_stop_year: Optional[int] = None  # default: year before retirement
    expected_return: float = Field(default=0.07, ge=-0.5, le=0.5)
    # Taxable: cost basis. Roth: total contributions so far (withdrawn tax-free first).
    # None means the whole current balance is basis.
    cost_basis: Optional[float] = Field(default=None, ge=0)
    # Year-to-year swing in returns (standard deviation), used by the Monte Carlo simulation.
    volatility: Optional[float] = Field(default=None, ge=0, le=1)  # None: DEFAULT_VOLATILITY
    holdings: List[Holding] = []  # optional; used to look up live prices and history

    @model_validator(mode="after")
    def _start_before_stop(self) -> "Account":
        start, stop = self.contribution_start_year, self.contribution_stop_year
        if start is not None and stop is not None and stop < start:
            raise ValueError(f"{self.name}: contribution_stop_year is before contribution_start_year")
        return self


IncomeKind = Literal["social_security", "pension", "annuity", "business", "rental", "other"]


class IncomeStream(BaseModel):
    """Income besides salary: Social Security, pensions, annuities, business or rental income."""

    id: str
    name: str
    kind: IncomeKind = "other"
    annual_amount: float = Field(ge=0)  # today's dollars
    start_age: int = Field(ge=0, le=120)
    end_age: Optional[int] = Field(default=None, ge=0, le=120)  # None: for life
    inflation_adjusted: bool = True  # grows with inflation (COLA); otherwise fixed in nominal dollars
    taxable_share: float = Field(default=1.0, ge=0, le=1)  # ignored for Social Security, which has its own rules

    @model_validator(mode="after")
    def _start_before_end(self) -> "IncomeStream":
        if self.end_age is not None and self.end_age < self.start_age:
            raise ValueError(f"{self.name}: end_age is before start_age")
        return self


GoalCategory = Literal["home", "college", "home_improvement", "travel", "charity", "healthcare", "family", "other"]


class Financing(BaseModel):
    """Pay for a goal with a loan: a down payment in the goal's year, then fixed yearly payments."""

    down_payment_share: float = Field(default=0.2, ge=0, le=1)
    rate: float = Field(ge=0, le=0.3)  # yearly interest rate
    years: int = Field(default=30, ge=1, le=40)


class Goal(BaseModel):
    """A cost in one year, or every year for a run of years. College goals are paid from 529 accounts first.
    A home goal also adds the home to net worth from its purchase year, growing with inflation."""

    id: str
    name: str
    category: GoalCategory = "other"
    annual_amount: float = Field(ge=0)  # today's dollars, per year (the price, for a financed goal)
    start_year: int
    years: int = Field(default=1, ge=1, le=100)
    financing: Optional[Financing] = None

    @model_validator(mode="after")
    def _financed_is_one_time(self) -> "Goal":
        if self.financing is not None and self.years != 1:
            raise ValueError(f"{self.name}: a financed goal is a one-time purchase (years must be 1)")
        return self


DebtKind = Literal["mortgage", "auto", "student", "credit_card", "other"]


class Debt(BaseModel):
    """An existing loan, paid down by a fixed yearly payment until it's gone."""

    id: str
    name: str
    kind: DebtKind = "other"
    balance: float = Field(ge=0)
    rate: float = Field(ge=0, le=0.4)  # yearly interest rate
    annual_payment: float = Field(ge=0)


InflowKind = Literal["inheritance", "home_sale", "gift", "other"]


class Inflow(BaseModel):
    """One-time money coming in, e.g. an inheritance. Treated as tax-free (inheritances,
    gifts and a primary home's sale gain within the exclusion are), with full cost basis."""

    id: str
    name: str
    kind: InflowKind = "inheritance"
    amount: float = Field(ge=0)  # today's dollars
    year: int
    account_id: Optional[str] = None  # taxable account to deposit into; None: the first taxable account


class RothConversion(BaseModel):
    """Move money from traditional to Roth accounts each year, paying the income tax now."""

    start_year: int
    end_year: int
    mode: Literal["fixed", "fill_bracket"] = "fill_bracket"
    annual_amount: float = Field(default=0, ge=0)  # fixed mode, nominal dollars
    bracket_rate: float = 0.12  # fill_bracket mode: convert up to the top of this federal bracket

    @model_validator(mode="after")
    def _valid(self) -> "RothConversion":
        if self.end_year < self.start_year:
            raise ValueError("Roth conversion end_year is before start_year")
        if self.mode == "fill_bracket" and self.bracket_rate not in (0.10, 0.12, 0.22, 0.24, 0.32, 0.35):
            raise ValueError("bracket_rate must be a federal bracket rate below 37%")
        return self


class Plan(BaseModel):
    version: int = PLAN_FILE_VERSION
    client: Client
    income: Income
    spending: Spending
    accounts: List[Account] = []
    income_streams: List[IncomeStream] = []
    goals: List[Goal] = []
    debts: List[Debt] = []
    inflows: List[Inflow] = []
    # Taxable account that leftover cash is invested in every year. None: leftover cash is
    # unallocated while working and goes to the first taxable account in retirement.
    surplus_account_id: Optional[str] = None
    roth_conversion: Optional[RothConversion] = None

    @model_validator(mode="after")
    def _consistent(self) -> "Plan":
        for label, items in (("account", self.accounts), ("income", self.income_streams), ("goal", self.goals),
                             ("debt", self.debts), ("inflow", self.inflows)):
            ids = [x.id for x in items]
            if len(ids) != len(set(ids)):
                raise ValueError(f"{label} ids must be unique")
        taxable_ids = {a.id for a in self.accounts if a.type == AccountType.taxable}
        if self.surplus_account_id is not None and self.surplus_account_id not in taxable_ids:
            raise ValueError("surplus_account_id must be a taxable account in this plan")
        for f in self.inflows:
            if f.account_id is not None and f.account_id not in taxable_ids:
                raise ValueError(f"{f.name}: account_id must be a taxable account in this plan")
        return self


class YearRow(BaseModel):
    year: int
    age: int
    retired: bool
    income: float  # salary
    other_income: float  # income streams, including Social Security
    spending: float  # living expenses
    healthcare: float
    goals: float
    contributions: float
    withdrawals: float  # everything taken out of accounts, including RMDs
    savings_drawn: float  # part of withdrawals that covered a cash gap (not RMDs, 529 or HSA money)
    rmd: float  # required minimum distributions (part of withdrawals)
    income_tax: float
    payroll_tax: float
    penalties: float  # early-withdrawal penalties
    state_tax: float
    debt_payments: float  # existing debts; financed goals' payments are in goals
    inflows: float  # inheritances and other one-time money
    roth_conversion: float
    shortfall: float  # costs that income and accounts could not cover
    surplus: float  # cash left after all costs; reinvested in retirement, unallocated while working
    balances: dict  # account id -> end-of-year balance
    total: float  # end-of-year total, nominal dollars
    total_today_dollars: float  # total deflated to the first projection year
    debt: float  # remaining debt, including loans on financed goals
    property: float  # value of homes bought through home goals
    net_worth: float  # total + property - debt


class GoalResult(BaseModel):
    id: str
    name: str
    total_cost: float  # nominal dollars
    funded_share: float  # 0..1 of the cost the plan pays for


class DebtResult(BaseModel):
    id: str
    name: str
    payoff_age: Optional[int]  # None: not paid off within the plan


class Summary(BaseModel):
    start_year: int
    retirement_year: int
    balance_at_retirement: float
    balance_at_retirement_today_dollars: float
    final_balance: float
    depletion_age: Optional[int]  # first retired age the accounts could not cover costs
    lifetime_taxes: float  # federal + state income tax, payroll tax and penalties, nominal
    lifetime_taxes_today_dollars: float  # the same, each year's taxes deflated to today's dollars
    goals: List[GoalResult]
    debts: List[DebtResult]
    state: Optional[str]  # state code whose tax was applied; None if the plan's state isn't recognized


class Projection(BaseModel):
    summary: Summary
    years: List[YearRow]


# --- Market data ---------------------------------------------------------------------------

class HoldingAnalysis(BaseModel):
    ticker: str
    name: str
    kind: str
    shares: float
    price: float
    value: float
    weight: float  # share of the account's value
    annual_return: Optional[float]  # compound annual growth over the history available
    volatility: Optional[float]
    years_of_data: Optional[float]
    asset_classes: dict
    error: Optional[str] = None  # set when this ticker couldn't be looked up


class AccountAnalysis(BaseModel):
    value: float
    holdings: List[HoldingAnalysis]
    # Whole-account figures over the months every holding has data for.
    annual_return: Optional[float]
    volatility: Optional[float]
    years_of_data: Optional[float]
    asset_classes: dict  # stock / bond / cash / other -> share
    sectors: dict


# --- Monte Carlo -----------------------------------------------------------------------------

class SimulationRequest(BaseModel):
    plan: Plan
    runs: int = Field(default=1000, ge=50, le=5000)
    seed: Optional[int] = None


class GoalProbability(BaseModel):
    id: str
    name: str
    probability: float  # share of runs where the goal is fully funded


class Band(BaseModel):
    """Total balance across runs at one age, in today's dollars."""

    age: int
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float


class Simulation(BaseModel):
    runs: int
    success_probability: float  # share of runs where the money lasts to life expectancy
    goals: List[GoalProbability]
    bands: List[Band]
