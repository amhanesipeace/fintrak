"""Reusable query helpers shared by the API and web views."""
from datetime import date

from sqlalchemy import func

from extensions import db
from models import Budget, Transaction

# A category this close to its limit (as a fraction) is flagged as a warning.
WARNING_THRESHOLD = 0.8


def month_bounds(today=None):
    """Return (first_of_this_month, first_of_next_month) as date objects."""
    today = today or date.today()
    start = today.replace(day=1)
    if start.month == 12:
        nxt = start.replace(year=start.year + 1, month=1)
    else:
        nxt = start.replace(month=start.month + 1)
    return start, nxt


def current_month_spending(user_id):
    """Return {category: total_expense} for the current calendar month."""
    start, nxt = month_bounds()
    rows = (db.session.query(Transaction.category,
                             func.coalesce(func.sum(Transaction.amount), 0.0))
            .filter(Transaction.user_id == user_id,
                    Transaction.type == "expense",
                    Transaction.date >= start, Transaction.date < nxt)
            .group_by(Transaction.category)
            .all())
    return {category: float(total) for category, total in rows}


def budget_alerts(user_id):
    """Categories at or near their monthly budget, worst first.

    Returns a list of dicts for every budgeted category whose spending this
    month has reached the warning threshold (80%). Each entry carries the limit,
    the amount spent, the percentage used (capped at 100 for the bar), how much
    is left, and a status of ``"over"`` (>= 100%) or ``"warning"`` (80-99%).
    Categories comfortably under budget are omitted so the dashboard only shows
    what needs attention.
    """
    spending = current_month_spending(user_id)
    alerts = []
    for b in Budget.query.filter_by(user_id=user_id).all():
        spent = spending.get(b.category, 0.0)
        if not b.amount or spent < b.amount * WARNING_THRESHOLD:
            continue
        ratio = spent / b.amount
        alerts.append({
            "category": b.category,
            "limit": b.amount,
            "spent": round(spent, 2),
            "remaining": round(b.amount - spent, 2),
            "percent": min(100, round(100 * ratio)),
            "status": "over" if spent >= b.amount else "warning",
        })
    alerts.sort(key=lambda a: a["spent"] / a["limit"], reverse=True)
    return alerts
