"""Guard against the Safari focus/touch regression without a browser dependency."""
from pathlib import Path

from authentic_dynamics import create_app


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "authentic_dynamics/static/js/site.js").read_text()


def test_touch_safe_navigation_event_handlers():
    assert SCRIPT.count("menuButton.addEventListener('click'") == 1
    assert "navigation.addEventListener('focusout'" not in SCRIPT
    assert "window.setTimeout(closeMenu, 0)" in SCRIPT
    assert "event.detail === 0" in SCRIPT


def test_mobile_nav_includes_tappable_links_and_cache_busted_script():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    html = app.test_client().get("/").get_data(as_text=True)
    assert 'aria-controls="nav"' in html
    assert 'aria-expanded="false"' in html
    assert 'href="/websites"' in html
    assert 'href="/blog"' in html
    assert "ios-nav-20261021" in html
