"""Celery tasks — run market-data work off the request path.

`refresh_quotes` is scheduled by Celery beat to pre-warm the Redis quote cache
for every symbol any user holds, so portfolio pages render from cache.
"""
from sqlalchemy import distinct

import market
from celery_app import celery
from extensions import db
from models import Holding

# A dedicated Flask app instance gives tasks an application context for the ORM.
from app import create_app

flask_app = create_app()


@celery.task(name="tasks.refresh_quotes")
def refresh_quotes():
    """Fetch and cache the latest quote for every held symbol."""
    with flask_app.app_context():
        symbols = [row[0] for row in
                   db.session.query(distinct(Holding.symbol)).all()]

    refreshed = {}
    for symbol in symbols:
        # get_quote writes fresh values into the Redis cache as a side effect.
        refreshed[symbol] = market.get_quote(symbol)
    return refreshed


@celery.task(name="tasks.refresh_symbol")
def refresh_symbol(symbol):
    """Refresh a single symbol on demand (e.g. right after it's added)."""
    return {symbol: market.get_quote(symbol)}
