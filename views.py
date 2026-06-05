"""Main app pages: dashboard, transactions, portfolio, chart images."""
from datetime import date, datetime

from flask import (Blueprint, render_template, redirect, url_for, request,
                   flash, Response)
from flask_login import login_required, current_user
from sqlalchemy import func

import charts
import market
from extensions import db
from models import Transaction, Holding

main = Blueprint("main", __name__)

CATEGORIES = ["Salary", "Freelance", "Food", "Rent", "Transport", "Utilities",
              "Entertainment", "Shopping", "Health", "Savings", "Other"]


def _sum(user_id, t_type):
    return float(db.session.query(func.coalesce(func.sum(Transaction.amount), 0.0))
                 .filter_by(user_id=user_id, type=t_type).scalar())


@main.route("/")
def index():
    return redirect(url_for("main.dashboard"))


@main.route("/dashboard")
@login_required
def dashboard():
    uid = current_user.id
    income = _sum(uid, "income")
    expense = _sum(uid, "expense")
    recent = (Transaction.query.filter_by(user_id=uid)
              .order_by(Transaction.date.desc(), Transaction.id.desc())
              .limit(8).all())
    return render_template("dashboard.html", income=income, expense=expense,
                           balance=income - expense, recent=recent)


@main.route("/transactions")
@login_required
def transactions():
    txns = (Transaction.query.filter_by(user_id=current_user.id)
            .order_by(Transaction.date.desc(), Transaction.id.desc()).all())
    return render_template("transactions.html", txns=txns, categories=CATEGORIES,
                           today=date.today().isoformat())


@main.route("/transactions/add", methods=["POST"])
@login_required
def add_transaction():
    try:
        t_type = request.form.get("type")
        amount = float(request.form.get("amount", ""))
        category = request.form.get("category") or "Other"
        note = request.form.get("note", "").strip()
        d_raw = request.form.get("date") or date.today().isoformat()
        d = datetime.strptime(d_raw, "%Y-%m-%d").date()
        if t_type not in ("income", "expense") or amount <= 0:
            raise ValueError("bad input")
        db.session.add(Transaction(user_id=current_user.id, type=t_type,
                                   amount=round(amount, 2), category=category,
                                   note=note, date=d))
        db.session.commit()
        flash("Transaction added.", "success")
    except Exception:
        flash("Please enter a valid amount, type and date.", "error")
    return redirect(url_for("main.transactions"))


@main.route("/transactions/<int:tid>/delete", methods=["POST"])
@login_required
def delete_transaction(tid):
    txn = Transaction.query.filter_by(id=tid, user_id=current_user.id).first_or_404()
    db.session.delete(txn)
    db.session.commit()
    flash("Transaction deleted.", "success")
    return redirect(url_for("main.transactions"))


@main.route("/portfolio")
@login_required
def portfolio():
    holdings = Holding.query.filter_by(user_id=current_user.id).all()
    prices = market.get_prices([h.coin_id for h in holdings]) if holdings else {}
    rows, total = [], 0.0
    for h in holdings:
        price = prices.get(h.coin_id) or 0.0
        value = price * h.quantity
        total += value
        rows.append({"h": h, "price": price, "value": value})
    rows.sort(key=lambda r: r["value"], reverse=True)
    return render_template("portfolio.html", rows=rows, total=total,
                           coins=market.COINS)


@main.route("/portfolio/add", methods=["POST"])
@login_required
def add_holding():
    coin_id = request.form.get("coin_id")
    coin = market.COIN_BY_ID.get(coin_id)
    try:
        qty = float(request.form.get("quantity", ""))
        if not coin or qty <= 0:
            raise ValueError("bad input")
        existing = Holding.query.filter_by(user_id=current_user.id,
                                           coin_id=coin_id).first()
        if existing:
            existing.quantity += qty
        else:
            db.session.add(Holding(user_id=current_user.id, coin_id=coin_id,
                                   symbol=coin["symbol"], name=coin["name"],
                                   quantity=qty))
        db.session.commit()
        flash(f"Added {qty:g} {coin['symbol']}.", "success")
    except Exception:
        flash("Please choose a coin and enter a valid quantity.", "error")
    return redirect(url_for("main.portfolio"))


@main.route("/portfolio/<int:hid>/delete", methods=["POST"])
@login_required
def delete_holding(hid):
    h = Holding.query.filter_by(id=hid, user_id=current_user.id).first_or_404()
    db.session.delete(h)
    db.session.commit()
    flash("Holding removed.", "success")
    return redirect(url_for("main.portfolio"))


@main.route("/charts/spending.png")
@login_required
def chart_spending():
    return Response(charts.spending_by_category_png(current_user.id),
                    mimetype="image/png")


@main.route("/charts/trend.png")
@login_required
def chart_trend():
    return Response(charts.income_expense_trend_png(current_user.id),
                    mimetype="image/png")
