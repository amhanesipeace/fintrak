# 💰 FinTrack — Personal Finance Tracker

A web application built with **Flask** for tracking and managing personal
finances. Features secure user authentication, server-side data visualisation
with **Matplotlib**, a **RESTful API**, and real-time financial data from a
live market API. Backed by **SQLAlchemy** so it runs on SQLite locally and
**PostgreSQL** in production with no code changes.

## Features

- 🔐 **User authentication** — register / login / logout with hashed passwords
  (Werkzeug) and session management (Flask-Login)
- 💸 **Income & expense tracking** — add, categorise, date, annotate and delete
  transactions; running balance and totals
- 📊 **Data visualisation (Matplotlib)** — spending-by-category donut and a
  6-month income-vs-expense bar chart, rendered server-side as PNGs
- 📈 **Real-time financial data** — a crypto portfolio valued with **live prices
  from the CoinGecko REST API** (no API key required)
- 🧩 **RESTful JSON API** — programmatic access to summary, transactions, and
  live prices
- 🗄️ **PostgreSQL-ready schema** — clean, indexed SQLAlchemy models

## Architecture

```
app.py            Application factory, config, money filter
config.py         Settings (SECRET_KEY, DATABASE_URL -> SQLite/PostgreSQL)
extensions.py     Shared db + login_manager instances
models.py         SQLAlchemy models: User, Transaction, Holding (indexed)
auth.py           Blueprint: register / login / logout
views.py          Blueprint: dashboard, transactions, portfolio, chart images
api.py            Blueprint: RESTful JSON endpoints (/api/...)
charts.py         Matplotlib chart rendering (thread-safe Figure API)
market.py         CoinGecko live-price integration (cached)
templates/        Jinja2 templates (server-rendered UI)
static/style.css  Dark finance theme
seed.py           Demo account + sample data
```

## Quick start

```bash
cd ~/finance-tracker
pip install -r requirements.txt     # first time only
python3 seed.py                     # optional: demo account + sample data
python3 app.py                      # http://localhost:5060
```

Open **http://localhost:5060**. Log in to the demo account (**`demo` / `demo123`**)
or register your own.

## REST API

All endpoints require an authenticated session.

| Method & path                | Description                          |
| ---------------------------- | ----------------------------------- |
| `GET  /api/summary`          | Income, expense, and balance totals |
| `GET  /api/transactions`     | List your transactions (JSON)       |
| `POST /api/transactions`     | Create a transaction (JSON body)    |
| `DELETE /api/transactions/<id>` | Delete a transaction             |
| `GET  /api/prices?ids=bitcoin,ethereum` | Live market prices       |

Example:

```bash
curl -X POST http://localhost:5060/api/transactions \
  -H "Content-Type: application/json" \
  -d '{"type":"expense","amount":12.50,"category":"Food","note":"lunch"}'
```

## Using PostgreSQL

The app uses SQLite by default. To run on PostgreSQL, just set `DATABASE_URL`
(the schema is created automatically on first run):

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/finance"
export SECRET_KEY="a-long-random-string"
python3 app.py
```

The `psycopg2-binary` driver is already in `requirements.txt`.

## Tech stack

Flask · Flask-SQLAlchemy · Flask-Login · SQLAlchemy · Matplotlib ·
PostgreSQL / SQLite · CoinGecko REST API · Jinja2 · vanilla CSS

## Notes

- Passwords are stored hashed; never in plain text.
- Set a strong `SECRET_KEY` in production.
- The crypto portfolio is for tracking only — no real funds are involved.
