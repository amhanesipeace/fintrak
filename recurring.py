"""Materialise recurring-transaction rules into real transactions.

Kept free of Flask/Celery imports so the scheduling logic stays unit-testable in
isolation. ``process_due_recurring`` is driven by ``tasks.process_recurring``
(Celery beat, daily) and by the ``POST /api/recurring/run`` endpoint.
"""
from calendar import monthrange
from datetime import date, timedelta

from extensions import db
from models import RecurringTransaction, Transaction


def advance_date(d, frequency):
    """Return the next occurrence strictly after ``d`` for a cadence.

    Monthly cadence clamps to the last valid day of the target month, so a rule
    anchored on the 31st lands on the 28th/30th in shorter months instead of
    overflowing into the next one.
    """
    if frequency == "daily":
        return d + timedelta(days=1)
    if frequency == "weekly":
        return d + timedelta(weeks=1)
    if frequency == "monthly":
        year = d.year + (1 if d.month == 12 else 0)
        month = d.month % 12 + 1
        day = min(d.day, monthrange(year, month)[1])
        return date(year, month, day)
    raise ValueError(f"unknown frequency: {frequency!r}")


def process_due_recurring(today=None, user_id=None, max_catch_up=366):
    """Create transactions for every rule whose ``next_date`` has arrived.

    Advances each active rule past ``today``, emitting one Transaction per due
    occurrence — including any missed while the worker was down. ``max_catch_up``
    bounds the back-fill per rule so a long-dormant rule can't spawn thousands of
    rows in one pass. Returns the number of transactions created.
    """
    today = today or date.today()
    query = RecurringTransaction.query.filter(
        RecurringTransaction.active.is_(True),
        RecurringTransaction.next_date <= today,
    )
    if user_id is not None:
        query = query.filter_by(user_id=user_id)

    created = 0
    for rule in query.all():
        occurrences = 0
        while rule.next_date <= today and occurrences < max_catch_up:
            db.session.add(Transaction(
                user_id=rule.user_id,
                type=rule.type,
                amount=rule.amount,
                category=rule.category,
                note=rule.note,
                date=rule.next_date,
            ))
            rule.next_date = advance_date(rule.next_date, rule.frequency)
            occurrences += 1
            created += 1
    db.session.commit()
    return created
