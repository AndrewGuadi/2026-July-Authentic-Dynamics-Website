"""Connected Hub workflows, authorization, migration and recovery regression coverage."""

import io
import re
import sqlite3
from datetime import UTC

import pytest
from sqlalchemy import inspect

from authentic_dynamics import create_app
from authentic_dynamics.extensions import db
from authentic_dynamics.hub import models as m
from authentic_dynamics.models import AdminUser
from authentic_dynamics.services.hub import backup, core, jobs

PASSWORD = 'hub-test-password-only'


@pytest.fixture
def app(tmp_path):
    app = create_app({'TESTING': True, 'SECRET_KEY': 'hub-test-key',
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{tmp_path / "app.db"}',
        'HUB_PRIVATE_DIR': str(tmp_path / 'private'), 'SESSION_COOKIE_SECURE': False})
    runner = app.test_cli_runner()
    result = runner.invoke(args=['db', 'upgrade'])
    assert result.exit_code == 0, result.output
    with app.app_context():
        user = AdminUser(email='hub@example.test')
        user.set_password(PASSWORD)
        db.session.add(user)
        db.session.commit()
    result = runner.invoke(args=['hub', 'init'])
    assert result.exit_code == 0, result.output
    return app


def csrf(client, path='/admin/login'):
    response = client.get(path)
    assert response.status_code == 200, response.text[:500]
    return re.search(r'name="csrf_token" value="([^"]+)"', response.text)[1]


@pytest.fixture
def client(app):
    client = app.test_client()
    result = client.post('/admin/login', data={'csrf_token': csrf(client),
        'email': 'hub@example.test', 'password': PASSWORD, 'next': '/hub'})
    assert result.status_code == 303 and result.location == '/hub'
    return client


def mutate(client, resource, values, record_id=None, status=None):
    headers = {'X-CSRFToken': csrf(client, '/hub')}
    path = f'/hub/api/{resource}' + (f'/{record_id}' if record_id else '')
    response = client.patch(path, json=values, headers=headers) if record_id else client.post(path, json=values, headers=headers)
    assert response.status_code == (status or (200 if record_id else 201)), response.text
    return response.get_json()


def business(client):
    return mutate(client, 'businesses', {'name': 'Test business'})


def project(client, company=None):
    return mutate(client, 'projects', {'title': 'Website', 'business_id': (company or business(client))['id']})


def test_migrations_and_seed_are_repeatable(app):
    runner = app.test_cli_runner()
    assert runner.invoke(args=['db', 'upgrade']).exit_code == 0
    assert runner.invoke(args=['hub', 'init']).exit_code == 0
    with app.app_context():
        assert len(inspect(db.engine).get_table_names()) == 40
        assert db.session.scalar(db.select(db.func.count()).select_from(m.Workspace)) == 1
        assert db.session.scalar(db.select(db.func.count()).select_from(m.PipelineStage)) == 10
        assert db.session.execute(db.text('PRAGMA foreign_keys')).scalar() == 1
        assert db.session.execute(db.text('PRAGMA journal_mode')).scalar() == 'wal'


def test_connected_crm_and_history(client, app):
    company = business(client)
    person = mutate(client, 'people', {'name': 'Client contact', 'email': 'person@example.test'})
    mutate(client, 'business_contacts', {'business_id': company['id'], 'person_id': person['id'], 'is_primary': True})
    stages = client.get('/hub/api/pipeline_stages').json['items']
    first, second = stages[:2]
    opportunity = mutate(client, 'opportunities', {'business_id': company['id'], 'pipeline_id': first['pipeline_id'],
        'stage_id': first['id'], 'title': 'Website proposal', 'estimated_value_minor': 50000})
    mutate(client, 'opportunities', {'stage_id': second['id']}, opportunity['id'])
    delivery = mutate(client, 'projects', {'business_id': company['id'], 'opportunity_id': opportunity['id'], 'title': 'Client website'})
    assert client.get(f'/hub/businesses/{company["id"]}').status_code == 200
    assert 'Website proposal' in client.get(f'/hub/businesses/{company["id"]}').text
    with app.app_context():
        record = db.session.get(m.Opportunity, opportunity['id'])
        assert record.stage_id == second['id']
        assert record.created_at.tzinfo == UTC
        history = db.session.scalars(db.select(m.AuditEvent).where(m.AuditEvent.entity_id == record.id)).all()
        assert len(history) == 2
        assert history[1].change_json['transitions']['stage_id']['after'] == second['id']
    assert client.get(f'/hub/projects/{delivery["id"]}').status_code == 200
    assert 'Test business' in client.get('/hub/search?q=Test').text


