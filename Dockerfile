# FinTrak image — used by the web, worker and beat services.
FROM python:3.12-slim

# Faster, cleaner Python in containers.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# curl is used by the compose healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Run as a non-root user.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Default command runs the web server; worker/beat override this in compose.
# Shell form so $PORT (set by Render/other PaaS) and $WEB_CONCURRENCY expand;
# both fall back to sensible local defaults. `exec` replaces the shell with
# gunicorn so it receives SIGTERM directly for graceful shutdown.
CMD exec gunicorn --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --timeout 60 app:app
