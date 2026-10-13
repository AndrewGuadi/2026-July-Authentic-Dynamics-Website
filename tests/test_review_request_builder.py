"""Coverage for the review-request feature on the growth page."""

from authentic_dynamics import create_app


def test_growth_page_includes_local_review_request_builder():
    client = create_app({"TESTING": True}).test_client()
    response = client.get("/growth-technology")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="review-request-form"' in page
    assert 'id="review-business"' in page
    assert 'id="review-link"' in page
    assert 'id="review-message"' in page
    assert "Ask for an honest review—not a positive one." in page
    assert "support.google.com/business/answer/16816815" in page
    assert "support.google.com/contributionpolicy/answer/7400114" in page
    assert 'css/review-request-builder.css' in page
    assert 'js/review-request-builder.js' in page
    assert "five-star" not in page.lower()
    assert "5-star" not in page.lower()

    for asset in (
        "/static/css/review-request-builder.css",
        "/static/js/review-request-builder.js",
    ):
        asset_response = client.get(asset)
        assert asset_response.status_code == 200
        assert asset_response.data
