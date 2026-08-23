"""Create a demo account with sample data:  python3 seed.py

Login afterwards with  demo / demo123
"""
import random
from datetime import date, timedelta

from app import create_app
from extensions import db
from models import User, Transaction, Holding

app = create_app()

INCOME = [("Salary", 3200), ("Freelance", 450)]
EXPENSES = [
    ("Rent", 1200), ("Food", 60), ("Transport", 25), ("Utilities", 90),
    ("Entertainment", 40), ("Shopping", 75), ("Health", 50),
]


def run():
    with app.app_context():
        if User.query.filter_by(username="demo").first():
            print("Demo user already exists. Login: demo / demo123")
            return

        user = User(username="demo", email="demo@example.com")
        user.set_password("demo123")
        db.session.add(user)
        db.session.commit()

        today = date.today()
        for month_back in range(6):
            base = today.replace(day=1) - timedelta(days=month_back * 30)
            for cat, amt in INCOME:
                db.session.add(Transaction(user_id=user.id, type="income",
                    amount=amt, category=cat, note="", date=base))
            for _ in range(random.randint(8, 14)):
                cat, typical = random.choice(EXPENSES)
                d = base + timedelta(days=random.randint(0, 27))
                if d > today:
                    d = today
                amt = round(typical * random.uniform(0.6, 1.5), 2)
                db.session.add(Transaction(user_id=user.id, type="expense",
                    amount=amt, category=cat, note="", date=d))

        db.session.add(Holding(user_id=user.id, symbol="AAPL",
            name="Apple Inc.", quantity=10))
        db.session.add(Holding(user_id=user.id, symbol="MSFT",
            name="Microsoft Corporation", quantity=5))
        db.session.add(Holding(user_id=user.id, symbol="SPY",
            name="SPDR S&P 500 ETF Trust", quantity=3))
        db.session.commit()
        print("Seeded demo data. Login: demo / demo123")


if __name__ == "__main__":
    run()
