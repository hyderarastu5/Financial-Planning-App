"""Analyze an account's holdings with live market data."""

from __future__ import annotations

from typing import Dict, List

from . import market_data, portfolio
from .models import AccountAnalysis, Holding, HoldingAnalysis


def analyze_account(holdings: List[Holding], years: int = 10) -> AccountAnalysis:
    """Live value, historical growth and volatility, and asset mix of a set of holdings.

    A ticker that can't be found is reported with an error instead of failing
    the whole account. MarketDataUnavailable (Yahoo unreachable, nothing
    cached) is raised to the caller.
    """
    rows: List[HoldingAnalysis] = []
    histories: Dict[str, portfolio.History] = {}
    asset_classes: Dict[str, Dict[str, float]] = {}
    sectors: Dict[str, Dict[str, float]] = {}

    for h in holdings:
        ticker = h.ticker.strip().upper()
        try:
            profile = market_data.get_profile(ticker)
            price = market_data.get_price(ticker)
            history = market_data.get_history(ticker, years)
        except market_data.TickerNotFound as e:
            rows.append(HoldingAnalysis(ticker=ticker, name="", kind="", shares=h.shares, price=0, value=0,
                                        weight=0, annual_return=None, volatility=None, years_of_data=None,
                                        asset_classes={}, error=str(e)))
            continue
        returns = list(portfolio.monthly_returns(history).values())
        cagr, vol = portfolio.annual_stats(returns) if len(returns) >= 2 else (None, None)
        histories[ticker] = history
        asset_classes[ticker] = profile.asset_classes
        sectors[ticker] = profile.sectors
        rows.append(HoldingAnalysis(ticker=ticker, name=profile.name, kind=profile.kind, shares=h.shares,
                                    price=price, value=price * h.shares, weight=0, annual_return=cagr,
                                    volatility=vol, years_of_data=portfolio.data_years(returns),
                                    asset_classes=profile.asset_classes))

    total = sum(r.value for r in rows)
    weights: Dict[str, float] = {}
    for r in rows:
        r.weight = r.value / total if total else 0.0
        if r.error is None:
            weights[r.ticker] = weights.get(r.ticker, 0.0) + r.value

    combined = portfolio.portfolio_returns(histories, weights)
    cagr, vol = portfolio.annual_stats(combined) if len(combined) >= 2 else (None, None)
    return AccountAnalysis(
        value=total,
        holdings=rows,
        annual_return=cagr,
        volatility=vol,
        years_of_data=portfolio.data_years(combined),
        asset_classes=portfolio.weighted_mix(asset_classes, weights),
        sectors=portfolio.weighted_mix(sectors, weights),
    )
