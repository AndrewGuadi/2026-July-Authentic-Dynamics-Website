"""Photo to Menu public access, limits, and the Flask-to-OpenAI request contract."""

import io
import json
import re
from base64 import b64decode
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier

import pytest
from PIL import Image

from authentic_dynamics import create_app
from authentic_dynamics.blueprints.tools import menu_limits, menu_scan
from authentic_dynamics.blueprints.tools.menu_routes import SAMPLE_MENU

PAGE = "/tools/photo-to-menu"
SCAN = PAGE + "/scan"
BASE_URL = "https://www.authenticdynamics.com"


def make_app(tmp_path, **config):
    app = create_app({
        "TESTING": True, "SECRET_KEY": "test", "SQLALCHEMY_DATABASE_URI": "sqlite://",
        **config,
    })
    app.instance_path = str(tmp_path)
    return app


def photo():
    stream = io.BytesIO()
    image = Image.new("RGB", (60, 30), "white")
    exif = image.getexif()
    exif[274] = 6
    exif[305] = "test metadata"
    image.save(stream, "JPEG", exif=exif)
    stream.seek(0)
    return stream


def scan(client, stream, headers=None):
    page = client.get(PAGE, headers=headers, base_url=BASE_URL)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True))[1]
    return client.post(SCAN, data={"photo": (stream, "menu.jpg"), "csrf_token": token},
                       headers={"Referer": BASE_URL + PAGE, **(headers or {})}, base_url=BASE_URL)


def test_sample_renders_when_scanner_is_unconfigured(tmp_path):
    app = make_app(tmp_path, MENU_OPENAI_API_KEY=" ")
    client = app.test_client()
    page = client.get(PAGE)
    assert page.status_code == 200
    assert b"Juniper &amp; Main" in page.data
    assert b"Maple Cold Brew" in page.data
    assert b"Photo scanning is temporarily unavailable." in page.data
    assert b'photo-menu-upload' not in page.data
    assert page.data.index(b'id="photo-menu-section-bar"') < page.data.index(
        b'class="photo-menu-source"'
    )
    assert page.data.count(b'aria-label="Menu sections"') == 1
    for index in range(1, len(SAMPLE_MENU["sections"]) + 1):
        section_id = f"photo-menu-section-{index}".encode()
        assert b'href="#' + section_id + b'"' in page.data
        assert b'id="' + section_id + b'" tabindex="-1"' in page.data
    assert page.headers["Cache-Control"] == "no-store"

    app.config["WTF_CSRF_ENABLED"] = False
    assert client.post(SCAN).status_code == 503


def test_public_scanner_preserves_csrf_and_rejects_invalid_photos(monkeypatch, tmp_path):
    app = make_app(tmp_path, MENU_OPENAI_API_KEY="fake")
    client = app.test_client()

    def unexpected_api_call(*args):
        raise AssertionError("Invalid uploads must never call OpenAI")

    monkeypatch.setattr(menu_scan, "extract_menu", unexpected_api_call)
    assert client.post(SCAN, data={"photo": (photo(), "menu.jpg")}, base_url=BASE_URL,
                       headers={"Referer": BASE_URL + PAGE}).status_code == 400
    assert scan(client, io.BytesIO(b"not an image")).status_code == 400
    assert scan(client, io.BytesIO(b"x" * (menu_scan.MAX_IMAGE_BYTES + 1))).status_code == 413
    assert not (tmp_path / "photo-menu-limits.sqlite3").exists()


def test_signed_out_scan_calls_terra_with_normalized_photo_and_strict_schema(monkeypatch, tmp_path):
    menu = deepcopy(SAMPLE_MENU)
    menu["sections"][0]["items"][0]["prices"] = []
    menu["sections"][0]["items"][0]["review_note"] = "Price obscured by glare"
    calls = []
    now = 10_000
    monkeypatch.setattr(menu_limits, "time", lambda: now)

    def fake_open(request, timeout):
        calls.append(request)
        payload = json.loads(request.data)
        assert request.full_url == "https://api.openai.com/v1/responses"
        assert request.get_header("Authorization") == "Bearer fake"
        assert payload["model"] == "gpt-6.1-terra"
        assert payload["store"] is False
        assert payload["service_tier"] == "default"
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
            "usage": {"input_tokens": 2000, "output_tokens": 500, "input_tokens_details": {
                "cached_tokens": 100, "cache_write_tokens": 200,
                "cache_write_tokens_details": {"ttl_30m_tokens": 120, "ttl_12h_tokens": 80},
            }},
        }).encode())

    monkeypatch.setattr(menu_scan, "urlopen", fake_open)
    monkeypatch.setenv("AD_MENU_OPENAI_API_KEY", "fake")
    app = make_app(tmp_path, SESSION_COOKIE_SECURE=True)
    assert not app.debug
    client = app.test_client()
    response = scan(client, photo())
    assert response.status_code == 200
    assert response.json == {"menu": menu, "estimated_cost_usd": "0.00455500"}
    assert len(calls) == 1

    now += 300
    menu["sections"] = []
    unreadable = scan(client, photo())
    assert unreadable.status_code == 422
    assert unreadable.json["estimated_cost_usd"] == "0.00455500"
    assert scan(client, photo()).status_code == 429
    now += 300
    menu["sections"] = "invalid result"
    assert scan(client, photo()).status_code == 502


