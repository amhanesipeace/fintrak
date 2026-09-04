"""Web (session) auth tests: register, login, logout via the HTML forms."""


def test_web_register_logs_in(client):
    resp = client.post("/register",
                       data={"username": "webuser", "password": "secret1"},
                       follow_redirects=True)
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data          # nav shown once authenticated


def test_web_register_short_password_rejected(client):
    resp = client.post("/register",
                       data={"username": "shorty", "password": "123"},
                       follow_redirects=True)
    assert b"at least 6 characters" in resp.data


def test_web_login_wrong_password(client):
    client.post("/register", data={"username": "jane", "password": "secret1"},
                follow_redirects=True)
    client.get("/logout", follow_redirects=True)   # register auto-logs-in
    resp = client.post("/login", data={"username": "jane", "password": "nope"},
                       follow_redirects=True)
    assert b"Invalid username or password" in resp.data


def test_web_login_success(client):
    client.post("/register", data={"username": "kyle", "password": "secret1"},
                follow_redirects=True)
    client.get("/logout", follow_redirects=True)
    resp = client.post("/login", data={"username": "kyle", "password": "secret1"},
                       follow_redirects=True)
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data


def test_web_logout_returns_to_login(client):
    client.post("/register", data={"username": "liam", "password": "secret1"},
                follow_redirects=True)
    resp = client.get("/logout", follow_redirects=True)
    assert resp.status_code == 200
    assert b"<form" in resp.data               # back on the login page
