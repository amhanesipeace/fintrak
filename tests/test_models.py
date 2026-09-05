"""Model tests: password hashing, timestamps, and uniqueness constraints."""
import pytest
from sqlalchemy.exc import IntegrityError


def _make_user(db, username="u1", email=None, password="secret1"):
    from models import User
    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def test_password_is_bcrypt_hashed(db_session):
    from models import User
    user = User(username="hashme")
    user.set_password("secret1")
    assert user.password_hash != "secret1"          # never stored in plain text
    assert user.password_hash.startswith("$2b$")     # bcrypt hash marker
    assert user.check_password("secret1")
    assert not user.check_password("wrong")


def test_utcnow_helper_is_timezone_aware():
    from models import utcnow
    assert utcnow().tzinfo is not None


def test_created_at_is_set_on_insert(db_session):
    user = _make_user(db_session)
    assert user.created_at is not None


def test_duplicate_username_rejected(db_session):
    _make_user(db_session, username="dup")
    with pytest.raises(IntegrityError):
        _make_user(db_session, username="dup")
    db_session.session.rollback()


def test_duplicate_holding_symbol_rejected(db_session):
    from models import Holding
    user = _make_user(db_session)
    db_session.session.add(
        Holding(user_id=user.id, symbol="AAPL", name="Apple", quantity=1))
    db_session.session.commit()
    # Same (user, symbol) violates the uq_holding_user_symbol constraint.
    db_session.session.add(
        Holding(user_id=user.id, symbol="AAPL", name="Apple", quantity=2))
    with pytest.raises(IntegrityError):
        db_session.session.commit()
    db_session.session.rollback()
