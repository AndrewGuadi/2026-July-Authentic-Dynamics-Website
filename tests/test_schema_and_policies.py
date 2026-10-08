"""Check the public business markup and policy destinations."""

import json
import re

from authentic_dynamics import create_app


def test_homepage_business_schema_matches_public_details():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    page = app.test_client().get("/").get_data(as_text=True)
    scripts = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>', page, re.DOTALL
    )

    assert len(scripts) == 1
    graph = json.loads(scripts[0])["@graph"]
    business = next(item for item in graph if item["@type"] == "LocalBusiness")
    website = next(item for item in graph if item["@type"] == "WebSite")
    assert business["telephone"] == "+1-717-729-5751"
    assert business["address"]["streetAddress"] == "4625 Laurel Valley Lane"
    assert business["address"]["postalCode"] == "17025"
    assert business["sameAs"] == ["https://share.google/1Wx1jHgaHJBC02ICt"]
    assert "logo" not in business
    assert website["publisher"]["@id"] == business["@id"]


def test_footer_policy_links_resolve_to_real_pages():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "CANONICAL_HOST": "www.authenticdynamics.com",
    })
    client = app.test_client()
    home = client.get("/", base_url="https://www.authenticdynamics.com").get_data(as_text=True)

    for path, heading in (
        ("/privacy-policy", "Privacy Policy"),
        ("/terms", "Website Terms"),
    ):
        assert f'href="{path}"' in home
        response = client.get(path, base_url="https://www.authenticdynamics.com")
        assert response.status_code == 200
        page = response.get_data(as_text=True)
        assert f"<h1>{heading}.</h1>" in page
        assert f'<link rel="canonical" href="https://www.authenticdynamics.com{path}">' in page
        assert 'hello@authenticdynamics.com' in page
