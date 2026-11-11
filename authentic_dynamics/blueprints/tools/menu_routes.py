"""Photo to Menu demo and restricted extraction endpoint."""

import sqlite3

from flask import current_app, render_template, request, session
from werkzeug.exceptions import RequestEntityTooLarge

from authentic_dynamics.blueprints.admin.routes import get_session_admin

from . import bp, menu_limits, menu_scan

SAMPLE_MENU = {
    "name": "Juniper & Main",
    "notes": ["Sandwiches are served with kettle chips."],
    "warnings": [],
    "sections": [
        {"name": "Sandwiches", "note": None, "items": [
            {"name": "Roast Turkey & Apple", "description": "Sharp cheddar, arugula and maple mustard.",
             "prices": [{"label": None, "text": "$12.50"}], "review_note": None},
            {"name": "Garden Grilled Cheese", "description": "Tomato jam, basil and three cheeses.",
             "prices": [{"label": None, "text": "$10.00"}], "review_note": None},
        ]},
        {"name": "Coffee & Drinks", "note": None, "items": [
            {"name": "Maple Cold Brew", "description": "Cold brew with a splash of Pennsylvania maple.",
             "prices": [{"label": "Small", "text": "$4.25"}, {"label": "Large", "text": "$5.25"}],
             "review_note": None},
            {"name": "House Lemonade", "description": "Fresh lemon and a little cane sugar.",
             "prices": [{"label": None, "text": "$3.75"}], "review_note": None},
        ]},
    ],
}


def _scan_available():
    if not current_app.config["MENU_OPENAI_API_KEY"].strip():
        return False
    if current_app.debug and request.remote_addr in {"127.0.0.1", "::1"}:
        return True
    return bool(session.get("admin_token") and get_session_admin())


@bp.get("/photo-to-menu")
def photo_to_menu():
    scan_available = _scan_available()
    if scan_available:
        menu_limits.browser_identity()
    return render_template(
        "tools/photo_to_menu.html", active_page="tools", sample=SAMPLE_MENU,
        scan_available=scan_available, max_image_bytes=menu_scan.MAX_IMAGE_BYTES,
        max_tests=current_app.config["MENU_SCAN_MAX_TESTS"],
        hourly_limit=menu_limits.HOURLY_LIMIT, cooldown_minutes=menu_limits.COOLDOWN_SECONDS // 60,
    )


@bp.post("/photo-to-menu/scan")
def scan_menu():
    if not _scan_available():
        return {"error": "Photo scanning is available to pilot testers."}, 403
    try:
        photos = request.files.getlist("photo")
        if len(photos) != 1 or len(request.files) != 1 or not photos[0].filename:
            return {"error": "Choose one menu photo."}, 400
        photo = menu_scan.prepare_photo(photos[0].stream)
    except RequestEntityTooLarge:
        return {"error": "Choose a photo that is 12 MB or smaller."}, 413
    except menu_scan.MenuScanError as error:
        return {"error": str(error)}, error.status

    try:
        menu_limits.reserve_scan()
    except menu_limits.ScanLimitReached as error:
        headers = {"Retry-After": str(error.retry_after)} if error.retry_after is not None else {}
        return {"error": str(error)}, 429, headers
    except (OSError, sqlite3.Error):
        current_app.logger.exception("Photo to Menu could not reserve a scan")
        return {"error": "The scanner is temporarily unavailable. Try again shortly."}, 503

    try:
        menu, cost = menu_scan.extract_menu(photo, current_app.config["MENU_OPENAI_API_KEY"].strip())
    except menu_scan.MenuScanError as error:
        return {"error": str(error), "estimated_cost_usd": error.estimated_cost_usd}, error.status
    return {"menu": menu, "estimated_cost_usd": cost}
