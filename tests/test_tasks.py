"""Tests for the Celery tasks (called directly, with the market layer mocked)."""


def test_refresh_symbol(mocker):
    mocker.patch("market.get_quote", return_value=123.0)
    from tasks import refresh_symbol
    assert refresh_symbol("AAPL") == {"AAPL": 123.0}


def test_refresh_quotes_returns_dict(mocker):
    # No holdings in the fresh test DB -> empty dict, but the code path (DB
    # query + loop) still runs. market.get_quote is mocked so nothing hits net.
    mocker.patch("market.get_quote", return_value=1.0)
    from tasks import refresh_quotes
    assert isinstance(refresh_quotes(), dict)
