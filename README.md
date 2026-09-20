# Authentic Dynamics website

Flask application for the Authentic Dynamics website. The main pages are `/`, `/websites`, `/growth-technology`, `/work`, and `/about-community`. The public pages, including the tools, are listed at `/sitemap.xml`.

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
node --check authentic_dynamics/static/js/tools.js
node --check authentic_dynamics/static/js/local-ai.js
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

## Browser X-Ray

`/browser-xray` is a public, browser-native educational lab for browser capabilities,
motion/orientation, acceleration, location, camera, microphone and screen sharing.
Every sensitive experiment has a permission explanation and an explicit Continue
button. Sensor readings stay in page memory; Stop, Reset, hiding the tab or leaving
the page cleans up active resources. Browser permission grants themselves may remain.
No new runtime dependencies or server-side sensor endpoints are required.

See [Browser X-Ray developer documentation](docs/browser-xray.md) for its API and
privacy table, lifecycle design, known browser limitations, regression tests and
physical-device HTTPS testing checklist.

## File conversion tools

### Browser QR code maker

`/tools/qr-code-maker` creates static QR codes and branded signs entirely in the
browser. It is linked in `/tools` and `/sitemap.xml`. URLs, logos, and artwork stay
in tab memory: no uploads, local storage, redirect service, or scan analytics.
Refreshing the page discards the design. The code has no expiration, but the
destination (including any third-party redirect) must remain available. Only the
explicit Test this link action visits the entered URL.

Review, website, menu, social, and custom-link presets accept HTTP(S) URLs up to
1,800 encoded bytes. Credentials and control characters are rejected. QR colors
require a light background and at least 4.5:1 contrast; exports preserve at least
four quiet-zone modules and render whole-pixel modules. Error correction is M or H.
PNG downloads support 512, 1024, or 2048 pixels; SVG downloads remain scalable.
Optional PNG/JPEG/WebP logos (5 MiB, 20 megapixels maximum) are resized locally and
placed outside the QR pattern. Artwork includes counter (5×7 inch), window (Letter),
insert (4×6 inch), square social, and plain-code layouts. Artwork PNG and US Letter
PDF exports share the canvas rendering. Smaller artwork is centered at its stated
size on Letter paper; browser printing requires Actual size / 100% for sizing.
PDF embeds raster artwork at 300 DPI, using the existing local jsPDF dependency.
Scan a downloaded/printed sample before printing in quantity.

The MIT-licensed `qrcode-generator` 2.0.4 ES module by Kazuhiko Arase is vendored
unchanged at `static/vendor/qr/qrcode-2.0.4.mjs`; attribution and license are beside
it. Encoding uses browser TextEncoder; URL serialization makes international URL
components safe for the QR byte payload. Runtime assets are served locally, and
there are no new environment variables or Python runtime dependencies.

Optional browser regression: install `playwright` and `jsqr` in a temporary npm
prefix, then run `NODE_PATH=/path/to/node_modules node tests/qr_code_browser.cjs`
against a running Flask server (`QR_BASE_URL`, default `http://127.0.0.1:5055`).
The checks independently decode exports, check invalid inputs and all layouts,
exercise PDF/print/logo flows, and verify generation makes no destination requests.

### Experimental browser AI

`GET /tools/local-ai` renders a public test page in the existing tools blueprint.
It uses `SmolLM2-360M-Instruct-q4f16_1-MLC` through the version-pinned WebLLM
`0.2.85` browser module. The runtime and model load only after **Load Local AI**
is clicked and WebGPU, a compatible adapter, and `shader-f16` support are checked.
Use HTTPS in production (localhost is suitable for development). The first load
can download hundreds of megabytes; model assets may remain in browser cache.

The prompt flows from the textarea into a JavaScript variable, directly into
`engine.chat.completions.create`, then streamed output is rendered with
`textContent`. There is no prompt form, upload, AI API route, server inference,
prompt persistence, analytics, or remote error reporting on this page. Each
request contains only the current question and a fixed system message. Input is
limited to 4,000 characters and output to 300 tokens; unusual text can still
exceed the model's token window. Generation errors log only their type so runtime
exception payloads cannot accidentally print a prompt in the browser console.

