"""Application factory for FinTrak — full-stack financial management SaaS."""
import os

from flask import Flask, jsonify

from config import Config
from extensions import db, login_manager, bcrypt, jwt


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Initialise extensions.
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    login_manager.init_app(app)

    # Import models so SQLAlchemy is aware of them, then wire the user loader.
    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints.
    from auth import auth as auth_bp
    from views import main as main_bp
    from api import api as api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    # Currency formatter with thousands separators, e.g. 1234.5 -> "$1,234.50".
    @app.template_filter("money")
    def money(value):
        try:
            return "${:,.2f}".format(float(value))
        except (TypeError, ValueError):
            return "$0.00"

    # Liveness/readiness probe for Docker & load balancers.
    @app.route("/healthz")
    def healthz():
        import cache
        db_ok = True
        try:
            db.session.execute(db.text("SELECT 1"))
        except Exception:
            db_ok = False
        return jsonify({"status": "ok" if db_ok else "degraded",
                        "db": db_ok, "redis": cache.ping()}), (200 if db_ok else 503)

    # Create tables on first run (no-op if they already exist).
    with app.app_context():
        db.create_all()

        # Optional one-time demo seed for shell-less deploys (Render free tier).
        if os.environ.get("SEED_ON_START") == "1":
            try:
                from seed import seed_demo
                seed_demo()
            except Exception as exc:  # never let seeding block app startup
                app.logger.warning("SEED_ON_START skipped: %s", exc)

    return app


app = create_app()


if __name__ == "__main__":
    print("  FinTrak running at http://localhost:8000")
    app.run(host="0.0.0.0", port=8000, threaded=True, debug=False)
