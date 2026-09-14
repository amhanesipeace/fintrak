"""Tests for editing a transaction: API PUT/PATCH and the web edit form."""


def _create_txn(client, headers, **kw):
    payload = {"type": "expense", "amount": 10, "category": "Food"}
    payload.update(kw)
    return client.post("/api/transactions", headers=headers,
                       json=payload).get_json()["id"]


def _api_headers(client, username):
    r = client.post("/api/auth/register",
                    json={"username": username, "password": "secret1"})
    return {"Authorization": f"Bearer {r.get_json()['access_token']}"}


# --- REST API ---------------------------------------------------------------

def test_update_transaction_success(client, auth_headers):
    tid = _create_txn(client, auth_headers, amount=10, category="Food")
    resp = client.put(f"/api/transactions/{tid}", headers=auth_headers,
                      json={"type": "income", "amount": 500,
                            "category": "Salary", "note": "raise"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["type"] == "income"
    assert data["amount"] == 500.0
    assert data["category"] == "Salary"
    assert data["note"] == "raise"


def test_partial_update_keeps_other_fields(client, auth_headers):
    tid = _create_txn(client, auth_headers, amount=10, category="Food", note="lunch")
    resp = client.patch(f"/api/transactions/{tid}", headers=auth_headers,
                        json={"amount": 25})
    data = resp.get_json()
    assert data["amount"] == 25.0
    assert data["category"] == "Food"    # unchanged
    assert data["note"] == "lunch"       # unchanged


def test_update_invalid_amount_rejected(client, auth_headers):
    tid = _create_txn(client, auth_headers)
    resp = client.put(f"/api/transactions/{tid}", headers=auth_headers,
                      json={"amount": -5})
    assert resp.status_code == 400


def test_update_missing_transaction_404(client, auth_headers):
    resp = client.put("/api/transactions/999", headers=auth_headers,
                      json={"amount": 5})
    assert resp.status_code == 404


def test_update_requires_auth(client):
    assert client.put("/api/transactions/1", json={"amount": 5}).status_code == 401


def test_cannot_update_other_users_transaction(client, auth_headers):
    tid = _create_txn(client, auth_headers, amount=10)
    other = _api_headers(client, "intruder")
    resp = client.put(f"/api/transactions/{tid}", headers=other,
                      json={"amount": 999})
    assert resp.status_code == 404


# --- Web form ---------------------------------------------------------------

def _register(client, username="editor"):
    return client.post("/register",
                       data={"username": username, "password": "secret1"},
                       follow_redirects=True)


def test_edit_page_is_prefilled(client):
    _register(client)
    client.post("/transactions/add",
                data={"type": "expense", "amount": "12.50", "category": "Food",
                      "note": "lunch", "date": "2026-01-15"})
    tid = client.get("/api/transactions").get_json()[0]["id"]
    resp = client.get(f"/transactions/{tid}/edit")
    assert resp.status_code == 200
    assert b"Edit transaction" in resp.data
    assert b"12.50" in resp.data
    assert b"lunch" in resp.data


def test_edit_updates_transaction_web(client):
    _register(client)
    client.post("/transactions/add",
                data={"type": "expense", "amount": "12.50", "category": "Food",
                      "date": "2026-01-15"})
    tid = client.get("/api/transactions").get_json()[0]["id"]
    resp = client.post(f"/transactions/{tid}/edit",
                       data={"type": "expense", "amount": "20.00",
                             "category": "Transport", "date": "2026-01-16"},
                       follow_redirects=True)
    assert b"Transaction updated" in resp.data
    assert b"Transport" in client.get("/transactions").data


def test_edit_invalid_web(client):
    _register(client)
    client.post("/transactions/add",
                data={"type": "expense", "amount": "12.50", "category": "Food"})
    tid = client.get("/api/transactions").get_json()[0]["id"]
    resp = client.post(f"/transactions/{tid}/edit",
                       data={"type": "expense", "amount": "abc"},
                       follow_redirects=True)
    assert b"valid amount" in resp.data