def test_pages_and_forms_render(client):
    for resource in core.RESOURCES:
        assert client.get(f'/hub/{resource}').status_code == 200, resource
        assert client.get(f'/hub/{resource}/new').status_code == 200, resource
    assert client.get('/hub/settings').status_code == 200
    result = client.post('/hub/businesses/new', data={'csrf_token': csrf(client, '/hub'),
        'name': '<script>client</script>', 'website_url': '', 'industry': '',
        'lifecycle_status': 'prospect', 'source': '', 'description': ''})
    assert result.status_code == 303
    page = client.get(result.location)
    assert '&lt;script&gt;client&lt;/script&gt;' in page.text


def test_projects_cycles_and_atomic_move(client):
    delivery = project(client)
    section = mutate(client, 'project_sections', {'project_id': delivery['id'], 'name': 'Build', 'sort_order': 1})
    task = mutate(client, 'tasks', {'project_id': delivery['id'], 'title': 'Build pages'})
    child = mutate(client, 'tasks', {'project_id': delivery['id'], 'parent_task_id': task['id'], 'title': 'Homepage'})
    mutate(client, 'tasks', {'parent_task_id': child['id']}, task['id'], status=400)
    mutate(client, 'task_dependencies', {'task_id': task['id'], 'depends_on_task_id': child['id']})
    mutate(client, 'task_dependencies', {'task_id': child['id'], 'depends_on_task_id': task['id']}, status=400)
    mutate(client, 'tasks', {'section_id': section['id'], 'position': 2, 'status': 'blocked',
        'blocked_reason': 'Waiting for photos', 'due_at': '2026-10-10T14:00:00-04:00'}, task['id'])
    saved = client.get(f'/hub/api/tasks/{task["id"]}').json
    assert saved['section_id'] == section['id'] and saved['position'] == 2
    assert saved['due_at'] == '2026-10-10T18:00:00+00:00'
    mutate(client, 'tasks', {'due_at': '2026-10-10T14:00:00'}, task['id'], status=400)
    other = project(client)
    other_section = mutate(client, 'project_sections', {'project_id': other['id'], 'name': 'Other', 'sort_order': 1})
    mutate(client, 'tasks', {'section_id': other_section['id']}, task['id'], status=400)


def test_documents_contract_evidence_and_private_downloads(client, app):
    company = business(client)
    document = mutate(client, 'documents', {'title': 'Proposal', 'business_id': company['id']})
    for content in (b'Proposal version one', b'Proposal version two'):
        response = client.post(f'/hub/documents/{document["id"]}/versions', data={
            'csrf_token': csrf(client, '/hub'), 'file': (io.BytesIO(content), 'proposal.txt')})
        assert response.status_code == 303, response.text
    with app.app_context():
        versions = db.session.scalars(db.select(m.DocumentVersion).order_by(m.DocumentVersion.version_number)).all()
        first, second = [(v.id, v.sha256) for v in versions]
        assert first[1] != second[1]
        assert db.session.get(m.Document, document['id']).current_version_id == second[0]
    path = f'/hub/documents/{document["id"]}/versions/{first[0]}/download'
    response = client.get(path)
    assert response.data == b'Proposal version one'
    assert 'attachment' in response.headers['Content-Disposition']
    assert 'no-store' in response.headers['Cache-Control']
    assert app.test_client().get(path).status_code == 303
    mutate(client, 'contracts', {'business_id': company['id'], 'title': 'Agreement', 'status': 'signed'}, status=400)
    contract = mutate(client, 'contracts', {'business_id': company['id'], 'title': 'Agreement', 'status': 'signed',
        'executed_version_id': first[0], 'signed_date': '2026-10-08', 'signature_evidence': 'Signed copy received from client.'})
    mutate(client, 'contracts', {'signature_evidence': 'replacement'}, contract['id'], status=400)
    with app.app_context():
        doc = db.session.get(m.DocumentVersion, first[0])
        doc.sha256 = 'x' * 64
        with pytest.raises(ValueError, match='append-only'):
            db.session.commit()
        db.session.rollback()


