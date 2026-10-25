"""Offline content and real Jinja template checks; no database or inference required."""
import importlib.util
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("blog_content_under_test", ROOT / "authentic_dynamics/blog.py")
blog_content = importlib.util.module_from_spec(spec)
spec.loader.exec_module(blog_content)
POSTS = blog_content.get_blog_posts()


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def find(self, tag, **attrs):
        return [a for t, a in self.tags if t == tag and all(a.get(k) == v for k, v in attrs.items())]


def url_for(endpoint, **values):
    if endpoint == "static":
        return "/static/" + values["filename"]
    if endpoint == "tools.ai_lab":
        return "/tools/ai-lab/" + values["slug"]
    if endpoint == "main.blog_post":
        return "/blog/" + values["slug"]
    return {
        "coding.index": "/coding-calendar/",
        "main.index": "/", "main.blog": "/blog", "main.websites": "/websites",
        "main.growth_technology": "/growth-technology", "main.work": "/work",
        "main.about_community": "/about-community", "main.privacy_policy": "/privacy-policy",
        "main.terms": "/terms",
    }[endpoint]


def render(name, post=None, canonical_host="www.example.org"):
    env = Environment(
        loader=FileSystemLoader(ROOT / "authentic_dynamics/templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    path = "/blog/" + post["slug"] if post else "/blog"
    return env.get_template(name).render(
        config={"CANONICAL_HOST": canonical_host}, request=SimpleNamespace(path=path),
        url_for=url_for, active_page="blog", posts=POSTS, post=post, related=POSTS[:3],
        canonical_url="https://www.example.org" + path,
        structured_data={"@context": "https://schema.org", "name": "Safe <test>"},
    )


def test_ten_unique_complete_articles():
    assert len(POSTS) == 10
    assert len({p["slug"] for p in POSTS}) == 10
    assert len({p["title"] for p in POSTS}) == 10
    assert len({p["description"] for p in POSTS}) == 10


@pytest.mark.parametrize("post", POSTS, ids=lambda p: p["slug"])
def test_content_is_complete_and_safe(post):
    body = post["body_html"]
    page = Page(body)
    assert len(re.sub(r"<[^>]+>", " ", body).split()) >= 500
    assert post["demo"] in body
    assert not any(tag in {"script", "iframe", "form", "h1"} for tag, _ in page.tags)
    assert all(not key.lower().startswith("on") for _, attrs in page.tags for key in attrs)
    assert post["reviewed"] <= post["published"] <= post["modified"]
    assert len(post["toc"]) >= 4
    for item in post["toc"]:
        assert len(page.find("h2", id=item["id"])) == 1
    for attrs in page.find("a"):
        assert attrs["href"].startswith("https://")
    assert page.find("a", href=post["model_url"])


@pytest.mark.parametrize("post", POSTS, ids=lambda p: p["slug"])
def test_article_template_metadata_and_navigation(post):
    html = render("blog/post.html", post)
    page = Page(html)
    assert len(page.find("h1")) == 1
    assert len(page.find("link", rel="canonical")) == 1
    assert page.find("link", rel="canonical")[0]["href"].endswith("/blog/" + post["slug"])
    assert page.find("meta", name="description")[0]["content"] == post["description"]
    assert page.find("meta", property="og:type")[0]["content"] == "article"
    assert len(page.find("a", href="/blog", **{"aria-current": "page"})) == 1
    assert "Browser tool live" in html
    assert f'data-tool="{post["slug"]}"' in html
    assert "noindex" not in html
    assert "Editorial preview only" not in html
    assert "../posts/" not in html and "READ_ALL_TEN_POSTS" not in html
    schema = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)[1]
    assert json.loads(schema)["name"] == "Safe <test>"
    assert "<test>" not in schema


def test_index_links_every_article_and_has_one_h1():
    html = render("blog/index.html")
    page = Page(html)
    assert len(page.find("h1")) == 1
    assert page.find("button", **{"aria-controls": "nav"})
    for post in POSTS:
        assert page.find("a", href="/blog/" + post["slug"])
    assert len(page.find("link", rel="canonical")) == 1


def test_fallback_canonical_has_no_duplicate():
    for post in (None, POSTS[0]):
        html = render("blog/post.html" if post else "blog/index.html", post, "")
        assert len(Page(html).find("link", rel="canonical")) == 1


@pytest.mark.parametrize("slug", ["missing", "../posts", "../../config", "", "AI-WEBSITE"])
def test_unknown_slug_never_reads_arbitrary_files(slug):
    assert blog_content.get_blog_post(slug) is None


def test_rejects_duplicate_slugs(tmp_path, monkeypatch):
    (tmp_path / "posts.json").write_text(json.dumps([POSTS[0], POSTS[0]]))
    (tmp_path / (POSTS[0]["slug"] + ".html")).write_text(POSTS[0]["body_html"])
    monkeypatch.setattr(blog_content, "CONTENT_DIR", tmp_path)
    blog_content.get_blog_posts.cache_clear()
    try:
        with pytest.raises(ValueError, match="duplicate"):
            blog_content.get_blog_posts()
    finally:
        blog_content.get_blog_posts.cache_clear()
