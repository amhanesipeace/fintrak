"""Main app pages: dashboard, transactions, portfolio, chart images."""
from datetime import date, datetime

from flask import (Blueprint, render_template, redirect, url_for, request,
                   flash, Response)
from flask_login import login_required, current_user
from sqlalchemy import func

import charts
import market
from extensions import db
from models import Transaction, Holding, Budget, SavingsGoal, RecurringTransaction
from queries import budget_alerts, current_month_spending
from recurring import process_due_recurring

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
                           balance=income - expense, recent=recent,
                           alerts=budget_alerts(uid))


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


@main.route("/transactions/<int:tid>/edit", methods=["GET", "POST"])
@login_required
def edit_transaction(tid):
    txn = Transaction.query.filter_by(id=tid, user_id=current_user.id).first_or_404()
    if request.method == "POST":
        try:
            t_type = request.form.get("type")
            amount = float(request.form.get("amount", ""))
            category = request.form.get("category") or "Other"
            note = request.form.get("note", "").strip()
            d_raw = request.form.get("date") or date.today().isoformat()
            d = datetime.strptime(d_raw, "%Y-%m-%d").date()
            if t_type not in ("income", "expense") or amount <= 0:
                raise ValueError("bad input")
            txn.type = t_type
            txn.amount = round(amount, 2)
            txn.category = category
            txn.note = note
            txn.date = d
            db.session.commit()
            flash("Transaction updated.", "success")
            return redirect(url_for("main.transactions"))
        except Exception:
            flash("Please enter a valid amount, type and date.", "error")
    return render_template("edit_transaction.html", txn=txn, categories=CATEGORIES)


@main.route("/portfolio")
@login_required
def portfolio():
    holdings = Holding.query.filter_by(user_id=current_user.id).all()
    prices = market.get_quotes([h.symbol for h in holdings]) if holdings else {}
    rows, total = [], 0.0
    for h in holdings:
        price = prices.get(h.symbol) or 0.0
        value = price * h.quantity
        total += value
        rows.append({"h": h, "price": price, "value": value})
    rows.sort(key=lambda r: r["value"], reverse=True)
    return render_template("portfolio.html", rows=rows, total=total,
                           stocks=market.STOCKS)


@main.route("/portfolio/add", methods=["POST"])
@login_required
def add_holding():
    symbol = (request.form.get("symbol") or "").upper().strip()
    try:
        qty = float(request.form.get("quantity", ""))
        if not symbol or qty <= 0:
            raise ValueError("bad input")
        existing = Holding.query.filter_by(user_id=current_user.id,
                                           symbol=symbol).first()
        if existing:
            existing.quantity += qty
        else:
            db.session.add(Holding(user_id=current_user.id, symbol=symbol,
                                   name=market.lookup_name(symbol), quantity=qty))
        db.session.commit()
        flash(f"Added {qty:g} {symbol}.", "success")
    except Exception:
        flash("Please choose a stock and enter a valid quantity.", "error")
    return redirect(url_for("main.portfolio"))


@main.route("/portfolio/<int:hid>/delete", methods=["POST"])
@login_required
def delete_holding(hid):
    h = Holding.query.filter_by(id=hid, user_id=current_user.id).first_or_404()
    db.session.delete(h)
    db.session.commit()
    flash("Holding removed.", "success")
    return redirect(url_for("main.portfolio"))


@main.route("/budgets")
@login_required
def budgets():
    spending = current_month_spending(current_user.id)
    rows = []
    for b in (Budget.query.filter_by(user_id=current_user.id)
              .order_by(Budget.category).all()):
        spent = spending.get(b.category, 0.0)
        rows.append({
            "b": b,
            "spent": spent,
            "remaining": b.amount - spent,
            "percent": min(100, round(100 * spent / b.amount)) if b.amount else 0,
            "over": spent > b.amount,
        })
    return render_template("budgets.html", rows=rows, categories=CATEGORIES)


@main.route("/budgets/add", methods=["POST"])
@login_required
def add_budget():
    category = request.form.get("category") or "Other"
    try:
        amount = float(request.form.get("amount", ""))
        if amount <= 0:
            raise ValueError("bad input")
        # Web convenience: setting a budget for an existing category updates it.
        existing = Budget.query.filter_by(user_id=current_user.id,
                                          category=category).first()
        if existing:
            existing.amount = round(amount, 2)
        else:
            db.session.add(Budget(user_id=current_user.id, category=category,
                                  amount=round(amount, 2)))
        db.session.commit()
        flash("Budget saved.", "success")
    except Exception:
        flash("Please enter a valid amount.", "error")
    return redirect(url_for("main.budgets"))


@main.route("/budgets/<int:bid>/delete", methods=["POST"])
@login_required
def delete_budget(bid):
    b = Budget.query.filter_by(id=bid, user_id=current_user.id).first_or_404()
    db.session.delete(b)
    db.session.commit()
    flash("Budget removed.", "success")
    return redirect(url_for("main.budgets"))


