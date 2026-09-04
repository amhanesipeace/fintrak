"""SQLAlchemy models — normalised schema, indexed for PostgreSQL (and SQLite).

Passwords are hashed with bcrypt (via Flask-Bcrypt). The stock portfolio is
valued from the Alpha Vantage / Yahoo Finance quote services.
"""
from datetime import datetime, date, timezone

from flask_login import UserMixin

from extensions import db, bcrypt


def utcnow():
    """Timezone-aware UTC timestamp (replaces the deprecated datetime.utcnow)."""
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    transactions = db.relationship(
        "Transaction", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    holdings = db.relationship(
        "Holding", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password):
        # bcrypt returns bytes; store as utf-8 string.
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    type = db.Column(db.String(10), nullable=False)          # "income" | "expense"
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    note = db.Column(db.String(255))
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    # Composite index matching our hottest query: a user's history by date.
    __table_args__ = (
        db.Index("ix_txn_user_date", "user_id", "date"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "amount": self.amount,
            "category": self.category,
            "note": self.note,
            "date": self.date.isoformat(),
        }


class Holding(db.Model):
    """A quantity of a publicly traded equity, valued from live quotes."""
    __tablename__ = "holdings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    symbol = db.Column(db.String(20), nullable=False)        # e.g. "AAPL"
    name = db.Column(db.String(120))                         # e.g. "Apple Inc."
    quantity = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=utcnow)

    # One row per (user, symbol); look-ups filter on both.
    __table_args__ = (
        db.UniqueConstraint("user_id", "symbol", name="uq_holding_user_symbol"),
        db.Index("ix_holding_user_symbol", "user_id", "symbol"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "quantity": self.quantity,
        }
