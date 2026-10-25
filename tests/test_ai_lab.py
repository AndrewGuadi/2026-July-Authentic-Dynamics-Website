"""End-to-end Flask route and static-contract checks for all ten free AI Labs."""
import shutil
import subprocess
from pathlib import Path

import pytest

from authentic_dynamics import create_app
from authentic_dynamics.blog import get_blog_posts

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "authentic_dynamics/static/js/ai-lab.js"


@pytest.fixture()
def client():
    return create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"}).test_client()


def test_labs_link_from_blog_index_and_each_article(client):
    index = client.get("/blog")
    assert index.status_code == 200
    for post in get_blog_posts():
        path = "/tools/ai-lab/" + post["slug"]
        assert path in index.get_data(as_text=True)
        article = client.get("/blog/" + post["slug"])
        assert article.status_code == 200
        assert path in article.get_data(as_text=True)
        assert f'data-tool="{post["slug"]}"' in article.get_data(as_text=True)


@pytest.mark.parametrize("post", get_blog_posts(), ids=lambda p: p["slug"])
def test_every_lab_is_live_safe_and_visibly_not_model_inference(client, post):
    response = client.get("/tools/ai-lab/" + post["slug"])
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    html = response.get_data(as_text=True)
    assert html.count("<h1>") == 1
    assert post["demo"] in html
    assert f'data-tool="{post["slug"]}"' in html
    assert "not connected" in html.lower() or "not running" in html.lower()
    assert '<meta name="robots" content="noindex,follow">' in html
    assert '/static/js/ai-lab.js' in html
    assert '/static/css/ai-lab.css' in html
    assert client.get("/static/js/ai-lab.js").status_code == 200


def test_missing_labs_never_receive_dynamic_files(client):
    assert client.get("/tools/ai-lab/unknown").status_code == 404
    assert client.get("/tools/ai-lab/..%2f..%2fconfig.py").status_code in {400, 404}


def test_ten_tools_are_backed_by_real_browser_functions():
    script = SCRIPT.read_text(encoding="utf-8")
    for post in get_blog_posts():
        assert f"'{post['slug']}':" in script
    for name in ("homepage", "menu", "voicemail", "voice", "graphic", "video",
                 "docs", "hardware", "forecast", "cutout"):
        assert f"function {name}(root)" in script
    # No third-party browser SDKs, secret tokens, or backend upload calls.
    assert "fetch(" not in script
    assert "XMLHttpRequest" not in script
    assert "api_key" not in script.lower()
    assert "LocalStorage" not in script
    assert "createObjectURL" in script
    assert "canvas" in script


def test_javascript_parses_when_node_available():
    if not shutil.which("node"):
        pytest.skip("Node is optional in the Python-only deployment environment")
    result = subprocess.run(["node", "--check", str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_page_discovery_has_no_duplicated_indexable_tool_variants(client):
    sitemap = client.get("/sitemap.xml").get_data(as_text=True)
    assert "/blog" in sitemap
    assert "/tools/ai-lab" not in sitemap
