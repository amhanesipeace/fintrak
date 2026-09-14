"""Tests for market.py provider paths that need a stand-in for yfinance."""
import types

import market


def _fake_yfinance(last_price=None, info=None):
    """Build a fake `yfinance` module so no network/library is needed."""
    mod = types.ModuleType("yfinance")
    info_dict = info or {}   # named distinctly to avoid class-body name shadowing

    class _FastInfo:
        pass
    fi = _FastInfo()
    if last_price is not None:
        fi.last_price = last_price

    class _Ticker:
        def __init__(self, symbol):
            self.symbol = symbol
        fast_info = fi
        info = info_dict

    mod.Ticker = _Ticker
    return mod


def test_yf_quote_reads_last_price(mocker):
    mocker.patch.dict("sys.modules", {"yfinance": _fake_yfinance(last_price=250.0)})
    assert market._yf_quote("AAPL") == 250.0


def test_yf_quote_returns_none_when_unavailable(mocker):
    # No last_price attribute -> engine should return None, not crash.
    mocker.patch.dict("sys.modules", {"yfinance": _fake_yfinance(last_price=None)})
    assert market._yf_quote("AAPL") is None


def test_lookup_name_known_symbol_needs_no_network():
    assert market.lookup_name("AAPL") == "Apple Inc."


def test_lookup_name_unknown_symbol_uses_yfinance(mocker):
    mocker.patch.dict("sys.modules",
                      {"yfinance": _fake_yfinance(info={"shortName": "Zeta Corp"})})
    assert market.lookup_name("ZZZZ") == "Zeta Corp"
