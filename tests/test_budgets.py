"""Tests for monthly budgets: model, REST API (incl. spending), and web form."""
import pytest
from sqlalchemy.exc import IntegrityError


def _api_headers(client, username):
    r = client.post("/api/auth/register",
                    json={"username": username, "password": "secret1"})
    return {"Authorization": f"Bearer {r.get_json()['access_token']}"}


def _add_expense(client, headers, amount, category="Food"):
    # No date -> defaults to today, i.e. the current month.
    return client.post("/api/transactions", headers=headers,
                       json={"type": "expense", "amount": amount, "category": category})


# --- REST API ---------------------------------------------------------------

def test_create_budget(client, auth_headers):
    r = client.post("/api/budgets", headers=auth_headers,
                    json={"category": "Food", "amount": 500})
    assert r.status_code == 201
    assert r.get_json()["category"] == "Food"


def test_create_budget_duplicate_409(client, auth_headers):
    client.post("/api/budgets", headers=auth_headers,
                json={"category": "Food", "amount": 500})
    r = client.post("/api/budgets", headers=auth_headers,
                    json={"category": "Food", "amount": 300})
    assert r.status_code == 409


def test_create_budget_invalid(client, auth_headers):
    assert client.post("/api/budgets", headers=auth_headers,
                       json={"category": "Food", "amount": -5}).status_code == 400
    assert client.post("/api/budgets", headers=auth_headers,
                       json={"amount": 100}).status_code == 400  # missing category


def test_budgets_require_auth(client):
    assert client.get("/api/budgets").status_code == 401


def test_list_budgets_with_spending(client, auth_headers):
    client.post("/api/budgets", headers=auth_headers,
                json={"category": "Food", "amount": 100})
    _add_expense(client, auth_headers, 30, "Food")
    _add_expense(client, auth_headers, 10, "Food")
    data = client.get("/api/budgets", headers=auth_headers).get_json()
    assert len(data) == 1
    b = data[0]
    assert b["spent"] == 40.0
    assert b["remaining"] == 60.0
    assert b["percent"] == 40.0
    assert b["over_budget"] is False


def test_budget_over_budget(client, auth_headers):
    client.post("/api/budgets", headers=auth_headers,
                json={"category": "Food", "amount": 50})
    _add_expense(client, auth_headers, 80, "Food")
    b = client.get("/api/budgets", headers=auth_headers).get_json()[0]
    assert b["over_budget"] is True
    assert b["remaining"] == -30.0


def test_update_budget(client, auth_headers):
    bid = client.post("/api/budgets", headers=auth_headers,
                      json={"category": "Food", "amount": 100}).get_json()["id"]
    r = client.put(f"/api/budgets/{bid}", headers=auth_headers, json={"amount": 250})
    assert r.status_code == 200
    assert r.get_json()["amount"] == 250.0


def test_update_budget_missing_404(client, auth_headers):
    assert client.put("/api/budgets/999", headers=auth_headers,
                      json={"amount": 5}).status_code == 404


def test_delete_budget(client, auth_headers):
    bid = client.post("/api/budgets", headers=auth_headers,
                      json={"category": "Food", "amount": 100}).get_json()["id"]
    assert client.delete(f"/api/budgets/{bid}", headers=auth_headers).status_code == 200
    assert client.get("/api/budgets", headers=auth_headers).get_json() == []


def test_budgets_user_isolation(client, auth_headers):
    client.post("/api/budgets", headers=auth_headers,
                json={"category": "Food", "amount": 100})
    other = _api_headers(client, "intruder")
    assert client.get("/api/budgets", headers=other).get_json() == []


# --- Web form ---------------------------------------------------------------

def _register(client, username="budgeter"):
    return client.post("/register",
                       data={"username": username, "password": "secret1"},
                       follow_redirects=True)


def test_budgets_page_and_add_web(client):
    _register(client)
    r = client.post("/budgets/add", data={"category": "Food", "amount": "200"},
                    follow_redirects=True)
    assert b"Budget saved" in r.data
    assert b"Food" in client.get("/budgets").data


def test_budget_delete_web(client):
    _register(client)
    client.post("/budgets/add", data={"category": "Food", "amount": "200"},
                follow_redirects=True)
    bid = client.get("/api/budgets").get_json()[0]["id"]
    r = client.post(f"/budgets/{bid}/delete", follow_redirects=True)
    assert b"Budget removed" in r.data


# --- Model ------------------------------------------------------------------

def test_budget_unique_per_category(db_session):
    from models import User, Budget
    u = User(username="bu")
    u.set_password("x")
    db_session.session.add(u)
    db_session.session.commit()
    db_session.session.add(Budget(user_id=u.id, category="Food", amount=100))
    db_session.session.commit()
    db_session.session.add(Budget(user_id=u.id, category="Food", amount=200))
    with pytest.raises(IntegrityError):
        db_session.session.commit()
    db_session.session.rollback()


def test_budget_cascade_delete(db_session):
    from models import User, Budget
    u = User(username="bu2")
    u.set_password("x")
    db_session.session.add(u)
    db_session.session.commit()
    db_session.session.add(Budget(user_id=u.id, category="Rent", amount=1000))
    db_session.session.commit()
    assert Budget.query.count() == 1
    db_session.session.delete(u)
    db_session.session.commit()
    assert Budget.query.count() == 0
