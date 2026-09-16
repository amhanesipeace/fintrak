"""Performance benchmark for FinTrak.

Produces the numbers behind two resume claims, measured — not guessed:
  1) hot-path DATABASE QUERY latency  (the "sub-100ms query" claim)
  2) API RESPONSE latency, incl. the Redis-cached portfolio (the "responsive
     under load / ~2s" claim)

Run it against the production-like stack (PostgreSQL + Redis) so pooling and
indexing are actually exercised:

    DATABASE_URL=postgresql://fintrak:fintrak@localhost:5432/fintrak \
    REDIS_URL=redis://localhost:6379/0 \
    python benchmark.py --transactions 5000 --iterations 200

Methodology notes (state these honestly in an interview):
  - Query timings measure server-side ORM query execution against PostgreSQL.
  - API timings use Flask's test client, i.e. server-side processing time
    (excludes network + gunicorn overhead).
  - We report median and p95 over many iterations (not a single lucky run).
"""
import argparse
import random
import statistics
import time
from datetime import date, timedelta

from sqlalchemy import func

from app import create_app
from extensions import db
from models import User, Transaction, Holding

BENCH_USER = "bench"
BENCH_PASS = "benchpass123"


def percentile(values, p):
    values = sorted(values)
    k = (len(values) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(values) - 1)
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def timeit(label, fn, iterations):
    samples = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)  # ms
    return {
        "label": label,
        "n": iterations,
        "median": statistics.median(samples),
        "p95": percentile(samples, 0.95),
    }


def seed_bench_data(n_txns):
    """Create a 'bench' user with n_txns transactions + a few holdings."""
    user = User.query.filter_by(username=BENCH_USER).first()
    if user is None:
        user = User(username=BENCH_USER)
        user.set_password(BENCH_PASS)
        db.session.add(user)
        db.session.commit()

    have = Transaction.query.filter_by(user_id=user.id).count()
    to_add = max(0, n_txns - have)
    if to_add:
        today = date.today()
        cats = ["Food", "Rent", "Transport", "Salary", "Utilities",
                "Shopping", "Health", "Entertainment"]
        batch = []
        for i in range(to_add):
            batch.append(Transaction(
                user_id=user.id,
                type="income" if i % 7 == 0 else "expense",
                amount=round(random.uniform(5, 3000), 2),
                category=random.choice(cats),
                note="",
                date=today - timedelta(days=random.randint(0, 720)),
            ))
            if len(batch) >= 1000:
                db.session.bulk_save_objects(batch)
                db.session.commit()
                batch = []
        if batch:
            db.session.bulk_save_objects(batch)
            db.session.commit()

    for sym, name in [("AAPL", "Apple Inc."), ("MSFT", "Microsoft"),
                      ("SPY", "SPDR S&P 500 ETF")]:
        if not Holding.query.filter_by(user_id=user.id, symbol=sym).first():
            db.session.add(Holding(user_id=user.id, symbol=sym, name=name,
                                   quantity=random.randint(1, 20)))
    db.session.commit()
    return user


def main():
    ap = argparse.ArgumentParser(description="FinTrak performance benchmark")
    ap.add_argument("--transactions", type=int, default=5000)
    ap.add_argument("--iterations", type=int, default=200)
    args = ap.parse_args()

    app = create_app()
    backend = app.config["SQLALCHEMY_DATABASE_URI"].split(":")[0]
    print(f"Backend: {backend} | dataset: {args.transactions} transactions | "
          f"iterations: {args.iterations}\n")
    if backend.startswith("sqlite"):
        print("WARNING: SQLite is not representative. Point DATABASE_URL at "
              "PostgreSQL for meaningful pooling/index numbers.\n")

    with app.app_context():
        user = seed_bench_data(args.transactions)
        uid = user.id

        # --- 1) Database query latency -----------------------------------
        def q_summary():
            db.session.query(func.coalesce(func.sum(Transaction.amount), 0.0)) \
                .filter_by(user_id=uid, type="expense").scalar()

        def q_recent():
            Transaction.query.filter_by(user_id=uid) \
                .order_by(Transaction.date.desc(), Transaction.id.desc()) \
                .limit(8).all()

        def q_holdings():
            Holding.query.filter_by(user_id=uid).all()

        query_results = [
            timeit("SUM(expense) aggregation", q_summary, args.iterations),
            timeit("recent transactions (indexed, limit 8)", q_recent, args.iterations),
            timeit("user holdings lookup", q_holdings, args.iterations),
        ]

        # --- 2) API response latency -------------------------------------
        client = app.test_client()
        tok = client.post("/api/auth/login",
                          json={"username": BENCH_USER, "password": BENCH_PASS}
                          ).get_json()["access_token"]
        H = {"Authorization": f"Bearer {tok}"}
        # Warm the quote cache once so /api/portfolio measures the cached path.
        client.get("/api/portfolio", headers=H)

        api_iter = max(30, args.iterations // 4)
        api_results = [
            timeit("GET /api/summary", lambda: client.get("/api/summary", headers=H), api_iter),
            timeit("GET /api/portfolio (cached quotes)",
                   lambda: client.get("/api/portfolio", headers=H), api_iter),
        ]

    def render(title, rows, threshold, unit_note):
        print(f"=== {title} ===")
        print(f"{'operation':<42}{'n':>5}{'median':>10}{'p95':>10}")
        for r in rows:
            print(f"{r['label']:<42}{r['n']:>5}{r['median']:>9.2f}ms{r['p95']:>9.2f}ms")
        worst = max(r["p95"] for r in rows)
        ok = "PASS" if worst < threshold else "OVER"
        print(f"-> worst p95 {worst:.2f}ms vs target {threshold:.0f}ms  [{ok}]  {unit_note}\n")

    print()
    render("Database query latency", query_results, 100, "(backs: sub-100ms queries)")
    render("API response latency", api_results, 2000, "(backs: consistent <2s responses)")


if __name__ == "__main__":
    main()
