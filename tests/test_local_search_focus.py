from urllib.parse import urlsplit

import pytest

from authentic_dynamics import create_app


@pytest.fixture
def client():
    app = create_app({
        "TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "WTF_CSRF_ENABLED": False, "CANONICAL_HOST": "www.authenticdynamics.com",
    })
    return app.test_client()


@pytest.mark.parametrize("old,target", [
    ("/services/web-development", "/websites"),
    ("/services/digital-marketing", "/growth-technology#services"),
    ("/pricing", "/websites#starter"),
    ("/contact", "/about-community#contact"),
])
def test_retired_urls_permanently_reach_relevant_live_content(client, old, target):
    for suffix in ("", "/"):
        response = client.get(old + suffix, base_url="https://www.authenticdynamics.com")
        assert response.status_code == 301
        assert response.headers["Location"] == target
        destination = client.get(target, base_url="https://www.authenticdynamics.com")
        assert destination.status_code == 200
        fragment = urlsplit(target).fragment
        if fragment:
            assert f'id="{fragment}"'.encode() in destination.data


def test_legacy_get_does_not_redirect_contact_posts_or_unknown_pages(client):
    response = client.post("/contact", data={}, base_url="https://www.authenticdynamics.com")
    assert response.status_code == 400
    assert "Location" not in response.headers
    assert client.get("/services/not-a-real-service",
                      base_url="https://www.authenticdynamics.com").status_code == 404


def test_landing_pages_have_unique_relevant_metadata_and_canonicals(client):
    for path, title, section in [
        ("/websites", "Harrisburg Web Design for Small Businesses", "harrisburg-web-design"),
        ("/growth-technology", "Website Analytics &amp; Growth Services in Central PA",
         "website-analytics"),
    ]:
        response = client.get(path, base_url="https://www.authenticdynamics.com")
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert f"<title>{title} | Authentic Dynamics</title>" in html
        assert f'<link rel="canonical" href="https://www.authenticdynamics.com{path}">' in html
        assert f'id="{section}"' in html
        assert html.count("<h1>") == 1
        assert 'name="robots" content="noindex' not in html
