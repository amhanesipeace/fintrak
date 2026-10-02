"""Tests for pagination + filtering on GET /api/transactions."""


def _add(client, headers, **kw):
    payload = {"type": "expense", "amount": 10, "category": "Food"}
    payload.update(kw)
    return client.post("/api/transactions", headers=headers, json=payload)


def test_pagination_envelope_and_paging(client, auth_headers):
    for i in range(1, 26):                      # 25 transactions
        _add(client, auth_headers, amount=i)
    r1 = client.get("/api/transactions?page=1&per_page=10", headers=auth_headers).get_json()
    assert r1["total"] == 25
    assert r1["pages"] == 3
    assert r1["page"] == 1
    assert len(r1["items"]) == 10

    r3 = client.get("/api/transactions?page=3&per_page=10", headers=auth_headers).get_json()
    assert len(r3["items"]) == 5               # remainder on the last page

    # pages don't overlap
    ids1 = {t["id"] for t in r1["items"]}
    ids3 = {t["id"] for t in r3["items"]}
    assert ids1.isdisjoint(ids3)


def test_filter_by_type(client, auth_headers):
    _add(client, auth_headers, type="income", amount=100, category="Salary")
    _add(client, auth_headers, type="expense", amount=20, category="Food")
    _add(client, auth_headers, type="expense", amount=30, category="Rent")
    body = client.get("/api/transactions?type=expense", headers=auth_headers).get_json()
    assert body["total"] == 2
    assert all(t["type"] == "expense" for t in body["items"])


def test_filter_by_category(client, auth_headers):
    _add(client, auth_headers, category="Food")
    _add(client, auth_headers, category="Rent")
    body = client.get("/api/transactions?category=Rent", headers=auth_headers).get_json()
    assert body["total"] == 1
    assert body["items"][0]["category"] == "Rent"


def test_filter_by_date_range(client, auth_headers):
    _add(client, auth_headers, date="2026-01-10")
    _add(client, auth_headers, date="2026-02-15")
    _add(client, auth_headers, date="2026-03-20")
    body = client.get("/api/transactions?from=2026-02-01&to=2026-02-28",
                      headers=auth_headers).get_json()
    assert body["total"] == 1
    assert body["items"][0]["date"] == "2026-02-15"


def test_invalid_date_rejected(client, auth_headers):
    assert client.get("/api/transactions?from=nope",
                      headers=auth_headers).status_code == 400


def test_per_page_is_capped(client, auth_headers):
    _add(client, auth_headers)
    body = client.get("/api/transactions?per_page=9999", headers=auth_headers).get_json()
    assert body["per_page"] == 200             # capped
