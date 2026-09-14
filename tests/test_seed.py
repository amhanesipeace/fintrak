"""Tests for the demo-data seeder."""


def test_seed_demo_populates(db_session):
    from seed import seed_demo
    from models import User, Transaction, Holding

    seed_demo()
    assert User.query.filter_by(username="demo").first() is not None
    assert Transaction.query.count() > 0
    assert Holding.query.count() == 3


def test_seed_demo_is_idempotent(db_session):
    from seed import seed_demo
    from models import User

    seed_demo()
    seed_demo()   # second call should detect the existing demo user and no-op
    assert User.query.filter_by(username="demo").count() == 1
