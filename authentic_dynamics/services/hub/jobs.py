"""Small local outbox worker; no messages or provider mutations are sent."""

import fcntl
from datetime import timedelta
from pathlib import Path

from flask import current_app
from sqlalchemy import or_

from authentic_dynamics.extensions import db
from authentic_dynamics.hub import models as m

from .core import audit, write_lock


def enqueue(workspace_id, job_type, key, payload=None):
    if job_type not in {'renewal_digest', 'due_digest'}:
        raise ValueError('Unsupported job type.')
    existing = db.session.scalar(db.select(m.Job).where(
        m.Job.workspace_id == workspace_id, m.Job.idempotency_key == key))
    if existing:
        return existing
    job = m.Job(workspace_id=workspace_id, job_type=job_type,
                idempotency_key=key, payload_json=payload or {})
    db.session.add(job)
    db.session.flush()
    return job


def run_jobs(max_jobs=20):
    lock_path = Path(current_app.config['HUB_PRIVATE_DIR']) / 'worker.lock'
    with lock_path.open('a') as worker:
        try:
            fcntl.flock(worker, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('A Hub worker is already running.') from error
        completed = 0
        for _ in range(max_jobs):
            with write_lock():
                job = db.session.scalar(db.select(m.Job).where(or_(
                    (m.Job.status == 'pending') & (m.Job.available_at <= m.now()),
                    (m.Job.status == 'running') & (m.Job.lease_until < m.now()),
                )).order_by(m.Job.available_at).limit(1))
                if job is None:
                    break
                if job.attempt_count >= 5:
                    job.status = 'failed'
                    db.session.commit()
                    continue
                job.status = 'running'
                job.attempt_count += 1
                job.claimed_at = m.now()
                job.lease_until = m.now() + timedelta(minutes=5)
                db.session.commit()
                job_id = job.id
                try:
                    if job.job_type == 'renewal_digest':
                        count = db.session.scalar(db.select(db.func.count()).select_from(m.DigitalAsset).where(
                            m.DigitalAsset.workspace_id == job.workspace_id,
                            m.DigitalAsset.status == 'active',
                            m.DigitalAsset.renewal_date <= (m.now() + timedelta(days=30)).date()))
                    elif job.job_type == 'due_digest':
                        count = db.session.scalar(db.select(db.func.count()).select_from(m.Task).where(
                            m.Task.workspace_id == job.workspace_id, m.Task.due_at <= m.now(),
                            m.Task.status.notin_(['done', 'canceled'])))
                    else:
                        raise ValueError('Unsupported handler.')
                    job.payload_json = {'count': count, 'generated_at': m.now().isoformat()}
                    audit(job.workspace_id, None, 'digest_generated', job)
                    job.status = 'completed'
                    job.lease_until = None
                    db.session.commit()  # Result and acknowledgement are one durable transaction.
                    completed += 1
                except Exception as error:  # noqa: BLE001 -- persist retries without logging payloads
                    current_app.logger.error('Hub job %s failed (%s)', job_id, type(error).__name__)
                    db.session.rollback()
                    job = db.session.get(m.Job, job_id)
                    job.last_error_redacted = type(error).__name__
                    job.status = 'failed' if job.attempt_count >= 5 else 'pending'
                    job.available_at = m.now() + timedelta(seconds=min(3600, 30 * 2 ** job.attempt_count))
                    job.lease_until = None
                    db.session.commit()
        return completed
