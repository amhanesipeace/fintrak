"""Tests for CSV export of transactions."""


def _add(client, headers, **kw):
    payload = {"type": "expense", "amount": 10, "category": "Food"}
    payload.update(kw)
    return client.post("/api/transactions", headers=headers, json=payload)


def test_csv_export_basic(client, auth_headers):
    _add(client, auth_headers, amount=12.5, category="Food", note="lunch",
         date="2026-01-15")
    resp = client.get("/api/transactions.csv", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert "attachment" in resp.headers["Content-Disposition"]
    text = resp.get_data(as_text=True)
    lines = text.strip().splitlines()
    assert lines[0] == "date,type,category,amount,note"
    assert "2026-01-15,expense,Food,12.50,lunch" in text


def test_csv_export_respects_filters(client, auth_headers):
    _add(client, auth_headers, type="income", amount=100, category="Salary")
    _add(client, auth_headers, type="expense", amount=20, category="Food")
    resp = client.get("/api/transactions.csv?type=income", headers=auth_headers)
    text = resp.get_data(as_text=True)
    assert "Salary" in text
    assert "Food" not in text


def test_csv_export_invalid_date(client, auth_headers):
    assert client.get("/api/transactions.csv?from=bad",
                      headers=auth_headers).status_code == 400


def test_csv_export_requires_auth(client):
    assert client.get("/api/transactions.csv").status_code == 401


def test_csv_export_only_own_rows(client, auth_headers):
    _add(client, auth_headers, category="Mine")
    other = client.post("/api/auth/register",
                        json={"username": "other", "password": "secret1"}).get_json()
    other_h = {"Authorization": f"Bearer {other['access_token']}"}
    text = client.get("/api/transactions.csv", headers=other_h).get_data(as_text=True)
    assert "Mine" not in text                      # isolation
    assert text.strip() == "date,type,category,amount,note"  # header only
