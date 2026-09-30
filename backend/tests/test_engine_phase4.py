"""Phase 4 engine features: debts, financed goals, inflows, surplus investing, Roth conversions, state tax."""

from datetime import date

import pytest

from app import tax
from app.engine import project
from app.models import (Account, Client, Debt, Financing, Goal, Income, Inflow, Plan, RothConversion,
                        Spending)

START = 2026


def make_plan(accounts=(), *, born=1990, retire=65, income=0, spend_now=0, spend_retired=0, state="",
              **extra):
    return Plan(
        client=Client(date_of_birth=date(born, 6, 1), retirement_age=retire, life_expectancy=95, state=state),
        income=Income(annual_income=income, annual_raise=0),
        spending=Spending(current_annual=spend_now, retirement_annual=spend_retired, inflation=0,
                          healthcare_annual=0),
        accounts=list(accounts),
        **extra,
    )


def acct(id, type, balance, **kw):
    return Account(id=id, name=id, type=type, balance=balance, expected_return=kw.pop("r", 0.0), **kw)


def rows(plan):
    return {r.year: r for r in project(plan, start_year=START).years}


# --- debts ---------------------------------------------------------------------------------

def test_debt_is_paid_down_with_interest():
    loan = Debt(id="d", name="Car", balance=10_000, rate=0.10, annual_payment=3_000)
    proj = project(make_plan(income=100_000, debts=[loan]), start_year=START)
    by_year = {r.year: r for r in proj.years}
    # 11,000-3,000=8,000; 8,800-3,000=5,800; 6,380-3,000=3,380; 3,718-3,000=718; 789.80 paid off
    assert [by_year[y].debt for y in range(2026, 2031)] == pytest.approx([8_000, 5_800, 3_380, 718, 0], abs=0.01)
    assert by_year[2030].debt_payments == pytest.approx(789.80)
    assert by_year[2031].debt_payments == 0
    assert proj.summary.debts[0].payoff_age == 40


def test_debt_payments_reduce_leftover_cash():
    loan = Debt(id="d", name="Loan", balance=50_000, rate=0.0, annual_payment=5_000)
    with_debt = project(make_plan(income=100_000, debts=[loan]), start_year=START).years[0]
    without = project(make_plan(income=100_000), start_year=START).years[0]
    assert without.surplus - with_debt.surplus == pytest.approx(5_000)


def test_net_worth_subtracts_debt():
    loan = Debt(id="d", name="Loan", balance=50_000, rate=0.0, annual_payment=5_000)
    row = project(make_plan([acct("b", "taxable", 100_000)], income=100_000, debts=[loan]), start_year=START).years[0]
    assert row.net_worth == pytest.approx(row.total - 45_000)


# --- financed goals --------------------------------------------------------------------------

def test_financed_home_costs_down_payment_then_mortgage_payments():
    home = Goal(id="h", name="Home", category="home", annual_amount=100_000, start_year=2027,
                financing=Financing(down_payment_share=0.2, rate=0.05, years=30))
    by_year = rows(make_plan(income=200_000, goals=[home]))
    payment = 80_000 * 0.05 / (1 - 1.05 ** -30)
    assert by_year[2026].goals == 0
    assert by_year[2027].goals == pytest.approx(20_000 + payment, abs=0.01)
    assert by_year[2028].goals == pytest.approx(payment, abs=0.01)
    assert by_year[2056].goals == pytest.approx(payment, abs=0.01)  # 30th payment
    assert by_year[2057].goals == 0
    assert by_year[2027].debt == pytest.approx(80_000 * 1.05 - payment, abs=0.01)
    assert by_year[2056].debt == pytest.approx(0, abs=0.01)
    # The home counts toward net worth from the purchase year.
    assert by_year[2026].property == 0
    assert by_year[2027].property == 100_000
    r = by_year[2027]
    assert r.net_worth == pytest.approx(r.total + 100_000 - r.debt)


def test_financed_goal_must_be_one_time():
    with pytest.raises(ValueError):
        Goal(id="h", name="Home", annual_amount=1, start_year=2030, years=2,
             financing=Financing(rate=0.05))


# --- inflows and surplus -------------------------------------------------------------------------

def test_inheritance_is_deposited_with_full_basis():
    gift = Inflow(id="i", name="Inheritance", amount=100_000, year=2028)
    plan = make_plan([acct("b", "taxable", 0)], born=1956, spend_retired=20_000, inflows=[gift])
    by_year = rows(plan)
    assert by_year[2028].inflows == 100_000
    assert by_year[2028].balances["b"] == pytest.approx(80_000)
    assert by_year[2028].income_tax == 0  # withdrawals from it are all basis


def test_inflow_without_taxable_account_is_cash():
    gift = Inflow(id="i", name="Gift", amount=10_000, year=START)
    row = project(make_plan(income=0, inflows=[gift]), start_year=START).years[0]
    assert row.surplus == pytest.approx(10_000)


