"""Portfolio math on monthly price histories: returns, volatility, allocation.

Pure functions, no network access; market_data.py supplies the inputs.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

History = Sequence[Tuple[str, float]]


def monthly_returns(history: History) -> Dict[str, float]:
    """Month -> return over that month, keyed by YYYY-MM of the month's end price."""
    out = {}
    for (_, prev), (date, price) in zip(history, history[1:]):
        if prev > 0:
            out[date[:7]] = price / prev - 1
    return out


def annual_stats(returns: Sequence[float]) -> Tuple[float, float]:
    """(compound annual growth rate, annualized volatility) from monthly returns.

    The growth rate is the typical year's growth, which is what the
    projection's expected_return means. Volatility is the standard deviation
    of monthly returns scaled to a year (x sqrt 12).
    """
    n = len(returns)
    if n < 2:
        raise ValueError("need at least two months of returns")
    growth = math.prod(1 + r for r in returns)
    cagr = growth ** (12 / n) - 1
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    return cagr, math.sqrt(variance) * math.sqrt(12)


def portfolio_returns(histories: Dict[str, History], weights: Dict[str, float]) -> List[float]:
    """Monthly returns of a portfolio rebalanced to `weights` each month, over the months all holdings share."""
    per_holding = {t: monthly_returns(h) for t, h in histories.items() if weights.get(t, 0) > 0}
    if not per_holding:
        return []
    common = sorted(set.intersection(*(set(r) for r in per_holding.values())))
    total = sum(weights[t] for t in per_holding)
    return [sum(weights[t] / total * per_holding[t][m] for t in per_holding) for m in common]


def weighted_mix(parts: Dict[str, Dict[str, float]], weights: Dict[str, float]) -> Dict[str, float]:
    """Combine each holding's breakdown (asset classes or sectors) by portfolio weight."""
    total = sum(w for t, w in weights.items() if parts.get(t))
    if total <= 0:
        return {}
    mix: Dict[str, float] = {}
    for ticker, weight in weights.items():
        for key, share in (parts.get(ticker) or {}).items():
            mix[key] = mix.get(key, 0.0) + share * weight / total
    return dict(sorted(mix.items(), key=lambda kv: -kv[1]))


def data_years(returns: Sequence[float]) -> Optional[float]:
    return round(len(returns) / 12, 1) if returns else None
