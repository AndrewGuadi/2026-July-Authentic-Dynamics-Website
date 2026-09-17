# Authentic Dynamics website

Flask application for the Authentic Dynamics website. The main pages are `/`, `/websites`, `/growth-technology`, `/work`, and `/about-community`.

## Run locally

Requires Python 3.11 or newer.

```bash
python3 -m venv myenv
myenv/bin/python -m pip install -e '.[dev]'
myenv/bin/python -m flask --app wsgi db upgrade
myenv/bin/python -m flask --app wsgi run --debug
```

Open <http://127.0.0.1:5000/>. On Windows, use `myenv\Scripts\python` in place of `myenv/bin/python`.

## Configuration

[`example.env`](example.env) lists the supported `AD_` settings and safe local defaults. The app reads environment variables; it does not load `.env` files by itself. To use a local file on macOS or Linux, copy and edit the example, then load it in the same shell before running Flask:

```bash
cp example.env .env
set -a
. ./.env
set +a
```

The `.env` file is ignored by Git. Leave `AD_SECRET_KEY` blank locally to use the generated `instance/.secret_key`; set a unique secret for deployment. Set `AD_SESSION_COOKIE_SECURE=true` when the site is served over HTTPS.

Home page images, styles, scripts, and fonts are served locally. The free tool cards use styled previews built in HTML and CSS.

Place local images in `authentic_dynamics/static/images/`, organized by page. The existing folders are `home/hero/`, `home/built-around-you/`, `home/what-we-do/`, `home/selected-work/`, `home/an-asset/`, `home/a-little-help/`, `home/rooted-here/`, `home/no-mystery-in-the-middle/`, `home/your-partner/`, `websites/`, `growth-technology/`, `work/`, and `about-community/`. The contact photos are currently in `static/images/`. Use `shared/` for images shown on more than one page. Add new folders within a page as its image collection grows. For example, a home hero image is referenced in a Flask template with `{{ url_for('static', filename='images/home/hero/your-photo.jpg') }}` and served at `/static/images/home/hero/your-photo.jpg`.

## Contact inquiries and database

The Home and About & Community contact forms validate submissions and save them to `instance/authentic_dynamics.db`, a local SQLite file ignored by Git. The free planning tools still run entirely in the browser. Contact submissions are stored locally; the app does not send email notifications.

Review inquiries from the command line:

```bash
myenv/bin/python -m flask --app wsgi contacts list
myenv/bin/python -m flask --app wsgi contacts show 1
```

Flask-Migrate tracks schema changes in `migrations/`. After changing a model, run `myenv/bin/python -m flask --app wsgi db migrate -m "Describe change"`, review the generated revision, then run `myenv/bin/python -m flask --app wsgi db upgrade`.

For local use, the app creates an untracked `instance/.secret_key` for form protection. The database path can be overridden with `AD_SQLALCHEMY_DATABASE_URI`.

## Verify changes

```bash
myenv/bin/python -m pytest -q
myenv/bin/ruff check .
node --check authentic_dynamics/static/js/home.js
node --check authentic_dynamics/static/js/site.js
```

The JavaScript syntax check requires Node.js. For a production server, run `myenv/bin/gunicorn wsgi:app`.

The `/healthz` route returns a liveness response.
