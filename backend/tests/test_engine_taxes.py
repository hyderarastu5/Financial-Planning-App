"""Phase 2 engine rules: taxes, withdrawal order, RMDs, income streams, goals."""

from datetime import date

import pytest

from app import tax
from app.engine import project
from app.models import Account, Client, Goal, Income, IncomeStream, Plan, Spending

START = 2026


def make_plan(accounts, *, born, retire=65, life=95, income=0, spend_now=0, spend_retired=0,
              healthcare=0, streams=(), goals=(), status="single"):
    return Plan(
        client=Client(date_of_birth=date(born, 6, 1), retirement_age=retire, life_expectancy=life,
                      filing_status=status),
        income=Income(annual_income=income, annual_raise=0),
        spending=Spending(current_annual=spend_now, retirement_annual=spend_retired, inflation=0,
                          healthcare_annual=healthcare, healthcare_inflation=0),
        accounts=list(accounts),
        income_streams=list(streams),
        goals=list(goals),
    )


def acct(id, type, balance, **kw):
    return Account(id=id, name=id, type=type, balance=balance, expected_return=kw.pop("r", 0.0), **kw)


def first_year(plan):
    return project(plan, start_year=START).years[0]


def test_salary_pays_income_and_payroll_tax():
    plan = make_plan([], born=1990, income=100_000, spend_now=50_000)
    row = first_year(plan)
    assert row.income_tax == pytest.approx(13_170)
    assert row.payroll_tax == pytest.approx(7_650)
    assert row.surplus == pytest.approx(100_000 - 50_000 - 13_170 - 7_650)
    assert row.savings_drawn == 0


def test_working_cash_gap_is_drawn_from_savings():
    # Spending alone exceeds take-home pay, so the difference comes out of the brokerage account.
    plan = make_plan([acct("brk", "taxable", 50_000)], born=1990, income=100_000, spend_now=90_000)
    row = first_year(plan)
    assert row.savings_drawn == pytest.approx(90_000 + 13_170 + 7_650 - 100_000)
    assert row.shortfall == 0


def test_pretax_contribution_lowers_income_tax():
    plan = make_plan([acct("k", "traditional", 0, annual_contribution=10_000)],
                     born=1990, income=100_000, spend_now=50_000)
    row = first_year(plan)
    expected = tax.income_tax(tax.TaxYear.for_year(START, "single", 0), ordinary=90_000, gains=0,
                              social_security=0, age=36)
    assert row.income_tax == pytest.approx(expected)


def test_traditional_withdrawal_is_grossed_up_for_tax():
    # Age 70, no other income, $50k to spend from a traditional IRA.
    # W - tax(W) = 50,000 with deduction 24,150 (standard + 65+ + senior) -> W = 53,243.18
    plan = make_plan([acct("ira", "traditional", 1_000_000)], born=1956, spend_retired=50_000)
    row = first_year(plan)
    assert row.withdrawals == pytest.approx(53_243.18, abs=0.02)
    assert row.withdrawals - row.income_tax == pytest.approx(50_000, abs=0.02)
    assert row.shortfall == 0


def test_early_traditional_withdrawal_is_penalized():
    plan = make_plan([acct("ira", "traditional", 1_000_000)], born=1976, retire=45, spend_retired=40_000)
    row = first_year(plan)  # age 50
    assert row.penalties == pytest.approx(0.10 * row.withdrawals, abs=0.01)
    assert row.withdrawals - row.income_tax - row.penalties == pytest.approx(40_000, abs=0.02)


def test_roth_contributions_come_out_tax_and_penalty_free():
    plan = make_plan([acct("roth", "roth", 100_000, cost_basis=100_000)], born=1976, retire=45,
                     spend_retired=40_000)
    row = first_year(plan)
    assert (row.withdrawals, row.income_tax, row.penalties) == (40_000, 0, 0)


def test_early_roth_earnings_are_taxed_and_penalized():
    plan = make_plan([acct("roth", "roth", 100_000, cost_basis=10_000)], born=1976, retire=45,
                     spend_retired=40_000)
    row = first_year(plan)
    assert row.penalties == pytest.approx(0.10 * (row.withdrawals - 10_000), abs=0.01)


