"""Hand-authored OpenAPI (Swagger 2.0) spec for the FinTrak REST API.

Served as interactive docs by flasgger (see ``app.py``) at ``/api/docs`` with a
machine-readable spec at ``/api/openapi.json``. Kept as a single source of truth
rather than scattered per-view docstrings, so the whole API reads in one place.

Auth: obtain a token from ``POST /api/auth/login`` and click **Authorize** in the
UI, entering ``Bearer <access_token>``.
"""

_ERROR = {
    "type": "object",
    "properties": {"error": {"type": "string"}},
}

_TRANSACTION = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "type": {"type": "string", "enum": ["income", "expense"]},
        "amount": {"type": "number", "format": "float"},
        "category": {"type": "string"},
        "note": {"type": "string"},
        "date": {"type": "string", "format": "date"},
    },
}

_BUDGET = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "category": {"type": "string"},
        "amount": {"type": "number", "format": "float"},
    },
}

_RECURRING = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "type": {"type": "string", "enum": ["income", "expense"]},
        "amount": {"type": "number", "format": "float"},
        "category": {"type": "string"},
        "note": {"type": "string"},
        "frequency": {"type": "string", "enum": ["daily", "weekly", "monthly"]},
        "next_date": {"type": "string", "format": "date"},
        "active": {"type": "boolean"},
    },
}

_TOKENS = {
    "type": "object",
    "properties": {
        "access_token": {"type": "string"},
        "refresh_token": {"type": "string"},
    },
}

_SECURED = [{"Bearer": []}]


def _body(name, schema, required=True):
    return {
        "in": "body", "name": name, "required": required,
        "schema": schema,
    }


def build_template():
    """Return the full Swagger 2.0 template dict passed to flasgger."""
    return {
        "swagger": "2.0",
        "info": {
            "title": "FinTrak API",
            "description": (
                "REST API for FinTrak, a personal-finance SaaS: JWT-authenticated "
                "transactions, budgets, recurring rules, and a live-valued stock "
                "portfolio.\n\n"
                "**Getting started:** call `POST /api/auth/login`, then click "
                "**Authorize** above and enter `Bearer <access_token>`."
            ),
            "version": "1.0.0",
        },
        "basePath": "/api",
        "schemes": ["https", "http"],
        "consumes": ["application/json"],
        "produces": ["application/json"],
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT access token, formatted as `Bearer <token>`.",
            }
        },
        "tags": [
            {"name": "Auth", "description": "Registration, login, and tokens"},
            {"name": "Transactions", "description": "Income and expense records"},
            {"name": "Budgets", "description": "Per-category monthly spending limits"},
            {"name": "Recurring", "description": "Rules that auto-create transactions"},
            {"name": "Portfolio", "description": "Stock holdings and live quotes"},
        ],
        "definitions": {
            "Error": _ERROR,
            "Transaction": _TRANSACTION,
            "Budget": _BUDGET,
            "RecurringTransaction": _RECURRING,
            "Tokens": _TOKENS,
        },
        "paths": _paths(),
    }


