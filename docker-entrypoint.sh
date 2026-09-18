#!/bin/sh
# Web container entrypoint: bring the schema up to date, then serve.
set -e

# One-time adoption for databases created BEFORE migrations existed (e.g. by an
# older create_all()): if the app schema is present but Alembic has never
# stamped it, mark it at the initial revision so `flask db upgrade` won't try to
# recreate the existing tables. Idempotent and safe on fresh/already-adopted DBs.
python - <<'PY'
import os
from sqlalchemy import create_engine, inspect, text

url = os.environ.get("DATABASE_URL", "")
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)

if url and not url.startswith("sqlite"):
    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    if "users" in tables and "alembic_version" not in tables:
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE alembic_version ("
                "version_num VARCHAR(32) NOT NULL, "
                "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"))
            conn.execute(text(
                "INSERT INTO alembic_version (version_num) "
                "VALUES ('0668873b8722')"))
        print("[entrypoint] existing schema adopted -> stamped 0668873b8722")
PY

# Apply any pending migrations, then hand off to gunicorn (exec = PID 1).
flask db upgrade
exec gunicorn --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" \
     --timeout 60 app:app
