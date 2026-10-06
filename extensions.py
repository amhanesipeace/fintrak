"""Shared Flask extensions (kept separate to avoid circular imports)."""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()

# Rate limiting (brute-force protection on auth), backed by Redis in prod.
# Storage URI and enabled-flag come from app config (RATELIMIT_* keys).
limiter = Limiter(key_func=get_remote_address)

# Alembic-based schema migrations (flask db init/migrate/upgrade)
migrate = Migrate()

# bcrypt password hashing (resume: "bcrypt hashing")
bcrypt = Bcrypt()

# JWT auth for the REST API (resume: "JWT-based authentication")
jwt = JWTManager()

# Flask-Login secure server-side sessions for the browser UI
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "error"
