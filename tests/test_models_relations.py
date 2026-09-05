"""Model tests: relationship cascades and dict serialization."""
from datetime import date


def _make_user(db, username="rel"):
    from models import User
    user = User(username=username)
    user.set_password("secret1")
    db.session.add(user)
    db.session.commit()
    return user


def test_deleting_user_cascades_to_children(db_session):
    from models import Transaction, Holding
    user = _make_user(db_session)
    db_session.session.add(Transaction(
        user_id=user.id, type="expense", amount=10, category="Food",
        date=date.today()))
    db_session.session.add(Holding(
        user_id=user.id, symbol="AAPL", name="Apple", quantity=1))
    db_session.session.commit()
    assert Transaction.query.count() == 1
    assert Holding.query.count() == 1

    db_session.session.delete(user)
    db_session.session.commit()
    # cascade="all, delete-orphan" should remove the user's rows too.
    assert Transaction.query.count() == 0
    assert Holding.query.count() == 0


def test_transaction_to_dict(db_session):
    from models import Transaction
    user = _make_user(db_session)
    txn = Transaction(user_id=user.id, type="income", amount=100.0,
                      category="Salary", note="pay", date=date(2026, 1, 15))
    db_session.session.add(txn)
    db_session.session.commit()
    assert txn.to_dict() == {
        "id": txn.id, "type": "income", "amount": 100.0,
        "category": "Salary", "note": "pay", "date": "2026-01-15",
    }


def test_holding_to_dict(db_session):
    from models import Holding
    user = _make_user(db_session)
    holding = Holding(user_id=user.id, symbol="MSFT",
                      name="Microsoft", quantity=3)
    db_session.session.add(holding)
    db_session.session.commit()
    assert holding.to_dict() == {
        "id": holding.id, "symbol": "MSFT",
        "name": "Microsoft", "quantity": 3,
    }
