"""Auth helpers shared by the REST API.

`auth_required` accepts EITHER a JWT bearer token (API clients) OR a valid
Flask-Login session cookie (the browser UI), so the same endpoints serve both.
The resolved user id is stashed on `flask.g.user_id` for the view to use.
"""
from functools import wraps

from flask import g, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask_login import current_user


def resolve_user_id():
    """Return the authenticated user id from a JWT or session, else None."""
    # 1) Try a JWT bearer token (optional=True → no error if absent).
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity is not None:
            return int(identity)
    except Exception:
        pass  # malformed/expired token → fall through to session

    # 2) Fall back to a logged-in browser session.
    if current_user.is_authenticated:
        return current_user.id

    return None


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        uid = resolve_user_id()
        if uid is None:
            return jsonify({"error": "authentication required"}), 401
        g.user_id = uid
        return fn(*args, **kwargs)
    return wrapper
