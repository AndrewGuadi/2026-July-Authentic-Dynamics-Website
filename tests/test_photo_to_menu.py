"""Photo to Menu pilot boundaries and the Flask-to-OpenAI request contract."""

import io
import json
import re
from base64 import b64decode
from copy import deepcopy

from flask import session
from PIL import Image

from authentic_dynamics import create_app
from authentic_dynamics.blueprints.admin.routes import start_session
from authentic_dynamics.blueprints.tools import menu_scan
from authentic_dynamics.blueprints.tools.menu_routes import SAMPLE_MENU
from authentic_dynamics.extensions import db
from authentic_dynamics.models import AdminUser

PAGE = "/tools/photo-to-menu"
SCAN = PAGE + "/scan"


def make_app(**config):
    return create_app({
        "TESTING": True, "SECRET_KEY": "test", "SQLALCHEMY_DATABASE_URI": "sqlite://",
        **config,
    })


def photo():
    stream = io.BytesIO()
    image = Image.new("RGB", (60, 30), "white")
    exif = image.getexif()
    exif[274] = 6
    exif[305] = "test metadata"
    image.save(stream, "JPEG", exif=exif)
    stream.seek(0)
    return stream


def scan(client, stream, page=None):
    page = page or client.get(PAGE)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True))[1]
    return client.post(SCAN, data={"photo": (stream, "menu.jpg"), "csrf_token": token})


def test_sample_renders_and_hosted_guest_cannot_scan():
    app = make_app(MENU_OPENAI_API_KEY="fake")
    client = app.test_client()
    page = client.get(PAGE)
    assert page.status_code == 200
    assert b"Juniper &amp; Main" in page.data
    assert b"Maple Cold Brew" in page.data
    assert b"Photo scanning is available during the pilot." in page.data
    assert page.headers["Cache-Control"] == "no-store"

    app.config["WTF_CSRF_ENABLED"] = False
    assert client.post(SCAN).status_code == 403


def test_local_pilot_preserves_csrf_and_rejects_invalid_photos(monkeypatch):
    app = make_app(DEBUG=True, MENU_OPENAI_API_KEY="fake")
    client = app.test_client()

    def unexpected_api_call(*args):
        raise AssertionError("Invalid uploads must never call OpenAI")

    monkeypatch.setattr(menu_scan, "extract_menu", unexpected_api_call)
    assert client.post(SCAN).status_code == 400
    assert scan(client, io.BytesIO(b"not an image")).status_code == 400
    assert scan(client, io.BytesIO(b"x" * (menu_scan.MAX_IMAGE_BYTES + 1))).status_code == 413
    assert b'photo-menu-upload' not in client.get(PAGE, environ_overrides={
        "REMOTE_ADDR": "203.0.113.4",
    }).data


def test_hosted_pilot_accepts_only_valid_admin_sessions():
    app = make_app(MENU_OPENAI_API_KEY="fake")
    with app.test_request_context():
        db.create_all()
        user = AdminUser(email="pilot@example.test", password_hash="unused")
        db.session.add(user)
        db.session.flush()
        start_session(user)
        db.session.commit()
        token = session["admin_token"]

    client = app.test_client()
    with client.session_transaction() as cookie:
        cookie["admin_token"] = "invalid"
    assert b'photo-menu-upload' not in client.get(PAGE).data
    with client.session_transaction() as cookie:
        cookie["admin_token"] = token
    assert b'photo-menu-upload' in client.get(PAGE).data


def test_scan_calls_terra_with_normalized_photo_and_strict_schema(monkeypatch):
    menu = deepcopy(SAMPLE_MENU)
    menu["sections"][0]["items"][0]["prices"] = []
    menu["sections"][0]["items"][0]["review_note"] = "Price obscured by glare"
    calls = []

    def fake_open(request, timeout):
        calls.append(request)
        payload = json.loads(request.data)
        assert request.full_url == "https://api.openai.com/v1/responses"
        assert request.get_header("Authorization") == "Bearer fake"
        assert payload["model"] == "gpt-6.1-terra"
        assert payload["store"] is False
        assert payload["text"]["format"]["strict"] is True
        image_data = payload["input"][0]["content"][1]["image_url"].split(",", 1)[1]
        with Image.open(io.BytesIO(b64decode(image_data))) as normalized:
            assert normalized.size == (30, 60)
            assert not normalized.getexif()
        assert timeout == menu_scan.TIMEOUT_SECONDS
        return io.BytesIO(json.dumps({
            "status": "completed", "output": [{"type": "reasoning"}, {
                "type": "message", "content": [{"type": "output_text", "text": json.dumps(menu)}],
            }],
        }).encode())

    monkeypatch.setattr(menu_scan, "urlopen", fake_open)
    client = make_app(DEBUG=True, MENU_OPENAI_API_KEY="fake").test_client()
    response = scan(client, photo())
    assert response.status_code == 200
    assert response.json == {"menu": menu}
    assert len(calls) == 1

    menu["sections"] = []
    assert scan(client, photo()).status_code == 422
    menu["sections"] = "invalid result"
    assert scan(client, photo()).status_code == 502
