"""Reviewed, repository-owned blog content; no model/API calls on page requests."""
import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent / "content" / "blog"


@lru_cache(maxsize=1)
def get_blog_posts():
    """Load the published catalog once per worker, validating safe article paths."""
    posts = json.loads((CONTENT_DIR / "posts.json").read_text(encoding="utf-8"))
    seen = set()
    for post in posts:
        slug = post["slug"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or slug in seen:
            raise ValueError(f"Invalid or duplicate blog slug: {slug!r}")
        seen.add(slug)
        for key in ("published", "modified", "reviewed"):
            date.fromisoformat(post[key])
        post["body_html"] = (CONTENT_DIR / f"{slug}.html").read_text(encoding="utf-8")
    return tuple(posts)


def get_blog_post(slug):
    """Unknown slugs never become filesystem paths."""
    return next((post for post in get_blog_posts() if post["slug"] == slug), None)
