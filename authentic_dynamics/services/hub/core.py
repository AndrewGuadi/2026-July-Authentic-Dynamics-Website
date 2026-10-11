"""Validated Hub operations shared by pages, JSON endpoints, and CLI jobs."""

import fcntl
import re
from contextlib import contextmanager
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

from flask import current_app
from sqlalchemy import Boolean, Date, Integer, Numeric, String, Text
from werkzeug.exceptions import Forbidden, NotFound

from authentic_dynamics.extensions import db
from authentic_dynamics.hub import models as m

# Explicitly published resources. Administrative/history records use separate actions.
RESOURCES = {
    name: m.MODELS[name] for name in (
        'businesses', 'people', 'business_contacts', 'pipelines', 'pipeline_stages',
        'opportunities', 'activities', 'projects', 'project_sections', 'tasks',
        'task_dependencies', 'task_comments', 'milestones', 'approvals', 'documents',
        'contracts', 'contract_parties', 'invoices', 'invoice_lines', 'payments',
        'payment_allocations', 'expenses', 'digital_assets', 'asset_access',
        'integrations', 'external_record_links', 'record_links',
    )
}
ADMIN_ONLY = {'pipelines', 'pipeline_stages', 'integrations', 'external_record_links'}
FINANCE = {'invoices', 'invoice_lines', 'payments', 'payment_allocations', 'expenses'}
SERVER_FIELDS = {'id', 'workspace_id', 'created_at', 'updated_at', 'created_by',
                 'current_version_id', 'author_id', 'total_minor', 'line_total_minor',
                 'last_synced_at'}
IMMUTABLE = {'approvals', 'payment_allocations', 'task_comments', 'invoice_lines',
             'task_dependencies', 'business_contacts', 'record_links', 'external_record_links'}


