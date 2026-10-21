"""Integration checks for the new public blog routes in the full Flask app."""
import json
import re

import pytest

from authentic_dynamics import create_app
from authentic_dynamics.blog import get_blog_posts


@pytest.fixture
def client():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    return app.test_client()


def test_blog_index_and_shared_navigation(client):
    response = client.get("/blog")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert html.count("<h1>") == 1
    for post in get_blog_posts():
        assert f'href="/blog/{post["slug"]}"' in html
    home = client.get("/").get_data(as_text=True)
    assert 'href="/blog"' in home
    assert '>Blog</a>' in home
    assert client.get("/static/css/blog.css").status_code == 200
    assert client.get("/static/css/blog-navigation.css").status_code == 200


@pytest.mark.parametrize("post", get_blog_posts(), ids=lambda post: post["slug"])
def test_each_article_has_content_canonical_and_schema(client, post):
    response = client.get("/blog/" + post["slug"], base_url="https://example.org")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert post["body_html"] in html
    assert "Planned — not deployed" in html
    assert "noindex" not in html
    assert html.count('<link rel="canonical"') == 1
    schema = json.loads(re.search(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    ).group(1))
    article = schema["@graph"][0]
    assert article["@type"] == "BlogPosting"
    assert article["headline"] == post["title"]
    assert article["mainEntityOfPage"]["@id"] == (
        "https://example.org/blog/" + post["slug"]
    )
    assert article["datePublished"] == post["published"]
    assert len(schema["@graph"][1]["itemListElement"]) == 3


def test_missing_article_returns_404(client):
    assert client.get("/blog/not-a-published-article").status_code == 404
    assert client.get("/blog/not-a-published-article/").status_code == 404


def test_trailing_slash_redirects(client):
    response = client.get("/blog/")
    assert response.status_code == 308
    assert response.headers["Location"].endswith("/blog")
    post = get_blog_posts()[0]
    response = client.get("/blog/" + post["slug"] + "/")
    assert response.status_code == 308
    assert response.headers["Location"].endswith("/blog/" + post["slug"])


def test_canonical_host_on_blog_pages():
    app = create_app({
        "TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "CANONICAL_HOST": "www.example.org",
    })
    response = app.test_client().get("/blog", base_url="https://www.example.org")
    assert response.status_code == 200
    assert b'<link rel="canonical" href="https://www.example.org/blog">' in response.data
