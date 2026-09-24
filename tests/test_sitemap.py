from xml.etree import ElementTree

from authentic_dynamics import create_app


def test_sitemap_lists_only_public_pages_with_absolute_urls():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    response = app.test_client().get("/sitemap.xml", base_url="https://example.org")

    assert response.status_code == 200
    assert response.mimetype == "application/xml"
    root = ElementTree.fromstring(response.data)
    assert root.tag == "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset"
    locations = [
        element.text for element in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
    ]
    assert locations == [
        "https://example.org/",
        "https://example.org/websites",
        "https://example.org/growth-technology",
        "https://example.org/work",
        "https://example.org/about-community",
        "https://example.org/tools/",
        "https://example.org/tools/pdf-to-image",
        "https://example.org/tools/csv-converter",
        "https://example.org/tools/qr-code-maker",
        "https://example.org/tools/video-converter",
    ]


def test_canonical_host_redirect_and_sitemap():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "CANONICAL_HOST": "www.example.org",
    })
    client = app.test_client()

    redirect_response = client.get(
        "/websites?source=apex", base_url="http://example.org", follow_redirects=False
    )
    assert redirect_response.status_code == 308
    assert redirect_response.headers["Location"] == (
        "https://www.example.org/websites?source=apex"
    )
    assert client.post("/contact", base_url="http://example.org").status_code == 308

    response = client.get("/sitemap.xml", base_url="http://www.example.org")
    root = ElementTree.fromstring(response.data)
    locations = [
        element.text for element in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
    ]
    assert locations[0] == "https://www.example.org/"
    assert all(url.startswith("https://www.example.org/") for url in locations)

    page = client.get("/websites", base_url="https://www.example.org")
    assert b'<link rel="canonical" href="https://www.example.org/websites">' in page.data
