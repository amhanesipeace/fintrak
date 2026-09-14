"""Web UI tests: the server-rendered pages and form actions (session auth).

These drive the same routes a browser would, exercising views.py and the
Matplotlib chart rendering in charts.py.
"""


def _register(client, username="viewer"):
    """Register (which auto-logs-in) so the session cookie is set."""
    return client.post("/register",
                       data={"username": username, "password": "secret1"},
                       follow_redirects=True)


def test_dashboard_renders(client):
    _register(client)
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data


def test_add_and_delete_transaction_web(client):
    _register(client)
    resp = client.post("/transactions/add",
                       data={"type": "expense", "amount": "12.50",
                             "category": "Food", "note": "lunch",
                             "date": "2026-01-15"}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Transaction added" in resp.data
    assert b"Food" in client.get("/transactions").data

    # Find its id (the API accepts the same session), then delete via the form.
    tid = client.get("/api/transactions").get_json()[0]["id"]
    resp = client.post(f"/transactions/{tid}/delete", follow_redirects=True)
    assert b"Transaction deleted" in resp.data


def test_add_transaction_invalid_web(client):
    _register(client)
    resp = client.post("/transactions/add",
                       data={"type": "expense", "amount": "not-a-number"},
                       follow_redirects=True)
    assert b"valid amount" in resp.data


def test_portfolio_add_and_delete_web(client, mocker):
    mocker.patch("market.get_quotes", return_value={"AAPL": 100.0})
    mocker.patch("market.lookup_name", return_value="Apple Inc.")
    _register(client)

    resp = client.post("/portfolio/add",
                       data={"symbol": "AAPL", "quantity": "3"},
                       follow_redirects=True)
    assert resp.status_code == 200
    assert b"Added" in resp.data
    assert b"AAPL" in client.get("/portfolio").data

    hid = client.get("/api/portfolio").get_json()["holdings"][0]["id"]
    resp = client.post(f"/portfolio/{hid}/delete", follow_redirects=True)
    assert b"Holding removed" in resp.data


def test_portfolio_add_invalid_web(client):
    _register(client)
    resp = client.post("/portfolio/add",
                       data={"symbol": "", "quantity": "oops"},
                       follow_redirects=True)
    assert b"valid quantity" in resp.data


def test_chart_endpoints_return_png_when_empty(client):
    _register(client)
    for path in ("/charts/spending.png", "/charts/trend.png"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert resp.content_type == "image/png"
        assert resp.data[:8] == b"\x89PNG\r\n\x1a\n"   # PNG magic bytes


def test_chart_endpoints_return_png_with_data(client):
    _register(client)
    # No date -> defaults to today, so the 6-month trend has data too.
    client.post("/transactions/add",
                data={"type": "expense", "amount": "50", "category": "Food"})
    client.post("/transactions/add",
                data={"type": "income", "amount": "1000", "category": "Salary"})
    for path in ("/charts/spending.png", "/charts/trend.png"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert resp.content_type == "image/png"
