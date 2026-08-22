"""RESTful JSON API.

Auth (JWT):
    POST /api/auth/register   -> create account, returns tokens
    POST /api/auth/login      -> returns access + refresh tokens
    POST /api/auth/refresh    -> new access token (send refresh token)
    GET  /api/me              -> current user

Data (JWT bearer token OR session cookie):
    GET/POST     /api/transactions
    DELETE       /api/transactions/<id>
    GET          /api/summary
    GET          /api/quotes?symbols=AAPL,MSFT
    GET          /api/portfolio
"""
from datetime import date, datetime

from flask import Blueprint, jsonify, request, g
from flask_jwt_extended import (create_access_token, create_refresh_token,
                                jwt_required, get_jwt_identity)
from sqlalchemy import func

import market
from extensions import db
from models import Transaction, Holding, User
from security import auth_required

api = Blueprint("api", __name__, url_prefix="/api")


# --------------------------------------------------------------------------- #
#  Auth
# --------------------------------------------------------------------------- #
def _tokens(user):
    identity = str(user.id)
    return {
        "access_token": create_access_token(identity=identity),
        "refresh_token": create_refresh_token(identity=identity),
        "user": {"id": user.id, "username": user.username, "email": user.email},
    }


@api.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip() or None
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "password must be at least 6 characters"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "username already taken"}), 409
    if email and User.query.filter_by(email=email).first():
        return jsonify({"error": "email already registered"}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify(_tokens(user)), 201


@api.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    user = User.query.filter_by(username=(data.get("username") or "").strip()).first()
    if not user or not user.check_password(data.get("password") or ""):
        return jsonify({"error": "invalid username or password"}), 401
    return jsonify(_tokens(user))


@api.route("/auth/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    return jsonify({"access_token": create_access_token(identity=get_jwt_identity())})


@api.route("/me")
@auth_required
def me():
    user = db.session.get(User, g.user_id)
    return jsonify({"id": user.id, "username": user.username, "email": user.email})


# --------------------------------------------------------------------------- #
#  Data
# --------------------------------------------------------------------------- #
def _sum(user_id, t_type):
    return float(db.session.query(func.coalesce(func.sum(Transaction.amount), 0.0))
                 .filter_by(user_id=user_id, type=t_type).scalar())


@api.route("/summary")
@auth_required
def summary():
    income = _sum(g.user_id, "income")
    expense = _sum(g.user_id, "expense")
    return jsonify({"income": income, "expense": expense,
                    "balance": income - expense})


@api.route("/transactions", methods=["GET", "POST"])
@auth_required
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
            txn = Transaction(user_id=g.user_id, type=t_type,
                              amount=round(amount, 2),
                              category=data.get("category", "Other"),
                              note=data.get("note", ""), date=d)
            db.session.add(txn)
            db.session.commit()
            return jsonify(txn.to_dict()), 201
        except (KeyError, ValueError, TypeError):
            return jsonify({"error": "invalid payload"}), 400

    txns = (Transaction.query.filter_by(user_id=g.user_id)
            .order_by(Transaction.date.desc(), Transaction.id.desc()).all())
    return jsonify([t.to_dict() for t in txns])


@api.route("/transactions/<int:tid>", methods=["DELETE"])
@auth_required
def delete_transaction(tid):
    txn = Transaction.query.filter_by(id=tid, user_id=g.user_id).first()
    if not txn:
        return jsonify({"error": "not found"}), 404
    db.session.delete(txn)
    db.session.commit()
    return jsonify({"deleted": tid})


@api.route("/quotes")
@auth_required
def quotes():
    raw = request.args.get("symbols", "")
    symbols = [s.strip() for s in raw.split(",") if s.strip()] \
        or [s["symbol"] for s in market.STOCKS]
    return jsonify(market.get_quotes(symbols))


@api.route("/portfolio")
@auth_required
def portfolio():
    holdings = Holding.query.filter_by(user_id=g.user_id).all()
    prices = market.get_quotes([h.symbol for h in holdings]) if holdings else {}
    rows, total = [], 0.0
    for h in holdings:
        price = prices.get(h.symbol) or 0.0
        value = price * h.quantity
        total += value
        rows.append({**h.to_dict(), "price": price, "value": round(value, 2)})
    rows.sort(key=lambda r: r["value"], reverse=True)
    return jsonify({"total": round(total, 2), "holdings": rows})
