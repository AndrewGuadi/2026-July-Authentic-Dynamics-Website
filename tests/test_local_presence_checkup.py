"""Coverage for the local-presence self-check on the growth page."""

from authentic_dynamics import create_app


def test_growth_page_includes_local_presence_checkup():
    client = create_app({"TESTING": True}).test_client()
    response = client.get("/growth-technology")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="local-presence-checkup"' in page
    assert 'data-local-presence-checkup' in page
    assert page.count('data-presence-check value=') == 10
    assert 'value="service-area"' in page
    assert 'value="hybrid"' in page
    assert "not a Google score" in page
    assert "support.google.com/business/answer/3038177" in page
    assert "official_gbp_best_practices_playbook_2026.pdf" in page
    assert 'id="presence-remember"' in page
    assert "stores only your selected business type and checkboxes" in page
    assert 'href="#review-request"' in page
    assert "/about-community?interest=growth#contact" in page

    for asset in (
        "/static/css/local-presence-checkup.css",
        "/static/js/local-presence-checkup.js",
    ):
        asset_response = client.get(asset)
        assert asset_response.status_code == 200
        assert asset_response.data


def test_local_presence_checkup_does_not_request_customer_or_account_data():
    client = create_app({"TESTING": True}).test_client()
    page = client.get("/growth-technology").get_data(as_text=True)
    section = page.split('id="local-presence-checkup"', 1)[1].split("</section>", 1)[0]

    assert 'type="password"' not in section
    assert 'type="file"' not in section
    assert 'name="email"' not in section
    assert 'name="phone"' not in section
    assert "stores only your selected business type and checkboxes" in section
