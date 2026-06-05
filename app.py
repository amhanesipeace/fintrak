"""Application factory for the Personal Finance Tracker."""
from flask import Flask

from config import Config
from extensions import db, login_manager


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
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

    # Create tables on first run (no-op if they already exist).
    with app.app_context():
        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    print("  Personal Finance Tracker running at http://localhost:5060")
    app.run(host="127.0.0.1", port=5060, threaded=True, debug=False)
