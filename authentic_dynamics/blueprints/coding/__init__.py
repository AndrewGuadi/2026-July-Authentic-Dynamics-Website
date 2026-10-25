"""Git-backed lessons; visitor code is never executed by Flask."""

import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Blueprint, abort, current_app, make_response, render_template

bp = Blueprint("coding", __name__, url_prefix="/coding-calendar")
LANGUAGES = {"javascript": "JavaScript", "python": "Python", "sql": "SQL (SQLite)"}


def today():
    return datetime.now(ZoneInfo("America/New_York")).date()


def lessons():
    root = Path(current_app.root_path) / "content" / "coding"
    return sorted(
        [json.loads(path.read_text(encoding="utf-8")) for path in root.glob("*/*.json")],
        key=lambda item: (item["date"], item["language"]),
    )


@bp.get("")
@bp.get("/")
def index():
    published = [item for item in lessons() if date.fromisoformat(item["date"]) <= today()]
    return render_template(
        "coding/index.html", lessons=published, languages=LANGUAGES,
        today=today().isoformat(), active_page="coding",
    )


@bp.get("/<language>/<day>/")
def lesson(language, day):
    if language not in LANGUAGES:
        abort(404)
    try:
        selected = date.fromisoformat(day)
    except ValueError:
        abort(404)
    if selected.isoformat() != day or selected > today():
        abort(404)
    item = next((item for item in lessons()
                 if item["language"] == language and item["date"] == day), None)
    if item is None:
        abort(404)
    return render_template(
        "coding/lesson.html", lesson=item, languages=LANGUAGES, active_page="coding",
    )


@bp.get("/sandbox")
def sandbox():
    response = make_response(render_template("coding/sandbox.html"))
    # This document also has iframe sandbox=allow-scripts, never allow-same-origin.
    # Blob workers inherit this policy: even Python's JS bridge has no network.
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval' blob:; "
        "worker-src blob:; connect-src 'none'; frame-src 'none'; "
        "form-action 'none'; base-uri 'none'; frame-ancestors 'self'; sandbox allow-scripts"
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), usb=()"
    return response
