"""Smoke tests: health probe and basic routing/rendering."""


def test_healthz_ok(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["db"] is True
    # Redis is intentionally unreachable in tests; the app stays healthy.
    assert data["redis"] is False


def test_root_redirects_to_dashboard(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/dashboard" in resp.headers["Location"]


def test_login_page_renders(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"<form" in resp.data


def test_protected_page_requires_login(client):
    # /dashboard should bounce an anonymous user to the login page.
    resp = client.get("/dashboard")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
