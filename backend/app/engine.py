"""Year-by-year projection of a client's accounts, income and spending.

Order of events within each projected year:
  1. Retired years: spending is withdrawn from the accounts at the start of
     the year, proportionally to each account's balance.
  2. Each account grows by its expected return.
  3. Contributions are added at the end of the year.

Phase 1 ignores taxes, Social Security and other retirement income, so
retirement spending is funded entirely from the accounts.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, Optional

from .models import Plan, Projection, Summary, YearRow


def _round(x: float) -> float:
    return round(x, 2)


def project(plan: Plan, start_year: Optional[int] = None) -> Projection:
    start_year = start_year or date.today().year
    client = plan.client
    birth_year = client.date_of_birth.year
    retirement_year = birth_year + client.retirement_age
    end_year = birth_year + client.life_expectancy

    if end_year < start_year:
        raise ValueError("life expectancy is already past")

    balances: Dict[str, float] = {a.id: a.balance for a in plan.accounts}
    years = []
    balance_at_retirement: Optional[float] = None
    balance_at_retirement_real: Optional[float] = None
    depletion_age: Optional[int] = None

    for year in range(start_year, end_year + 1):
        t = year - start_year
        age = year - birth_year
        retired = year >= retirement_year
        price_level = (1 + plan.spending.inflation) ** t

        if retired and balance_at_retirement is None:
            balance_at_retirement = sum(balances.values())
            balance_at_retirement_real = balance_at_retirement / price_level

        income = 0.0 if retired else plan.income.annual_income * (1 + plan.income.annual_raise) ** t
        base_spending = plan.spending.retirement_annual if retired else plan.spending.current_annual
        spending = base_spending * price_level

        # 1. Retirement withdrawals, proportional to balances.
        withdrawals = shortfall = 0.0
        if retired:
            available = sum(balances.values())
            withdrawals = min(spending, available)
            shortfall = spending - withdrawals
            if available > 0:
                for acct_id in balances:
                    balances[acct_id] -= withdrawals * balances[acct_id] / available
            if shortfall > 0.005 and depletion_age is None:
                depletion_age = age

        # 2. Growth, then 3. end-of-year contributions.
        contributions = 0.0
        for acct in plan.accounts:
            balances[acct.id] *= 1 + acct.expected_return
            start = acct.contribution_start_year if acct.contribution_start_year is not None else start_year
            stop = acct.contribution_stop_year if acct.contribution_stop_year is not None else retirement_year - 1
            if start <= year <= stop:
                balances[acct.id] += acct.annual_contribution
                contributions += acct.annual_contribution

        total = sum(balances.values())
        years.append(
            YearRow(
                year=year,
                age=age,
                retired=retired,
                income=_round(income),
                spending=_round(spending),
                contributions=_round(contributions),
                withdrawals=_round(withdrawals),
                shortfall=_round(shortfall),
                surplus=0.0 if retired else _round(income - spending - contributions),
                balances={k: _round(v) for k, v in balances.items()},
                total=_round(total),
                total_today_dollars=_round(total / price_level),
            )
        )

    # life_expectancy > retirement_age is validated, so a retired year always runs.
    assert balance_at_retirement is not None and balance_at_retirement_real is not None

    return Projection(
        summary=Summary(
            start_year=start_year,
            retirement_year=retirement_year,
            balance_at_retirement=_round(balance_at_retirement),
            balance_at_retirement_today_dollars=_round(balance_at_retirement_real),
            final_balance=years[-1].total,
            depletion_age=depletion_age,
        ),
        years=years,
    )
