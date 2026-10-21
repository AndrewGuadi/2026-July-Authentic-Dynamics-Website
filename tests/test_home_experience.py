"""Public content remains useful before progressive enhancement runs."""

from html.parser import HTMLParser

import pytest

from authentic_dynamics import create_app


class PageContent(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.images = []
        self.headings = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "a":
            self.links.append(values)
        if tag == "img":
            self.images.append(values)
        if tag == "h1":
            self.headings.append(tag)


@pytest.fixture
def client():
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "home-experience-test",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "CANONICAL_HOST": "",
        "HUB_ENABLED": False,
    }).test_client()


def content(client, route):
    response = client.get(route)
    assert response.status_code == 200
    parser = PageContent()
    parser.feed(response.get_data(as_text=True))
    return parser, response.get_data(as_text=True)


def test_home_has_one_primary_heading_and_inspectable_project(client):
    page, html = content(client, "/")
    assert len(page.headings) == 1
    assert any(link.get("href") == "/work#plumbing" for link in page.links)
    assert "A CLOSER LOOK AT THE WORK" in html
    project = next(image for image in page.images if "1776-desktop" in image["src"])
    assert project["alt"]
    assert client.get(project["src"]).status_code == 200
    assert 'id="industry-panel"' in html
    # The initial panel has useful content and links even without JavaScript.
    panel = html.split('id="industry-panel"', 1)[1].split('</section>', 1)[0]
    assert "Make your services, coverage and next step easy to find" in panel
    assert 'href="/websites"' in panel
    for tool in ("planner", "calculator", "visibility"):
        assert f'data-tool="{tool}"' in html


def test_community_jump_links_and_existing_imagery_resolve(client):
    page, _html = content(client, "/about-community")
    assert len(page.headings) == 1
    for target in ("founder", "community", "business-resources", "contact"):
        assert target in page.ids
        assert any(link.get("href") == f"#{target}" for link in page.links)
    for asset in ("guasch-andrew.webp", "section-8-group-photo-1200.webp"):
        image = next(image for image in page.images if asset in image["src"])
        assert image["alt"]
        assert client.get(image["src"]).status_code == 200
    assert client.get("/static/css/community-experience.css").status_code == 200


def test_resource_fallback_is_server_rendered_and_safe(client):
    page, html = content(client, "/about-community")
    expected = {
        "https://business.pa.gov/",
        "https://www.pasbdc.org/",
        "https://www.pa.gov/agencies/dos/programs/business",
    }
    links = [link for link in page.links if link.get("href") in expected]
    assert {link["href"] for link in links} == expected
    assert all(link.get("rel") == "noopener noreferrer" for link in links)
    assert "Browse statewide starting points" in html
    # A structural update does not falsely refresh the source review date.
    assert "reviewed October 14, 2026" in html