@main.route("/goals")
@login_required
def goals():
    rows = [g.to_dict() for g in (SavingsGoal.query
            .filter_by(user_id=current_user.id)
            .order_by(SavingsGoal.name).all())]
    return render_template("goals.html", rows=rows)


@main.route("/goals/add", methods=["POST"])
@login_required
def add_goal():
    name = (request.form.get("name") or "").strip()
    try:
        if not name:
            raise ValueError("name required")
        target = float(request.form.get("target_amount", ""))
        if target <= 0:
            raise ValueError("bad target")
        current = float(request.form.get("current_amount") or 0)
        if current < 0:
            raise ValueError("bad current")
        target_date = None
        raw_date = (request.form.get("target_date") or "").strip()
        if raw_date:
            target_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
        # Web convenience: re-saving an existing goal name updates its target.
        existing = SavingsGoal.query.filter_by(user_id=current_user.id,
                                               name=name).first()
        if existing:
            existing.target_amount = round(target, 2)
            existing.target_date = target_date
        else:
            db.session.add(SavingsGoal(
                user_id=current_user.id, name=name,
                target_amount=round(target, 2),
                current_amount=round(current, 2), target_date=target_date))
        db.session.commit()
        flash("Goal saved.", "success")
    except Exception:
        flash("Please enter a name and a valid target amount.", "error")
    return redirect(url_for("main.goals"))


@main.route("/goals/<int:gid>/contribute", methods=["POST"])
@login_required
def contribute_goal(gid):
    g = SavingsGoal.query.filter_by(id=gid, user_id=current_user.id).first_or_404()
    try:
        amount = float(request.form.get("amount", ""))
        if amount == 0:
            raise ValueError("no amount")
        g.current_amount = round(max(g.current_amount + amount, 0.0), 2)
        db.session.commit()
        flash("Contribution recorded." if amount > 0 else "Goal adjusted.",
              "success")
    except Exception:
        flash("Please enter a valid amount.", "error")
    return redirect(url_for("main.goals"))


@main.route("/goals/<int:gid>/delete", methods=["POST"])
@login_required
def delete_goal(gid):
    g = SavingsGoal.query.filter_by(id=gid, user_id=current_user.id).first_or_404()
    db.session.delete(g)
    db.session.commit()
    flash("Goal removed.", "success")
    return redirect(url_for("main.goals"))


@main.route("/recurring")
@login_required
def recurring():
    rows = [r.to_dict() for r in (RecurringTransaction.query
            .filter_by(user_id=current_user.id)
            .order_by(RecurringTransaction.next_date).all())]
    return render_template("recurring.html", rows=rows, categories=CATEGORIES,
                           frequencies=RecurringTransaction.FREQUENCIES,
                           today=date.today().isoformat())


@main.route("/recurring/add", methods=["POST"])
@login_required
def add_recurring():
    try:
        t_type = request.form.get("type")
        amount = float(request.form.get("amount", ""))
        category = request.form.get("category") or "Other"
        note = request.form.get("note", "").strip() or None
        frequency = request.form.get("frequency")
        d_raw = request.form.get("start_date") or date.today().isoformat()
        next_date = datetime.strptime(d_raw, "%Y-%m-%d").date()
        if (t_type not in ("income", "expense") or amount <= 0
                or frequency not in RecurringTransaction.FREQUENCIES):
            raise ValueError("bad input")
        db.session.add(RecurringTransaction(
            user_id=current_user.id, type=t_type, amount=round(amount, 2),
            category=category, note=note, frequency=frequency,
            next_date=next_date))
        db.session.commit()
        flash("Recurring rule added.", "success")
    except Exception:
        flash("Please enter a valid amount, type and frequency.", "error")
    return redirect(url_for("main.recurring"))


@main.route("/recurring/<int:rid>/toggle", methods=["POST"])
@login_required
def toggle_recurring(rid):
    rule = RecurringTransaction.query.filter_by(
        id=rid, user_id=current_user.id).first_or_404()
    rule.active = not rule.active
    db.session.commit()
    flash("Rule resumed." if rule.active else "Rule paused.", "success")
    return redirect(url_for("main.recurring"))


@main.route("/recurring/<int:rid>/delete", methods=["POST"])
@login_required
def delete_recurring(rid):
    rule = RecurringTransaction.query.filter_by(
        id=rid, user_id=current_user.id).first_or_404()
    db.session.delete(rule)
    db.session.commit()
    flash("Recurring rule removed.", "success")
    return redirect(url_for("main.recurring"))


@main.route("/recurring/run", methods=["POST"])
@login_required
def run_recurring_web():
    created = process_due_recurring(user_id=current_user.id)
    if created:
        flash(f"Posted {created} due transaction{'s' if created != 1 else ''}.",
              "success")
    else:
        flash("Nothing due right now.", "success")
    return redirect(url_for("main.recurring"))


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
