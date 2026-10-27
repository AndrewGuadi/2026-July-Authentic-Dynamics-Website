from flask import Blueprint

bp = Blueprint("main", __name__)

from . import builder, legacy, routes  # noqa: F401
