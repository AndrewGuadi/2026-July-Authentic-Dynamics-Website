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
    ]
