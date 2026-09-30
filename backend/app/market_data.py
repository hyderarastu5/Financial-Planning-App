"""Live market data from Yahoo Finance (via yfinance), cached on disk.

yfinance is an unofficial client: it needs no API key and has no request
quota, but Yahoo can throttle heavy use or change its responses. So every
lookup is cached, and when Yahoo can't be reached the last cached copy is used
even if it's stale.

Cache lifetimes: prices 15 minutes, fund profiles 7 days, price history 1 day.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "market"

PRICE_TTL = 15 * 60
PROFILE_TTL = 7 * 24 * 3600
HISTORY_TTL = 24 * 3600


class TickerNotFound(Exception):
    pass


class MarketDataUnavailable(Exception):
    pass


@dataclass
class Profile:
    ticker: str
    name: str
    kind: str  # yfinance quoteType: ETF, MUTUALFUND, EQUITY, ...
    currency: str
    # Share of the holding in each asset class: stock, bond, cash, other (sums to ~1).
    asset_classes: Dict[str, float] = field(default_factory=dict)
    # Share in each sector, e.g. {"technology": 0.3}; for a stock, its one sector.
    sectors: Dict[str, float] = field(default_factory=dict)


# Monthly closing prices, adjusted for dividends and splits: [(YYYY-MM-DD, price), ...]
History = List[Tuple[str, float]]


def _cache_path(kind: str, ticker: str) -> Path:
    return CACHE_DIR / f"{kind}-{ticker.upper()}.json"


def _cached(kind: str, ticker: str, ttl: float, fetch: Callable[[], object]):
    """Return a fresh cached value, or fetch and cache it; fall back to a stale copy on network errors."""
    path = _cache_path(kind, ticker)
    stored = None
    if path.exists():
        try:
            stored = json.loads(path.read_text())
        except ValueError:
            stored = None
    if stored and time.time() - stored["fetched_at"] < ttl:
        return stored["value"]
    try:
        value = fetch()
    except TickerNotFound:
        raise
    except Exception as e:  # network errors, Yahoo throttling, response format changes
        if stored:
            log.warning("Using stale %s for %s: %s", kind, ticker, e)
            return stored["value"]
        raise MarketDataUnavailable(f"Couldn't get market data for {ticker}: {e}") from e
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"fetched_at": time.time(), "value": value}))
    return value


def _normalize_symbol(ticker: str) -> str:
    symbol = ticker.strip().upper()
    if not symbol or len(symbol) > 15 or not all(c.isalnum() or c in ".-^=" for c in symbol):
        raise TickerNotFound(f"'{ticker}' is not a valid ticker symbol")
    return symbol


def _yf_ticker(symbol: str):
    import yfinance as yf  # imported lazily: slow to import and unused by the rest of the app

    return yf.Ticker(symbol)


def get_price(ticker: str) -> float:
    symbol = _normalize_symbol(ticker)

    def fetch() -> float:
        info = _yf_ticker(symbol).info
        price = info.get("regularMarketPrice") or info.get("navPrice") or info.get("previousClose")
        if price is None:
            raise TickerNotFound(f"No price found for {symbol}")
        return float(price)

    return _cached("price", symbol, PRICE_TTL, fetch)


_ASSET_CLASS_KEYS = {
    "stockPosition": "stock",
    "bondPosition": "bond",
    "cashPosition": "cash",
    "preferredPosition": "other",
    "convertiblePosition": "other",
    "otherPosition": "other",
}


def get_profile(ticker: str) -> Profile:
    symbol = _normalize_symbol(ticker)

    def fetch() -> dict:
        t = _yf_ticker(symbol)
        info = t.info
        kind = info.get("quoteType")
        if not kind or kind == "NONE":
            raise TickerNotFound(f"{symbol} was not found on Yahoo Finance")
        profile = Profile(
            ticker=symbol,
            name=info.get("longName") or info.get("shortName") or symbol,
            kind=kind,
            currency=info.get("currency") or "USD",
        )
        if kind in ("ETF", "MUTUALFUND"):
            try:
                funds = t.funds_data
                for key, value in (funds.asset_classes or {}).items():
                    cls = _ASSET_CLASS_KEYS.get(key, "other")
                    profile.asset_classes[cls] = profile.asset_classes.get(cls, 0.0) + float(value or 0)
                profile.sectors = {k: float(v or 0) for k, v in (funds.sector_weightings or {}).items()}
            except Exception as e:  # some funds have no holdings breakdown on Yahoo
                log.info("No fund breakdown for %s: %s", symbol, e)
        elif kind == "EQUITY":
            profile.asset_classes = {"stock": 1.0}
            if info.get("sector"):
                profile.sectors = {info["sector"].lower().replace(" ", "_"): 1.0}
        if not profile.asset_classes:
            profile.asset_classes = {"other": 1.0}
        return asdict(profile)

    return Profile(**_cached("profile", symbol, PROFILE_TTL, fetch))


def get_history(ticker: str, years: int = 10) -> History:
    symbol = _normalize_symbol(ticker)

    def fetch() -> list:
        frame = _yf_ticker(symbol).history(period=f"{years}y", interval="1mo", auto_adjust=True)
        if frame.empty:
            raise TickerNotFound(f"No price history for {symbol}")
        closes = frame["Close"].dropna()
        return [(ts.strftime("%Y-%m-%d"), float(price)) for ts, price in closes.items()]

    return [tuple(row) for row in _cached(f"history{years}y", symbol, HISTORY_TTL, fetch)]
