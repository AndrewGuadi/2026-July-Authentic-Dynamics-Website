"""Explicit enrollment and scheduled operations for the private Hub."""

from datetime import timedelta
from pathlib import Path

import click
from flask import current_app
from flask.cli import with_appcontext

from authentic_dynamics.extensions import db
from authentic_dynamics.hub import models as m
from authentic_dynamics.models import AdminUser
from authentic_dynamics.services.hub import backup as recovery
from authentic_dynamics.services.hub import core, jobs


@click.group('hub')
def hub():
    """Set up and operate the internal Business Hub."""


def workspace():
    record = db.session.scalar(db.select(m.Workspace).order_by(m.Workspace.created_at))
    if not record:
        raise click.ClickException('Run hub init first.')
    return record


@hub.command('init')
@click.option('--email', help='Existing admin email; optional only when exactly one admin exists.')
@click.option('--role', type=click.Choice(['owner', 'admin', 'staff', 'read_only']), default='owner')
@with_appcontext
def initialize(email, role):
    query = db.select(AdminUser)
    if email:
        query = query.where(AdminUser.email == email.strip().lower())
    users = db.session.scalars(query).all()
    if len(users) != 1:
        raise click.ClickException('Specify --email for one existing admin account.')
    with core.write_lock():
        company, user = core.seed(users[0], role)
        core.audit(company.id, user.id, 'membership_initialized', user)
        db.session.commit()
    if db.engine.dialect.name == 'sqlite':
        db.session.remove()
        with db.engine.connect().execution_options(isolation_level='AUTOCOMMIT') as connection:
            connection.exec_driver_sql('PRAGMA journal_mode=WAL')
    click.echo('Hub access enabled for the selected existing login. Open /hub.')


@hub.command('run-jobs')
@click.option('--max-jobs', type=click.IntRange(1, 1000), default=20)
@with_appcontext
def run_jobs(max_jobs):
    try:
        click.echo(f'Completed {jobs.run_jobs(max_jobs)} jobs.')
    except ValueError as error:
        raise click.ClickException(str(error)) from error


@hub.command('check-renewals')
@with_appcontext
def check_renewals():
    with core.write_lock():
        job = jobs.enqueue(workspace().id, 'renewal_digest', f'renewals:{m.now().date()}')
        db.session.commit()
    click.echo(f'Renewal digest queued: {job.id}')


@hub.command('backup')
@click.option('--verify', is_flag=True, help='Verification always runs; accepted for scheduler clarity.')
@click.option('--upload-offsite', is_flag=True)
@with_appcontext
def backup(verify, upload_offsite):
    try:
        result = recovery.backup(workspace().id, upload_offsite)
        click.echo(f'{result.id}: {result.status}')
    except Exception as error:
        raise click.ClickException(f'Backup failed ({type(error).__name__}); inspect operations history.') from error


@hub.command('verify-backups')
@with_appcontext
def verify_backups():
    run = db.session.scalar(db.select(m.BackupRun).where(
        m.BackupRun.workspace_id == workspace().id).order_by(m.BackupRun.started_at.desc()))
    if not run or run.status not in {'local_verified', 'protected'}:
        raise click.ClickException('ALERT: no successful latest backup.')
    try:
        directory = Path(current_app.config['HUB_BACKUP_STAGING_DIR']) / run.id
        if recovery.sha256(directory / 'manifest.json') != run.file_manifest_sha256:
            raise ValueError('Manifest mismatch.')
        recovery.verify(directory)
    except Exception as error:
        run.status = 'failed'
        run.error_redacted = type(error).__name__
        db.session.commit()
        raise click.ClickException('ALERT: backup verification failed.') from error
    if not run.offsite_verified_at or run.offsite_verified_at < m.now() - timedelta(hours=24):
        raise click.ClickException('ALERT: local backup verified; offsite verification is missing or stale.')
    click.echo('Latest backup verified; offsite transfer was verified within 24 hours.')


@hub.command('restore-test')
@click.option('--backup-id', required=True)
@click.option('--isolated-target', required=True, type=click.Path(path_type=Path))
@with_appcontext
def restore_test(backup_id, isolated_target):
    run = db.session.get(m.BackupRun, backup_id)
    if run is None:
        raise click.ClickException('Unknown backup ID.')
    try:
        result = recovery.restore_test(run, isolated_target)
        click.echo(f'Restore test {result.outcome}.')
    except Exception as error:
        raise click.ClickException(f'Restore test failed ({type(error).__name__}).') from error
