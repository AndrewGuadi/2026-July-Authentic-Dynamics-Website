"""Smoke tests for the first page and its local dependencies."""

import pytest

from authentic_dynamics import create_app


@pytest.fixture
def client():
    return create_app({"TESTING": True}).test_client()


def test_homepage_renders_with_local_assets(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert b"Authentic Dynamics" in response.data
    assert b"We build" in response.data
    assert b'href="/static/css/site.css"' in response.data
    assert b'src="/static/js/home.js"' in response.data

    for asset in ("css/site.css", "js/home.js", "fonts/inter-1.woff"):
        asset_response = client.get(f"/static/{asset}")
        assert asset_response.status_code == 200
        assert asset_response.data


def test_health_endpoint(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json == {"status": "ok"}
    assert response.headers["Cache-Control"] == "no-store"


def test_unknown_page_has_a_home_link(client):
    response = client.get("/not-a-page")

    assert response.status_code == 404
    assert b'404' in response.data
    assert b'href="/"' in response.data


@pytest.mark.parametrize(
    ("path", "heading", "active_label"),
    [
        ("/websites", "A website that", "Websites"),
        ("/growth-technology", "More than", "Growth &amp; Technology"),
        ("/work", "Built for real", "Work"),
        ("/about-community", "Local enough", "About &amp; Community"),
    ],
)
def test_interior_pages_render_with_navigation(client, path, heading, active_label):
    response = client.get(path)
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert heading in page
    assert f'aria-current="page">{active_label}</a>' in page
    assert 'href="/static/css/pages.css"' in page
    assert 'src="/static/js/site.js"' in page
    for destination in ("/", "/websites", "/growth-technology", "/work", "/about-community"):
        assert f'href="{destination}"' in page


def test_about_page_has_contact_submission_form_elements(client):
    response = client.get("/about-community")
    page = response.get_data(as_text=True)

    assert 'id="contact-form"' in page
    assert 'action="/contact#contact" method="post"' in page
    assert 'name="csrf_token"' in page
    assert 'id="interest"' in page
    assert 'id="contact-status"' in page
    assert 'name="email" type="email"' in page
    for asset in ("/static/css/pages.css", "/static/js/site.js"):
        assert client.get(asset).status_code == 200
