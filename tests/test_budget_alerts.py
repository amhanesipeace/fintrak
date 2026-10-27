"""Tests for budget alerts: the queries.budget_alerts helper + dashboard card.

An alert fires when this month's spending in a budgeted category reaches the
warning threshold (80% of the limit). The dashboard surfaces these so the user
sees trouble without opening the budgets page.
"""


def _budget(client, auth_headers, category, amount):
    return client.post("/api/budgets", headers=auth_headers,
                       json={"category": category, "amount": amount})


def _spend(client, auth_headers, amount, category="Food"):
    # No date -> defaults to today, i.e. the current month.
    return client.post("/api/transactions", headers=auth_headers,
                       json={"type": "expense", "amount": amount, "category": category})


def _uid(app, username="tester"):
    from models import User
    with app.app_context():
        return User.query.filter_by(username=username).first().id


# --- queries.budget_alerts --------------------------------------------------

def test_alert_over_budget(app, client, auth_headers):
    from queries import budget_alerts
    _budget(client, auth_headers, "Food", 100)
    _spend(client, auth_headers, 120)
    with app.app_context():
        alerts = budget_alerts(_uid(app))
    assert len(alerts) == 1
    a = alerts[0]
    assert a["category"] == "Food" and a["status"] == "over"
    assert a["spent"] == 120.0 and a["percent"] == 100   # capped
    assert a["remaining"] == -20.0


def test_alert_warning_threshold(app, client, auth_headers):
    from queries import budget_alerts
    _budget(client, auth_headers, "Food", 100)
    _spend(client, auth_headers, 85)                     # 85% >= 80%
    with app.app_context():
        alerts = budget_alerts(_uid(app))
    assert len(alerts) == 1 and alerts[0]["status"] == "warning"
    assert alerts[0]["percent"] == 85


def test_no_alert_when_comfortably_under(app, client, auth_headers):
    from queries import budget_alerts
    _budget(client, auth_headers, "Food", 100)
    _spend(client, auth_headers, 50)                     # 50% < 80%
    with app.app_context():
        assert budget_alerts(_uid(app)) == []


def test_no_alert_without_budget(app, client, auth_headers):
    from queries import budget_alerts
    _spend(client, auth_headers, 999)                    # spending but no budget set
    with app.app_context():
        assert budget_alerts(_uid(app)) == []


def test_alerts_sorted_worst_first(app, client, auth_headers):
    from queries import budget_alerts
    _budget(client, auth_headers, "Food", 100)
    _budget(client, auth_headers, "Transport", 100)
    _spend(client, auth_headers, 90, "Food")             # 90%
    _spend(client, auth_headers, 150, "Transport")       # 150%
    with app.app_context():
        alerts = budget_alerts(_uid(app))
    assert [a["category"] for a in alerts] == ["Transport", "Food"]


# --- dashboard card ---------------------------------------------------------

def _register_web(client, username="tester"):
    return client.post("/register",
                       data={"username": username, "password": "secret1"},
                       follow_redirects=True)


def test_dashboard_shows_alert_card(client, auth_headers):
    # auth_headers already registered "tester"; log the browser session in too.
    client.post("/login", data={"username": "tester", "password": "secret1"},
                follow_redirects=True)
    _budget(client, auth_headers, "Food", 100)
    _spend(client, auth_headers, 120)
    page = client.get("/dashboard").data
    assert b"Budget alerts" in page
    assert b"Food" in page and b"Over budget" in page


def test_dashboard_hides_alert_card_when_none(client):
    _register_web(client, "fresh")
    page = client.get("/dashboard").data
    assert b"Budget alerts" not in page
