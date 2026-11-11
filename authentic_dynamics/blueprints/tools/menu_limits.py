"""Server-side Photo to Menu limits shared by Flask workers."""

import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import closing
from ipaddress import ip_address
from math import ceil
from pathlib import Path
from time import time

from flask import after_this_request, current_app, request, url_for
from itsdangerous import BadData, URLSafeTimedSerializer

HOURLY_LIMIT = 3
HOUR_SECONDS = 3600
COOLDOWN_SECONDS = 5 * 60
BROWSER_COOKIE = "ad_menu_browser"
COOKIE_AGE_SECONDS = 365 * 24 * 60 * 60


class ScanLimitReached(Exception):
    def __init__(self, retry_after=None):
        self.retry_after = retry_after
        if retry_after is None:
            message = "This browser or network has reached its total menu scan limit."
        else:
            minutes = ceil(retry_after / 60)
            unit = "minute" if minutes == 1 else "minutes"
            message = f"Menu scan limit reached. Try again in {minutes} {unit}."
        super().__init__(message)


def browser_identity():
    signer = URLSafeTimedSerializer(current_app.secret_key, salt="photo-menu-browser")
    try:
        cookie = request.cookies.get(BROWSER_COOKIE, "")
        return signer.loads(cookie, max_age=COOKIE_AGE_SECONDS)
    except BadData:
        browser = secrets.token_urlsafe(24)

    @after_this_request
    def set_browser_cookie(response):
        response.set_cookie(
            BROWSER_COOKIE, signer.dumps(browser), max_age=COOKIE_AGE_SECONDS,
            path=url_for("tools.photo_to_menu"), httponly=True, samesite="Lax",
            secure=current_app.config["SESSION_COOKIE_SECURE"] or request.is_secure,
        )
        return response

    return browser


def _client_ip():
    addresses = [request.remote_addr]
    if current_app.config["MENU_SCAN_TRUST_X_REAL_IP"]:
        addresses.insert(0, request.headers.get("X-Real-IP"))
    for value in addresses:
        if value:
            try:
                address = ip_address(value)
            except ValueError:
                continue
            return str(getattr(address, "ipv4_mapped", None) or address)
    return "unknown"


def reserve_scan():
    """Reserve against both identities in one transaction before contacting OpenAI."""
    secret = current_app.secret_key
    if isinstance(secret, str):
        secret = secret.encode()
    identities = tuple(
        hmac.new(secret, value.encode(), hashlib.sha256).hexdigest()
        for value in (f"ip:{_client_ip()}", f"browser:{browser_identity()}")
    )
    maximum = current_app.config["MENU_SCAN_MAX_TESTS"]
    path = Path(current_app.instance_path) / "photo-menu-limits.sqlite3"
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.close(os.open(path, os.O_CREAT | os.O_RDWR, 0o600))

    with closing(sqlite3.connect(path, timeout=5)) as connection, connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS scan_limits (
                identity TEXT PRIMARY KEY,
                total INTEGER NOT NULL,
                newest REAL NOT NULL,
                previous REAL,
                oldest REAL
            )
        """)
        connection.execute("BEGIN IMMEDIATE")
        now = time()
        records = connection.execute(
            "SELECT total, newest, oldest FROM scan_limits WHERE identity IN (?, ?)", identities,
        ).fetchall()
        allowed_at = now
        for total, newest, oldest in records:
            if maximum and total >= maximum:
                raise ScanLimitReached()
            allowed_at = max(allowed_at, newest + COOLDOWN_SECONDS)
            # The table retains the last three timestamps for the rolling hourly window.
            if oldest is not None:
                allowed_at = max(allowed_at, oldest + HOUR_SECONDS)
        if allowed_at > now:
            raise ScanLimitReached(ceil(allowed_at - now))

        connection.executemany("""
            INSERT INTO scan_limits (identity, total, newest) VALUES (?, 1, ?)
            ON CONFLICT(identity) DO UPDATE SET
                total = scan_limits.total + 1,
                oldest = scan_limits.previous,
                previous = scan_limits.newest,
                newest = excluded.newest
        """, [(identity, now) for identity in identities])
