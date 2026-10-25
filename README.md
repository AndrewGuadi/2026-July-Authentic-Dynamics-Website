# Authentic Dynamics

Flask and Jinja website, public business tools, and a private Business Hub.

## Repository map

| Location | Purpose |
| --- | --- |
| `authentic_dynamics/blueprints/main/` | Business pages, contact handling, robots and sitemap routes |
| `authentic_dynamics/blueprints/tools/` | Public tools and conversion endpoints |
| `authentic_dynamics/blueprints/admin/` | Contact inbox and administrator access |
| `authentic_dynamics/blueprints/hub/` | Private Business Hub routes |
| `authentic_dynamics/hub/`, `services/hub/` | Hub models, commands and services (both under `authentic_dynamics/`) |
| `authentic_dynamics/templates/` | Jinja pages and shared partials |
| `authentic_dynamics/static/` | CSS, JavaScript, images and vendored browser dependencies |
| `migrations/` | Versioned database migration history |
| `tests/` | Python checks and browser test scripts |

## Local development

Use Python 3.11 or newer. From the repository root on macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
flask --app wsgi db upgrade
flask --app wsgi run --debug
```

The development server is available at `http://127.0.0.1:5000`.
Review `example.env` for supported settings; the application reads `AD_`
environment variables and `instance/config.py`. Copying the example alone does
not configure your shell. Keep local credentials and databases in ignored files.
Use the deployment instructions below for production; the debug server is local only.

## Change workflow

Start each change from current `main` on a fresh dated branch, run checks relevant
to the change, and open a pull request for Andrew's review. Review pending PRs
before editing shared files. Merge and deployment are separate approval steps.
Keep local planning material in `dev_docs/`, which is ignored. Preserve vendored
licenses and database migrations when cleaning up the repository.

The proposed visual update is documented in [UPDATE-PROPOSAL.md](UPDATE-PROPOSAL.md).

## Database migrations and deployment

The `migrations/` directory is part of the repository. It contains the complete
migration history for the website and Business Hub. Run commands from the project
root with the application's virtual environment activated.

On PythonAnywhere, after pulling the application and its migrations, run:

```bash
flask --app wsgi db upgrade
```

This creates all tables in an empty database, or applies pending migrations to a
database using this migration history. Do not run `flask db init`: the repository
already contains an initialized migration directory. Do not generate migrations
on the server.

### One-time PythonAnywhere reset after conflicting migrations

Pulling does not remove untracked migrations previously generated on the server.
Those extra files cause "Multiple head revisions" even after deleting the database.
The reset below discards all data, uploads, and local configuration in `instance/`,
plus local changes and extra files in `migrations/`. Use it only when intentionally
starting over with the default SQLite database, as in this deployment reset.
If a database URL is configured, deleting `instance/` does not reset that external
database. Preserve any configuration you still need before deleting the folder.

In the activated PythonAnywhere virtual environment, run these commands from the
project root. Stop if any command fails:

```bash
cd ~/2026-July-Authentic-Dynamics-Website
git pull --ff-only
bash scripts/restore_migrations.sh
rm -rf -- instance
flask --app wsgi db heads
flask --app wsgi db upgrade
flask --app wsgi db check
```

`db heads` should show exactly one head (`hub_0004` for this release). The restore
script replaces migration files with the checked-out commit's versions and removes
extra migration files, including ignored files. It does not change the database.
Flask automatically recreates `instance/`; do not run `mkdir instance`, `db init`,
`db migrate`, or `db stamp head` during this reset. Reload the PythonAnywhere web app
after the upgrade succeeds.

If `git pull` reports local changes or untracked files specifically under
`migrations/`, move that folder outside the checkout, restore the tracked copy with
`git restore --source=HEAD --worktree -- migrations/`, then retry the pull and reset.

During development, after changing models, generate and review a migration:

```bash
flask --app wsgi db migrate -m "Describe the schema change"
flask --app wsgi db upgrade
flask --app wsgi db check
```

Commit migration files with their corresponding model changes. The migration
environment renders the Hub's `UTCDateTime` as `sa.DateTime()`, matching its stored
SQL type without requiring imports of application types in generated revisions.

## Configuration

Application settings can be supplied in `instance/config.py` or with the `AD_`
environment prefix. For example, `AD_SQLALCHEMY_DATABASE_URI` selects the database
and `AD_SECRET_KEY` supplies a stable session key. Ensure the PythonAnywhere web
app and migration console use the same database configuration. Keep credentials
and the `instance/` directory out of version control.

## Checks

```bash
python -m pytest -q
ruff check .
```

Run these commands with your development environment activated. Browser scripts
under `tests/` describe their own runtime requirements; Python checks alone do not
verify mobile layout or browser interactions.

## Coding Calendar

`/coding-calendar/` adds daily JavaScript, Python and SQL learning pages with official references, practical scenarios, and code that runs in an isolated browser workspace. The calendar includes dated, categorized lesson files, actual-date defaults, keyboard language tabs, and date/archive navigation. A finite 30-day content expansion adds three earlier and three later dates per batch across all three tracks. See [the authoring, isolation, testing and deployment guide](docs/coding-calendar.md).