def test_finance_partial_payment_and_rules(client):
    company = business(client)
    invoice = mutate(client, 'invoices', {'business_id': company['id'], 'invoice_number': 'AD-100',
        'issue_date': '2026-10-08', 'due_date': '2026-10-22'})
    for quantity, amount in [('1', 50000), ('2.5', 10000)]:
        mutate(client, 'invoice_lines', {'invoice_id': invoice['id'], 'description': 'Services',
            'quantity_decimal': quantity, 'unit_amount_minor': amount})
    mutate(client, 'invoices', {'status': 'issued'}, invoice['id'])
    payment = mutate(client, 'payments', {'business_id': company['id'], 'received_on': '2026-10-08',
        'amount_minor': 25000, 'method': 'check'})
    allocation = {'invoice_id': invoice['id'], 'payment_id': payment['id'], 'allocated_minor': 25000}
    mutate(client, 'payment_allocations', allocation, status=400)
    mutate(client, 'payments', {'status': 'posted'}, payment['id'])
    mutate(client, 'payment_allocations', {**allocation, 'allocated_minor': 30000}, status=400)
    mutate(client, 'payment_allocations', allocation)
    result = client.get(f'/hub/api/invoices/{invoice["id"]}').json
    assert result['total_minor'] == 75000 and result['outstanding_minor'] == 50000
    mutate(client, 'payments', {'status': 'pending'}, payment['id'], status=400)
    mutate(client, 'invoices', {'status': 'void'}, invoice['id'], status=400)
    mutate(client, 'invoice_lines', {'invoice_id': invoice['id'], 'description': 'Extra',
        'quantity_decimal': '1', 'unit_amount_minor': 100}, status=400)
    mutate(client, 'invoices', {'business_id': company['id'], 'invoice_number': 'AD-100',
        'issue_date': '2026-10-08', 'due_date': '2026-10-22'}, status=400)


def test_permissions_csrf_workspace_and_confidentiality(client, app):
    company = business(client)
    document = mutate(client, 'documents', {'title': 'Confidential', 'business_id': company['id']})
    assert client.post('/hub/api/businesses', json={'name': 'No CSRF'}).status_code == 400
    with app.app_context():
        owner = db.session.scalar(db.select(m.Membership))
        owner.role = 'read_only'
        other = m.Workspace(name='Other workspace')
        db.session.add(other)
        db.session.flush()
        other_business = m.Business(workspace_id=other.id, name='Other business')
        db.session.add(other_business)
        db.session.commit()
        other_id = other_business.id
    mutate(client, 'businesses', {'name': 'Nope'}, status=403)
    assert client.get(f'/hub/documents/{document["id"]}').status_code == 403
    assert client.get('/hub/api/documents').json['items'] == []
    assert client.get('/hub/invoices').status_code == 403
    assert client.get('/hub/settings').status_code == 403
    assert client.get(f'/hub/api/businesses/{other_id}').status_code == 404
    with app.app_context():
        db.session.scalar(db.select(m.Membership)).role = 'owner'
        db.session.commit()
    mutate(client, 'projects', {'business_id': other_id, 'title': 'Cross workspace'}, status=404)
    assert app.test_client().get('/hub').status_code == 303


def test_backup_restore_jobs_and_failure(client, app, tmp_path, monkeypatch):
    company = business(client)
    document = mutate(client, 'documents', {'title': 'Persistent file', 'business_id': company['id']})
    assert client.post(f'/hub/documents/{document["id"]}/versions', data={
        'csrf_token': csrf(client, '/hub'), 'file': (io.BytesIO(b'Keep this file'), 'proof.txt')}).status_code == 303
    with app.app_context():
        scope = db.session.scalar(db.select(m.Workspace.id))
        run = backup.backup(scope)
        assert run.status == 'local_verified' and run.offsite_verified_at is None
        isolated = tmp_path / 'restore'
        assert backup.restore_test(run, isolated).outcome == 'passed'
        with sqlite3.connect(isolated / 'database.sqlite3') as restored:
            assert restored.execute('SELECT name FROM hub_businesses').fetchone()[0] == 'Test business'
        jobs.enqueue(scope, 'renewal_digest', 'renewals:test')
        jobs.enqueue(scope, 'renewal_digest', 'renewals:test')
        db.session.commit()
        assert jobs.run_jobs() == 1
        assert jobs.run_jobs() == 0
        assert db.session.scalar(db.select(db.func.count()).select_from(m.Job)) == 1
        def fail(_):
            raise OSError('sensitive simulated failure')
        monkeypatch.setattr(backup, 'offsite_upload', fail)
        with pytest.raises(OSError):
            backup.backup(scope, upload_offsite=True)
        failed = db.session.scalar(db.select(m.BackupRun).order_by(m.BackupRun.started_at.desc()))
        assert failed.status == 'failed' and failed.offsite_verified_at is None
        assert failed.error_redacted == 'OSError'
        version = db.session.scalar(db.select(m.DocumentVersion))
        (isolated / 'files' / version.storage_key).write_bytes(b'corrupt')
        with pytest.raises(ValueError, match='checksum'):
            backup.verify(isolated)
    assert app.test_cli_runner().invoke(args=['hub', 'verify-backups']).exit_code != 0


