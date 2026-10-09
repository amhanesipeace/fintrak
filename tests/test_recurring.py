"""Tests for recurring transactions: date cadence, materialisation, and REST API."""
from datetime import date, timedelta

import pytest

from models import RecurringTransaction
from recurring import advance_date, process_due_recurring


def _headers(client, username="recur"):
    r = client.post("/api/auth/register",
                    json={"username": username, "password": "secret1"})
    return {"Authorization": f"Bearer {r.get_json()['access_token']}"}


# --- advance_date (pure logic) ---------------------------------------------

def test_advance_daily():
    assert advance_date(date(2026, 1, 31), "daily") == date(2026, 2, 1)


def test_advance_weekly():
    assert advance_date(date(2026, 1, 1), "weekly") == date(2026, 1, 8)


def test_advance_monthly_simple():
    assert advance_date(date(2026, 1, 15), "monthly") == date(2026, 2, 15)


def test_advance_monthly_clamps_to_short_month():
    # Jan 31 has no counterpart in February -> clamp to Feb 28 (2026 not a leap year).
    assert advance_date(date(2026, 1, 31), "monthly") == date(2026, 2, 28)


def test_advance_monthly_year_rollover():
    assert advance_date(date(2026, 12, 10), "monthly") == date(2027, 1, 10)


def test_advance_unknown_frequency_raises():
    with pytest.raises(ValueError):
        advance_date(date(2026, 1, 1), "yearly")


# --- REST API ---------------------------------------------------------------

def test_create_recurring(client, auth_headers):
    r = client.post("/api/recurring", headers=auth_headers,
                    json={"type": "expense", "amount": 9.99,
                          "category": "Netflix", "frequency": "monthly"})
    assert r.status_code == 201
    body = r.get_json()
    assert body["category"] == "Netflix"
    assert body["frequency"] == "monthly"
    assert body["active"] is True
    assert body["next_date"] == date.today().isoformat()


def test_create_recurring_invalid(client, auth_headers):
    # bad frequency
    assert client.post("/api/recurring", headers=auth_headers,
                       json={"type": "expense", "amount": 5, "category": "X",
                             "frequency": "yearly"}).status_code == 400
    # bad type
    assert client.post("/api/recurring", headers=auth_headers,
                       json={"type": "spend", "amount": 5, "category": "X",
                             "frequency": "daily"}).status_code == 400
    # non-positive amount
    assert client.post("/api/recurring", headers=auth_headers,
                       json={"type": "expense", "amount": 0, "category": "X",
                             "frequency": "daily"}).status_code == 400
    # bad start_date
    assert client.post("/api/recurring", headers=auth_headers,
                       json={"type": "expense", "amount": 5, "category": "X",
                             "frequency": "daily",
                             "start_date": "not-a-date"}).status_code == 400


def test_recurring_requires_auth(client):
    assert client.get("/api/recurring").status_code == 401


def test_update_recurring(client, auth_headers):
    rid = client.post("/api/recurring", headers=auth_headers,
                      json={"type": "expense", "amount": 10, "category": "Gym",
                            "frequency": "monthly"}).get_json()["id"]
    r = client.patch(f"/api/recurring/{rid}", headers=auth_headers,
                     json={"amount": 15, "active": False, "frequency": "weekly"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["amount"] == 15
    assert body["active"] is False
    assert body["frequency"] == "weekly"


def test_delete_recurring(client, auth_headers):
    rid = client.post("/api/recurring", headers=auth_headers,
                      json={"type": "income", "amount": 2000, "category": "Salary",
                            "frequency": "monthly"}).get_json()["id"]
    assert client.delete(f"/api/recurring/{rid}", headers=auth_headers).status_code == 200
    assert client.get("/api/recurring", headers=auth_headers).get_json() == []


def test_recurring_is_user_scoped(client, auth_headers):
    # Alice's rule must not be visible to (or deletable by) Bob.
    rid = client.post("/api/recurring", headers=auth_headers,
                      json={"type": "expense", "amount": 5, "category": "A",
                            "frequency": "daily"}).get_json()["id"]
    bob = _headers(client, "bob")
    assert client.get("/api/recurring", headers=bob).get_json() == []
    assert client.delete(f"/api/recurring/{rid}", headers=bob).status_code == 404


# --- Materialisation (run endpoint + catch-up) ------------------------------

def test_run_materialises_due_occurrences(client, auth_headers):
    # A daily rule starting 3 days ago should emit 4 transactions (days -3..0).
    start = (date.today() - timedelta(days=3)).isoformat()
    client.post("/api/recurring", headers=auth_headers,
                json={"type": "expense", "amount": 1, "category": "Coffee",
                      "frequency": "daily", "start_date": start})

    r = client.post("/api/recurring/run", headers=auth_headers)
    assert r.status_code == 200
    assert r.get_json()["created"] == 4

    # Running again is a no-op: next_date has advanced past today.
    assert client.post("/api/recurring/run", headers=auth_headers).get_json()["created"] == 0

    # The generated rows are real transactions in the user's history.
    txns = client.get("/api/transactions", headers=auth_headers).get_json()
    items = txns["items"] if isinstance(txns, dict) else txns
    assert sum(1 for t in items if t["category"] == "Coffee") == 4


def test_run_skips_future_and_inactive(client, auth_headers):
    future = (date.today() + timedelta(days=5)).isoformat()
    client.post("/api/recurring", headers=auth_headers,
                json={"type": "expense", "amount": 1, "category": "Later",
                      "frequency": "daily", "start_date": future})
    # A due-but-inactive rule is also skipped.
    rid = client.post("/api/recurring", headers=auth_headers,
                      json={"type": "expense", "amount": 1, "category": "Paused",
                            "frequency": "daily"}).get_json()["id"]
    client.patch(f"/api/recurring/{rid}", headers=auth_headers, json={"active": False})

    assert client.post("/api/recurring/run", headers=auth_headers).get_json()["created"] == 0


def test_process_due_advances_next_date(db_session):
    """process_due_recurring advances next_date past today after materialising."""
    from models import User
    user = User(username="mat")
    user.set_password("secret1")
    db_session.session.add(user)
    db_session.session.commit()

    rule = RecurringTransaction(
        user_id=user.id, type="expense", amount=5, category="Bus",
        frequency="weekly", next_date=date.today() - timedelta(days=7),
    )
    db_session.session.add(rule)
    db_session.session.commit()

    created = process_due_recurring(user_id=user.id)
    assert created == 2  # one week ago + today
    assert rule.next_date > date.today()
