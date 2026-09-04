"""JWT REST API auth tests: register, login, refresh, and protected routes."""


def test_register_returns_tokens(client):
    resp = client.post("/api/auth/register",
                       json={"username": "alice", "password": "secret1"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["username"] == "alice"


def test_register_requires_username_and_password(client):
    resp = client.post("/api/auth/register", json={"username": "", "password": ""})
    assert resp.status_code == 400


def test_register_rejects_short_password(client):
    resp = client.post("/api/auth/register",
                       json={"username": "bob", "password": "123"})
    assert resp.status_code == 400


def test_register_rejects_duplicate_username(client):
    client.post("/api/auth/register",
                json={"username": "carol", "password": "secret1"})
    resp = client.post("/api/auth/register",
                       json={"username": "carol", "password": "secret1"})
    assert resp.status_code == 409


def test_register_rejects_duplicate_email(client):
    client.post("/api/auth/register",
                json={"username": "dave", "email": "d@example.com",
                      "password": "secret1"})
    resp = client.post("/api/auth/register",
                       json={"username": "dave2", "email": "d@example.com",
                             "password": "secret1"})
    assert resp.status_code == 409


def test_login_success_returns_tokens(client):
    client.post("/api/auth/register",
                json={"username": "erin", "password": "secret1"})
    resp = client.post("/api/auth/login",
                       json={"username": "erin", "password": "secret1"})
    assert resp.status_code == 200
    assert "access_token" in resp.get_json()


def test_login_wrong_password_rejected(client):
    client.post("/api/auth/register",
                json={"username": "frank", "password": "secret1"})
    resp = client.post("/api/auth/login",
                       json={"username": "frank", "password": "nope"})
    assert resp.status_code == 401


def test_login_unknown_user_rejected(client):
    resp = client.post("/api/auth/login",
                       json={"username": "ghost", "password": "secret1"})
    assert resp.status_code == 401


def test_protected_route_requires_token(client):
    resp = client.get("/api/summary")
    assert resp.status_code == 401


def test_protected_route_works_with_token(client, auth_headers):
    resp = client.get("/api/summary", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json() == {"income": 0.0, "expense": 0.0, "balance": 0.0}


def test_me_returns_current_user(client, auth_headers):
    resp = client.get("/api/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["username"] == "tester"


def test_refresh_issues_new_access_token(client):
    reg = client.post("/api/auth/register",
                      json={"username": "heidi", "password": "secret1"}).get_json()
    headers = {"Authorization": f"Bearer {reg['refresh_token']}"}
    resp = client.post("/api/auth/refresh", headers=headers)
    assert resp.status_code == 200
    assert "access_token" in resp.get_json()


def test_access_token_rejected_on_refresh_route(client):
    # Presenting an access token where a refresh token is required must fail.
    reg = client.post("/api/auth/register",
                      json={"username": "ivan", "password": "secret1"}).get_json()
    headers = {"Authorization": f"Bearer {reg['access_token']}"}
    resp = client.post("/api/auth/refresh", headers=headers)
    assert resp.status_code in (401, 422)
