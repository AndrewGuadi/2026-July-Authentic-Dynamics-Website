"""Consistent SQLite snapshots plus immutable document generations and restore drills."""

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tarfile
from pathlib import Path

from flask import current_app

from authentic_dynamics.extensions import db
from authentic_dynamics.hub import models as m

from .storage import StorageService


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory / 'manifest.json').read_text())
    database = directory / 'database.sqlite3'
    if sha256(database) != manifest['db_sha256']:
        raise ValueError('Database checksum mismatch.')
    with sqlite3.connect(f'file:{database}?mode=ro', uri=True) as snapshot:
        if snapshot.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Database integrity check failed.')
        if snapshot.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Foreign-key integrity check failed.')
        revision = snapshot.execute('SELECT version_num FROM alembic_version').fetchone()[0]
        if revision != manifest['migration_revision']:
            raise ValueError('Migration revision mismatch.')
        rows = snapshot.execute('SELECT storage_key, sha256, size_bytes FROM hub_document_versions').fetchall()
        expected = {key: {'sha256': digest, 'size_bytes': size} for key, digest, size in rows}
        if expected != manifest['files']:
            raise ValueError('Manifest does not match database document versions.')
        # Representative reads fail if a core table cannot be accessed.
        for table in ('hub_businesses', 'hub_tasks', 'hub_contracts', 'hub_invoices'):
            snapshot.execute(f'SELECT id FROM {table} LIMIT 1').fetchall()
    storage = StorageService(directory / 'files')
    for key, data in manifest['files'].items():
        path = storage.path(key)
        if path.stat().st_size != data['size_bytes'] or sha256(path) != data['sha256']:
            raise ValueError('Document checksum mismatch.')
    return manifest


def offsite_upload(directory):
    """Encrypt with age; upload and fetch via rclone; compare encrypted bytes."""
    recipient = current_app.config['HUB_BACKUP_AGE_RECIPIENT']
    destination = current_app.config['HUB_BACKUP_DESTINATION']
    if not recipient or not destination or ':' not in destination or destination.startswith(('/', '-')):
        raise ValueError('Configure an age recipient and an independent rclone remote.')
    archive = directory / 'bundle.tar'
    encrypted = directory / 'bundle.tar.age'
    retrieved = directory / 'offsite-check.age'
    with tarfile.open(archive, 'w') as bundle:
        for name in ('database.sqlite3', 'manifest.json', 'files'):
            bundle.add(directory / name, arcname=name)
    os.chmod(archive, 0o600)
    try:
        subprocess.run(['age', '--recipient', recipient, '--output', str(encrypted), str(archive)],
                       check=True, timeout=300, capture_output=True)
        os.chmod(encrypted, 0o600)
        target = f'{destination.rstrip("/")}/{directory.name}.tar.age'
        for source, dest in ((str(encrypted), target), (target, str(retrieved))):
            subprocess.run(['rclone', 'copyto', source, dest, '--immutable'],
                           check=True, timeout=600, capture_output=True)
        if sha256(encrypted) != sha256(retrieved):
            raise ValueError('Offsite checksum verification failed.')
    finally:
        archive.unlink(missing_ok=True)
        retrieved.unlink(missing_ok=True)


def backup(workspace_id, upload_offsite=False):
    if db.engine.dialect.name != 'sqlite' or not db.engine.url.database:
        raise ValueError('This backup command requires a persistent SQLite database.')
    run = m.BackupRun(workspace_id=workspace_id)
    db.session.add(run)
    db.session.commit()
    directory = Path(current_app.config['HUB_BACKUP_STAGING_DIR']) / run.id
    directory.mkdir(parents=True, mode=0o700)
    try:
        target = directory / 'database.sqlite3'
        target.touch(mode=0o600)
        with sqlite3.connect(db.engine.url.database) as source, sqlite3.connect(target) as snapshot:
            source.backup(snapshot)
            revision = snapshot.execute('SELECT version_num FROM alembic_version').fetchone()[0]
            versions = snapshot.execute('SELECT storage_key, sha256, size_bytes FROM hub_document_versions').fetchall()
        files = directory / 'files'
        files.mkdir(mode=0o700)
        manifest = {'version': 1, 'snapshot_at': m.now().isoformat(),
                    'migration_revision': revision, 'db_sha256': sha256(target), 'files': {}}
        # Snapshot references only committed immutable versions; they are never deleted.
        # New uploads after the snapshot are intentionally outside this generation.
        storage = StorageService()
        for key, digest, size in versions:
            shutil.copyfile(storage.path(key), files / key)
            (files / key).chmod(0o600)
            manifest['files'][key] = {'sha256': digest, 'size_bytes': size}
        manifest_path = directory / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, sort_keys=True))
        manifest_path.chmod(0o600)
        verify(directory)
        run.manifest_key = run.id
        run.db_sha256 = manifest['db_sha256']
        run.file_manifest_sha256 = sha256(manifest_path)
        run.verified_at = m.now()
        run.status = 'local_verified'
        if upload_offsite:
            offsite_upload(directory)
            run.offsite_verified_at = m.now()
            run.status = 'protected'
    except Exception as error:
        run.status = 'failed'
        run.error_redacted = type(error).__name__
        current_app.logger.error('Hub backup %s failed (%s)', run.id, type(error).__name__)
        raise
    finally:
        run.finished_at = m.now()
        db.session.commit()
    return run


def restore_test(run, target):
    target = Path(target).resolve()
    private = Path(current_app.config['HUB_PRIVATE_DIR']).resolve()
    if target.exists() or target == private or target.is_relative_to(private):
        raise ValueError('Choose a new isolated directory outside live private storage.')
    directory = Path(current_app.config['HUB_BACKUP_STAGING_DIR']) / run.id
    try:
        if sha256(directory / 'manifest.json') != run.file_manifest_sha256:
            raise ValueError('Manifest checksum mismatch.')
        verify(directory)
        target.mkdir(parents=True, mode=0o700)
        for name in ('manifest.json', 'database.sqlite3'):
            shutil.copyfile(directory / name, target / name)
            (target / name).chmod(0o600)
        shutil.copytree(directory / 'files', target / 'files')
        verify(target)
        result = m.RestoreTest(workspace_id=run.workspace_id, backup_run_id=run.id,
                               outcome='passed', notes='Isolated database and document checks passed.')
    except Exception as error:
        result = m.RestoreTest(workspace_id=run.workspace_id, backup_run_id=run.id,
                               outcome='failed', notes=type(error).__name__)
        db.session.add(result)
        db.session.commit()
        raise
    db.session.add(result)
    db.session.commit()
    return result
