"""Portfolio math, market data caching and holdings analysis. Yahoo is faked; no network access."""

import json
import math

import pytest

from app import holdings, market_data, portfolio
from app.models import Holding


# --- portfolio math ------------------------------------------------------------------------

def monthly_history(start_price, monthly_growth, months, start_year=2020):
    out, price = [], start_price
    for i in range(months + 1):
        out.append((f"{start_year + i // 12}-{i % 12 + 1:02d}-01", price))
        price *= 1 + monthly_growth
    return out


def test_steady_growth_has_zero_volatility():
    g = 2 ** (1 / 12) - 1  # doubles every 12 months
    returns = list(portfolio.monthly_returns(monthly_history(100, g, 24)).values())
    cagr, vol = portfolio.annual_stats(returns)
    assert cagr == pytest.approx(1.0)
    assert vol == pytest.approx(0, abs=1e-12)


def test_volatility_is_annualized_sample_std():
    returns = [0.01, -0.01] * 12
    _, vol = portfolio.annual_stats(returns)
    sample_std = math.sqrt(sum((r - 0) ** 2 for r in returns) / (len(returns) - 1))
    assert vol == pytest.approx(sample_std * math.sqrt(12))


def test_portfolio_returns_weight_holdings_over_shared_months():
    a = [("2020-01-01", 100), ("2020-02-01", 110), ("2020-03-01", 121)]  # +10%, +10%
    b = [("2020-02-01", 50), ("2020-03-01", 50)]  # starts later; 0%
    rets = portfolio.portfolio_returns({"A": a, "B": b}, {"A": 3, "B": 1})
    assert rets == [pytest.approx(0.75 * 0.10)]  # only March is shared


def test_weighted_mix():
    mix = portfolio.weighted_mix({"VTI": {"stock": 1.0}, "BND": {"bond": 0.99, "cash": 0.01}},
                                 {"VTI": 60, "BND": 40})
    assert mix == pytest.approx({"stock": 0.6, "bond": 0.396, "cash": 0.004})


# --- market data -----------------------------------------------------------------------------

class FakeFrame:
    def __init__(self, rows):
        import pandas as pd

        self._s = pd.Series({pd.Timestamp(d): p for d, p in rows}, dtype=float)
        self.empty = self._s.empty

    def __getitem__(self, col):
        assert col == "Close"
        return self._s


class FakeFunds:
    asset_classes = {"stockPosition": 0.98, "bondPosition": 0.0, "cashPosition": 0.02}
    sector_weightings = {"technology": 0.3, "healthcare": 0.7}


class FakeTicker:
    calls = 0
    catalog = {
        "VTI": {"info": {"quoteType": "ETF", "shortName": "Total Stock", "regularMarketPrice": 300.0}},
        "BND": {"info": {"quoteType": "ETF", "shortName": "Total Bond", "regularMarketPrice": 70.0}},
        "AAPL": {"info": {"quoteType": "EQUITY", "shortName": "Apple", "regularMarketPrice": 200.0,
                          "sector": "Technology"}},
    }

    def __init__(self, symbol):
        FakeTicker.calls += 1
        self.symbol = symbol
        self.entry = self.catalog.get(symbol)

    @property
    def info(self):
        return self.entry["info"] if self.entry else {"quoteType": None}

    @property
    def funds_data(self):
        return FakeFunds()

    def history(self, **_):
        if not self.entry:
            return FakeFrame([])
        growth = {"VTI": 0.01, "BND": 0.002, "AAPL": 0.02}[self.symbol]
        return FakeFrame(monthly_history(100, growth, 24))


@pytest.fixture
def fake_yahoo(monkeypatch, tmp_path):
    monkeypatch.setattr(market_data, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(market_data, "_yf_ticker", FakeTicker)
    FakeTicker.calls = 0
    return FakeTicker


def test_fund_profile(fake_yahoo):
    p = market_data.get_profile("vti")
    assert (p.ticker, p.kind, p.name) == ("VTI", "ETF", "Total Stock")
    assert p.asset_classes == {"stock": 0.98, "bond": 0.0, "cash": 0.02}
    assert p.sectors == {"technology": 0.3, "healthcare": 0.7}


def test_stock_profile_is_all_stock_in_its_sector(fake_yahoo):
    p = market_data.get_profile("AAPL")
    assert p.asset_classes == {"stock": 1.0}
    assert p.sectors == {"technology": 1.0}


def test_unknown_ticker(fake_yahoo):
    with pytest.raises(market_data.TickerNotFound):
        market_data.get_profile("NOPE")
    with pytest.raises(market_data.TickerNotFound):
        market_data.get_price("bad ticker!")


def test_lookups_are_cached(fake_yahoo):
    assert market_data.get_price("VTI") == 300
    market_data.get_price("VTI")
    assert fake_yahoo.calls == 1


def test_stale_cache_is_used_when_yahoo_fails(fake_yahoo, monkeypatch, tmp_path):
    market_data.get_price("VTI")
    path = tmp_path / "price-VTI.json"
    stored = json.loads(path.read_text())
    stored["fetched_at"] -= market_data.PRICE_TTL + 1  # expire it
    path.write_text(json.dumps(stored))

    def offline(symbol):
        raise ConnectionError("no network")

    monkeypatch.setattr(market_data, "_yf_ticker", offline)
    assert market_data.get_price("VTI") == 300
    with pytest.raises(market_data.MarketDataUnavailable):
        market_data.get_price("BND")  # nothing cached to fall back on


# --- holdings analysis -----------------------------------------------------------------------

def test_analyze_account(fake_yahoo):
    result = holdings.analyze_account([Holding(ticker="VTI", shares=2), Holding(ticker="BND", shares=10)])
    assert result.value == pytest.approx(2 * 300 + 10 * 70)
    vti, bnd = result.holdings
    assert vti.weight == pytest.approx(600 / 1300)
    assert vti.annual_return == pytest.approx(1.01 ** 12 - 1)
    # Monthly-rebalanced blend of steady 1% and 0.2% growth.
    blend = 600 / 1300 * 0.01 + 700 / 1300 * 0.002
    assert result.annual_return == pytest.approx((1 + blend) ** 12 - 1)
    assert result.volatility == pytest.approx(0, abs=1e-9)
    assert result.years_of_data == 2.0
    assert result.asset_classes["stock"] == pytest.approx(0.98)


def test_analyze_account_reports_bad_ticker_without_failing(fake_yahoo):
    result = holdings.analyze_account([Holding(ticker="VTI", shares=1), Holding(ticker="NOPE", shares=5)])
    assert result.value == 300
    assert result.holdings[1].error
    assert result.annual_return is not None
