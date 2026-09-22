"""Application factory and component registration."""

import os
import secrets
from pathlib import Path

from flask import Flask

from .config import Config
from .errors import register_error_handlers
from .extensions import csrf, db, migrate
from .security import register_security_headers


def _ensure_secret_key(app: Flask) -> None:
    """Keep a stable, untracked key for local sessions when none is configured."""
    if app.config["SECRET_KEY"]:
        return

    key_path = Path(app.instance_path) / ".secret_key"
    key_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(descriptor, "w", encoding="utf-8") as key_file:
            key_file.write(secrets.token_hex(32))
    app.config["SECRET_KEY"] = key_path.read_text(encoding="utf-8").strip()


def _prepare_local_database(app: Flask) -> None:
    """Create the default SQLite file with private permissions."""
    if app.config["SQLALCHEMY_DATABASE_URI"] != Config.SQLALCHEMY_DATABASE_URI:
        return
    database_path = Path(app.instance_path) / "authentic_dynamics.db"
    database_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(database_path, os.O_RDWR | os.O_CREAT, 0o600)
    os.close(descriptor)
    database_path.chmod(0o600)


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    app.config.from_pyfile("config.py", silent=True)
    app.config.from_prefixed_env(prefix="AD")
    if test_config is not None:
        app.config.update(test_config)
    _ensure_secret_key(app)
    _prepare_local_database(app)

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)

    # Apply the larger video-only limit before CSRF protection can parse a request.
    @app.before_request
    def video_request_limit():
        from flask import request

        if request.endpoint == "tools.video_server":
            request.max_content_length = app.config["VIDEO_MAX_BYTES"] + 1024 * 1024

    csrf.init_app(app)

    from . import models  # noqa: F401
    from .commands import admin, contacts

    app.cli.add_command(contacts)
    app.cli.add_command(admin)

    from .blueprints.admin import bp as admin_bp
    from .blueprints.games import bp as games_bp
    from .blueprints.health import bp as health_bp
    from .blueprints.main import bp as main_bp
    from .blueprints.tools import bp as tools_bp

    app.register_blueprint(tools_bp)
    app.register_blueprint(games_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(admin_bp)
    register_error_handlers(app)
    register_security_headers(app)
    return app
