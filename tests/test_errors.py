"""Error-handling tests: the REST API returns JSON; web pages stay HTML."""


def test_unknown_api_route_returns_json_404(client):
    resp = client.get("/api/does-not-exist")
    assert resp.status_code == 404
    assert resp.is_json
    assert resp.get_json() == {"error": "not found"}


def test_wrong_method_on_api_returns_json_405(client):
    # /api/summary is GET-only; PUT should be a JSON 405 (routing rejects it
    # before auth runs).
    resp = client.put("/api/summary")
    assert resp.status_code == 405
    assert resp.is_json
    assert resp.get_json() == {"error": "method not allowed"}


def test_unknown_web_route_stays_html_404(client):
    resp = client.get("/no-such-page")
    assert resp.status_code == 404
    assert "text/html" in resp.content_type
