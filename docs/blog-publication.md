# AI blog publication — 2026-10-21

This release integrates all ten previously prepared model-investigation articles into the Flask website. Article wording and source links are retained; the reading-copy wrapper is replaced by the shared site layout.

## Public routes

- `/blog`: server-rendered directory of all ten articles.
- `/blog/<slug>`: complete article, source links, planned-demo notice, related reading and service links.
- Trailing-slash requests redirect to canonical paths; unknown slugs return 404.
- The shared desktop/mobile header and footer link to Blog.
- `/sitemap.xml` includes the directory and all ten articles. Existing utility exclusions are unchanged.

## Content and security

Content lives in `authentic_dynamics/content/blog/`: one JSON catalog and ten reviewed HTML fragments. The catalog is cached once per worker; reload workers after editing. Only version-controlled HTML is rendered as trusted markup. Never connect unreviewed user-supplied HTML to this rendering path. Slugs are allowlisted through the catalog and unknown URLs cannot become filesystem paths.

The posts are research-based guides, not completed model benchmark reports. Proposed interactive tools are not deployed in this release, and no inference APIs, uploads, new subscriptions, or paid compute are enabled. Existing license restrictions and disclosure language remain visible. Local keyword volumes and customer-acquisition results are not fabricated.

## Validation

Executed in the authoring environment: `python -m pytest -q tests/test_blog_content.py` — 29 passed. This exercises the actual catalog and Jinja templates, completeness, safe content, headings, canonical/description/social metadata, shared navigation links, source links, JSON escaping, and missing/duplicate slugs.

Full Flask integration tests were added in `tests/test_blog.py` and the sitemap regression expectations updated in `tests/test_sitemap.py`. The complete Flask suite was not executable in the authoring environment: Flask and its extension dependencies were unavailable and installation/network access was blocked. Do not report those integration tests as passed until run in the application environment.

## Deployment

No new runtime dependency or database migration is introduced. In the existing application virtual environment and repository checkout:

```bash
git pull --ff-only origin main
python -m pytest -q tests/test_blog_content.py tests/test_blog.py tests/test_sitemap.py
```

Then run the site's normal regression checks and reload the PythonAnywhere web application. Do not reset the database or run the destructive reset instructions from unrelated migration documentation for this blog release. Verify `/blog`, one article, the desktop navigation, the mobile Menu, and `/sitemap.xml` on the production domain after reload. A GitHub commit alone does not establish that production has reloaded.
