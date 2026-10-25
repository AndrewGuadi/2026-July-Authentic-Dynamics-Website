# Finite daily Coding Calendar updates

Andrew authorized a 30-day program covering October 24–November 22, 2026 inclusive. The October 24 source batch is included in this change. A separate ChatGPT scheduled task covers 29 remaining mornings, starting October 25 at approximately 8 AM America/New_York, with RRULE COUNT=29. It is allowed to commit, merge, deploy and live-test **coding-calendar changes only**. The existing general Authentic Dynamics improvement task retains its separate manual-review rules.

## One batch

1. Read current main, open calendar PRs, repository instructions and `authentic_dynamics/content/coding/maintenance.json`.
2. Run `python scripts/coding_calendar_plan.py`. The script defaults to the actual New York date and prints a plan without writing anything. `--date YYYY-MM-DD` is available for a deliberate retry or a test. Do not use it to manufacture extra authorized batches.
3. If `already-recorded`, verify and finish deployment of the existing batch; never add six more dates for the same run date. If `closed`, do not expand. The program ends after 30 source batches or November 22, whichever comes first.
4. For `new-batch`, use the actual earliest/latest complete existing dates. Add exactly three immediately preceding dates and three immediately following dates. Each new date gets one JavaScript, one Python and one SQL lesson: **six dates, 18 lesson files per source batch**. Do not overwrite or redate an existing lesson.
5. Author substantive, varied content and trusted reference solutions. Review primary documentation. Each lesson has a method/premise, syntax, accurate explanation, inputs/returns/caution, official reference link, three real scenarios, a problem, a hint, a starter and at least three example/edge-case assertions. Use the existing topic slugs in `coding.CATEGORIES` and difficulty slugs in `coding.LEVELS`. Do not clone thin paraphrases just to fill dates.
6. Append the run date, three older dates, three forward dates and lesson_count=18 to `maintenance.json` alongside the new files. A batch record means the source was authored; it is not a claim that deployment succeeded. Keep the program start/end/limit intact. Do not exceed 30 distinct run dates. Update `tests/fixtures/coding/solutions.json` for every new lesson.
7. Test, commit on a fresh dated calendar branch, open a PR, inspect all checks, and merge verified changes. The daily program explicitly authorizes this calendar-only release without asking Andrew to approve it again.
8. Deploy the tested app files and live-test before calling the run complete. If a deployment fails, repair it or restore the saved original shared files; retain a precise partial status and blocker.

The initial source bounds were October 24–30. The first batch adds October 21–23 and October 31–November 2, yielding 39 lessons over 13 dates. The next unprocessed batch adds October 18–20 and November 3–5. Always derive subsequent bounds from the actual current files.

## User behavior to preserve

- An unqualified `/coding-calendar/` request always selects the actual date in America/New_York, even if that date has no lesson. Do not silently present another date as today's content.
- `?date=YYYY-MM-DD` is an intentional selection. Preserve it while browsing, including across midnight. Today removes the explicit date. No-store response headers prevent stale selected dates; a default index left open refreshes at a New York date change.
- Three language tabs use manual activation: Tab enters the tablist, arrows/Home/End move focus, Enter/Space select a panel, and Tab leaves to its content. There must be no keyboard trap in the editor.
- Previous/Next and the date picker retain the selected language. Each lesson also has adjacent published-date links and same-day language links.
- Upcoming dates show their topic and availability date on the calendar; their direct challenge pages stay 404 until publication. The archive contains published content only.
- Archive filters support topic, language, level and month, with 20 date groups per page and a useful empty state.
- Browser execution isolation, runtime integrity checks, drafts and local results stay intact. No API billing, server-side visitor-code execution, accounts or tracking is part of this program.

## Checks

```sh
python -m pip install -e '.[dev]'
pytest -q
python scripts/test_coding_browser.py
CODING_TEST_DATE=2026-10-24 CODING_BROWSER_SUITE=coding_calendar_navigation.cjs python scripts/test_coding_browser.py
```

Browser suites require Playwright and Chromium; see `coding-calendar.md` for installation and optional cache/executable variables. The first suite publishes seed content only inside its local test process and exercises real reference solutions in browser runtimes. The second freezes the server and browser to October 24 to verify stable date/keyboard fixtures. Its checks intentionally remain valid as older/newer source content is added. Run affected/new reference solutions and necessary regressions; retain cumulative coverage as the collection grows.

## Existing production target

- Account: `authenticdynamics`, API host `https://www.pythonanywhere.com/api/v0/user/authenticdynamics/`.
- Domain: `www.authenticdynamics.com`; Python 3.12.
- Project: `/home/authenticdynamics/2026-July-Authentic-Dynamics-Website`.
- Virtualenv: `/home/authenticdynamics/.virtualenvs/sep26ADenv`.
- Existing WSGI imports the project's `wsgi.app`; no WSGI change is needed.

Use the already authorized secure PythonAnywhere token, never a token in source or browser code. Prefer an existing configured deployment environment. For API file deployment, the documented endpoint is `files/path{absolute_path}`: POST multipart field `content` writes the file and creates missing parent directories, GET reads it back. Preserve any production changes that differ from the expected base. Back up existing changed app files before writing, then upload only relevant calendar code/content/assets, compare read-back SHA-256 hashes, and POST `webapps/www.authenticdynamics.com/reload/`. Respect the API's per-endpoint 40 requests/minute limit. Do not change databases, instance configuration, other hosted sites, account settings, or WSGI.

After reload verify the homepage, `/healthz`, tools link, calendar default, older date pages, upcoming date state, archive filters, keyboard tabs and affected editor controls at desktop and mobile sizes. Execute the new older lessons and current-day samples using actual JavaScript/Pyodide/SQLite in a browser; upcoming challenges remain tested locally until they publish. Verify the live sandbox CSP and that learner code is not uploaded. A merged commit alone is not deployment evidence.
