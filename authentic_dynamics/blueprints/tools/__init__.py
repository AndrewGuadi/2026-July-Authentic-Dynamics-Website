from flask import Blueprint

bp = Blueprint("tools", __name__, url_prefix="/tools")

from . import menu_routes, routes  # noqa: F401
