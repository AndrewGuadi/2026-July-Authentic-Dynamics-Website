# Authentic Dynamics website

Flask application for the Authentic Dynamics website. The main pages are `/`, `/websites`, `/growth-technology`, `/work`, and `/about-community`.

## Run locally

Requires Python 3.11 or newer.

```bash
python3 -m venv myenv
myenv/bin/python -m pip install -e '.[dev]'
myenv/bin/python -m flask --app wsgi run --debug
```

Open <http://127.0.0.1:5000/>. On Windows, use `myenv\Scripts\python` in place of `myenv/bin/python`.

The page includes external placeholder photos. Those images require an internet connection; the page, stylesheet, script, and fonts are served locally.

## Verify changes

```bash
myenv/bin/python -m pytest -q
myenv/bin/ruff check .
node --check authentic_dynamics/static/js/home.js
node --check authentic_dynamics/static/js/site.js
```

The JavaScript syntax check requires Node.js. For a production server, run `myenv/bin/gunicorn wsgi:app`.

The `/healthz` route returns a liveness response.
