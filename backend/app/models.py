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

PLAN_FILE_VERSION = 2  # 2: filing status, healthcare, cost basis, income streams, goals


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


class Goal(BaseModel):
    """A cost in one year, or every year for a run of years. College goals are paid from 529 accounts first."""

    id: str
    name: str
    category: GoalCategory = "other"
    annual_amount: float = Field(ge=0)  # today's dollars, per year
    start_year: int
    years: int = Field(default=1, ge=1, le=100)


class Plan(BaseModel):
    version: int = PLAN_FILE_VERSION
    client: Client
    income: Income
    spending: Spending
    accounts: List[Account] = []
    income_streams: List[IncomeStream] = []
    goals: List[Goal] = []

    @model_validator(mode="after")
    def _unique_ids(self) -> "Plan":
        for label, items in (("account", self.accounts), ("income", self.income_streams), ("goal", self.goals)):
            ids = [x.id for x in items]
            if len(ids) != len(set(ids)):
                raise ValueError(f"{label} ids must be unique")
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
    shortfall: float  # costs that income and accounts could not cover
    surplus: float  # cash left after all costs; reinvested in retirement, unallocated while working
    balances: dict  # account id -> end-of-year balance
    total: float  # end-of-year total, nominal dollars
    total_today_dollars: float  # total deflated to the first projection year


class GoalResult(BaseModel):
    id: str
    name: str
    total_cost: float  # nominal dollars
    funded_share: float  # 0..1 of the cost the plan pays for


class Summary(BaseModel):
    start_year: int
    retirement_year: int
    balance_at_retirement: float
    balance_at_retirement_today_dollars: float
    final_balance: float
    depletion_age: Optional[int]  # first retired age the accounts could not cover costs
    lifetime_taxes: float  # income + payroll taxes + penalties, nominal
    goals: List[GoalResult]


class Projection(BaseModel):
    summary: Summary
    years: List[YearRow]
