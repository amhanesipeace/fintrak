"""Shared Flask extensions (kept separate to avoid circular imports)."""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager

db = SQLAlchemy()

# bcrypt password hashing (resume: "bcrypt hashing")
bcrypt = Bcrypt()

# JWT auth for the REST API (resume: "JWT-based authentication")
jwt = JWTManager()

# Flask-Login secure server-side sessions for the browser UI
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "error"
