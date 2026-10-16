"""Business Hub user interface and authenticated JSON interface."""
from flask import Blueprint

bp = Blueprint('hub', __name__, url_prefix='/hub')

from . import routes  # noqa: F401
