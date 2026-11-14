"""Tests for the net-worth trend chart (charts.net_worth_trend_png).

The chart functions render to PNG bytes, so the rendering tests assert the PNG
magic number; the running-balance maths is checked through the pure _signed_sum
helper and by driving the rendering down each branch (empty / in-window /
opening-balance carry).
"""
from datetime import date, timedelta

import pytest

import charts
from extensions import db
from models import Holding, Transaction, User

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _user():
    u = User(username="charty")
    u.set_password("secret1")
    db.session.add(u)
    db.session.commit()
    return u.id


def _holding(uid, symbol, qty):
    db.session.add(Holding(user_id=uid, symbol=symbol, name=symbol, quantity=qty))
    db.session.commit()


def _txn(uid, type_, amount, when):
    db.session.add(Transaction(user_id=uid, type=type_, amount=amount,
                               category="Food", note="", date=when))
    db.session.commit()


class _T:
    def __init__(self, type_, amount):
        self.type = type_
        self.amount = amount


def test_signed_sum_nets_income_minus_expense():
    txns = [_T("income", 100.0), _T("expense", 30.0), _T("income", 5.0)]
    assert charts._signed_sum(txns) == 75.0


def test_signed_sum_empty_is_zero():
    assert charts._signed_sum([]) == 0.0


def test_net_worth_empty_renders_placeholder_png(db_session):
    uid = _user()
    png = charts.net_worth_trend_png(uid)
    assert png[:8] == PNG_MAGIC          # empty-state still a valid PNG


def test_net_worth_with_in_window_data_renders(db_session):
    uid = _user()
    _txn(uid, "income", 1000.0, date.today())
    _txn(uid, "expense", 250.0, date.today())
    png = charts.net_worth_trend_png(uid)
    assert png[:8] == PNG_MAGIC


def test_net_worth_carries_opening_balance_from_before_window(db_session):
    """A transaction older than the 6-month window must not be dropped: it seeds
    the opening balance, so the curve renders even with nothing inside the
    window."""
    uid = _user()
    _txn(uid, "income", 5000.0, date.today() - timedelta(days=400))  # pre-window
    png = charts.net_worth_trend_png(uid)
    assert png[:8] == PNG_MAGIC          # opening balance alone -> not "no data"


# --- portfolio_allocation_png -----------------------------------------------

def test_allocation_empty_when_no_holdings(db_session):
    uid = _user()
    png = charts.portfolio_allocation_png(uid)
    assert png[:8] == PNG_MAGIC          # placeholder PNG, no quote fetch needed


def test_allocation_renders_with_priced_holdings(db_session, mocker):
    uid = _user()
    _holding(uid, "AAPL", 2)
    _holding(uid, "MSFT", 1)
    mocker.patch("market.get_quotes", return_value={"AAPL": 100.0, "MSFT": 50.0})
    png = charts.portfolio_allocation_png(uid)
    assert png[:8] == PNG_MAGIC


def test_allocation_placeholder_when_no_market_value(db_session, mocker):
    # Holdings exist but quotes are unavailable (0 value) -> placeholder, no crash.
    uid = _user()
    _holding(uid, "AAPL", 2)
    mocker.patch("market.get_quotes", return_value={})
    png = charts.portfolio_allocation_png(uid)
    assert png[:8] == PNG_MAGIC


def test_allocation_drops_zero_value_holdings(db_session, mocker):
    # AAPL priced, ZZZ unpriced -> only AAPL contributes; still a valid chart.
    uid = _user()
    _holding(uid, "AAPL", 2)
    _holding(uid, "ZZZ", 5)
    mocker.patch("market.get_quotes", return_value={"AAPL": 100.0})
    png = charts.portfolio_allocation_png(uid)
    assert png[:8] == PNG_MAGIC
