"""Scenario comparisons."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.compare import PRETAX_BALANCE_TAX_RATE, compare, contributions_as
from app.engine import project
from app.main import app
from app.models import Account, AccountType, Client, Income, Plan, RothConversion, Spending

START = 2026


def make_plan(accounts, **extra):
    return Plan(
        client=Client(date_of_birth=date(1990, 6, 1), retirement_age=65, life_expectancy=90),
        income=Income(annual_income=120_000, annual_raise=0),
        spending=Spending(current_annual=60_000, retirement_annual=50_000, inflation=0),
        accounts=accounts,
        **extra,
    )


def acct(id, type, balance, contribution=0.0):
    return Account(id=id, name=id, type=type, balance=balance, annual_contribution=contribution,
                   expected_return=0.05)


def test_contributions_as_redirects_contributions_but_not_balances():
    plan = make_plan([acct("k", "traditional", 50_000, 10_000), acct("r", "roth", 5_000, 7_000)])
    roth = contributions_as(plan, AccountType.roth)
    by_id = {a.id: a for a in roth.accounts}
    assert by_id["k"].balance == 50_000 and by_id["k"].annual_contribution == 0
    assert by_id["k~roth"].type == AccountType.roth and by_id["k~roth"].annual_contribution == 10_000
    assert by_id["r"].annual_contribution == 7_000
    total = lambda p: sum(a.annual_contribution for a in p.accounts)  # noqa: E731
    assert total(roth) == total(plan) == total(contributions_as(plan, AccountType.traditional))


def test_pre_tax_contributions_pay_less_tax_while_working():
    plan = make_plan([acct("k", "traditional", 0, 20_000)])
    first_year = lambda p: project(p, START).years[0]  # noqa: E731
    pre = first_year(contributions_as(plan, AccountType.traditional))
    roth = first_year(contributions_as(plan, AccountType.roth))
    assert pre.income_tax < roth.income_tax


def test_contribution_comparison_invests_leftover_cash_in_both():
    result = compare(make_plan([acct("k", "traditional", 0, 20_000)]), "contribution_type", start_year=START)
    names = [s.name for s in result.scenarios]
    assert names == ["Pre-tax (traditional) contributions", "Roth contributions"]
    assert result.better in names
    diff = abs(result.scenarios[0].after_tax_final_today_dollars - result.scenarios[1].after_tax_final_today_dollars)
    assert result.difference_today_dollars == pytest.approx(diff)


def test_after_tax_value_discounts_pretax_balances():
    plan = make_plan([acct("k", "traditional", 100_000), acct("b", "taxable", 0)], surplus_account_id="b")
    result = compare(plan, "contribution_type", start_year=START)
    s = result.scenarios[0]
    last = project(plan, START).years[-1]
    assert s.after_tax_final_today_dollars == pytest.approx(last.net_worth - PRETAX_BALANCE_TAX_RATE
                                                            * last.balances["k"], abs=0.01)


def test_roth_conversion_comparison():
    rc = RothConversion(start_year=2055, end_year=2064, mode="fill_bracket", bracket_rate=0.22)
    plan = make_plan([acct("k", "traditional", 300_000, 20_000), acct("r", "roth", 0), acct("b", "taxable", 0)],
                     roth_conversion=rc)
    result = compare(plan, "roth_conversion", start_year=START)
    without, with_ = result.scenarios
    assert without.name == "Without Roth conversions"
    base = project(plan.model_copy(update={"roth_conversion": None, "surplus_account_id": "b"}), START)
    assert without.lifetime_taxes == base.summary.lifetime_taxes


def test_roth_conversion_comparison_needs_a_conversion():
    with pytest.raises(ValueError):
        compare(make_plan([acct("k", "traditional", 1)]), "roth_conversion")


def test_compare_endpoint():
    plan = make_plan([acct("k", "traditional", 0, 10_000)])
    res = TestClient(app).post("/api/compare", json={"plan": plan.model_dump(mode="json"), "kind": "contribution_type"})
    assert res.status_code == 200
    assert len(res.json()["scenarios"]) == 2
    bad = TestClient(app).post("/api/compare", json={"plan": plan.model_dump(mode="json"), "kind": "roth_conversion"})
    assert bad.status_code == 422
