"""Service demos remain truthful, reachable and harmless without JavaScript."""

import re

import pytest

from authentic_dynamics import create_app


@pytest.fixture
def client():
    return create_app({"TESTING": True, "SECRET_KEY": "service-tests", "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}).test_client()


def test_website_demo_has_static_offer_and_safe_controls(client):
    page = client.get("/websites").get_data(as_text=True)
    assert 'id="website-experience"' in page
    assert "Fictional business" in page
    assert 'data-website-goal="inquiries"' in page
    assert 'data-website-goal="booking"' in page
    assert 'data-website-goal="catalog"' in page
    assert 'id="website-demo-status"' in page
    assert '/about-community?interest=website#contact' in page
    assert "$500" in page and "first year of standard hosting" in page
    assert 'class="fake-button"' not in page
    demo = page.split('id="website-experience"', 1)[1].split('</section>', 1)[0]
    assert '<form' not in demo


def test_growth_simulation_keeps_existing_builder(client):
    page = client.get("/growth-technology").get_data(as_text=True)
    assert 'id="growth-experience"' in page
    assert "Simulation only" in page
    assert "Customer view" in page and "Owner view" in page
    assert 'id="review-request-form"' in page
    assert 'src="/static/js/review-request-builder.js"' in page
    assert '/about-community?interest=automation#contact' in page


def test_work_uses_existing_artifact_and_no_future_or_measured_claims(client):
    page = client.get("/work").get_data(as_text=True)
    assert 'id="featured-work"' in page
    assert 'images/home/hero/1776-desktop-website.webp' in page
    assert "Website screenshot" in page
    assert "Future project detail pages" not in page
    assert "measured outcomes will be added" not in page
    for path in re.findall(r'src="(/static/[^\"]+)"', page):
        assert client.get(path).status_code == 200


@pytest.mark.parametrize("route", ["/websites", "/growth-technology", "/work"])
def test_service_assets_load(client, route):
    page = client.get(route).get_data(as_text=True)
    assert 'css/service-experiences.css' in page
    for path in re.findall(r'(?:src|href)="(/static/[^\"]+)"', page):
        assert client.get(path).status_code == 200