def test_working_surplus_is_invested_when_a_surplus_account_is_set():
    plan = make_plan([acct("b", "taxable", 0)], income=100_000, spend_now=50_000, surplus_account_id="b")
    row = project(plan, start_year=START).years[0]
    assert row.balances["b"] == pytest.approx(row.surplus)
    assert row.surplus == pytest.approx(100_000 - 50_000 - 13_170 - 7_650)


def test_surplus_account_must_be_taxable():
    with pytest.raises(ValueError):
        make_plan([acct("r", "roth", 0)], surplus_account_id="r")


# --- Roth conversions ----------------------------------------------------------------------------

def conversion_plan(rc, spend=40_000):
    # Retired at 60, age 62 in 2026: taxable account pays the bills (all basis, so no gains).
    return make_plan([acct("b", "taxable", 1_000_000), acct("ira", "traditional", 500_000), acct("roth", "roth", 0)],
                     born=1964, retire=60, spend_retired=spend, roth_conversion=rc)


def test_fixed_roth_conversion_moves_money_and_is_taxed():
    rc = RothConversion(start_year=2026, end_year=2026, mode="fixed", annual_amount=50_000)
    row = project(conversion_plan(rc), start_year=START).years[0]
    assert row.roth_conversion == 50_000
    assert (row.balances["ira"], row.balances["roth"]) == (450_000, 50_000)
    assert row.income_tax == pytest.approx(0.10 * 12_400 + 0.12 * (50_000 - 16_100 - 12_400))
    assert row.penalties == 0  # converting isn't an early withdrawal
    assert row.withdrawals == pytest.approx(40_000 + row.income_tax, abs=0.01)


def test_fill_bracket_conversion_tops_up_to_the_bracket():
    rc = RothConversion(start_year=2026, end_year=2027, mode="fill_bracket", bracket_rate=0.12)
    row = project(conversion_plan(rc, spend=0), start_year=START).years[0]
    # No other income: convert exactly the standard deduction plus the top of the 12% bracket.
    assert row.roth_conversion == pytest.approx(16_100 + 50_400, abs=0.01)
    ty = tax.TaxYear.for_year(2026, "single", 0)
    assert row.income_tax == pytest.approx(ty.ordinary_tax(50_400))


def test_no_conversion_outside_its_years():
    rc = RothConversion(start_year=2027, end_year=2027, mode="fixed", annual_amount=10_000)
    by_year = rows(conversion_plan(rc))
    assert [by_year[y].roth_conversion for y in (2026, 2027, 2028)] == [0, 10_000, 0]


# --- state tax -------------------------------------------------------------------------------------

def test_state_tax_applies_by_residence():
    ca = project(make_plan(income=100_000, state="CA"), start_year=START)
    tx = project(make_plan(income=100_000, state="TX"), start_year=START)
    assert ca.years[0].state_tax > 0
    assert tx.years[0].state_tax == 0
    assert ca.summary.state == "CA" and tx.summary.state == "TX"
    assert ca.years[0].surplus == pytest.approx(tx.years[0].surplus - ca.years[0].state_tax)


def test_state_tax_is_grossed_up_in_withdrawals():
    plan = make_plan([acct("ira", "traditional", 1_000_000)], born=1956, spend_retired=50_000, state="CA")
    row = project(plan, start_year=START).years[0]
    assert row.withdrawals - row.income_tax - row.state_tax == pytest.approx(50_000, abs=0.02)


def test_unknown_state_is_reported():
    assert project(make_plan(state="Narnia"), start_year=START).summary.state is None


# --- bookkeeping -----------------------------------------------------------------------------------

def test_every_dollar_is_accounted_for():
    """With zero returns, each year's balance change must equal deposits minus withdrawals."""
    plan = make_plan(
        [acct("b", "taxable", 200_000, cost_basis=150_000), acct("ira", "traditional", 400_000, annual_contribution=5_000),
         acct("roth", "roth", 50_000, annual_contribution=3_000), acct("hsa", "hsa", 10_000)],
        born=1970, retire=62, income=90_000, spend_now=50_000, spend_retired=60_000, state="CA",
        surplus_account_id="b",
        goals=[Goal(id="h", name="Home", category="home", annual_amount=200_000, start_year=2030,
                    financing=Financing(rate=0.06, years=15))],
        debts=[Debt(id="d", name="Loan", balance=20_000, rate=0.05, annual_payment=6_000)],
        inflows=[Inflow(id="i", name="Inheritance", amount=75_000, year=2040)],
        roth_conversion=RothConversion(start_year=2032, end_year=2036, bracket_rate=0.22),
    )
    prev = sum(a.balance for a in plan.accounts)
    for r in project(plan, start_year=START).years:
        deposited = r.contributions + r.inflows + r.surplus  # surplus goes to the surplus account
        assert r.total == pytest.approx(prev + deposited - r.withdrawals, abs=0.05), r.year
        prev = r.total
