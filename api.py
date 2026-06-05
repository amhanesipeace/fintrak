"""RESTful JSON API for transactions, summary, and live market prices."""
from datetime import date, datetime

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func

import market
from extensions import db
from models import Transaction

api = Blueprint("api", __name__, url_prefix="/api")


def _sum(user_id, t_type):
    return float(db.session.query(func.coalesce(func.sum(Transaction.amount), 0.0))
                 .filter_by(user_id=user_id, type=t_type).scalar())


@api.route("/summary")
@login_required
def summary():
    uid = current_user.id
    income = _sum(uid, "income")
    expense = _sum(uid, "expense")
    return jsonify({"income": income, "expense": expense,
                    "balance": income - expense})


@api.route("/transactions", methods=["GET", "POST"])
@login_required
def transactions():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        try:
            t_type = data["type"]
            amount = float(data["amount"])
            if t_type not in ("income", "expense") or amount <= 0:
                raise ValueError
            d = (datetime.strptime(data["date"], "%Y-%m-%d").date()
                 if data.get("date") else date.today())
            txn = Transaction(user_id=current_user.id, type=t_type,
                              amount=round(amount, 2),
                              category=data.get("category", "Other"),
                              note=data.get("note", ""), date=d)
            db.session.add(txn)
            db.session.commit()
            return jsonify(txn.to_dict()), 201
        except (KeyError, ValueError, TypeError):
            return jsonify({"error": "invalid payload"}), 400

    txns = (Transaction.query.filter_by(user_id=current_user.id)
            .order_by(Transaction.date.desc(), Transaction.id.desc()).all())
    return jsonify([t.to_dict() for t in txns])


@api.route("/transactions/<int:tid>", methods=["DELETE"])
@login_required
def delete_transaction(tid):
    txn = Transaction.query.filter_by(id=tid, user_id=current_user.id).first()
    if not txn:
        return jsonify({"error": "not found"}), 404
    db.session.delete(txn)
    db.session.commit()
    return jsonify({"deleted": tid})


@api.route("/prices")
@login_required
def prices():
    ids = request.args.get("ids", "")
    coin_ids = [c.strip() for c in ids.split(",") if c.strip()] \
        or [c["id"] for c in market.COINS]
    return jsonify(market.get_prices(coin_ids))
