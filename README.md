# Authentic Dynamics

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
myenv/bin/python -m pytest -q
myenv/bin/ruff check .
```
