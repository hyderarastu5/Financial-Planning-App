"""Year-by-year projection of a client's accounts, income, costs and taxes.

Order of events within each projected year:
  1. Costs for the year: living expenses, healthcare, goals, contributions.
  2. Tax-free money is used first: 529s pay college goals, HSAs pay healthcare.
  3. Required minimum distributions come out of traditional accounts.
  4. If salary, other income and RMDs don't cover costs plus taxes, the rest is
     withdrawn at the start of the year in this order: taxable accounts,
     traditional accounts, HSAs (from age 65), Roth accounts. The amount is
     solved so that what's left after income tax, payroll tax and penalties
     exactly covers the costs.
  5. Each account grows by its expected return.
  6. Contributions are added at the end of the year. In retirement, leftover
     cash (e.g. RMDs beyond what was needed) is reinvested in the first taxable
     account.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

from . import tax
from .models import Account, AccountType, GoalResult, Plan, Projection, Summary, YearRow


def _round(x: float) -> float:
    return round(x, 2)


@dataclass
class _AccountState:
    spec: Account
    balance: float
    basis: float  # taxable: cost basis; roth: contributions not yet withdrawn

    @property
    def type(self) -> AccountType:
        return self.spec.type


@dataclass
class _Withdrawal:
    amounts: Dict[str, float] = field(default_factory=dict)
    ordinary: float = 0.0  # adds to ordinary income
    gains: float = 0.0  # long-term capital gains
    penalty: float = 0.0
    roth_basis_used: Dict[str, float] = field(default_factory=dict)


def _take_pro_rata(accounts: List[_AccountState], amount: float) -> Dict[str, float]:
    """Split `amount` across accounts in proportion to their balances."""
    total = sum(a.balance for a in accounts)
    if total <= 0 or amount <= 0:
        return {}
    amount = min(amount, total)
    return {a.spec.id: amount * a.balance / total for a in accounts}


def _withdrawal_pools(states: List[_AccountState], age: int) -> List[List[_AccountState]]:
    by_type = lambda t: [s for s in states if s.type == t and s.balance > 0]  # noqa: E731
    pools = [by_type(AccountType.taxable), by_type(AccountType.traditional)]
    if age >= 65:  # HSA money for non-medical use: taxed like a traditional IRA, no penalty
        pools.append(by_type(AccountType.hsa))
    pools.append(by_type(AccountType.roth))
    return [p for p in pools if p]


def _plan_withdrawal(pools: List[List[_AccountState]], amount: float, age: int) -> _Withdrawal:
    w = _Withdrawal()
    early = age < tax.PENALTY_FREE_AGE
    remaining = amount
    for pool in pools:
        if remaining <= 0:
            break
        pool_total = sum(a.balance for a in pool)
        take = min(remaining, pool_total)
        remaining -= take
        for acct_id, amt in _take_pro_rata(pool, take).items():
            s = next(a for a in pool if a.spec.id == acct_id)
            w.amounts[acct_id] = amt
            if s.type == AccountType.taxable:
                w.gains += amt * max(0.0, 1 - s.basis / s.balance)
            elif s.type == AccountType.traditional:
                w.ordinary += amt
                if early:
                    w.penalty += tax.EARLY_WITHDRAWAL_PENALTY * amt
            elif s.type == AccountType.hsa:
                w.ordinary += amt
            elif s.type == AccountType.roth:
                # Contributions come out first, tax- and penalty-free; earnings are
                # taxed and penalized only before 59½.
                basis_used = min(amt, s.basis)
                w.roth_basis_used[acct_id] = basis_used
                if early:
                    earnings = amt - basis_used
                    w.ordinary += earnings
                    w.penalty += tax.EARLY_WITHDRAWAL_PENALTY * earnings
    return w


def project(plan: Plan, start_year: Optional[int] = None) -> Projection:
    start_year = start_year or date.today().year
    client = plan.client
    status = client.filing_status
    birth_year = client.date_of_birth.year
    retirement_year = birth_year + client.retirement_age
    end_year = birth_year + client.life_expectancy

    if end_year < start_year:
        raise ValueError("life expectancy is already past")

    states = [
        _AccountState(spec=a, balance=a.balance,
                      basis=a.balance if a.cost_basis is None else a.cost_basis)
        for a in plan.accounts
    ]
    by_id = {s.spec.id: s for s in states}
    first_taxable = next((s for s in states if s.type == AccountType.taxable), None)

    goal_cost = {g.id: 0.0 for g in plan.goals}
    goal_funded = {g.id: 0.0 for g in plan.goals}

    years = []
    balance_at_retirement: Optional[float] = None
    balance_at_retirement_real: Optional[float] = None
    depletion_age: Optional[int] = None
    lifetime_taxes = 0.0

    for year in range(start_year, end_year + 1):
        t = year - start_year
        age = year - birth_year
        retired = year >= retirement_year
        price_level = (1 + plan.spending.inflation) ** t
        tax_year = tax.TaxYear.for_year(year, status, plan.spending.inflation)

        if retired and balance_at_retirement is None:
            balance_at_retirement = sum(s.balance for s in states)
            balance_at_retirement_real = balance_at_retirement / price_level

        # 1. Income and costs.
        salary = 0.0 if retired else plan.income.annual_income * (1 + plan.income.annual_raise) ** t
        social_security = other_income = other_taxable = 0.0
        for s in plan.income_streams:
            if s.start_age <= age and (s.end_age is None or age <= s.end_age):
                amount = s.annual_amount * (price_level if s.inflation_adjusted else 1)
                other_income += amount
                if s.kind == "social_security":
                    social_security += amount
                else:
                    other_taxable += amount * s.taxable_share

        living = (plan.spending.retirement_annual if retired else plan.spending.current_annual) * price_level
        healthcare = plan.spending.healthcare_annual * (1 + plan.spending.healthcare_inflation) ** t

        goals_now = {g.id: g.annual_amount * price_level for g in plan.goals
                     if g.start_year <= year < g.start_year + g.years}
        goals_total = sum(goals_now.values())
        college_ids = [g.id for g in plan.goals if g.id in goals_now and g.category == "college"]
        college_total = sum(goals_now[i] for i in college_ids)

        contributions: Dict[str, float] = {}
        for s in states:
            a = s.spec
            start = a.contribution_start_year if a.contribution_start_year is not None else start_year
            stop = a.contribution_stop_year if a.contribution_stop_year is not None else retirement_year - 1
            if start <= year <= stop and a.annual_contribution > 0:
                contributions[a.id] = a.annual_contribution
        contributions_total = sum(contributions.values())
        pretax_contributions = sum(amt for acct_id, amt in contributions.items()
                                   if by_id[acct_id].type in (AccountType.traditional, AccountType.hsa))

        # 2. Tax-free money: 529s pay college, HSAs pay healthcare.
        withdrawals = 0.0
        from_529 = min(college_total, sum(s.balance for s in states if s.type == AccountType.education_529))
        from_hsa = min(healthcare, sum(s.balance for s in states if s.type == AccountType.hsa))
        for acct_type, amount in ((AccountType.education_529, from_529), (AccountType.hsa, from_hsa)):
            for acct_id, amt in _take_pro_rata([s for s in states if s.type == acct_type], amount).items():
                by_id[acct_id].balance -= amt
                withdrawals += amt

        # 3. Required minimum distributions.
        rmd = 0.0
        for s in states:
            if s.type == AccountType.traditional:
                amt = min(s.balance, tax.rmd_amount(s.balance, age, birth_year))
                s.balance -= amt
                rmd += amt
        withdrawals += rmd

        # 4. Solve for the withdrawal that covers costs after taxes.
        costs = living + healthcare + goals_total + contributions_total
        cash_in = salary + other_income + rmd + from_529 + from_hsa
        ordinary_base = max(0.0, salary - pretax_contributions) + other_taxable + rmd
        payroll_tax = tax_year.payroll_tax(salary)
        pools = _withdrawal_pools(states, age)
        available = sum(a.balance for pool in pools for a in pool)

        def after_tax_cash(amount: float):
            w = _plan_withdrawal(pools, amount, age)
            income_tax = tax.income_tax(tax_year, ordinary=ordinary_base + w.ordinary, gains=w.gains,
                                        social_security=social_security, age=age)
            return cash_in + amount - costs - income_tax - payroll_tax - w.penalty, w, income_tax

        net, w, income_tax = after_tax_cash(0.0)
        amount = 0.0
        if net < 0:
            net_all, _, _ = after_tax_cash(available)
            if net_all < 0:
                amount = available
            else:
                lo, hi = 0.0, available
                for _ in range(60):
                    mid = (lo + hi) / 2
                    if after_tax_cash(mid)[0] >= 0:
                        hi = mid
                    else:
                        lo = mid
                amount = hi
            net, w, income_tax = after_tax_cash(amount)

        shortfall = max(0.0, -net)
        surplus = max(0.0, net)
        for acct_id, amt in w.amounts.items():
            s = by_id[acct_id]
            if s.type == AccountType.taxable and s.balance > 0:
                s.basis -= s.basis * amt / s.balance
            s.basis -= w.roth_basis_used.get(acct_id, 0.0)
            s.balance -= amt
        withdrawals += amount

        if retired and shortfall > 0.5 and depletion_age is None:
            depletion_age = age

        # Goal funding: 529 money covers college first; a shortfall reduces the rest proportionally.
        cash_needs = living + healthcare + goals_total - from_529 - from_hsa
        funded_share = 1.0 if cash_needs <= 0 else max(0.0, 1 - shortfall / cash_needs)
        for goal_id, cost in goals_now.items():
            paid_by_529 = from_529 * cost / college_total if goal_id in college_ids else 0.0
            goal_cost[goal_id] += cost
            goal_funded[goal_id] += paid_by_529 + (cost - paid_by_529) * funded_share

        # 5. Growth, then 6. end-of-year contributions and reinvestment.
        for s in states:
            s.balance *= 1 + s.spec.expected_return
        for acct_id, amt in contributions.items():
            s = by_id[acct_id]
            s.balance += amt
            if s.type in (AccountType.taxable, AccountType.roth):
                s.basis += amt
        if retired and surplus > 0 and first_taxable is not None:
            first_taxable.balance += surplus
            first_taxable.basis += surplus

        penalties = w.penalty
        lifetime_taxes += income_tax + payroll_tax + penalties
        total = sum(s.balance for s in states)
        years.append(
            YearRow(
                year=year,
                age=age,
                retired=retired,
                income=_round(salary),
                other_income=_round(other_income),
                spending=_round(living),
                healthcare=_round(healthcare),
                goals=_round(goals_total),
                contributions=_round(contributions_total),
                withdrawals=_round(withdrawals),
                savings_drawn=_round(amount),
                rmd=_round(rmd),
                income_tax=_round(income_tax),
                payroll_tax=_round(payroll_tax),
                penalties=_round(penalties),
                shortfall=_round(shortfall),
                surplus=_round(surplus),
                balances={s.spec.id: _round(s.balance) for s in states},
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
            lifetime_taxes=_round(lifetime_taxes),
            goals=[
                GoalResult(id=g.id, name=g.name, total_cost=_round(goal_cost[g.id]),
                           funded_share=round(goal_funded[g.id] / goal_cost[g.id], 4) if goal_cost[g.id] else 1.0)
                for g in plan.goals
            ],
        ),
        years=years,
    )
