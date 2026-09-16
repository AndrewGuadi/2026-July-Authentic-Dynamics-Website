"""Application factory and component registration."""

from flask import Flask

from .config import Config
from .errors import register_error_handlers
from .security import register_security_headers


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    app.config.from_pyfile("config.py", silent=True)
    app.config.from_prefixed_env(prefix="AD")
    if test_config is not None:
        app.config.update(test_config)

    from .blueprints.health import bp as health_bp
    from .blueprints.main import bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(health_bp)
    register_error_handlers(app)
    register_security_headers(app)
    return app
