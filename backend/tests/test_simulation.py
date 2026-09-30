"""Monte Carlo simulation."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.engine import project
from app.main import app
from app.models import Account, Client, Goal, Income, Plan, Spending
from app.simulation import simulate

START = 2026


def make_plan(balance, *, volatility=0.15, spend_retired=40_000, goals=()):
    return Plan(
        client=Client(date_of_birth=date(1961, 1, 1), retirement_age=65, life_expectancy=90),
        income=Income(annual_income=0),
        spending=Spending(current_annual=0, retirement_annual=spend_retired, inflation=0),
        accounts=[Account(id="a", name="A", type="taxable", balance=balance, expected_return=0.05,
                          volatility=volatility)],
        goals=list(goals),
    )


def test_zero_volatility_reproduces_the_steady_projection():
    plan = make_plan(600_000, volatility=0)
    sim = simulate(plan, runs=50, seed=1, start_year=START)
    steady = project(plan, START)
    assert sim.success_probability == (1.0 if steady.summary.depletion_age is None else 0.0)
    for band, row in zip(sim.bands, steady.years):
        assert band.p10 == band.p90 == pytest.approx(row.total_today_dollars, abs=0.02)


def test_same_seed_same_result():
    plan = make_plan(700_000)
    assert simulate(plan, runs=100, seed=7, start_year=START) == simulate(plan, runs=100, seed=7, start_year=START)


def test_probability_reflects_how_well_funded_the_plan_is():
    rich = simulate(make_plan(3_000_000), runs=200, seed=1, start_year=START).success_probability
    borderline = simulate(make_plan(650_000), runs=200, seed=1, start_year=START).success_probability
    poor = simulate(make_plan(100_000), runs=200, seed=1, start_year=START).success_probability
    assert rich == 1.0
    assert 0.05 < borderline < 0.95
    assert poor == 0.0


def test_bands_are_ordered_and_median_tracks_steady_path():
    plan = make_plan(2_000_000, spend_retired=0)
    sim = simulate(plan, runs=1000, seed=3, start_year=START)
    for b in sim.bands:
        assert b.p10 <= b.p25 <= b.p50 <= b.p75 <= b.p90
    # With no withdrawals the median path grows at the expected return.
    last = sim.bands[-1]
    steady = project(plan, START).years[-1].total_today_dollars
    assert last.p50 == pytest.approx(steady, rel=0.10)


def test_goal_probability():
    easy = Goal(id="e", name="Easy", annual_amount=1_000, start_year=2030)
    hard = Goal(id="h", name="Hard", annual_amount=40_000, start_year=2050, years=10)
    sim = simulate(make_plan(650_000, goals=[easy, hard]), runs=200, seed=1, start_year=START)
    probs = {g.id: g.probability for g in sim.goals}
    assert probs["e"] == 1.0
    assert probs["h"] < probs["e"]


def test_simulate_endpoint():
    plan = make_plan(1_000_000)
    res = TestClient(app).post("/api/simulate", json={"plan": plan.model_dump(mode="json"), "runs": 50, "seed": 1})
    assert res.status_code == 200
    body = res.json()
    assert body["runs"] == 50
    assert 0 <= body["success_probability"] <= 1
    assert len(body["bands"]) == len(project(plan).years)
