"""Celery application: async task queue backed by Redis.

Run the worker:   celery -A celery_app.celery worker --loglevel=info
Run the beat:     celery -A celery_app.celery beat  --loglevel=info
(Both are wired up as separate services in docker-compose.yml.)
"""
import os

from celery import Celery

_broker = os.environ.get(
    "CELERY_BROKER_URL", os.environ.get("REDIS_URL", "redis://localhost:6379/0")
)
_backend = os.environ.get("CELERY_RESULT_BACKEND", _broker)

celery = Celery("fintrak", broker=_broker, backend=_backend, include=["tasks"])

celery.conf.update(
    timezone="UTC",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Periodically warm the quote cache so page loads stay fast.
    beat_schedule={
        "refresh-quotes": {
            "task": "tasks.refresh_quotes",
            "schedule": float(os.environ.get("QUOTE_REFRESH_SECONDS", 300)),
        },
    },
)
