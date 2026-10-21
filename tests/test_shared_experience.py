"""Regression checks for contextual inquiries and recoverable shared controls."""
import re

import pytest
from sqlalchemy.exc import SQLAlchemyError

from authentic_dynamics import create_app
from authentic_dynamics.extensions import db


@pytest.fixture
def app():
    return create_app({"TESTING": True, "SECRET_KEY": "test-experience",
                       "SQLALCHEMY_DATABASE_URI": "sqlite://", "HUB_ENABLED": False})


@pytest.mark.parametrize("path", ["/privacy-policy", "/terms", "/tools/"])
def test_home_is_not_current_on_other_pages(app, path):
    html = app.test_client().get(path).text
    assert not re.search(r'<a href="/"[^>]*aria-current="page"', html)


@pytest.mark.parametrize("path", ["/", "/about-community"])
def test_allowlisted_interest_prefills_but_arbitrary_input_does_not(app, path):
    client = app.test_client()
    html = client.get(path + "?interest=automation").text
    assert re.search(r'<option value="AI, automation &amp; custom systems"\s+selected', html)
    arbitrary = client.get(path + "?interest=arbitrary-injected-choice").text
    assert "arbitrary-injected-choice" not in arbitrary


def test_invalid_interest_has_linked_summary_and_retains_other_input(app):
    client = app.test_client()
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/").text)[1]
    response = client.post("/contact", data={"csrf_token": csrf, "source_page": "home",
        "name": "Example Owner", "email": "owner@example.com", "business": "Example Shop",
        "interest": "invalid", "message": "Please help with my website."})
    assert response.status_code == 400
    assert 'href="#interest"' in response.text
    assert 'id="interest-error"' in response.text
    assert 'aria-describedby="interest-error"' in response.text
    assert "Example Owner" in response.text


def test_failed_contact_save_keeps_draft_and_does_not_claim_success(app, monkeypatch):
    client = app.test_client()
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/").text)[1]
    def unavailable():
        raise SQLAlchemyError("test database unavailable")
    monkeypatch.setattr(db.session, "commit", unavailable)
    response = client.post("/contact", data={"csrf_token": csrf, "source_page": "home",
        "name": "Example Owner", "email": "owner@example.com", "business": "Example Shop",
        "interest": "Local visibility & marketing", "message": "Please help with my website."})
    assert response.status_code == 503
    assert "Please help with my website." in response.text
    assert "was not saved" in response.text
    assert "Your inquiry was saved" not in response.text


def test_policies_have_single_stylesheet_and_readable_anchor_targets(app):
    for path in ("/privacy-policy", "/terms"):
        html = app.test_client().get(path).text
        assert html.count('filename=') == 0
        assert html.count('/static/css/pages.css') == 1
        assert 'aria-label="On this page"' in html
        assert 'id="tools"' in html
