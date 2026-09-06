"""API tests: transaction CRUD, validation, summary math, and user isolation."""


def _headers(client, username):
    resp = client.post("/api/auth/register",
                       json={"username": username, "password": "secret1"})
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


def test_create_transaction(client, auth_headers):
    resp = client.post("/api/transactions", headers=auth_headers,
                       json={"type": "income", "amount": 3200, "category": "Salary"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["type"] == "income"
    assert data["amount"] == 3200.0
    assert data["category"] == "Salary"


def test_create_rejects_bad_type(client, auth_headers):
    resp = client.post("/api/transactions", headers=auth_headers,
                       json={"type": "nope", "amount": 5})
    assert resp.status_code == 400


def test_create_rejects_negative_amount(client, auth_headers):
    resp = client.post("/api/transactions", headers=auth_headers,
                       json={"type": "income", "amount": -5})
    assert resp.status_code == 400


def test_create_rejects_missing_amount(client, auth_headers):
    resp = client.post("/api/transactions", headers=auth_headers,
                       json={"type": "income"})
    assert resp.status_code == 400


def test_list_transactions(client, auth_headers):
    client.post("/api/transactions", headers=auth_headers,
                json={"type": "income", "amount": 100, "category": "Salary"})
    client.post("/api/transactions", headers=auth_headers,
                json={"type": "expense", "amount": 40, "category": "Food"})
    resp = client.get("/api/transactions", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2


def test_transactions_require_auth(client):
    assert client.get("/api/transactions").status_code == 401


def test_delete_transaction(client, auth_headers):
    tid = client.post("/api/transactions", headers=auth_headers,
                      json={"type": "expense", "amount": 10, "category": "Food"}
                      ).get_json()["id"]
    resp = client.delete(f"/api/transactions/{tid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json() == {"deleted": tid}
    assert client.get("/api/transactions", headers=auth_headers).get_json() == []


def test_delete_missing_transaction(client, auth_headers):
    resp = client.delete("/api/transactions/999", headers=auth_headers)
    assert resp.status_code == 404


def test_summary_math(client, auth_headers):
    client.post("/api/transactions", headers=auth_headers,
                json={"type": "income", "amount": 3200, "category": "Salary"})
    client.post("/api/transactions", headers=auth_headers,
                json={"type": "expense", "amount": 200, "category": "Rent"})
    data = client.get("/api/summary", headers=auth_headers).get_json()
    assert data == {"income": 3200.0, "expense": 200.0, "balance": 3000.0}


def test_users_are_isolated(client, auth_headers):
    # tester creates a transaction; a different user must not see or delete it.
    tid = client.post("/api/transactions", headers=auth_headers,
                      json={"type": "income", "amount": 500, "category": "Salary"}
                      ).get_json()["id"]
    other = _headers(client, "intruder")
    assert client.get("/api/transactions", headers=other).get_json() == []
    assert client.delete(f"/api/transactions/{tid}", headers=other).status_code == 404
    assert client.get("/api/summary", headers=other).get_json()["income"] == 0.0
