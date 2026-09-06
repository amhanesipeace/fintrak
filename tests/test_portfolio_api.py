"""API tests: quotes and portfolio valuation with the market API mocked.

market.get_quotes is patched so tests never hit Alpha Vantage / Yahoo Finance.
"""


def test_quotes_endpoint_returns_prices(client, auth_headers, mocker):
    mocker.patch("market.get_quotes", return_value={"AAPL": 123.45})
    resp = client.get("/api/quotes?symbols=AAPL", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json() == {"AAPL": 123.45}


def test_quotes_require_auth(client):
    assert client.get("/api/quotes").status_code == 401


def test_portfolio_valuation(client, app, auth_headers, mocker):
    mocker.patch("market.get_quotes", return_value={"AAPL": 100.0, "MSFT": 50.0})
    from extensions import db
    from models import User, Holding
    with app.app_context():
        uid = User.query.filter_by(username="tester").first().id
        db.session.add(Holding(user_id=uid, symbol="AAPL", name="Apple", quantity=2))
        db.session.add(Holding(user_id=uid, symbol="MSFT", name="Microsoft", quantity=4))
        db.session.commit()

    resp = client.get("/api/portfolio", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 400.0            # 2*100 + 4*50
    assert len(data["holdings"]) == 2
    aapl = next(h for h in data["holdings"] if h["symbol"] == "AAPL")
    assert aapl["price"] == 100.0
    assert aapl["value"] == 200.0


def test_portfolio_empty(client, auth_headers, mocker):
    mocker.patch("market.get_quotes", return_value={})
    resp = client.get("/api/portfolio", headers=auth_headers)
    assert resp.get_json() == {"total": 0.0, "holdings": []}
