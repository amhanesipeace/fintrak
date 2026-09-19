"""Reusable query helpers shared by the API and web views."""
from datetime import date

from sqlalchemy import func

from extensions import db
from models import Transaction


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
