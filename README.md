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

### Admin inbox

Open `/admin` to sign in and review inquiries. The inbox supports search, new/reviewed filters, pagination, full message details, and marking inquiries reviewed. “Reply by email” opens your email app; the website does not send or track replies.

Admin accounts live in separate tables in the existing database, alongside inquiries. Passwords are stored as salted scrypt hashes. No default account or password is embedded in the app or migrations. For a fresh deployment, apply the migrations and create an account through the hidden password prompt:

```bash
myenv/bin/python -m flask --app wsgi db upgrade
myenv/bin/python -m flask --app wsgi admin create --email your-admin@example.com
```

Use **Change password** inside the admin area, or recover access from the server:

```bash
myenv/bin/python -m flask --app wsgi admin reset-password --email your-admin@example.com
```

Admin sessions expire after eight hours and are revoked on sign-out. A password change revokes other sessions; a command-line reset revokes all sessions. Login failures are limited in the database to five per server-observed IP address or ten per email in 15 minutes, across workers. Admin actions require CSRF tokens, and admin responses disable browser caching and search indexing. Use HTTPS with `AD_SESSION_COOKIE_SECURE=true` in production and keep a stable `AD_SECRET_KEY` across workers. Back up the private database before deployments; keep the database and `.secret_key` outside source control. Migrations and tests are included in source control.

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

## Deploy on PythonAnywhere

This app runs as a Flask WSGI application. Use the same Python version for the virtualenv and the web app; the project currently requires Python 3.11 or newer.

1. Create a PythonAnywhere account and open a Bash console. Upload the project with Git or the Files tab, then change into its directory:

   ```bash
   cd /home/YOUR_USERNAME/authentic-dynamics
   ```

2. Create a virtualenv and install the project. Replace `3.11` with the Python version selected for the web app if needed:

   ```bash
   python3.11 -m venv /home/YOUR_USERNAME/.virtualenvs/authentic-dynamics
   /home/YOUR_USERNAME/.virtualenvs/authentic-dynamics/bin/pip install -e '.[dev]'
   ```

3. Apply the database migrations. This creates the SQLite database under the app’s `instance/` directory:

   ```bash
   cd /home/YOUR_USERNAME/authentic-dynamics
   /home/YOUR_USERNAME/.virtualenvs/authentic-dynamics/bin/python -m flask --app wsgi db upgrade
   /home/YOUR_USERNAME/.virtualenvs/authentic-dynamics/bin/python -m flask --app wsgi admin create --email YOUR_ADMIN_EMAIL
   ```

   The admin command prompts for the password without displaying it. Do not put the admin password in Git, `example.env`, or a public file.

4. In the PythonAnywhere **Web** tab, choose **Add a new web app**, select **Manual configuration**, and choose the same Python version used for the virtualenv. In the **Virtualenv** field, enter:

   ```text
   /home/YOUR_USERNAME/.virtualenvs/authentic-dynamics
   ```

5. Open the WSGI configuration file linked near the top of the Web tab. Replace its Flask section with the following, changing the username and project path:

   ```python
   import os
   import sys

   project_home = "/home/YOUR_USERNAME/authentic-dynamics"
   if project_home not in sys.path:
       sys.path.insert(0, project_home)

   os.environ.setdefault("AD_SECRET_KEY", "PASTE_A_LONG_RANDOM_VALUE_HERE")
   os.environ.setdefault("AD_SESSION_COOKIE_SECURE", "true")

   from wsgi import app  # noqa: E402
   ```

   Use a different long random `AD_SECRET_KEY` for the deployment and keep it stable. You can set environment variables in the Web tab instead of the `os.environ.setdefault` lines. Set `AD_SQLALCHEMY_DATABASE_URI` to an absolute SQLite URI if you want the database outside the project, for example `sqlite:////home/YOUR_USERNAME/instance/authentic_dynamics.db`.

6. In the Web tab, add a static files mapping so PythonAnywhere serves the local CSS, JavaScript, fonts, and images efficiently:

   | URL | Directory |
   | --- | --- |
   | `/static/` | `/home/YOUR_USERNAME/authentic-dynamics/authentic_dynamics/static/` |

7. Click **Reload**. Visit your PythonAnywhere domain, then open `/admin/login` to review submissions. Test the contact form, static images, and `/healthz` after the reload.

For later releases, pull or upload the new code, install any dependency changes, run `flask --app wsgi db upgrade`, and reload the web app. Back up `instance/authentic_dynamics.db` before migrations. PythonAnywhere’s [Flask setup guide](https://help.pythonanywhere.com/pages/Flask), [static files guide](https://help.pythonanywhere.com/pages/StaticFiles), and [environment variable guidance](https://help.pythonanywhere.com/pages/environment-variables-for-web-apps/) cover the corresponding dashboard settings.
