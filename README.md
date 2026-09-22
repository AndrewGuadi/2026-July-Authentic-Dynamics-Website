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

The `.env` file is ignored by Git. Leave `AD_SECRET_KEY` blank locally to use the generated `instance/.secret_key`; set a unique secret for deployment. Set `AD_SESSION_COOKIE_SECURE=true` when the site is served over HTTPS, and keep the admin site's same-origin referrer available for HTTPS CSRF validation.

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

## Browser games

`/games` (also `/games/`) is a separate catalog styled like the tools catalog.
It links to `/games/maze-chase`, an original Pac-Man-style maze game rendered with
Canvas 2D. The catalog and game are deliberately absent from site navigation,
footer links, and the sitemap for now; visit their URLs directly.

Maze Chase includes buffered arrow/WASD movement, touch direction buttons and
swipes, four ghosts with corridor pathfinding, dots and power pellets, capture
combos, three lives, and progressively faster levels. P or Space pauses while the
canvas has focus; the visible buttons also support pause/resume and restarting.
Tab hiding or window blur pauses automatically. All art is drawn locally with
canvas/CSS; there are no external assets, game APIs, or runtime dependencies.
Only the best score is saved under `ad-maze-chase-best` in localStorage; storage
failures fall back to the current visit. Clear best score removes the previous
record (an active run's score remains eligible). Game progress is not saved.
There are no new app configuration or environment variables.

Run simulation checks with `node tests/maze_core.mjs`. Optional Playwright checks:
`NODE_PATH=/path/to/node_modules node tests/maze_browser.cjs` against a running
Flask server (`GAMES_BASE_URL`, default `http://127.0.0.1:5055`). The browser test
covers play, keyboard/touch controls, pause/resume, restart, local storage failure,
catalog navigation, and viewport layout. Canvas gameplay is visual; instructions,
buttons, and game-state announcements are accessible, but this version does not
provide a nonvisual way to navigate the maze.

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

`/tools/json-converter` accepts a UTF-8 JSON upload (up to 10 MiB) or pasted text
(up to 400,000 UTF-8 bytes), and exports XLSX, DOCX, PDF, CSV, TSV, plain text or formatted JSON. Use one
input at a time. Table exports accept a single object or a nonempty array of objects;
keys become columns in first-seen order. Missing/null values become blank cells.
All spreadsheet cells are text; CSV/TSV formula-like values receive a protective
apostrophe. Word, PDF, CSV and TSV keep nested values as JSON in a single table.
Formatted JSON and plain text support any JSON value. Duplicate keys, nonfinite
numbers and invalid UTF-8 are rejected.

Excel offers four `nesting` modes: `keep` (nested values in cells), `flatten` (object
fields become dotted columns), `related` (arrays directly on each row become child
sheets, while objects stay in cells), and `combined` (flatten objects and separate
arrays, the default). `max_depth` is 1–10, default 5; a top-level field is level 1
and each object/array traversal adds a level. Containers beyond the limit stay as
JSON text and produce a preview warning. Keep mode ignores expansion depth.

Related sheets use generated `@record_id` and `@parent_id` columns; IDs are unique
within each sheet. The preview identifies each child sheet's parent and source
field. `@index` is the zero-based array position. Primitive and mixed arrays use
`@type` and `@value`; object items have ordinary field columns. Arrays inside array
items stay as JSON in `@value`. Empty arrays keep `[]` in the parent and generate
an empty child sheet; empty objects stay `{}` in cells. Nonempty expanded arrays
leave a count and sheet name in the parent cell. Independent arrays never multiply
each other's rows. Differently shaped objects share the union of columns.

Expanded layouts escape literal dots and backslashes in keys with a backslash,
escape leading `@` to avoid generated-column collisions, and use `\e` for empty
keys. Keep mode preserves original keys. Worksheet names are sanitized, shortened
to 31 characters and made unique case-insensitively. Each worksheet has a styled
header, frozen header row, text cells, wrapped content and a filter.

The preview button posts `action=preview` to the same CSRF-protected converter
route. It uses the same normalization and limits as the XLSX download, returning
sheet names, row counts, columns, parent relationships and warnings. With JavaScript,
input changes clear stale previews; without JavaScript, preview renders on the page
and an uploaded file must be selected again before download. Preview data is not saved.
Limits: 20 sheets, 50,000 data rows and 200,000 cells across the entire workbook
(including generated fields and headers), 100 columns per sheet, and 32,767
characters per cell. Other table formats retain the existing single-table limits.

Optional browser regression checks: with Playwright and Chromium installed, run
`NODE_PATH=/path/to/node_modules node tests/json_converter_browser.cjs` against the
app at `http://127.0.0.1:5055` (or set `JSON_BASE_URL` for the test runner). These
cover all four layouts, upload/text previews, downloads, stale responses, mobile
layout, and the no-JavaScript preview form.

PDF tables use ReportLab with an embedded, bundled DejaVu Sans font (license in
`static/fonts/DejaVu-LICENSE.txt`). Install updated dependencies with
`myenv/bin/python -m pip install -e '.[dev]'`. The previous raster-only table export
is replaced by selectable text. PDF settings offer automatic/portrait/landscape
A4 orientation, 10/11/12 pt text, column selection and ordering, and three long-cell
policies: full wrapping (default), a linked appendix for values over 1,000
characters, or explicitly marked shortening after 1,000 characters. Missing/null
values are blank; nested values remain JSON text. There is no Excel-style
32,767-character cap for PDF cells.

Automatic layout compares portrait/landscape and equal/content-weighted columns
without reducing font size. It prioritizes fewer row continuations, less wrapping,
then fewer pages. Headers repeat, normal rows move intact when possible, and rows
taller than a page continue with source row labels. Runtime checks verify exact
coverage of the prepared text, cell boundaries, overlap, and the 10 pt minimum.
Unsupported glyphs, control characters, and scripts needing shaping are displayed
as visible Unicode escape codes, with a warning in the preview and PDF footer.
Automatic shortening never occurs; user-selected shortening is visibly marked.

PDF limits are 12 selected columns, 5,000 rows, 2 million source/rendered characters,
200 pages and 10 MiB generated output. Wide tables may require fewer columns or
landscape. The column picker supports up to 100 source fields. Use Excel/JSON for
larger datasets. Values moved to the appendix remain complete.

With JavaScript, PDF preview posts `action=pdf_preview` to `/tools/json-converter`.
The response includes the generated PDF, a first-page image, and layout metadata.
The browser retains that PDF in memory, so downloads use exactly the reviewed bytes.
Input/settings changes invalidate the PDF and any outstanding preview request.
`POST /tools/json-converter/pdf-page` renders a requested page from that same PDF
blob, with CSRF, byte/page/dimension limits and `Cache-Control: no-store`. Page
images are rendered by PDFium, not approximated as HTML. No preview is persisted.
Without JavaScript, PDF preview returns the PDF inline for the browser's viewer.
PDFium rendering and ReportLab font use are each serialized within a worker.

`tests/test_pdf_tables.py` independently checks exported text and glyph bounds with
PDFium, including a 100,000-character value, URL wrapping, Unicode, sparse/nested
data, page boundaries, randomized fixtures, explicit shortening, limits and CSRF.
It also compares a reviewed raster reference in `tests/fixtures`.
`NODE_PATH=/path/to/node_modules node tests/json_pdf_browser.cjs` exercises the
browser preview and verifies byte-identical downloads, page navigation, column
selection/order, invalidation, uploads and mobile layout. It defaults to
`http://127.0.0.1:5056`; set `JSON_BASE_URL` to use another local test server.

Conversions run on the server using pypdfium2/PDFium, Pillow, ReportLab and openpyxl (installed
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

## Video Converter: browser or server

`GET /tools/video-converter` serves a public page, linked from the tool catalog.
Browser conversion is selected by default. Users can explicitly choose server
conversion and consent to uploading before `POST /tools/video-converter/convert`.
There is no database record, saved conversion history, or account requirement.
The separate `static/tools/video-converter` UI, conversion service, options/presets,
and module worker use self-hosted `@ffmpeg/core@0.12.10` (single-thread WebAssembly).
The engine loads only on Convert. MP4 uses H.264/AAC, WebM uses VP8/Opus; a separate
Extract audio operation produces MP3 or WAV. Common MP4/WebM/MOV inputs are supported
subject to their codecs. Only the first video and first audio tracks are retained;
subtitles and additional tracks are omitted. No HDR/color fidelity guarantees.

Presets cover compression, website-ready video, format changes, resizing, audio
removal, extraction and custom settings. Output settings include three quality
levels, original/1080p/720p/480p bounds and original/60/30/24 FPS. Portrait bounds
are swapped; resizing preserves aspect ratio and never upscales. Odd dimensions
are rounded down to even pixels for encoding. Explicit frame rates can duplicate
or drop frames. Compression savings are calculated from the finished Blob only.
The preview displays browser-detected dimensions/duration without guessing codecs.

Browser APIs: File and `File.arrayBuffer`, Blob, object URLs,
HTMLVideoElement metadata, drag/drop and module Web Workers with transferable
output buffers. WebCodecs availability is detected but no native conversion pipeline
is implemented. A future adapter can implement the same `convertVideo` boundary.
No File System Access permission is required; downloads use a standard link.

Privacy in browser mode: all file reads and media processing take place on the device.
No media requests occur in this mode. Neither mode adds analytics, telemetry or
persistent browser history/storage. Selection and mode changes never upload a file;
there is no automatic switch to server processing after a local error.
FFmpeg accepts only the `file` input protocol. Options are allowlisted and filenames
are displayed as text, never HTML or command arguments. Results/source object URLs
are revoked on replacement, clear and page exit. Cancel terminates the worker;
success/failure also terminates it, releasing its filesystem and WASM memory.
The worker unlinks temporary files on normal completion/failure. Each new job
loads a fresh engine using ordinary browser HTTP caching/revalidation.

Deployment: include the vendored JS and approximately 31 MB WASM file and serve
`.wasm` as `application/wasm`. See the engine's `ffmpeg/README.md` for provenance,
checksums and GPL license/source information. Server conversion uses the pinned
`imageio-ffmpeg==0.6.0` dependency, whose standard platform wheels include native
FFmpeg. Install updated project dependencies (`pip install -e .`) when deploying.
No Node runtime is required. Platforms without a bundled binary need native FFmpeg
on PATH or the library's `IMAGEIO_FFMPEG_EXE` override. Preserve the binary's
bundled license/source notices when redistributing it.
A route-specific CSP allows same-origin scripts/engine downloads, WASM compilation
and blob media; it blocks external connections, framing by other sites and form
submission. No global security headers or COOP/COEP isolation settings change.
Preserve this CSP if configuring a reverse proxy; the site’s other tools are unaffected.

Video limits are set in `example.env` and the local ignored `.env` file. Load `.env`
into the shell before running Flask, as described above. `AD_VIDEO_MAX_BYTES=134217728`
allows 128 MiB server input, `AD_VIDEO_MAX_SECONDS=180` allows three minutes of video,
and `AD_VIDEO_TIMEOUT_SECONDS=300` allows five minutes for native encoding. Browser
mode uses `AD_VIDEO_BROWSER_MAX_BYTES=67108864` (64 MiB) and
`AD_VIDEO_BROWSER_MAX_SECONDS=60`; it probes duration in the local WASM worker
and stops local encoding after 60 seconds. Videos with unreadable duration are
rejected in browser mode and can be tried in server mode with consent.
`AD_VIDEO_SERVER_ENABLED=true` keeps server conversion available.
Server output is capped at 128 MiB. The request limit is overridden only for this
endpoint, before CSRF parsing; the existing 16 MiB limit for other tools is unchanged.
The endpoint requires CSRF protection plus an explicit upload-consent header.
It receives a generic filename, allowlists options and media demuxers, disables
network input protocols/playlists, invokes FFmpeg without a shell, and discards
encoder logs. One encoder per WSGI process runs at a time (two codec threads);
busy requests fail instead of queuing. Limit WSGI worker counts accordingly.

Server input/intermediate files use private temporary directories removed on
success, error or encoding timeout. The result uses an anonymous temporary file
closed after delivery/disconnect. No public output URL or conversion database exists.
Abrupt host/process termination can leave temporary directories; configure host
temporary-directory cleanup. Browser Cancel aborts the upload/response, but an
already-running native job can continue until completion or its bounded timeout.
The UI states this limitation. Upload progress is measured; server processing uses
an indeterminate indicator rather than a fabricated percentage.

For production, allow the video request size (input limit plus 1 MiB multipart
overhead) at the reverse proxy, and allow enough WSGI/proxy request time for upload,
the encoding timeout, and download (for example Gunicorn `--timeout 420`). Check
PythonAnywhere account CPU/request limits before enabling large conversions.
Set `AD_VIDEO_SERVER_ENABLED=false` to disable server conversion while retaining
browser mode. Native encoding is often faster, but end-to-end speed is not guaranteed.

Memory/performance limitations in browser mode: input, virtual filesystem and output
must fit in browser memory. Files over 64 MiB or videos over one minute require server
mode; files above 1080p pixel count require explicit acknowledgement in browser mode.
Mobile browsers can exhaust memory earlier or suspend background tabs. Keep the
tab visible and device awake; Cancel remains available if progress stalls. Progress
is estimated and capped at 99% until output exists. Unsupported/corrupt media,
missing audio during extraction, engine load failures and worker errors show a
recoverable message. Engine preparation times out after two minutes with a retry
message; encoding has a 60-second limit after engine preparation. Preview codec
support can differ from conversion support. WebM output uses the tested VP8 encoder;
VP9 encoding is not offered in this iteration.

The native server inspects duration before conversion and rejects videos longer than
three minutes. It decodes tested HEVC/H.265 and ProRes MOV inputs. FFmpeg applies
display rotation metadata before resize, so portrait exports have upright pixels.
PQ and HLG HDR inputs use the bundled `zscale` and `tonemap` filters and become SDR
BT.709 H.264/VP8 output, with BT.709 color tags. This conversion does not preserve
HDR brightness or metadata. Dolby Vision dynamic metadata is not reproduced; colors
can differ from the iPhone display. Other codec/profile combinations depend on the
bundled FFmpeg build and may fail. The browser engine remains less capable for MOV.

Validation: `tests/test_video_converter.py` covers route rendering, GET-only behavior,
catalog discovery, scoped CSP and WASM serving. `tests/video_converter_browser.cjs`
generates synthetic media using native FFmpeg, drives actual in-browser conversions,
downloads and independently decodes the results. It checks MP4/WebM/MOV inputs,
audio/no audio, portrait/landscape, 720p/1080p, compression, resize, extraction,
cancel/retry, consecutive conversions, corrupt/unsupported files, large-file warning
and mobile layout. It monitors browser network requests throughout, asserting
same-origin GET-only traffic, no request bodies and no source filenames in URLs.

Run a local app on port 5056, install test-only `playwright@1.58.2` and
`ffmpeg-static@5.3.0` in a temporary directory, then run:

```sh
NODE_PATH=/path/to/node_modules node tests/video_converter_browser.cjs
```

Set `VIDEO_BASE_URL` to change the origin, `VIDEO_BROWSERS=chromium,firefox,webkit`
to choose engines, or `FFMPEG_BINARY` to use an existing native FFmpeg executable.
These testing dependencies are not used by Flask or shipped to browsers.

`tests/test_video_backend.py` tests actual native MP4/WebM/MP3/WAV output, HEVC SDR/HDR
and ProRes MOV inputs, display rotation, duration enforcement, consent, CSRF, input
limits, disabled mode, corrupt files, timeout cleanup and concurrency.
`tests/video_modes_browser.cjs` checks actual browser/server conversions, explicit
consent, mode switching, no upload on selection, and no uploads in browser mode.
It uses `VIDEO_BASE_URL` (default port 5057) with the same test-only Node dependencies.
