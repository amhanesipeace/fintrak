"""Tests for savings goals: model, progress maths, and REST API."""
import pytest
from sqlalchemy.exc import IntegrityError


def _other_headers(client, username="other"):
    r = client.post("/api/auth/register",
                    json={"username": username, "password": "secret1"})
    return {"Authorization": f"Bearer {r.get_json()['access_token']}"}


# --- Model ------------------------------------------------------------------

def test_goal_to_dict_progress(app):
    from extensions import db
    from models import SavingsGoal, User
    with app.app_context():
        u = User(username="g1"); u.set_password("x")
        db.session.add(u); db.session.commit()
        goal = SavingsGoal(user_id=u.id, name="Laptop", target_amount=1000,
                           current_amount=250)
        db.session.add(goal); db.session.commit()
        d = goal.to_dict()
        assert d["remaining"] == 750.0
        assert d["progress_percent"] == 25.0
        assert d["reached"] is False


def test_goal_progress_caps_at_100(app):
    from extensions import db
    from models import SavingsGoal, User
    with app.app_context():
        u = User(username="g2"); u.set_password("x")
        db.session.add(u); db.session.commit()
        goal = SavingsGoal(user_id=u.id, name="Fund", target_amount=100,
                           current_amount=150)
        db.session.add(goal); db.session.commit()
        d = goal.to_dict()
        assert d["progress_percent"] == 100.0      # not 150
        assert d["remaining"] == 0.0               # not negative
        assert d["reached"] is True


def test_goal_name_unique_per_user(app):
    from extensions import db
    from models import SavingsGoal, User
    with app.app_context():
        u = User(username="g3"); u.set_password("x")
        db.session.add(u); db.session.commit()
        db.session.add(SavingsGoal(user_id=u.id, name="Car", target_amount=10))
        db.session.commit()
        db.session.add(SavingsGoal(user_id=u.id, name="Car", target_amount=20))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


# --- REST API ---------------------------------------------------------------

def test_create_goal(client, auth_headers):
    r = client.post("/api/goals", headers=auth_headers,
                    json={"name": "Emergency fund", "target_amount": 5000,
                          "target_date": "2027-01-01"})
    assert r.status_code == 201
    body = r.get_json()
    assert body["name"] == "Emergency fund"
    assert body["remaining"] == 5000.0
    assert body["target_date"] == "2027-01-01"
    assert body["reached"] is False


def test_create_goal_with_initial_amount(client, auth_headers):
    r = client.post("/api/goals", headers=auth_headers,
                    json={"name": "Trip", "target_amount": 2000,
                          "current_amount": 500})
    assert r.status_code == 201
    assert r.get_json()["progress_percent"] == 25.0


def test_create_goal_duplicate_409(client, auth_headers):
    client.post("/api/goals", headers=auth_headers,
                json={"name": "Car", "target_amount": 100})
    r = client.post("/api/goals", headers=auth_headers,
                    json={"name": "Car", "target_amount": 200})
    assert r.status_code == 409


def test_create_goal_invalid(client, auth_headers):
    assert client.post("/api/goals", headers=auth_headers,
                       json={"name": "X", "target_amount": -1}).status_code == 400
    assert client.post("/api/goals", headers=auth_headers,
                       json={"target_amount": 100}).status_code == 400   # no name
    assert client.post("/api/goals", headers=auth_headers,
                       json={"name": "Y", "target_amount": 100,
                             "current_amount": -5}).status_code == 400
    assert client.post("/api/goals", headers=auth_headers,
                       json={"name": "Z", "target_amount": 100,
                             "target_date": "nope"}).status_code == 400


def test_goals_require_auth(client):
    assert client.get("/api/goals").status_code == 401


def test_list_goals(client, auth_headers):
    client.post("/api/goals", headers=auth_headers,
                json={"name": "B", "target_amount": 10})
    client.post("/api/goals", headers=auth_headers,
                json={"name": "A", "target_amount": 20})
    data = client.get("/api/goals", headers=auth_headers).get_json()
    assert [g["name"] for g in data] == ["A", "B"]           # ordered by name


def test_update_goal(client, auth_headers):
    gid = client.post("/api/goals", headers=auth_headers,
                      json={"name": "Old", "target_amount": 100}).get_json()["id"]
    r = client.patch(f"/api/goals/{gid}", headers=auth_headers,
                     json={"name": "New", "target_amount": 200})
    assert r.status_code == 200
    body = r.get_json()
    assert body["name"] == "New" and body["target_amount"] == 200.0


def test_update_goal_clears_target_date(client, auth_headers):
    gid = client.post("/api/goals", headers=auth_headers,
                      json={"name": "Dated", "target_amount": 100,
                            "target_date": "2027-06-01"}).get_json()["id"]
    r = client.patch(f"/api/goals/{gid}", headers=auth_headers,
                     json={"target_date": None})
    assert r.get_json()["target_date"] is None


def test_contribute_increments_and_reaches(client, auth_headers):
    gid = client.post("/api/goals", headers=auth_headers,
                      json={"name": "Phone", "target_amount": 100}).get_json()["id"]
    r = client.post(f"/api/goals/{gid}/contribute", headers=auth_headers,
                    json={"amount": 60})
    assert r.get_json()["current_amount"] == 60.0
    r = client.post(f"/api/goals/{gid}/contribute", headers=auth_headers,
                    json={"amount": 40})
    body = r.get_json()
    assert body["current_amount"] == 100.0 and body["reached"] is True


def test_contribute_withdraw_clamps_at_zero(client, auth_headers):
    gid = client.post("/api/goals", headers=auth_headers,
                      json={"name": "Jar", "target_amount": 100,
                            "current_amount": 30}).get_json()["id"]
    r = client.post(f"/api/goals/{gid}/contribute", headers=auth_headers,
                    json={"amount": -50})
    assert r.get_json()["current_amount"] == 0.0             # not -20


def test_contribute_invalid(client, auth_headers):
    gid = client.post("/api/goals", headers=auth_headers,
                      json={"name": "K", "target_amount": 100}).get_json()["id"]
    assert client.post(f"/api/goals/{gid}/contribute", headers=auth_headers,
                       json={"amount": 0}).status_code == 400
    assert client.post(f"/api/goals/{gid}/contribute", headers=auth_headers,
                       json={}).status_code == 400


def test_delete_goal(client, auth_headers):
    gid = client.post("/api/goals", headers=auth_headers,
                      json={"name": "Temp", "target_amount": 100}).get_json()["id"]
    assert client.delete(f"/api/goals/{gid}", headers=auth_headers).status_code == 200
    assert client.get("/api/goals", headers=auth_headers).get_json() == []


def test_goal_not_found_404(client, auth_headers):
    assert client.patch("/api/goals/999", headers=auth_headers,
                        json={"target_amount": 1}).status_code == 404
    assert client.delete("/api/goals/999", headers=auth_headers).status_code == 404
    assert client.post("/api/goals/999/contribute", headers=auth_headers,
                       json={"amount": 1}).status_code == 404


def test_goals_isolated_per_user(client, auth_headers):
    gid = client.post("/api/goals", headers=auth_headers,
                      json={"name": "Mine", "target_amount": 100}).get_json()["id"]
    other = _other_headers(client)
    assert client.get("/api/goals", headers=other).get_json() == []
    assert client.delete(f"/api/goals/{gid}", headers=other).status_code == 404
