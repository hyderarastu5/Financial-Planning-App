"""Data shapes for a client plan (input) and its projection (output).

A Plan is exactly what gets saved to and loaded from a client's plan file.
Rates are decimals: 0.07 means 7%. Money is in nominal dollars unless a
field says otherwise.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

PLAN_FILE_VERSION = 1


class AccountType(str, Enum):
    taxable = "taxable"
    traditional = "traditional"  # Traditional IRA / 401(k)
    roth = "roth"  # Roth IRA / Roth 401(k)
    education_529 = "529"
    hsa = "hsa"


class Client(BaseModel):
    name: str = ""
    date_of_birth: date
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


class Account(BaseModel):
    id: str
    name: str
    type: AccountType = AccountType.taxable
    balance: float = Field(ge=0)
    annual_contribution: float = Field(default=0, ge=0)
    contribution_start_year: Optional[int] = None  # default: this year
    contribution_stop_year: Optional[int] = None  # default: year before retirement
    expected_return: float = Field(default=0.07, ge=-0.5, le=0.5)

    @model_validator(mode="after")
    def _start_before_stop(self) -> "Account":
        start, stop = self.contribution_start_year, self.contribution_stop_year
        if start is not None and stop is not None and stop < start:
            raise ValueError(f"{self.name}: contribution_stop_year is before contribution_start_year")
        return self


class Plan(BaseModel):
    version: int = PLAN_FILE_VERSION
    client: Client
    income: Income
    spending: Spending
    accounts: List[Account] = []

    @model_validator(mode="after")
    def _unique_account_ids(self) -> "Plan":
        ids = [a.id for a in self.accounts]
        if len(ids) != len(set(ids)):
            raise ValueError("account ids must be unique")
        return self


class YearRow(BaseModel):
    year: int
    age: int
    retired: bool
    income: float
    spending: float
    contributions: float
    withdrawals: float
    shortfall: float  # spending that the accounts could not cover
    surplus: float  # income - spending - contributions (working years only)
    balances: dict  # account id -> end-of-year balance
    total: float  # end-of-year total, nominal dollars
    total_today_dollars: float  # total deflated to the first projection year


class Summary(BaseModel):
    start_year: int
    retirement_year: int
    balance_at_retirement: float
    balance_at_retirement_today_dollars: float
    final_balance: float
    depletion_age: Optional[int]  # first age the accounts could not cover spending


class Projection(BaseModel):
    summary: Summary
    years: List[YearRow]
