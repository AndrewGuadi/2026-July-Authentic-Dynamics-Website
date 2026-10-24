"""Retired public links reach equivalent pages without changing form submissions."""
import pytest

from authentic_dynamics import create_app


@pytest.fixture
def client():
    return create_app({"TESTING": True, "SECRET_KEY": "test-only", "CANONICAL_HOST": ""}).test_client()


@pytest.mark.parametrize(("path", "target"), [
    ("/contact", "/about-community#contact"),
    ("/about", "/about-community"),
    ("/portfolio", "/work"),
    ("/services/web-development", "/websites"),
    ("/services/digital-marketing", "/growth-technology#services"),
    ("/pricing", "/websites#starter"),
])
@pytest.mark.parametrize("suffix", ["", "/", "?intent=consult&service=google-business-profile"])
def test_retired_links_have_one_permanent_redirect(client, path, target, suffix):
    response = client.get(path + suffix)
    assert response.status_code == 301
    assert response.headers["Location"] == target
    page, _, anchor = target.partition("#")
    destination = client.get(page)
    assert destination.status_code == 200
    if anchor:
        assert f'id="{anchor}"'.encode() in destination.data


@pytest.mark.parametrize("path", [
    "/blog/guide-35-lead-generation-real-estate-websites",
    "/static/pdf/google-ads-primer-for-real-estate.pdf",
    "/locations/", "/portfolio/nonexistent", "/.env",
])
def test_unmatched_content_is_not_redirected_to_unrelated_pages(client, path):
    assert client.get(path).status_code == 404


def test_contact_get_does_not_replace_post_or_allow_external_redirect(client):
    assert client.post("/contact", data={}).status_code == 400
    assert client.get("/contact?next=https://example.com").headers["Location"] == "/about-community#contact"
    assert client.head("/contact").status_code == 301
