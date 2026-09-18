from flask import Blueprint

bp = Blueprint("tools", __name__, url_prefix="/tools")

from . import routes  # noqa: F401
