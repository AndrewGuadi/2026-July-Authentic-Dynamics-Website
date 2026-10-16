"""Private path and SQLite connection setup without changing the existing DB URL."""

import sqlite3
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine


@event.listens_for(Engine, 'connect')
def sqlite_settings(connection, record):
    if isinstance(connection, sqlite3.Connection):
        cursor = connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.execute('PRAGMA busy_timeout=5000')
        cursor.close()


def configure(app):
    private = Path(app.config['HUB_PRIVATE_DIR'] or Path(app.instance_path) / 'hub').resolve()
    static = Path(app.static_folder).resolve()
    repository = Path(app.root_path).parent.resolve()
    instance = Path(app.instance_path).resolve()
    for setting, default in (
        ('HUB_PRIVATE_DIR', private), ('HUB_UPLOAD_DIR', private / 'uploads'),
        ('HUB_BACKUP_STAGING_DIR', private / 'backup_staging'),
    ):
        supplied = app.config[setting]
        if supplied and not Path(supplied).is_absolute():
            raise ValueError(f'{setting} must be an absolute private path.')
        path = Path(supplied or default).resolve()
        if path == static or path.is_relative_to(static):
            raise ValueError('Hub private storage cannot be inside static.')
        if path.is_relative_to(repository) and not path.is_relative_to(instance):
            raise ValueError('Private storage inside this repository must be under instance/.')
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        app.config[setting] = str(path)
