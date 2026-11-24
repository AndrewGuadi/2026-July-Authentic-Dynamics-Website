import pytest

from authentic_dynamics import create_app


@pytest.fixture
def client():
    return create_app({"TESTING": True, "SECRET_KEY": "test", "WTF_CSRF_ENABLED": False,
                       "SQLALCHEMY_DATABASE_URI": "sqlite://"}).test_client()


def test_service_quote_page_and_local_assets(client):
    response = client.get("/tools/service-quote")
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert "Price the job." in page
    assert "Protect the margin." in page
    assert "Your inputs stay in this page" in page
    assert 'id="sq-inputs" class="sq-inputs" disabled' in page
    assert "Loading the local calculator" in page
    assert 'type="module" src="/static/js/service-quote.mjs"' in page
    assert client.get("/static/css/tools.css").status_code == 200
    assert client.get("/static/css/service-quote.css").status_code == 200
    assert client.get("/static/js/service-quote.mjs").status_code == 200
    assert client.get("/static/js/service-quote-core.mjs").status_code == 200
    nav = page.split('<nav id="nav"')[1].split("</nav>")[0]
    assert "/tools" not in nav


def test_service_quote_has_no_server_submission(client):
    response = client.post("/tools/service-quote")
    assert response.status_code == 405


def test_service_quote_catalog_discovery(client):
    page = client.get("/tools/").get_data(as_text=True)
    assert response_has_tool_card(page)
    assert "14 tools, ready when you are." in page


def response_has_tool_card(page):
    return (
        'href="/tools/service-quote"' in page
        and 'data-tool-job="billing"' in page
        and "Service Job Quote Calculator" in page
        and "Price a job" in page
    )
