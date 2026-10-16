"""Coverage for the Central Pennsylvania business resource finder."""

import pytest

from authentic_dynamics import create_app


@pytest.fixture
def client():
    return create_app({"TESTING": True}).test_client()


def test_about_page_includes_resource_finder_and_assets(client):
    response = client.get("/about-community")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="business-resources"' in page
    assert 'data-resource-finder' in page
    assert 'id="resource-county"' in page
    assert 'id="resource-need"' in page
    assert 'aria-live="polite"' in page
    assert 'href="#business-resources"' in page
    assert 'css/business-resource-finder.css' in page
    assert 'js/business-resource-finder.js' in page
    for county in ("Cumberland", "Dauphin", "Lancaster", "Lebanon", "Perry", "York"):
        assert f"{county} County" in page

    for asset in ("css/business-resource-finder.css", "js/business-resource-finder.js"):
        asset_response = client.get(f"/static/{asset}")
        assert asset_response.status_code == 200
        assert asset_response.data


def test_finder_uses_verified_sources_and_safe_external_links(client):
    script = client.get("/static/js/business-resource-finder.js").get_data(as_text=True)

    for domain in (
        "business.pa.gov",
        "pa.gov/agencies/dos",
        "pasbdc.org",
        "cumberlandbusiness.com",
        "dauphincounty.gov",
        "edclancaster.com",
        "lvedc.org",
        "perrycountyeda.com",
        "yceapa.org",
    ):
        assert domain in script
    assert "link.target = '_blank'" in script
    assert "link.rel = 'noopener noreferrer'" in script
    assert "localStorage" not in script
    assert "fetch(" not in script
