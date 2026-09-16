# 💰 FinTrak — Full-Stack Financial Management SaaS

[![CI](https://github.com/amhanesipeace/fintrak/actions/workflows/ci.yml/badge.svg)](https://github.com/amhanesipeace/fintrak/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.12-blue.svg)

A full-stack personal-finance platform built with **Flask** and **SQLAlchemy**.
It tracks income/expenses, values a live **stock portfolio**, exposes a
**JWT-secured REST API**, and offloads market-data work to **Celery** with
**Redis** caching. It runs on a **normalised PostgreSQL** schema with
connection pooling and ships as a **Docker Compose** stack.

## Stack

| Concern | Technology |
| --- | --- |
| Web / API | Flask (application factory, blueprints — MVC) |
| ORM / DB | SQLAlchemy → PostgreSQL (SQLite for local dev) |
| Auth | **JWT** (Flask-JWT-Extended) for the API · **bcrypt** password hashing · Flask-Login secure sessions for the UI |
| Market data | **Alpha Vantage** (primary) + **Yahoo Finance** (fallback) |
| Async / cache | **Celery** task queue + beat · **Redis** cache & broker |
| Visualisation | Matplotlib (server-rendered PNG charts) |
| Packaging | **Docker** + Docker Compose (web, worker, beat, db, redis) |

## Architecture

```
app.py            Application factory, extensions, /healthz, money filter
config.py         Config: Postgres + connection pool, JWT, Redis/Celery, APIs
extensions.py     Shared singletons: db, bcrypt, jwt, login_manager
models.py         Normalised, indexed models: User, Transaction, Holding
security.py       auth_required — accepts a JWT bearer token OR a session
auth.py           Web blueprint: register / login / logout (bcrypt)
views.py          Web blueprint: dashboard, transactions, portfolio, charts
api.py            REST blueprint: /api/auth/* (JWT) + data endpoints
market.py         Alpha Vantage + Yahoo Finance quotes (Redis-cached)
cache.py          Redis wrapper with graceful degradation
celery_app.py     Celery app + beat schedule
tasks.py          Async tasks: refresh_quotes, refresh_symbol
charts.py         Matplotlib charts (thread-safe Figure API)
Dockerfile        Image for web / worker / beat
docker-compose.yml  Postgres + Redis + web + worker + beat
```

## Quick start (Docker — recommended)

```bash
cd ~/finance-tracker
cp .env.example .env          # already provided for local dev
docker compose up --build     # web, worker, beat, postgres, redis

# (first run, in another terminal) create the demo account + sample data:
docker compose exec web python seed.py
```

Open **http://localhost:8000** and log in with **`demo` / `demo123`**.
Health check: **http://localhost:8000/healthz**.

## Quick start (no Docker)

Needs local PostgreSQL + Redis running (or omit `DATABASE_URL` to use SQLite;
Redis caching then degrades gracefully to no-ops).

```bash
pip install -r requirements.txt
export DATABASE_URL="postgresql://fintrak:fintrak@localhost:5432/fintrak"
export REDIS_URL="redis://localhost:6379/0"
python3 seed.py
python3 app.py                # http://localhost:8000

# in separate terminals, for async quote refresh:
celery -A celery_app.celery worker --loglevel=info
celery -A celery_app.celery beat   --loglevel=info
```

## Testing

The suite is self-contained — it uses a throwaway SQLite database and a stubbed
Redis, so no PostgreSQL, Redis, or network access is required.

```bash
pip install -r requirements-dev.txt
pytest                                   # run the suite
pytest --cov=. --cov-report=term-missing # with a coverage report
```

79 tests covering the health probe and routing, JWT + session authentication,
the data models (bcrypt hashing, constraints, cascade deletes, serialization),
the REST + web endpoints, Matplotlib chart rendering, the market/cache layer
(provider fallback + Redis), the demo seeder, and the Celery tasks —
**~93% line coverage**. CI enforces a 90% floor.

## REST API

Get a token, then call the data endpoints with `Authorization: Bearer <token>`.
(Data endpoints also accept a browser session cookie.)

```bash
# Register (or login) to receive access + refresh tokens
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo123"}'

TOKEN=...   # access_token from the response

# Add a transaction
curl -X POST http://localhost:8000/api/transactions \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"type":"expense","amount":12.50,"category":"Food","note":"lunch"}'
```

| Method & path | Description |
| --- | --- |
| `POST /api/auth/register` | Create account → tokens |
| `POST /api/auth/login` | Log in → access + refresh tokens |
| `POST /api/auth/refresh` | New access token (send refresh token) |
| `GET  /api/me` | Current user |
| `GET  /api/summary` | Income, expense, balance |
| `GET/POST /api/transactions` | List / create transactions |
| `DELETE /api/transactions/<id>` | Delete a transaction |
| `GET  /api/quotes?symbols=AAPL,MSFT` | Live stock quotes (cached) |
| `GET  /api/portfolio` | Valued holdings + total |

## Performance (measured)

Benchmarked with [`benchmark.py`](benchmark.py) on **PostgreSQL 16 + Redis**,
5,000 transactions, 200 iterations. Reported as **median / p95**.

**Database query latency** (server-side ORM against PostgreSQL, indexed + pooled):

| query | median | p95 |
|-------|-------:|----:|
| `SUM(expense)` aggregation | 0.56 ms | 0.60 ms |
| recent transactions (indexed, limit 8) | 0.55 ms | 0.58 ms |
| user holdings lookup | 0.23 ms | 0.27 ms |

→ all **well under 100 ms**.

**API response latency** (server-side processing via the Flask test client):

| endpoint | median | p95 |
|----------|-------:|----:|
| `GET /api/summary` | 4.41 ms | 6.88 ms |
| `GET /api/portfolio` (cached quotes) | 2.29 ms | 3.27 ms |

→ all **far under 2 s**.

**Why caching matters** — one quote fetch, cold vs warm:

| quote fetch | latency |
|-------------|--------:|
| cold (live Alpha Vantage / Yahoo) | ~695 ms / symbol |
| warm (Redis cache) | ~0.6 ms |

A multi-holding portfolio would otherwise serialize several ~0.7 s external
calls (easily >2 s). Redis caching + a Celery beat job that pre-warms the cache
keep it in the low-millisecond range — **~1,200× faster** on the warm path.

**Reproduce:**

```bash
docker compose up -d db redis
DATABASE_URL=postgresql://fintrak:fintrak@localhost:5432/fintrak \
REDIS_URL=redis://localhost:6379/0 \
python benchmark.py --transactions 5000 --iterations 200
```

*Methodology: query timings measure ORM execution against PostgreSQL; API
timings use Flask's test client (server-side, excludes network + gunicorn);
figures are median and p95 over many iterations.*

**How this maps to the design:** composite index `ix_txn_user_date` and
`ix_holding_user_symbol` serve the hottest queries; connection pooling
(`pool_size`/`max_overflow`/`pool_recycle`/`pool_pre_ping`) avoids per-request
connection setup; Redis caching + Celery keep responses off the slow external-API
path.

## Security notes

- Passwords are hashed with **bcrypt**; never stored in plain text.
- API auth uses signed **JWT** access/refresh tokens.
- Set strong `SECRET_KEY` / `JWT_SECRET_KEY` in `.env` for anything non-local.
- The portfolio tracks quantities only — no real funds or brokerage access.
