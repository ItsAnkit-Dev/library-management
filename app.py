"""
Flask application factory and extension initialization.
"""

import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from models import db, User
from config import config_map

# ── Extension instances (uninitialised) ───────────────────────────────────────
login_manager = LoginManager()
migrate       = Migrate()
csrf = CSRFProtect()


def create_app(config_name: str = "default") -> Flask:
    """Application factory."""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # ── Load config ───────────────────────────────────────────────────────────
    cfg = config_map.get(config_name, config_map["default"])
    app.config.from_object(cfg)

    # Ensure the uploads folder exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── Init extensions ───────────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    _init_login_manager(app)

    # ── Register blueprints ───────────────────────────────────────────────────
    from routes.auth       import auth_bp
    from routes.admin      import admin_bp
    from routes.librarian  import librarian_bp
    from routes.student    import student_bp
    from routes.api        import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp,     url_prefix="/admin")
    app.register_blueprint(librarian_bp, url_prefix="/librarian")
    app.register_blueprint(student_bp,   url_prefix="/student")
    app.register_blueprint(api_bp,       url_prefix="/api")

    # ── Context Processors ────────────────────────────────────────────────────
    @app.context_processor
    def inject_global_vars():
        from flask_login import current_user
        from models import Role
        from utils import get_student_recommendations
        context = {}
        if current_user.is_authenticated and current_user.role == Role.STUDENT:
            # Inject recommendation count (for Wishlist badge)
            recommendations = get_student_recommendations(current_user.id, limit=4)
            context['new_recommendations_count'] = len(recommendations)
        return context

    # ── Root redirect ─────────────────────────────────────────────────────────
    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    # ── Create tables (first run) ─────────────────────────────────────────────
    with app.app_context():
        try:
            db.create_all()
            app.logger.info("Successfully connected to the database and ensured tables exist.")
        except Exception as e:
            app.logger.error(f"Failed to connect to the database or create tables: {e}")

    # ── Custom CLI Commands ───────────────────────────────────────────────────
    @app.cli.command("init-db")
    def init_db_command():
        """Create new database tables."""
        try:
            db.create_all()
            print("Successfully initialized the database.")
        except Exception as e:
            print(f"Error initializing the database: {e}")

    return app


def _init_login_manager(app: Flask) -> None:
    login_manager.init_app(app)
    login_manager.login_view      = "auth.login"
    login_manager.login_message   = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = create_app("development")
    app.run(debug=True, host="0.0.0.0", port=5000)
