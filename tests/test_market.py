"""Unit tests for market.py: provider fallback and quote caching (all mocked)."""
import market


# --- provider fallback: Alpha Vantage primary, Yahoo Finance fallback --------

def test_fetch_uses_alpha_vantage_when_available(mocker):
    mocker.patch("market._av_quote", return_value=100.0)
    yf = mocker.patch("market._yf_quote", return_value=200.0)
    assert market._fetch_quote("AAPL") == 100.0
    yf.assert_not_called()          # AV succeeded, so Yahoo is skipped


def test_fetch_falls_back_to_yahoo_when_av_none(mocker):
    mocker.patch("market._av_quote", return_value=None)
    yf = mocker.patch("market._yf_quote", return_value=200.0)
    assert market._fetch_quote("AAPL") == 200.0
    yf.assert_called_once()


def test_fetch_returns_none_when_both_fail(mocker):
    mocker.patch("market._av_quote", return_value=None)
    mocker.patch("market._yf_quote", return_value=None)
    assert market._fetch_quote("AAPL") is None


# --- Alpha Vantage parsing ---------------------------------------------------

def test_av_quote_skips_request_without_api_key(mocker):
    mocker.patch("market.ALPHAVANTAGE_API_KEY", "")
    get = mocker.patch("market.requests.get")
    assert market._av_quote("AAPL") is None
    get.assert_not_called()


def test_av_quote_parses_price(mocker):
    mocker.patch("market.ALPHAVANTAGE_API_KEY", "KEY")
    resp = mocker.Mock()
    resp.raise_for_status = mocker.Mock()
    resp.json.return_value = {"Global Quote": {"05. price": "123.45"}}
    mocker.patch("market.requests.get", return_value=resp)
    assert market._av_quote("AAPL") == 123.45


def test_av_quote_none_on_rate_limit_payload(mocker):
    mocker.patch("market.ALPHAVANTAGE_API_KEY", "KEY")
    resp = mocker.Mock()
    resp.raise_for_status = mocker.Mock()
    resp.json.return_value = {"Information": "rate limit reached"}
    mocker.patch("market.requests.get", return_value=resp)
    assert market._av_quote("AAPL") is None


# --- get_quote caching behavior ----------------------------------------------

def test_get_quote_returns_cached_without_fetching(mocker):
    mocker.patch("cache.get_json", return_value=99.0)
    fetch = mocker.patch("market._fetch_quote")
    assert market.get_quote("AAPL") == 99.0
    fetch.assert_not_called()       # cache hit → no upstream call


def test_get_quote_fetches_and_caches_on_miss(mocker):
    mocker.patch("cache.get_json", return_value=None)
    setj = mocker.patch("cache.set_json")
    mocker.patch("market._fetch_quote", return_value=150.0)
    # lower-case input should be normalised to the AAPL cache key
    assert market.get_quote("aapl") == 150.0
    setj.assert_called_once_with("quote:AAPL", 150.0, market.QUOTE_CACHE_TTL)


def test_get_quote_does_not_cache_none(mocker):
    mocker.patch("cache.get_json", return_value=None)
    setj = mocker.patch("cache.set_json")
    mocker.patch("market._fetch_quote", return_value=None)
    assert market.get_quote("AAPL") is None
    setj.assert_not_called()


def test_get_quotes_maps_and_normalises_symbols(mocker):
    prices = {"AAPL": 1.0, "MSFT": 2.0}
    mocker.patch("market.get_quote", side_effect=lambda s: prices[s])
    assert market.get_quotes(["aapl", "MSFT"]) == {"AAPL": 1.0, "MSFT": 2.0}
