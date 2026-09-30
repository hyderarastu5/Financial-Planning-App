"""Engine results checked against closed-form finance formulas."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.engine import project
from app.main import app
from app.models import Account, Client, Income, Plan, Spending

START = 2026


def make_plan(accounts, *, born=1996, retire=65, life=90, income=100_000, raise_=0.0,
              spend_now=50_000, spend_retired=40_000, inflation=0.0):
    return Plan(
        client=Client(date_of_birth=date(born, 6, 1), retirement_age=retire, life_expectancy=life),
        income=Income(annual_income=income, annual_raise=raise_),
        spending=Spending(current_annual=spend_now, retirement_annual=spend_retired, inflation=inflation),
        accounts=accounts,
    )


def row(proj, year):
    return next(r for r in proj.years if r.year == year)


def test_lump_sum_compounds():
    plan = make_plan([Account(id="a", name="Brokerage", balance=10_000, expected_return=0.07)])
    proj = project(plan, start_year=START)
    # End of year n (n = 1..) holds 10,000 * 1.07^n.
    for n in (1, 10, 30):
        assert row(proj, START + n - 1).total == pytest.approx(10_000 * 1.07**n, abs=0.01)


def test_contributions_match_annuity_formula():
    r, p, n = 0.06, 6_000, 20
    plan = make_plan([Account(id="a", name="Roth", type="roth", balance=0, annual_contribution=p,
                              expected_return=r)])
    proj = project(plan, start_year=START)
    future_value = p * ((1 + r) ** n - 1) / r  # ordinary annuity, end-of-year deposits
    assert row(proj, START + n - 1).total == pytest.approx(future_value, abs=0.01)


def test_contribution_window_is_respected():
    plan = make_plan([Account(id="a", name="IRA", balance=0, annual_contribution=1_000,
                              contribution_start_year=2028, contribution_stop_year=2030,
                              expected_return=0.0)])
    proj = project(plan, start_year=START)
    assert [row(proj, y).contributions for y in range(2026, 2033)] == [0, 0, 1000, 1000, 1000, 0, 0]
    assert row(proj, 2032).total == 3_000


def test_contributions_stop_at_retirement_by_default():
    plan = make_plan([Account(id="a", name="401k", balance=0, annual_contribution=1_000,
                              expected_return=0.0)], retire=65)
    proj = project(plan, start_year=START)
    retirement_year = 1996 + 65
    assert row(proj, retirement_year - 1).contributions == 1_000
    assert row(proj, retirement_year).contributions == 0


def test_income_grows_and_stops_at_retirement():
    plan = make_plan([], income=100_000, raise_=0.03, retire=65)
    proj = project(plan, start_year=START)
    assert row(proj, START + 10).income == pytest.approx(100_000 * 1.03**10, abs=0.01)
    assert row(proj, 1996 + 65).income == 0


def test_spending_inflates_and_switches_at_retirement():
    plan = make_plan([], spend_now=50_000, spend_retired=40_000, inflation=0.02, retire=65)
    proj = project(plan, start_year=START)
    retirement_year = 1996 + 65
    assert row(proj, START + 5).spending == pytest.approx(50_000 * 1.02**5, abs=0.01)
    t = retirement_year - START
    assert row(proj, retirement_year).spending == pytest.approx(40_000 * 1.02**t, abs=0.01)


def test_money_runs_out_at_expected_age():
    # Already retired at 70 with $100k, spending $25k/yr, no growth: lasts 4 years.
    plan = make_plan([Account(id="a", name="IRA", balance=100_000, expected_return=0.0)],
                     born=1956, retire=65, life=90, spend_retired=25_000)
    proj = project(plan, start_year=START)
    assert [r.total for r in proj.years[:5]] == [75_000, 50_000, 25_000, 0, 0]
    assert proj.years[4].shortfall == 25_000
    assert proj.summary.depletion_age == 74


def test_withdrawals_are_proportional_to_balances():
    plan = make_plan([Account(id="a", name="A", balance=75_000, expected_return=0.0),
                      Account(id="b", name="B", balance=25_000, expected_return=0.0)],
                     born=1956, retire=65, spend_retired=10_000)
    first = project(plan, start_year=START).years[0]
    assert first.balances == {"a": 67_500, "b": 22_500}


def test_money_lasts_when_well_funded():
    plan = make_plan([Account(id="a", name="IRA", balance=2_000_000, expected_return=0.05)],
                     born=1956, spend_retired=40_000)
    assert project(plan, start_year=START).summary.depletion_age is None


def test_today_dollars_deflates_by_inflation():
    plan = make_plan([Account(id="a", name="A", balance=10_000, expected_return=0.0)], inflation=0.03)
    r = row(project(plan, start_year=START), START + 10)
    assert r.total_today_dollars == pytest.approx(10_000 / 1.03**10, abs=0.01)


def test_rejects_retirement_after_life_expectancy():
    with pytest.raises(ValidationError):
        Client(date_of_birth=date(1990, 1, 1), retirement_age=70, life_expectancy=65)


def test_rejects_stop_before_start():
    with pytest.raises(ValidationError):
        Account(id="a", name="A", balance=0, contribution_start_year=2030, contribution_stop_year=2029)


def test_api_round_trip():
    plan = make_plan([Account(id="a", name="A", balance=1_000, expected_return=0.05)])
    res = TestClient(app).post("/api/project", json=plan.model_dump(mode="json"))
    assert res.status_code == 200
    body = res.json()
    assert body["years"][0]["balances"]["a"] == 1_050
    assert "depletion_age" in body["summary"]


def test_api_rejects_bad_plan():
    res = TestClient(app).post("/api/project", json={"client": {}})
    assert res.status_code == 422
