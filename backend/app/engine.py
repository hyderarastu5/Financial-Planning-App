"""Year-by-year projection of a client's accounts, income, costs and taxes.

Order of events within each projected year:
  1. Costs for the year: living expenses, healthcare, goals (a financed goal
     costs its down payment, then loan payments), debt payments, contributions.
     One-time inflows (e.g. an inheritance) are deposited in a taxable account.
  2. Tax-free money is used first: 529s pay college goals, HSAs pay healthcare.
  3. Required minimum distributions come out of traditional accounts.
  4. If salary, other income and RMDs don't cover costs plus taxes, the rest is
     withdrawn at the start of the year in this order: taxable accounts,
     traditional accounts, HSAs (from age 65), Roth accounts. The amount is
     solved (regula falsi) so that what's left after federal and state income
     tax, payroll tax and penalties exactly covers the costs. A Roth conversion,
     if planned for the year, moves money from traditional to Roth accounts and
     the withdrawal is re-solved to also pay its tax.
  5. Each account grows by its expected return.
  6. Contributions are added at the end of the year. Leftover cash goes to the
     plan's surplus account if it has one; otherwise it is reinvested in the
     first taxable account in retirement and left unallocated while working.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

from . import states, tax
from .models import Account, AccountType, DebtResult, GoalResult, Plan, Projection, Summary, YearRow


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


def _solve_withdrawal(net_cash, net_at_zero: float, available: float, net_at_available: float) -> float:
    """Smallest withdrawal leaving non-negative cash (to within half a cent).

    net_cash(x) rises with x and is piecewise linear (one piece per tax bracket
    and account pool), so regula falsi (Illinois variant) usually lands on the
    answer in a handful of steps; the bracket [lo, hi] keeps it safe.
    """
    lo, f_lo, hi, f_hi = 0.0, net_at_zero, available, net_at_available
    true_f_hi = f_hi  # f_hi may be halved below; this is the real cash left at hi
    side = 0
    for _ in range(100):
        if true_f_hi < 0.005:
            break
        x = hi - f_hi * (hi - lo) / (f_hi - f_lo)
        if not lo < x < hi:
            x = (lo + hi) / 2
        f = net_cash(x)
        if f >= 0:
            hi, f_hi, true_f_hi = x, f, f
            if side == 1:
                f_lo /= 2  # Illinois: stop the far end from sticking
            side = 1
        else:
            lo, f_lo = x, f
            if side == -1:
                f_hi /= 2
            side = -1
        if hi - lo < 1e-6:
            break
    return hi


def _loan_payment(principal: float, rate: float, years: int) -> float:
    """Fixed yearly payment that pays off `principal` in `years` (standard amortization)."""
    if rate == 0:
        return principal / years
    return principal * rate / (1 - (1 + rate) ** -years)


def _loan_balance(principal: float, rate: float, payment: float, payments_made: int) -> float:
    if rate == 0:
        return max(0.0, principal - payment * payments_made)
    growth = (1 + rate) ** payments_made
    return max(0.0, principal * growth - payment * (growth - 1) / rate)


@dataclass
class _Loan:
    principal: float
    rate: float
    payment: float
    first_year: int
    years: int


def _goal_schedules(plan: Plan, start_year: int) -> Tuple[Dict[str, Dict[int, float]], List[_Loan]]:
    """Nominal cost of each goal by year, and the loans behind financed goals."""
    schedules: Dict[str, Dict[int, float]] = {}
    loans: List[_Loan] = []
    for g in plan.goals:
        price = lambda year: g.annual_amount * (1 + plan.spending.inflation) ** (year - start_year)  # noqa: E731
        if g.financing is None:
            schedules[g.id] = {y: price(y) for y in range(g.start_year, g.start_year + g.years)}
            continue
        f = g.financing
        cost = price(g.start_year)
        principal = cost * (1 - f.down_payment_share)
        payment = _loan_payment(principal, f.rate, f.years)
        schedule = {y: payment for y in range(g.start_year, g.start_year + f.years)}
        schedule[g.start_year] += cost * f.down_payment_share
        schedules[g.id] = schedule
        loans.append(_Loan(principal, f.rate, payment, g.start_year, f.years))
    return schedules, loans


def project(plan: Plan, start_year: Optional[int] = None,
            returns: Optional[Dict[str, Sequence[float]]] = None) -> Projection:
    """Project the plan. `returns` optionally overrides each account's expected
    return year by year (account id -> one return per projected year); the
    Monte Carlo simulation uses it to replay random market paths."""
    start_year = start_year or date.today().year
    client = plan.client
    status = client.filing_status
    birth_year = client.date_of_birth.year
    retirement_year = birth_year + client.retirement_age
    end_year = birth_year + client.life_expectancy

    if end_year < start_year:
        raise ValueError("life expectancy is already past")

    state_code, state_rules = states.lookup(client.state)

    accounts = [
        _AccountState(spec=a, balance=a.balance,
                      basis=a.balance if a.cost_basis is None else a.cost_basis)
        for a in plan.accounts
    ]
    by_id = {s.spec.id: s for s in accounts}
    first_taxable = next((s for s in accounts if s.type == AccountType.taxable), None)
    first_roth = next((s for s in accounts if s.type == AccountType.roth), None)
    surplus_account = by_id[plan.surplus_account_id] if plan.surplus_account_id else None

    goal_schedule, loans = _goal_schedules(plan, start_year)
    goal_cost = {g.id: 0.0 for g in plan.goals}
    goal_funded = {g.id: 0.0 for g in plan.goals}
    college_goals = {g.id for g in plan.goals if g.category == "college" and g.financing is None}
    homes = [g for g in plan.goals if g.category == "home"]

    debt_balance = {d.id: d.balance for d in plan.debts}
    payoff_age: Dict[str, Optional[int]] = {d.id: None for d in plan.debts}

    years = []
    balance_at_retirement: Optional[float] = None
    balance_at_retirement_real: Optional[float] = None
    depletion_age: Optional[int] = None
    lifetime_taxes = lifetime_taxes_real = 0.0

    for year in range(start_year, end_year + 1):
        t = year - start_year
        age = year - birth_year
        retired = year >= retirement_year
        price_level = (1 + plan.spending.inflation) ** t
        tax_year = tax.TaxYear.for_year(year, status, plan.spending.inflation)

        if retired and balance_at_retirement is None:
            balance_at_retirement = sum(s.balance for s in accounts)
            balance_at_retirement_real = balance_at_retirement / price_level

        # 1. Income and costs.
        salary = 0.0 if retired else plan.income.annual_income * (1 + plan.income.annual_raise) ** t
        social_security = other_income = pension_taxable = other_taxable = 0.0
        for s in plan.income_streams:
            if s.start_age <= age and (s.end_age is None or age <= s.end_age):
                amount = s.annual_amount * (price_level if s.inflation_adjusted else 1)
                other_income += amount
                if s.kind == "social_security":
                    social_security += amount
                elif s.kind in ("pension", "annuity"):
                    pension_taxable += amount * s.taxable_share
                else:
                    other_taxable += amount * s.taxable_share

        living = (plan.spending.retirement_annual if retired else plan.spending.current_annual) * price_level
        healthcare = plan.spending.healthcare_annual * (1 + plan.spending.healthcare_inflation) ** t

        goals_now = {gid: sched[year] for gid, sched in goal_schedule.items() if year in sched}
        goals_total = sum(goals_now.values())
        college_ids = [gid for gid in goals_now if gid in college_goals]
        college_total = sum(goals_now[i] for i in college_ids)

        debt_payments = 0.0
        for d in plan.debts:
            owed = debt_balance[d.id] * (1 + d.rate)
            payment = min(d.annual_payment, owed)
            debt_payments += payment
            debt_balance[d.id] = owed - payment
            if debt_balance[d.id] < 0.005 and payoff_age[d.id] is None:
                debt_balance[d.id] = 0.0
                payoff_age[d.id] = age

        contributions: Dict[str, float] = {}
        for s in accounts:
            a = s.spec
            start = a.contribution_start_year if a.contribution_start_year is not None else start_year
            stop = a.contribution_stop_year if a.contribution_stop_year is not None else retirement_year - 1
            if start <= year <= stop and a.annual_contribution > 0:
                contributions[a.id] = a.annual_contribution
        contributions_total = sum(contributions.values())
        pretax_contributions = sum(amt for acct_id, amt in contributions.items()
                                   if by_id[acct_id].type in (AccountType.traditional, AccountType.hsa))

        # One-time inflows land in a taxable account (full basis), or as cash if there is none.
        inflows = inflow_cash = 0.0
        for f in plan.inflows:
            if f.year == year:
                amount = f.amount * price_level
                inflows += amount
                target = by_id[f.account_id] if f.account_id else first_taxable
                if target is None:
                    inflow_cash += amount
                else:
                    target.balance += amount
                    target.basis += amount

        # 2. Tax-free money: 529s pay college, HSAs pay healthcare.
        withdrawals = 0.0
        from_529 = min(college_total, sum(s.balance for s in accounts if s.type == AccountType.education_529))
        from_hsa = min(healthcare, sum(s.balance for s in accounts if s.type == AccountType.hsa))
        for acct_type, amount in ((AccountType.education_529, from_529), (AccountType.hsa, from_hsa)):
            for acct_id, amt in _take_pro_rata([s for s in accounts if s.type == acct_type], amount).items():
                by_id[acct_id].balance -= amt
                withdrawals += amt

        # 3. Required minimum distributions.
        rmd = 0.0
        for s in accounts:
            if s.type == AccountType.traditional:
                amt = min(s.balance, tax.rmd_amount(s.balance, age, birth_year))
                s.balance -= amt
                rmd += amt
        withdrawals += rmd

        # 4. Solve for the withdrawal that covers costs after taxes.
        costs = living + healthcare + goals_total + debt_payments + contributions_total
        cash_in = salary + other_income + rmd + from_529 + from_hsa + inflow_cash
        wages_taxable = max(0.0, salary - pretax_contributions)
        payroll_tax = tax_year.payroll_tax(salary)

        def settle(conversion: float):
            """Withdrawal covering this year's costs, given a Roth conversion (which adds taxable income)."""
            pools = _withdrawal_pools(accounts, age)
            available = sum(a.balance for pool in pools for a in pool)
            retirement_income = pension_taxable + rmd + conversion

            def after_tax_cash(amount: float):
                w = _plan_withdrawal(pools, amount, age)
                ordinary = wages_taxable + other_taxable + retirement_income + w.ordinary
                federal = tax.income_tax(tax_year, ordinary=ordinary, gains=w.gains,
                                         social_security=social_security, age=age)
                state = 0.0
                if state_rules is not None:
                    state = states.state_income_tax(
                        state_rules, status, tax_year.index, age=age, wages=wages_taxable, other=other_taxable,
                        retirement=retirement_income + w.ordinary, gains=w.gains,
                        taxable_social_security=tax.taxable_social_security(social_security, ordinary + w.gains,
                                                                            status))
                net = cash_in + amount - costs - federal - state - payroll_tax - w.penalty
                return net, w, federal, state

            result = after_tax_cash(0.0)
            amount = 0.0
            if result[0] < 0:
                net_all = after_tax_cash(available)[0]
                amount = available if net_all < 0 else _solve_withdrawal(
                    lambda x: after_tax_cash(x)[0], result[0], available, net_all)
                result = after_tax_cash(amount)
            return (amount, *result)

        amount, net, w, income_tax, state_tax = settle(0.0)

        # Roth conversion: decide the amount from this year's income, move it, and re-solve.
        conversion = 0.0
        rc = plan.roth_conversion
        traditional = [s for s in accounts if s.type == AccountType.traditional and s.balance > 0]
        if rc and rc.start_year <= year <= rc.end_year and first_roth is not None and traditional:
            if rc.mode == "fixed":
                conversion = rc.annual_amount
            else:
                income = tax.taxable_income(
                    tax_year, ordinary=wages_taxable + other_taxable + pension_taxable + rmd + w.ordinary,
                    gains=w.gains, social_security=social_security, age=age)
                # Approximate when Social Security is taxable: converting also raises its taxable part.
                conversion = tax_year.bracket_top(rc.bracket_rate) - income.ordinary_after_deduction
            conversion = max(0.0, min(conversion, sum(s.balance for s in traditional)))
            if conversion > 0:
                for acct_id, amt in _take_pro_rata(traditional, conversion).items():
                    by_id[acct_id].balance -= amt
                first_roth.balance += conversion
                first_roth.basis += conversion  # conversions come out before earnings, like contributions
                amount, net, w, income_tax, state_tax = settle(conversion)

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
        cash_needs = living + healthcare + goals_total + debt_payments - from_529 - from_hsa
        funded_share = 1.0 if cash_needs <= 0 else max(0.0, 1 - shortfall / cash_needs)
        for goal_id, cost in goals_now.items():
            paid_by_529 = from_529 * cost / college_total if goal_id in college_ids else 0.0
            goal_cost[goal_id] += cost
            goal_funded[goal_id] += paid_by_529 + (cost - paid_by_529) * funded_share

        # 5. Growth, then 6. end-of-year contributions and reinvestment.
        for s in accounts:
            growth = returns[s.spec.id][t] if returns and s.spec.id in returns else s.spec.expected_return
            s.balance *= 1 + growth
        for acct_id, amt in contributions.items():
            s = by_id[acct_id]
            s.balance += amt
            if s.type in (AccountType.taxable, AccountType.roth):
                s.basis += amt
        reinvest_into = surplus_account or (first_taxable if retired else None)
        if surplus > 0 and reinvest_into is not None:
            reinvest_into.balance += surplus
            reinvest_into.basis += surplus

        penalties = w.penalty
        taxes = income_tax + state_tax + payroll_tax + penalties
        lifetime_taxes += taxes
        lifetime_taxes_real += taxes / price_level
        total = sum(s.balance for s in accounts)
        debt = sum(debt_balance.values()) + sum(
            _loan_balance(loan.principal, loan.rate, loan.payment, year - loan.first_year + 1)
            for loan in loans if loan.first_year <= year)
        home_value = sum(g.annual_amount * price_level for g in homes if g.start_year <= year)
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
                state_tax=_round(state_tax),
                debt_payments=_round(debt_payments),
                inflows=_round(inflows),
                roth_conversion=_round(conversion),
                shortfall=_round(shortfall),
                surplus=_round(surplus),
                balances={s.spec.id: _round(s.balance) for s in accounts},
                total=_round(total),
                total_today_dollars=_round(total / price_level),
                debt=_round(debt),
                property=_round(home_value),
                net_worth=_round(total + home_value - debt),
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
            lifetime_taxes_today_dollars=_round(lifetime_taxes_real),
            goals=[
                GoalResult(id=g.id, name=g.name, total_cost=_round(goal_cost[g.id]),
                           funded_share=round(goal_funded[g.id] / goal_cost[g.id], 4) if goal_cost[g.id] else 1.0)
                for g in plan.goals
            ],
            debts=[DebtResult(id=d.id, name=d.name, payoff_age=payoff_age[d.id]) for d in plan.debts],
            state=state_code,
        ),
        years=years,
    )