def _paths():
    bad_request = {"description": "Invalid payload", "schema": {"$ref": "#/definitions/Error"}}
    unauthorized = {"description": "Missing or invalid token", "schema": {"$ref": "#/definitions/Error"}}
    not_found = {"description": "Not found", "schema": {"$ref": "#/definitions/Error"}}

    return {
        "/auth/register": {
            "post": {
                "tags": ["Auth"], "summary": "Create an account and receive tokens",
                "parameters": [_body("credentials", {
                    "type": "object", "required": ["username", "password"],
                    "properties": {
                        "username": {"type": "string"},
                        "password": {"type": "string", "minLength": 6},
                        "email": {"type": "string"},
                    },
                })],
                "responses": {
                    "201": {"description": "Created", "schema": {"$ref": "#/definitions/Tokens"}},
                    "400": bad_request,
                    "409": {"description": "Username or email already taken",
                            "schema": {"$ref": "#/definitions/Error"}},
                },
            }
        },
        "/auth/login": {
            "post": {
                "tags": ["Auth"], "summary": "Exchange credentials for tokens",
                "parameters": [_body("credentials", {
                    "type": "object", "required": ["username", "password"],
                    "properties": {
                        "username": {"type": "string"},
                        "password": {"type": "string"},
                    },
                })],
                "responses": {
                    "200": {"description": "OK", "schema": {"$ref": "#/definitions/Tokens"}},
                    "401": {"description": "Invalid credentials",
                            "schema": {"$ref": "#/definitions/Error"}},
                },
            }
        },
        "/auth/refresh": {
            "post": {
                "tags": ["Auth"], "summary": "Mint a new access token",
                "description": "Authorize with the **refresh** token.",
                "security": _SECURED,
                "responses": {
                    "200": {"description": "OK", "schema": {
                        "type": "object",
                        "properties": {"access_token": {"type": "string"}}}},
                    "401": unauthorized,
                },
            }
        },
        "/me": {
            "get": {
                "tags": ["Auth"], "summary": "Current user profile",
                "security": _SECURED,
                "responses": {
                    "200": {"description": "OK", "schema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "username": {"type": "string"},
                            "email": {"type": "string"},
                        }}},
                    "401": unauthorized,
                },
            }
        },
        "/summary": {
            "get": {
                "tags": ["Transactions"], "summary": "Income, expense, and balance totals",
                "security": _SECURED,
                "responses": {
                    "200": {"description": "OK", "schema": {
                        "type": "object",
                        "properties": {
                            "income": {"type": "number"},
                            "expense": {"type": "number"},
                            "balance": {"type": "number"},
                        }}},
                    "401": unauthorized,
                },
            }
        },
        "/transactions": {
            "get": {
                "tags": ["Transactions"], "summary": "List transactions (paginated, filterable)",
                "security": _SECURED,
                "parameters": [
                    {"in": "query", "name": "type", "type": "string",
                     "enum": ["income", "expense"]},
                    {"in": "query", "name": "category", "type": "string"},
                    {"in": "query", "name": "from", "type": "string", "format": "date",
                     "description": "Inclusive start date (YYYY-MM-DD)"},
                    {"in": "query", "name": "to", "type": "string", "format": "date",
                     "description": "Inclusive end date (YYYY-MM-DD)"},
                    {"in": "query", "name": "page", "type": "integer", "default": 1},
                    {"in": "query", "name": "per_page", "type": "integer",
                     "default": 50, "maximum": 200},
                ],
                "responses": {
                    "200": {"description": "OK", "schema": {
                        "type": "object",
                        "properties": {
                            "items": {"type": "array",
                                      "items": {"$ref": "#/definitions/Transaction"}},
                            "page": {"type": "integer"},
                            "per_page": {"type": "integer"},
                            "total": {"type": "integer"},
                            "pages": {"type": "integer"},
                        }}},
                    "400": bad_request,
                    "401": unauthorized,
                },
            },
            "post": {
                "tags": ["Transactions"], "summary": "Create a transaction",
                "security": _SECURED,
                "parameters": [_body("transaction", {
                    "type": "object", "required": ["type", "amount"],
                    "properties": {
                        "type": {"type": "string", "enum": ["income", "expense"]},
                        "amount": {"type": "number"},
                        "category": {"type": "string", "default": "Other"},
                        "note": {"type": "string"},
                        "date": {"type": "string", "format": "date",
                                 "description": "Defaults to today"},
                    },
                })],
                "responses": {
                    "201": {"description": "Created", "schema": {"$ref": "#/definitions/Transaction"}},
                    "400": bad_request,
                    "401": unauthorized,
                },
            },
        },
        "/transactions/{tid}": {
            "parameters": [{"in": "path", "name": "tid", "type": "integer", "required": True}],
            "put": {
                "tags": ["Transactions"], "summary": "Update a transaction",
                "security": _SECURED,
                "parameters": [_body("transaction", {"$ref": "#/definitions/Transaction"}, required=False)],
                "responses": {
                    "200": {"description": "OK", "schema": {"$ref": "#/definitions/Transaction"}},
                    "400": bad_request, "401": unauthorized, "404": not_found,
                },
            },
            "delete": {
                "tags": ["Transactions"], "summary": "Delete a transaction",
                "security": _SECURED,
                "responses": {
                    "200": {"description": "Deleted"},
                    "401": unauthorized, "404": not_found,
                },
            },
        },
        "/transactions.csv": {
            "get": {
                "tags": ["Transactions"], "summary": "Export transactions as CSV",
                "description": "Same filters as `GET /transactions`. Returns `text/csv`.",
                "security": _SECURED,
                "produces": ["text/csv"],
                "responses": {
                    "200": {"description": "CSV file"},
                    "401": unauthorized,
                },
            }
        },
        "/budgets": {
            "get": {
                "tags": ["Budgets"], "summary": "List budgets with current-month spending",
                "security": _SECURED,
                "responses": {
                    "200": {"description": "OK", "schema": {
                        "type": "array", "items": {"$ref": "#/definitions/Budget"}}},
                    "401": unauthorized,
                },
            },
            "post": {
                "tags": ["Budgets"], "summary": "Create a budget",
                "security": _SECURED,
                "parameters": [_body("budget", {
                    "type": "object", "required": ["category", "amount"],
                    "properties": {
                        "category": {"type": "string"},
                        "amount": {"type": "number"},
                    },
                })],
                "responses": {
                    "201": {"description": "Created", "schema": {"$ref": "#/definitions/Budget"}},
                    "400": bad_request, "401": unauthorized,
                    "409": {"description": "Budget already exists for category",
                            "schema": {"$ref": "#/definitions/Error"}},
                },
            },
        },
        "/budgets/{bid}": {
            "parameters": [{"in": "path", "name": "bid", "type": "integer", "required": True}],
            "put": {
                "tags": ["Budgets"], "summary": "Update a budget",
                "security": _SECURED,
                "parameters": [_body("budget", {"$ref": "#/definitions/Budget"}, required=False)],
                "responses": {
                    "200": {"description": "OK", "schema": {"$ref": "#/definitions/Budget"}},
                    "400": bad_request, "401": unauthorized, "404": not_found,
                },
            },
            "delete": {
                "tags": ["Budgets"], "summary": "Delete a budget",
                "security": _SECURED,
                "responses": {"200": {"description": "Deleted"},
                              "401": unauthorized, "404": not_found},
            },
        },
        "/recurring": {
            "get": {
                "tags": ["Recurring"], "summary": "List recurring rules",
                "security": _SECURED,
                "responses": {
                    "200": {"description": "OK", "schema": {
                        "type": "array", "items": {"$ref": "#/definitions/RecurringTransaction"}}},
                    "401": unauthorized,
                },
            },
            "post": {
                "tags": ["Recurring"], "summary": "Create a recurring rule",
                "security": _SECURED,
                "parameters": [_body("rule", {
                    "type": "object", "required": ["type", "amount", "category", "frequency"],
                    "properties": {
                        "type": {"type": "string", "enum": ["income", "expense"]},
                        "amount": {"type": "number"},
                        "category": {"type": "string"},
                        "note": {"type": "string"},
                        "frequency": {"type": "string", "enum": ["daily", "weekly", "monthly"]},
                        "start_date": {"type": "string", "format": "date",
                                       "description": "First occurrence; defaults to today"},
                    },
                })],
                "responses": {
                    "201": {"description": "Created", "schema": {"$ref": "#/definitions/RecurringTransaction"}},
                    "400": bad_request, "401": unauthorized,
                },
            },
        },
        "/recurring/{rid}": {
            "parameters": [{"in": "path", "name": "rid", "type": "integer", "required": True}],
            "put": {
                "tags": ["Recurring"], "summary": "Update a recurring rule",
                "security": _SECURED,
                "parameters": [_body("rule", {"$ref": "#/definitions/RecurringTransaction"}, required=False)],
                "responses": {
                    "200": {"description": "OK", "schema": {"$ref": "#/definitions/RecurringTransaction"}},
                    "400": bad_request, "401": unauthorized, "404": not_found,
                },
            },
            "delete": {
                "tags": ["Recurring"], "summary": "Delete a recurring rule",
                "security": _SECURED,
                "responses": {"200": {"description": "Deleted"},
                              "401": unauthorized, "404": not_found},
            },
        },
        "/recurring/run": {
            "post": {
                "tags": ["Recurring"],
                "summary": "Materialise this user's due rules now",
                "description": "Creates transactions for every due occurrence. Also "
                               "runs automatically once a day via Celery beat.",
                "security": _SECURED,
                "responses": {
                    "200": {"description": "OK", "schema": {
                        "type": "object",
                        "properties": {"created": {"type": "integer"}}}},
                    "401": unauthorized,
                },
            }
        },
        "/portfolio": {
            "get": {
                "tags": ["Portfolio"],
                "summary": "Holdings valued at live quotes",
                "security": _SECURED,
                "responses": {"200": {"description": "OK"}, "401": unauthorized},
            }
        },
        "/quotes": {
            "get": {
                "tags": ["Portfolio"],
                "summary": "Live quote for one or more symbols",
                "security": _SECURED,
                "parameters": [{"in": "query", "name": "symbols", "type": "string",
                                "description": "Comma-separated tickers, e.g. AAPL,MSFT"}],
                "responses": {"200": {"description": "OK"}, "401": unauthorized},
            }
        },
    }