@contextmanager
def write_lock():
    """Serialize local Hub writers across WSGI/CLI; DB locks also protect finance."""
    root = Path(current_app.config['HUB_PRIVATE_DIR'])
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (root / 'write.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def audit(workspace_id, actor_id, action, record, changes=None):
    # Only names of changed fields and non-sensitive workflow state are retained.
    allowed = {'stage_id', 'status', 'section_id', 'position', 'lifecycle_status'}
    clean = {key: value for key, value in (changes or {}).items() if key in allowed}
    db.session.add(m.AuditEvent(
        workspace_id=workspace_id, actor_id=actor_id, action=action,
        entity_type=record.__tablename__.removeprefix('hub_'), entity_id=record.id,
        change_json={'fields': sorted((changes or {}).keys()), 'transitions': clean},
        request_id=str(uuid4()),
    ))


def membership(workspace_id, actor_id, write=False, admin=False, finance=False):
    user = db.session.get(m.User, actor_id)
    member = db.session.scalar(db.select(m.Membership).where(
        m.Membership.workspace_id == workspace_id, m.Membership.user_id == actor_id))
    if not user or not user.is_active or not member:
        raise Forbidden()
    if (write and member.role == 'read_only') or (
        (admin or finance) and member.role not in {'owner', 'admin'}
    ):
        raise Forbidden()
    return member


def get_record(resource, record_id, workspace_id):
    model = m.MODELS.get(resource)
    if model is None or not hasattr(model, 'workspace_id'):
        raise NotFound()
    record = db.session.scalar(db.select(model).where(
        model.id == record_id, model.workspace_id == workspace_id))
    if record is None:
        raise NotFound()
    return record


def fields_for(resource):
    return [c for c in RESOURCES[resource].__table__.columns if c.name not in SERVER_FIELDS]


def convert(column, value):
    if value is None or value == '':
        if column.nullable:
            return None
        raise ValueError(f'{column.name.replace("_", " ")} is required.')
    kind = column.type
    try:
        if isinstance(kind, m.UTCDateTime):
            parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
            if parsed.tzinfo is None:
                raise ValueError('Include a timezone offset, for example +00:00.')
            return parsed
        if isinstance(kind, Date):
            return date.fromisoformat(value)
        if isinstance(kind, Boolean):
            if value in (True, 'true', '1'):
                return True
            if value in (False, 'false', '0'):
                return False
            raise ValueError('Use true or false.')
        if isinstance(kind, Integer):
            if isinstance(value, bool) or not re.fullmatch(r'-?\d+', str(value)):
                raise ValueError('Use a whole number.')
            number = int(value)
            if abs(number) > 9_000_000_000_000:
                raise ValueError('Amount is too large.')
            return number
        if isinstance(kind, Numeric):
            number = Decimal(str(value))
            if not number.is_finite() or number <= 0 or number > 99_999_999:
                raise ValueError('Use a positive finite quantity.')
            if number != number.quantize(Decimal('0.0001')):
                raise ValueError('Use at most four decimal places.')
            return number
        if isinstance(kind, (String, Text)):
            if not isinstance(value, str):
                raise TypeError('Use text.')
            value = value.strip()
            if not value or len(value) > (getattr(kind, 'length', None) or 20000):
                raise ValueError('Text is empty or too long.')
            if column.name == 'currency' and not re.fullmatch('[A-Z]{3}', value):
                raise ValueError('Use a three-letter uppercase currency code.')
            if column.name in {'website_url', 'url'} and not value.startswith(('https://', 'http://')):
                raise ValueError('Use an http:// or https:// URL.')
            return value
    except (TypeError, InvalidOperation) as error:
        raise ValueError(f'Invalid {column.name}.') from error
    raise ValueError(f'Unsupported field: {column.name}')


def validate_links(record, workspace_id, actor_id):
    """Check all ordinary FKs and polymorphic links before touching persistent rows."""
    linked = {}
    for column in record.__table__.columns:
        value = getattr(record, column.name)
        if not value or column.name in {'workspace_id', 'current_version_id'}:
            continue
        for foreign in column.foreign_keys:
            resource = foreign.column.table.name.removeprefix('hub_')
            if resource == 'users':
                membership(workspace_id, value)
            else:
                linked[column.name] = get_record(resource, value, workspace_id)
                target = linked[column.name]
                if isinstance(target, m.DocumentVersion):
                    target = get_record('documents', target.document_id, workspace_id)
                if isinstance(target, m.Document) and target.confidential:
                    membership(workspace_id, actor_id, admin=True)
    for left, right, attr in (
        ('stage_id', 'pipeline_id', 'pipeline_id'),
        ('section_id', 'project_id', 'project_id'),
        ('parent_task_id', 'project_id', 'project_id'),
        ('opportunity_id', 'business_id', 'business_id'),
        ('project_id', 'business_id', 'business_id'),
    ):
        if left in linked and hasattr(record, right) and getattr(record, right) != getattr(linked[left], attr):
            raise ValueError(f'{left} must belong to the selected {right}.')
    if isinstance(record, m.Approval):
        subject = get_record(record.subject_type, record.subject_id, workspace_id)
        if record.subject_type not in {'projects', 'tasks', 'milestones', 'contracts'}:
            raise ValueError('Unsupported approval subject.')
        project_id = subject.id if isinstance(subject, m.Project) else subject.project_id
        evidence = linked['evidence_document_id']
        if project_id != record.project_id or evidence.project_id != record.project_id:
            raise ValueError('Approval and evidence must belong to the same project.')
    if isinstance(record, m.RecordLink):
        for prefix in ('from', 'to'):
            kind = getattr(record, f'{prefix}_type')
            if kind not in RESOURCES:
                raise ValueError('Unsupported link type.')
            get_record(kind, getattr(record, f'{prefix}_id'), workspace_id)
    if isinstance(record, m.ExternalRecordLink):
        if record.entity_type not in RESOURCES:
            raise ValueError('Unsupported link type.')
        get_record(record.entity_type, record.entity_id, workspace_id)
    if isinstance(record, m.Task):
        parent = record.parent_task_id
        seen = {record.id}
        while parent:
            if parent in seen:
                raise ValueError('Circular subtasks are not allowed.')
            seen.add(parent)
            parent = get_record('tasks', parent, workspace_id).parent_task_id
    if isinstance(record, m.TaskDependency):
        if linked['task_id'].project_id != linked['depends_on_task_id'].project_id:
            raise ValueError('Dependencies must be in the same project.')
        edges = db.session.scalars(db.select(m.TaskDependency).where(
            m.TaskDependency.workspace_id == workspace_id)).all()
        graph = {}
        for edge in edges:
            graph.setdefault(edge.task_id, []).append(edge.depends_on_task_id)
        pending, seen = [record.depends_on_task_id], set()
        while pending:
            current = pending.pop()
            if current == record.task_id:
                raise ValueError('Circular dependencies are not allowed.')
            if current not in seen:
                seen.add(current)
                pending.extend(graph.get(current, []))
    if isinstance(record, m.Contract) and record.executed_version_id:
        document = get_record('documents', linked['executed_version_id'].document_id, workspace_id)
        if document.business_id != record.business_id or document.project_id != record.project_id:
            raise ValueError('Executed document must belong to this business and project.')
    if (isinstance(record, m.Contract) and record.status == 'signed'
        and not (record.executed_version_id and record.signed_date and record.signature_evidence)):
        raise ValueError('Signed contracts require an executed version, date, and recorded evidence.')
    if isinstance(record, m.Invoice) and record.due_date < record.issue_date:
        raise ValueError('Due date cannot precede issue date.')
    if (isinstance(record, m.Project) and record.start_date and record.target_date
        and record.target_date < record.start_date):
        raise ValueError('Target date cannot precede start date.')


def outstanding(invoice):
    allocated = db.session.scalar(db.select(db.func.coalesce(
        db.func.sum(m.PaymentAllocation.allocated_minor), 0)).join(
        m.Payment, m.Payment.id == m.PaymentAllocation.payment_id).where(
        m.PaymentAllocation.invoice_id == invoice.id, m.Payment.status == 'posted'))
    return invoice.total_minor - allocated


def financial_rules(resource, record, workspace_id):
    if resource == 'invoice_lines':
        invoice = get_record('invoices', record.invoice_id, workspace_id)
        if invoice.status != 'draft':
            raise ValueError('Only draft invoices accept new lines.')
        record.line_total_minor = int((record.quantity_decimal * record.unit_amount_minor).quantize(
            Decimal(1), rounding=ROUND_HALF_UP))
        if record.line_total_minor < 0:
            raise ValueError('Line amount cannot be negative.')
        invoice.total_minor += record.line_total_minor
    if resource == 'payment_allocations':
        payment = get_record('payments', record.payment_id, workspace_id)
        invoice = get_record('invoices', record.invoice_id, workspace_id)
        if payment.status != 'posted' or invoice.status != 'issued':
            raise ValueError('Allocate posted payments to issued invoices only.')
        if payment.business_id != invoice.business_id or payment.currency != invoice.currency:
            raise ValueError('Payment and invoice must have the same business and currency.')
        used = db.session.scalar(db.select(db.func.coalesce(
            db.func.sum(m.PaymentAllocation.allocated_minor), 0)).where(
            m.PaymentAllocation.payment_id == payment.id))
        if record.allocated_minor <= 0 or record.allocated_minor > min(
            payment.amount_minor - used, outstanding(invoice)
        ):
            raise ValueError('Allocation exceeds the available payment or invoice balance.')


def save(resource, values, workspace_id, actor_id, record_id=None):
    """Caller commits once while holding write_lock; all failures roll back together."""
    if resource not in RESOURCES:
        raise NotFound()
    member = membership(workspace_id, actor_id, write=True, admin=resource in ADMIN_ONLY,
                        finance=resource in FINANCE)
    # PostgreSQL serializes validations even across hosts; SQLite uses the file lock.
    db.session.execute(db.select(m.Workspace).where(
        m.Workspace.id == workspace_id).with_for_update()).scalar_one()
    model = RESOURCES[resource]
    record = get_record(resource, record_id, workspace_id) if record_id else model(
        id=str(uuid4()), workspace_id=workspace_id)
    if (resource == 'documents' and record_id and record.confidential
        and member.role not in {'owner', 'admin'}):
        raise Forbidden()
    columns = {column.name: column for column in fields_for(resource)}
    if not isinstance(values, dict) or set(values) - columns.keys():
        raise ValueError('Unrecognized fields.')
    if record_id:
        if resource in IMMUTABLE:
            raise ValueError('This record is append-only.')
        if resource == 'payments' and record.status in {'posted', 'canceled'}:
            raise ValueError('Posted or canceled payment history cannot be edited.')
        if (resource == 'invoices' and record.status != 'draft' and (
            set(values) != {'status'} or values['status'] != 'void' or outstanding(record) != record.total_minor
        )):
            raise ValueError('Issued invoices cannot be edited; only unpaid invoices can be voided.')
        if (resource == 'contracts' and record.executed_version_id and (
            set(values) - {'status'} or values.get('status') not in {'expired', 'archived'}
        )):
            raise ValueError('Executed contract evidence is immutable.')
        # Moving parent records would invalidate linked history. Create a new record instead.
        for field, column in columns.items():
            if (column.foreign_keys and field not in {'stage_id', 'section_id', 'parent_task_id',
                                                     'assignee_id', 'owner_id', 'executed_version_id'}
                and field in values and values[field] != getattr(record, field)):
                raise ValueError(f'{field} cannot be changed after creation.')
    changes = {}
    for name, value in values.items():
        parsed = convert(columns[name], value)
        changes[name] = {'before': str(getattr(record, name, None)), 'after': str(parsed)}
        setattr(record, name, parsed)
    if not record_id:
        if resource == 'documents':
            record.created_by = actor_id
        if resource == 'task_comments':
            record.author_id = actor_id
        for column in model.__table__.columns:
            if getattr(record, column.name) is None and column.default and column.default.is_scalar:
                setattr(record, column.name, column.default.arg)
        for column in columns.values():
            if getattr(record, column.name) is None and not column.nullable and not column.default:
                raise ValueError(f'{column.name.replace("_", " ")} is required.')
    with db.session.no_autoflush:
        validate_links(record, workspace_id, actor_id)
        financial_rules(resource, record, workspace_id)
        if isinstance(record, m.BusinessContact) and record.is_primary:
            others = db.session.scalars(db.select(m.BusinessContact).where(
                m.BusinessContact.business_id == record.business_id,
                m.BusinessContact.id != record.id, m.BusinessContact.is_primary.is_(True)))
            for contact in others:
                contact.is_primary = False
                audit(workspace_id, actor_id, 'primary_contact_changed', contact,
                      {'is_primary': {'before': 'True', 'after': 'False'}})
        if isinstance(record, m.Pipeline) and record.is_default:
            for pipeline in db.session.scalars(db.select(m.Pipeline).where(
                m.Pipeline.workspace_id == workspace_id, m.Pipeline.id != record.id,
                m.Pipeline.is_default.is_(True)
            )):
                pipeline.is_default = False
                audit(workspace_id, actor_id, 'default_pipeline_changed', pipeline)
    db.session.add(record)
    db.session.flush()
    audit(workspace_id, actor_id, 'update' if record_id else 'create', record, changes)
    return record


def serialize(record):
    data = {}
    for col in record.__table__.columns:
        if col.name in {'storage_key', 'admin_user_id'}:
            continue
        value = getattr(record, col.name)
        data[col.name] = value.isoformat() if isinstance(value, (date, datetime)) else (
            str(value) if isinstance(value, Decimal) else value)
    if isinstance(record, m.Invoice):
        data['outstanding_minor'] = outstanding(record)
    return data


def seed(admin_user, role='owner'):
    """Explicit idempotent enrollment; never called automatically by web requests."""
    workspace = db.session.scalar(db.select(m.Workspace).order_by(m.Workspace.created_at))
    if workspace is None:
        workspace = m.Workspace(name='Authentic Dynamics', legal_name='Authentic Dynamics')
        db.session.add(workspace)
        db.session.flush()
    user = db.session.scalar(db.select(m.User).where(m.User.admin_user_id == admin_user.id))
    if user is None:
        user = m.User(admin_user_id=admin_user.id, display_name=admin_user.email.split('@')[0])
        db.session.add(user)
        db.session.flush()
    member = db.session.scalar(db.select(m.Membership).where(
        m.Membership.workspace_id == workspace.id, m.Membership.user_id == user.id))
    if member is None:
        member = m.Membership(workspace_id=workspace.id, user_id=user.id, role=role)
        db.session.add(member)
    pipeline = db.session.scalar(db.select(m.Pipeline).where(m.Pipeline.workspace_id == workspace.id))
    if pipeline is None:
        pipeline = m.Pipeline(workspace_id=workspace.id, name='Client opportunities', is_default=True)
        db.session.add(pipeline)
        db.session.flush()
        for index, name in enumerate(('Identified', 'Researched', 'Contacted', 'Conversation',
                                     'Discovery', 'Proposal', 'Decision', 'Won', 'Lost', 'Future')):
            db.session.add(m.PipelineStage(workspace_id=workspace.id, pipeline_id=pipeline.id,
                name=name, sort_order=index, is_terminal=name in {'Won', 'Lost', 'Future'}))
    db.session.flush()
    return workspace, user