def test_withdrawals_use_taxable_before_traditional_before_roth():
    plan = make_plan([acct("roth", "roth", 50_000), acct("ira", "traditional", 50_000),
                      acct("brk", "taxable", 20_000)], born=1956, spend_retired=30_000)
    row = first_year(plan)
    assert row.balances["brk"] == 0
    assert row.balances["roth"] == 50_000
    assert row.balances["ira"] < 50_000


def test_taxable_gains_in_zero_bracket_owe_nothing():
    plan = make_plan([acct("brk", "taxable", 100_000, cost_basis=50_000)], born=1956, spend_retired=30_000)
    row = first_year(plan)
    assert (row.withdrawals, row.income_tax) == (30_000, 0)


def test_rmd_is_forced_taxed_and_surplus_reinvested():
    # Born 1953: RMDs start at 73, which is 2026. 265,000 / 26.5 = 10,000.
    plan = make_plan([acct("ira", "traditional", 265_000), acct("brk", "taxable", 0)], born=1953)
    row = first_year(plan)
    assert row.rmd == pytest.approx(10_000)
    assert row.income_tax == 0  # under the 65+ deductions
    assert row.balances["brk"] == pytest.approx(10_000)


def test_no_rmd_before_start_age():
    plan = make_plan([acct("ira", "traditional", 265_000)], born=1962)  # 64 in 2026
    assert first_year(plan).rmd == 0


def test_social_security_covers_spending():
    ss = IncomeStream(id="ss", name="Social Security", kind="social_security", annual_amount=40_000, start_age=67)
    plan = make_plan([acct("ira", "traditional", 100_000)], born=1956, spend_retired=30_000, streams=[ss])
    row = first_year(plan)
    assert row.other_income == 40_000
    assert row.withdrawals == 0
    assert row.income_tax == 0  # provisional income 20k is under 25k


def test_income_stream_respects_start_and_end_age():
    pension = IncomeStream(id="p", name="Pension", kind="pension", annual_amount=10_000, start_age=72, end_age=73)
    plan = make_plan([], born=1956, streams=[pension])
    years = project(plan, start_year=START).years
    assert [r.other_income for r in years[:5]] == [0, 0, 10_000, 10_000, 0]  # ages 70-74


def test_529_pays_for_college_tax_free():
    college = Goal(id="c", name="College", category="college", annual_amount=20_000, start_year=2030, years=4)
    plan = make_plan([acct("529", "529", 50_000)], born=1990, income=100_000, spend_now=40_000, goals=[college])
    proj = project(plan, start_year=START)
    by_year = {r.year: r for r in proj.years}
    assert [by_year[y].balances["529"] for y in (2030, 2031, 2032, 2033)] == [30_000, 10_000, 0, 0]
    assert by_year[2030].income_tax == by_year[2029].income_tax  # 529 money isn't income
    assert proj.summary.goals[0].funded_share == 1


def test_hsa_pays_healthcare():
    plan = make_plan([acct("hsa", "hsa", 20_000)], born=1956, healthcare=5_000)
    row = first_year(plan)
    assert (row.withdrawals, row.income_tax, row.balances["hsa"]) == (5_000, 0, 15_000)


def test_unaffordable_goal_is_partly_funded():
    trip = Goal(id="t", name="Trip", annual_amount=20_000, start_year=START)
    plan = make_plan([acct("brk", "taxable", 10_000)], born=1956, goals=[trip])
    proj = project(plan, start_year=START)
    assert proj.years[0].shortfall == pytest.approx(10_000)
    assert proj.summary.goals[0].funded_share == pytest.approx(0.5)
    assert proj.summary.depletion_age == 70


def test_lifetime_taxes_add_up():
    plan = make_plan([acct("ira", "traditional", 500_000, r=0.05)], born=1960, income=80_000,
                     spend_now=40_000, spend_retired=40_000)
    proj = project(plan, start_year=START)
    expected = sum(r.income_tax + r.payroll_tax + r.penalties for r in proj.years)
    assert proj.summary.lifetime_taxes == pytest.approx(expected, abs=1)
