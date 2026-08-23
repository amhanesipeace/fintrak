"""Live equity quotes from Alpha Vantage (primary) and Yahoo Finance (fallback).

Quotes are cached in Redis (see cache.py) for `QUOTE_CACHE_TTL` seconds so
repeated look-ups are sub-millisecond and we stay within provider rate limits.
Alpha Vantage is used when ALPHAVANTAGE_API_KEY is set; otherwise — and on any
Alpha Vantage error or rate-limit — we fall back to Yahoo Finance (yfinance).
"""
import os

import requests

import cache

ALPHAVANTAGE_API_KEY = os.environ.get("ALPHAVANTAGE_API_KEY", "")
QUOTE_CACHE_TTL = int(os.environ.get("QUOTE_CACHE_TTL", 60))
AV_URL = "https://www.alphavantage.co/query"

# Curated set of popular tickers offered in the "add holding" dropdown.
# Users may also type any other valid symbol.
STOCKS = [
    {"symbol": "AAPL", "name": "Apple Inc."},
    {"symbol": "MSFT", "name": "Microsoft Corporation"},
    {"symbol": "GOOGL", "name": "Alphabet Inc."},
    {"symbol": "AMZN", "name": "Amazon.com, Inc."},
    {"symbol": "NVDA", "name": "NVIDIA Corporation"},
    {"symbol": "META", "name": "Meta Platforms, Inc."},
    {"symbol": "TSLA", "name": "Tesla, Inc."},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co."},
    {"symbol": "V", "name": "Visa Inc."},
    {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust"},
]
STOCK_BY_SYMBOL = {s["symbol"]: s for s in STOCKS}


def _av_quote(symbol):
    """Fetch a single quote from Alpha Vantage, or None on any problem."""
    if not ALPHAVANTAGE_API_KEY:
        return None
    try:
        resp = requests.get(AV_URL, params={
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": ALPHAVANTAGE_API_KEY,
        }, timeout=10)
        resp.raise_for_status()
        price = resp.json().get("Global Quote", {}).get("05. price")
        return float(price) if price else None
    except (requests.RequestException, ValueError, TypeError):
        return None


def _yf_quote(symbol):
    """Fetch a single quote from Yahoo Finance, or None on any problem."""
    try:
        import yfinance as yf
        fi = yf.Ticker(symbol).fast_info
        # yfinance FastInfo exposes values via attributes; .get() returns None.
        price = getattr(fi, "last_price", None)
        if price is None:
            try:
                price = fi["last_price"]
            except Exception:
                price = None
        return float(price) if price else None
    except Exception:
        return None


def _fetch_quote(symbol):
    """Alpha Vantage first, then Yahoo Finance as a fallback."""
    return _av_quote(symbol) or _yf_quote(symbol)


def get_quote(symbol):
    """Return the latest price for one symbol (Redis-cached), or None."""
    symbol = symbol.upper().strip()
    if not symbol:
        return None

    key = f"quote:{symbol}"
    cached = cache.get_json(key)
    if cached is not None:
        return cached

    price = _fetch_quote(symbol)
    if price is not None:
        cache.set_json(key, price, QUOTE_CACHE_TTL)
    return price


def get_quotes(symbols):
    """Return {SYMBOL: price} for many symbols, using the per-symbol cache."""
    out = {}
    for s in {sym.upper().strip() for sym in symbols if sym}:
        out[s] = get_quote(s)
    return out


def lookup_name(symbol):
    """Best-effort company/ETF name for a freshly added symbol."""
    symbol = symbol.upper().strip()
    if symbol in STOCK_BY_SYMBOL:
        return STOCK_BY_SYMBOL[symbol]["name"]
    try:
        import yfinance as yf
        info = yf.Ticker(symbol).info or {}
        return info.get("shortName") or info.get("longName") or symbol
    except Exception:
        return symbol