No Python dependencies, app configuration, environment variables or security
headers changed. The application currently does not set a Content Security Policy.
The new third-party JavaScript import is
`https://esm.run/@mlc-ai/web-llm@0.2.85`, which redirects to
`https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm@0.2.85/+esm`. WebLLM downloads model
assets from Hugging Face (including its download redirects) and the model WASM
library from GitHub over HTTPS. These hosts receive resource requests, not the
prompt. This experiment trusts the externally served runtime and model artifacts.
If a deployment proxy adds a CSP, inspect its blocked-resource reports and allow
only the required origins and WebAssembly compilation on this route; do not
disable the policy or introduce wildcard sources. No CSP allowlist was added here.
PythonAnywhere only serves the existing Flask page and static assets; no model,
worker, GPU or inference service is required on the server.

After deployment:

1. Visit `/tools/local-ai` over HTTPS in a WebGPU browser and open developer tools.
2. Check Network: no WebLLM/model downloads should occur before clicking Load.
3. Click **Load Local AI** and observe status/progress until **AI ready**.
4. Clear the Network log, enter `This is a private test phrase 938472`, and click **Ask AI**.
5. Verify the response streams, then inspect all new request URLs and bodies:
   the phrase must not be sent to Flask or any external API. Repeat while offline
   after the model has loaded to further check local generation.
6. Check unsupported-device messages and the layout at phone/tablet widths.

`tests/local_ai_browser.cjs` provides optional Playwright regression checks against
a running Flask server (`LOCAL_AI_BASE_URL`, default `http://127.0.0.1:5055`). It
simulates GPU compatibility and the engine to check UI states, input limits,
safe streamed output, failure recovery and zero network requests during generation.
Run `node tests/local_ai_browser.cjs` with Playwright installed in your development
environment (or supplied through `NODE_PATH`). These simulated checks do **not**
validate real model inference or the real runtime's network behavior; complete the
deployment procedure above on a compatible GPU. The API follows the
[WebLLM basic usage documentation](https://webllm.mlc.ai/docs/user/basic_usage.html).

### Server-side file conversions

The catalog is available directly at `/tools`; it is intentionally absent from the site navigation.
`/tools/pdf-to-image` converts PDFs to PNG, WebP or JPEG at 72, 150 or 300 DPI. A single
page downloads as an image; multiple pages download as a ZIP. Password-protected PDFs
must be unlocked before upload. Limits: 10 MiB input, 40 pages, 20 million pixels per
page, 80 million pixels total, 16,000 pixels per side, and 100 MiB generated image data.

`/tools/csv-converter` accepts UTF-8 CSV (including BOM) and exports XLSX, JSON, XML or
TSV. Users choose comma, semicolon, tab or pipe delimiters and whether the first row
contains headers. Headers must be unique and nonempty; headerless files receive
`column_1`, `column_2`, etc. Values remain strings, including leading zeros. XLSX cells
are explicitly text; TSV formula-like values are prefixed with an apostrophe. JSON is
an array of row objects; XML uses `<rows><row><field name="header">value</field></row></rows>`.
Blank lines are skipped; inconsistent row widths are rejected. Limits: 10 MiB input,
50,000 data rows, 100 columns, 200,000 total cells, and 32,767 characters per cell.

Conversions run on the server using pypdfium2/PDFium, Pillow and openpyxl (installed
with the project dependencies). The app does not persist uploads or results to its
database or a public directory. Flask may spool multipart uploads to temporary files
for the duration of a request. Download responses use `Cache-Control: no-store`.
Forms require CSRF protection and work without JavaScript; JavaScript adds inline
progress, errors and a repeat-download link.

`AD_MAX_CONTENT_LENGTH` defaults to 16777216 (16 MiB) to accommodate a 10 MiB file
plus multipart overhead. Update older deployments using the previous 1 MiB setting,
and configure any reverse proxy upload limit accordingly. Conversion limits are fixed
in the converter module. PDFium access is serialized within each worker. For a public
high-traffic deployment, provision worker capacity and proxy request throttling for
these synchronous conversion endpoints.
