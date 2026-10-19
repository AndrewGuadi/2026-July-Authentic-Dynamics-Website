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

For the server reset following the failed, independently generated migrations,
replace the server's old migration directory with this repository's directory and
start with an empty database. A failed SQLite upgrade can leave tables behind.
The default database file is `instance/authentic_dynamics.db`; if a database URL is
configured, use the database selected by that setting. Do not use `stamp head` to
skip creating missing tables. Resetting a database deletes its existing data.

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