def test_cost_estimate_handles_missing_or_invalid_usage():
    assert menu_scan.estimate_cost_usd(None) is None
    assert menu_scan.estimate_cost_usd({"input_tokens": 1000, "output_tokens": 300}) == "0.00250000"
    assert menu_scan.estimate_cost_usd({
        "input_tokens": 20, "output_tokens": 10, "input_tokens_details": {"cached_tokens": 25},
    }) is None


def test_ip_and_browser_limits_share_the_same_rolling_windows(monkeypatch, tmp_path):
    now = 10_000
    monkeypatch.setattr(menu_limits, "time", lambda: now)
    monkeypatch.setattr(menu_scan, "extract_menu", lambda *args: (SAMPLE_MENU, None))
    app = make_app(tmp_path, MENU_OPENAI_API_KEY="fake",
                   MENU_SCAN_TRUST_X_REAL_IP=True, MENU_SCAN_MAX_TESTS=0)
    first = app.test_client()
    second = app.test_client()
    ip_one = {"X-Real-IP": "203.0.113.1"}
    ip_two = {"X-Real-IP": "203.0.113.2"}
    assert scan(first, photo(), ip_one).status_code == 200
    for client, headers in [(second, ip_one), (first, ip_two)]:
        response = scan(client, photo(), headers)
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "300"
    now += 299.5
    assert scan(first, photo(), ip_one).headers["Retry-After"] == "1"
    now += .5
    assert scan(first, photo(), ip_one).status_code == 200
    now += 300
    assert scan(first, photo(), ip_one).status_code == 200
    now += 300
    response = scan(first, photo(), ip_one)
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "2700"
    assert scan(second, photo(), ip_two).status_code == 200
    now += 2700
    assert scan(first, photo(), ip_one).status_code == 200


def test_total_cap_is_configurable_and_persists_across_app_restarts(monkeypatch, tmp_path):
    now = 10_000
    monkeypatch.setattr(menu_limits, "time", lambda: now)
    monkeypatch.setattr(menu_scan, "extract_menu", lambda *args: (SAMPLE_MENU, None))
    monkeypatch.setenv("AD_MENU_SCAN_MAX_TESTS", "1")
    client = make_app(tmp_path, MENU_OPENAI_API_KEY="fake").test_client()
    assert scan(client, photo()).status_code == 200
    now += 86_400
    restarted = make_app(tmp_path, MENU_OPENAI_API_KEY="fake").test_client()
    response = scan(restarted, photo(), {"X-Real-IP": "203.0.113.5"})
    assert response.status_code == 429
    assert "total menu scan limit" in response.json["error"]
    assert "Retry-After" not in response.headers
    monkeypatch.setenv("AD_MENU_SCAN_MAX_TESTS", "2")
    app = make_app(tmp_path, MENU_OPENAI_API_KEY="fake")
    assert scan(app.test_client(), photo()).status_code == 200


def test_parallel_requests_only_start_one_scan(monkeypatch, tmp_path):
    app = make_app(tmp_path, MENU_OPENAI_API_KEY="fake")
    ready = Barrier(2, timeout=5)
    prepare = menu_scan.prepare_photo
    calls = []

    def prepare_together(stream):
        image = prepare(stream)
        ready.wait()
        return image

    def extract(*args):
        calls.append(1)
        return SAMPLE_MENU, None

    monkeypatch.setattr(menu_scan, "prepare_photo", prepare_together)
    monkeypatch.setattr(menu_scan, "extract_menu", extract)
    with ThreadPoolExecutor(2) as executor:
        results = list(executor.map(lambda _: scan(app.test_client(), photo()).status_code, range(2)))
    assert sorted(results) == [200, 429]
    assert calls == [1]


@pytest.mark.parametrize("value", ["-1", "true", "unlimited"])
def test_bad_total_cap_is_rejected_at_startup(monkeypatch, tmp_path, value):
    monkeypatch.setenv("AD_MENU_SCAN_MAX_TESTS", value)
    with pytest.raises(ValueError, match="AD_MENU_SCAN_MAX_TESTS"):
        make_app(tmp_path)