def test_upload_rejection_cleans_unreferenced_files(client, app):
    document = mutate(client, 'documents', {'title': 'Uploads'})
    response = client.post(f'/hub/documents/{document["id"]}/versions', data={
        'csrf_token': csrf(client, '/hub'), 'file': (io.BytesIO(b'not a pdf'), 'wrong.pdf')})
    assert response.status_code == 400
    from pathlib import Path
    assert list(Path(app.config['HUB_UPLOAD_DIR']).iterdir()) == []


def test_boards_template_and_move(client):
    assert client.get('/hub/pipeline').status_code == 200
    delivery = project(client)
    path = f'/hub/projects/{delivery["id"]}/website-template'
    assert client.post(path, data={'csrf_token': csrf(client, '/hub')}).status_code == 303
    assert client.post(path, data={'csrf_token': csrf(client, '/hub')}).status_code == 400
    page = client.get(f'/hub/projects/{delivery["id"]}/board')
    assert page.status_code == 200, page.text
    assert 'Discovery call' in page.text
    tasks = client.get('/hub/api/tasks').json['items']
    sections = client.get('/hub/api/project_sections').json['items']
    target = next(section for section in sections if section['id'] != tasks[0]['section_id'])
    response = client.post(f'/hub/tasks/{tasks[0]["id"]}/move', data={
        'csrf_token': csrf(client, '/hub'), 'section_id': target['id']}, headers={'Accept': 'application/json'})
    assert response.json == {'ok': True}
    assert client.get(f'/hub/api/tasks/{tasks[0]["id"]}').json['section_id'] == target['id']


def test_concurrent_allocations_cannot_overspend(client, app):
    from concurrent.futures import ThreadPoolExecutor

    company = business(client)
    invoices = []
    for index in range(2):
        invoice = mutate(client, 'invoices', {'business_id': company['id'], 'invoice_number': f'CON-{index}',
            'issue_date': '2026-10-08', 'due_date': '2026-10-22'})
        mutate(client, 'invoice_lines', {'invoice_id': invoice['id'], 'description': 'Work',
            'quantity_decimal': '1', 'unit_amount_minor': 20000})
        mutate(client, 'invoices', {'status': 'issued'}, invoice['id'])
        invoices.append(invoice['id'])
    payment = mutate(client, 'payments', {'business_id': company['id'], 'amount_minor': 25000,
        'currency': 'USD', 'status': 'posted', 'received_on': '2026-10-08', 'method': 'check'})
    with app.app_context():
        member = db.session.scalar(db.select(m.Membership))
        scope, actor = member.workspace_id, member.user_id

    def allocate(invoice_id):
        with app.app_context(), core.write_lock():
            try:
                core.save('payment_allocations', {'invoice_id': invoice_id, 'payment_id': payment['id'],
                    'allocated_minor': 20000}, scope, actor)
                db.session.commit()
                return True
            except ValueError:
                db.session.rollback()
                return False

    with ThreadPoolExecutor(max_workers=2) as workers:
        assert sorted(workers.map(allocate, invoices)) == [False, True]
    with app.app_context():
        assert db.session.scalar(db.select(db.func.sum(m.PaymentAllocation.allocated_minor))) == 20000


def test_inactive_and_unenrolled_login_denied(client, app):
    with app.app_context():
        db.session.scalar(db.select(m.User)).is_active = False
        db.session.commit()
    assert client.get('/hub').status_code == 403
    assert client.get('/admin/').status_code == 200


def test_migration_preserves_existing_admin_and_inquiry(tmp_path):
    app = create_app({'TESTING': True, 'SECRET_KEY': 'migration-only',
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{tmp_path / "legacy.db"}',
        'HUB_PRIVATE_DIR': str(tmp_path / 'private')})
    runner = app.test_cli_runner()
    assert runner.invoke(args=['db', 'upgrade', 'b4a7d2c891ef']).exit_code == 0
    with app.app_context():
        from authentic_dynamics.models import ContactSubmission
        user = AdminUser(email='preserve@example.test')
        user.set_password(PASSWORD)
        db.session.add(user)
        db.session.add(ContactSubmission(name='Existing client', business='', email='client@example.test',
            interest='Website', message='Preserve this inquiry', source_page='home'))
        db.session.commit()
        original_hash = user.password_hash
    assert runner.invoke(args=['db', 'upgrade']).exit_code == 0
    with app.app_context():
        assert db.session.get(AdminUser, 1).password_hash == original_hash
        assert db.session.get(ContactSubmission, 1).message == 'Preserve this inquiry'
        assert not db.session.scalar(db.select(m.Membership.id))
