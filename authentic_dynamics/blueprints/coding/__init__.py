"""Git-backed lessons; visitor code is never executed by Flask."""

import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Blueprint, abort, current_app, make_response, render_template, request, url_for

bp = Blueprint("coding", __name__, url_prefix="/coding-calendar")
LANGUAGES = {"javascript": "JavaScript", "python": "Python", "sql": "SQL (SQLite)"}
CATEGORIES = {
    "arrays": "Arrays & sequences", "strings": "Strings & text", "objects": "Objects & dictionaries",
    "numbers": "Numbers & validation", "querying": "Selecting & sorting", "aggregation": "Totals & groups",
    "joins": "Joining data", "conditions": "Conditions & missing values",
}
LEVELS = {"beginner": "Beginner", "intermediate": "Intermediate"}


def today():
    return datetime.now(ZoneInfo("America/New_York")).date()


def lessons():
    root = Path(current_app.root_path) / "content" / "coding"
    return sorted(
        [json.loads(path.read_text(encoding="utf-8")) for path in root.glob("*/*.json")],
        key=lambda item: (item["date"], item["language"]),
    )


def parse_day(value):
    try:
        selected = date.fromisoformat(value)
    except ValueError:
        abort(400, description="Choose a valid calendar date.")
    if selected.isoformat() != value:
        abort(400, description="Use a date in YYYY-MM-DD format.")
    return selected


def neighbors(days, selected):
    return (next((day for day in reversed(days) if day < selected), None),
            next((day for day in days if day > selected), None))


def fresh_page(template, **context):
    response = make_response(render_template(template, **context))
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("")
@bp.get("/")
def index():
    current = today()
    selected = parse_day(request.args.get("date", current.isoformat()))
    language = request.args.get("language", "javascript")
    category = request.args.get("category", "")
    level = request.args.get("level", "")
    track = request.args.get("track", "")
    month = request.args.get("month", "")
    if (language not in LANGUAGES or (category and category not in CATEGORIES)
            or (level and level not in LEVELS) or (track and track not in LANGUAGES)):
        abort(400, description="Choose a listed language, topic, or difficulty.")
    all_items = lessons()
    days = sorted({date.fromisoformat(item["date"]) for item in all_items})
    previous_day, next_day = neighbors(days, selected)
    published = [item for item in all_items if item["date"] <= current.isoformat()]
    months = sorted({item["date"][:7] for item in published}, reverse=True)
    if month and month not in months:
        abort(400, description="Choose a month in the archive.")
    filtered = [item for item in published
                if (not category or item["category"] == category)
                and (not level or item["level"] == level)
                and (not track or item["language"] == track)
                and (not month or item["date"].startswith(month))]
    archive_days = sorted({item["date"] for item in filtered}, reverse=True)
    try:
        page = int(request.args.get("page", "1"))
    except ValueError:
        abort(400, description="Choose a valid archive page.")
    page_count = max(1, (len(archive_days) + 19) // 20)
    if page < 1 or page > page_count:
        abort(400, description="That archive page is not available.")
    page_days = set(archive_days[(page - 1) * 20:page * 20])
    archive = [item for item in filtered if item["date"] in page_days]
    query = {"date": selected.isoformat(), "language": language, "category": category,
             "level": level, "track": track, "month": month, "page": page}

    def calendar_url(**changes):
        values = {**query, **changes}
        return url_for("coding.index", **{k: v for k, v in values.items()
                                         if v not in (None, "") and not (k == "page" and v == 1)})

    return fresh_page(
        "coding/index.html", lessons=archive, languages=LANGUAGES, categories=CATEGORIES,
        levels=LEVELS, months=months, filters=query, calendar_url=calendar_url,
        today=current.isoformat(), selected=selected.isoformat(), selected_language=language,
        selected_label=f"{selected:%A, %B} {selected.day}, {selected.year}",
        day_lessons={item["language"]: item for item in all_items if item["date"] == selected.isoformat()},
        upcoming=selected > current, previous_day=previous_day, next_day=next_day,
        first_day=min(days[0], current, selected) if days else min(current, selected),
        last_day=max(days[-1], current, selected) if days else max(current, selected),
        archive_count=len(filtered), archive_page=page, archive_pages=page_count,
        active_page="coding",
    )


@bp.get("/<language>/<day>/")
def lesson(language, day):
    if language not in LANGUAGES:
        abort(404)
    try:
        selected = date.fromisoformat(day)
    except ValueError:
        abort(404)
    current = today()
    if selected.isoformat() != day or selected > current:
        abort(404)
    all_items = lessons()
    item = next((item for item in all_items if item["language"] == language and item["date"] == day), None)
    if item is None:
        abort(404)
    track_days = sorted({date.fromisoformat(item["date"]) for item in all_items
                         if item["language"] == language and item["date"] <= current.isoformat()})
    previous_day, next_day = neighbors(track_days, selected)
    return fresh_page(
        "coding/lesson.html", lesson=item, languages=LANGUAGES, categories=CATEGORIES,
        levels=LEVELS, previous_day=previous_day, next_day=next_day, today=current.isoformat(),
        same_day_languages=[key for key in LANGUAGES
                            if any(x["language"] == key and x["date"] == day for x in all_items)],
        active_page="coding",
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
