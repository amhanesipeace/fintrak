"""Server-side data visualisation with Matplotlib (rendered to PNG bytes).

Uses Matplotlib's object-oriented Figure API (not pyplot) so it is safe to
call from Flask's threaded request handlers.
"""
import io
from datetime import date

import matplotlib
matplotlib.use("Agg")  # headless backend
from matplotlib.figure import Figure

from sqlalchemy import func

from extensions import db
from models import Transaction

PANEL = "#171a2b"
TEXT = "#e8eaf2"
MUTED = "#8b90b0"
GRID = "#2a2f4a"
GREEN = "#00e0a4"
RED = "#ff5b7f"
PALETTE = ["#00e0a4", "#5b8cff", "#ff5b7f", "#ffb454", "#a06bff",
           "#3ad1ff", "#ff8a5b", "#7af0c0", "#c98bff", "#ffd166"]


def _png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor(),
                bbox_inches="tight")
    buf.seek(0)
    return buf.getvalue()


def _empty(fig, msg):
    ax = fig.add_subplot(111)
    ax.text(0.5, 0.5, msg, ha="center", va="center", color=MUTED, fontsize=12)
    ax.axis("off")
    return _png(fig)


def spending_by_category_png(user_id):
    fig = Figure(figsize=(5.2, 3.8), dpi=110)
    fig.patch.set_facecolor(PANEL)

    rows = (db.session.query(Transaction.category, func.sum(Transaction.amount))
            .filter_by(user_id=user_id, type="expense")
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
            .all())
    if not rows:
        return _empty(fig, "No expenses yet")

    labels = [r[0] for r in rows]
    values = [float(r[1]) for r in rows]

    ax = fig.add_subplot(111)
    wedges, _, autotexts = ax.pie(
        values, colors=PALETTE[:len(values)], startangle=90,
        autopct=lambda p: f"{p:.0f}%", pctdistance=0.78,
        wedgeprops=dict(width=0.42, edgecolor=PANEL),
    )
    for t in autotexts:
        t.set_color(TEXT)
        t.set_fontsize(8.5)
    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.0, 0.5),
              frameon=False, labelcolor=TEXT, fontsize=9)
    ax.set_title("Spending by category", color=TEXT, fontsize=12, pad=10)
    return _png(fig)


def _last_months(n=6):
    today = date.today()
    y, m, out = today.year, today.month, []
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(out))


def income_expense_trend_png(user_id):
    fig = Figure(figsize=(5.6, 3.8), dpi=110)
    fig.patch.set_facecolor(PANEL)

    months = _last_months(6)
    start = date(months[0][0], months[0][1], 1)
    txns = (Transaction.query
            .filter(Transaction.user_id == user_id, Transaction.date >= start)
            .all())
    if not txns:
        return _empty(fig, "No data for the last 6 months")

    income = {ym: 0.0 for ym in months}
    expense = {ym: 0.0 for ym in months}
    for t in txns:
        ym = (t.date.year, t.date.month)
        if ym in income:
            if t.type == "income":
                income[ym] += t.amount
            else:
                expense[ym] += t.amount

    labels = [date(y, m, 1).strftime("%b") for (y, m) in months]
    inc_vals = [income[ym] for ym in months]
    exp_vals = [expense[ym] for ym in months]

    ax = fig.add_subplot(111)
    ax.set_facecolor(PANEL)
    x = range(len(months))
    w = 0.4
    ax.bar([i - w / 2 for i in x], inc_vals, width=w, label="Income", color=GREEN)
    ax.bar([i + w / 2 for i in x], exp_vals, width=w, label="Expense", color=RED)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, color=MUTED, fontsize=9)
    ax.tick_params(axis="y", colors=MUTED, labelsize=8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRID)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6, alpha=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, labelcolor=TEXT, fontsize=9, loc="upper left")
    ax.set_title("Income vs expenses (last 6 months)", color=TEXT, fontsize=12, pad=10)
    return _png(fig)
