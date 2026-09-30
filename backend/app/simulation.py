"""Monte Carlo simulation: replay the plan under many random market paths.

Each account's yearly growth is drawn from a lognormal distribution whose
median is the account's expected_return and whose spread is its volatility,
so the steady-return projection is the "typical" path. Accounts move
together: each year's draw mixes a shared market shock (correlation RHO) with
an account-specific one.
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Sequence

from .engine import project
from .models import DEFAULT_VOLATILITY, Band, GoalProbability, Plan, Simulation

RHO = 0.8  # correlation between accounts' yearly returns
GOAL_FUNDED = 0.999  # a goal counts as funded in a run if at least this share of it is paid


def _percentile(sorted_values: Sequence[float], q: float) -> float:
    """Linear interpolation between closest ranks."""
    pos = (len(sorted_values) - 1) * q
    lower = math.floor(pos)
    upper = min(lower + 1, len(sorted_values) - 1)
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (pos - lower)


def random_returns(plan: Plan, n_years: int, rng: random.Random) -> Dict[str, List[float]]:
    market = [rng.gauss(0, 1) for _ in range(n_years)]
    shared, own = math.sqrt(RHO), math.sqrt(1 - RHO)
    out = {}
    for a in plan.accounts:
        sigma = DEFAULT_VOLATILITY if a.volatility is None else a.volatility
        mu = math.log(1 + a.expected_return)
        out[a.id] = [math.exp(mu + sigma * (shared * market[t] + own * rng.gauss(0, 1))) - 1
                     for t in range(n_years)]
    return out


def simulate(plan: Plan, runs: int = 1000, seed: Optional[int] = None,
             start_year: Optional[int] = None) -> Simulation:
    rng = random.Random(seed)
    baseline = project(plan, start_year)
    start_year = baseline.summary.start_year
    ages = [row.age for row in baseline.years]
    n_years = len(ages)

    successes = 0
    goal_hits = {g.id: 0 for g in plan.goals}
    totals: List[List[float]] = [[] for _ in range(n_years)]

    for _ in range(runs):
        result = project(plan, start_year, returns=random_returns(plan, n_years, rng))
        if result.summary.depletion_age is None:
            successes += 1
        for g in result.summary.goals:
            if g.funded_share >= GOAL_FUNDED:
                goal_hits[g.id] += 1
        for i, row in enumerate(result.years):
            totals[i].append(row.total_today_dollars)

    bands = []
    for age, values in zip(ages, totals):
        values.sort()
        p = {q: round(_percentile(values, q), 2) for q in (0.10, 0.25, 0.50, 0.75, 0.90)}
        bands.append(Band(age=age, p10=p[0.10], p25=p[0.25], p50=p[0.50], p75=p[0.75], p90=p[0.90]))

    return Simulation(
        runs=runs,
        success_probability=successes / runs,
        goals=[GoalProbability(id=g.id, name=g.name, probability=goal_hits[g.id] / runs) for g in plan.goals],
        bands=bands,
    )
