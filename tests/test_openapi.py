"""Tests for the OpenAPI spec and bundled Swagger UI docs."""


def test_openapi_spec_served(client):
    r = client.get("/api/openapi.json")
    assert r.status_code == 200
    assert r.content_type.startswith("application/json")
    spec = r.get_json()
    assert spec["swagger"] == "2.0"
    assert spec["info"]["title"] == "FinTrak API"
    assert spec["basePath"] == "/api"


def test_openapi_documents_core_endpoints(client):
    spec = client.get("/api/openapi.json").get_json()
    paths = spec["paths"]
    for p in ("/auth/login", "/transactions", "/budgets",
              "/recurring", "/recurring/run", "/portfolio"):
        assert p in paths, f"{p} missing from spec"
    # Secured endpoints must declare the Bearer requirement.
    assert spec["paths"]["/transactions"]["get"]["security"] == [{"Bearer": []}]
    assert "Bearer" in spec["securityDefinitions"]


def test_swagger_ui_served(client):
    r = client.get("/api/docs/")
    assert r.status_code == 200
    assert b"swagger-ui" in r.data.lower()


def test_docs_do_not_break_real_api(client, auth_headers):
    # The API still responds normally with the docs mounted.
    assert client.get("/api/summary", headers=auth_headers).status_code == 200
