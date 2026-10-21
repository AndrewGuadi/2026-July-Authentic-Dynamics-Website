"""Thin, session-authenticated Hub views; mutations delegate to domain services."""

import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import (
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from sqlalchemy import Boolean, CheckConstraint, Date, Integer, Numeric, or_
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from authentic_dynamics.blueprints.admin.routes import authenticate as admin_authenticate
from authentic_dynamics.extensions import db
from authentic_dynamics.hub import models as m
from authentic_dynamics.services.hub import core, storage

from . import bp

NAV = [('businesses', 'Businesses'), ('people', 'People'), ('opportunities', 'Sales pipeline'),
       ('projects', 'Projects'), ('tasks', 'Tasks'), ('documents', 'Documents'),
       ('contracts', 'Contracts'), ('invoices', 'Invoices'), ('payments', 'Payments'),
       ('expenses', 'Expenses'), ('digital_assets', 'Digital assets'), ('activities', 'Activity')]


FILTER_KEYS = ('business_id', 'project_id', 'document_id', 'invoice_id', 'task_id',
               'asset_id', 'contract_id', 'pipeline_id', 'status', 'q', 'page')


def list_context():
    """Carry only known list filters, never arbitrary redirect URLs."""
    return {key: request.args[key][:150] for key in FILTER_KEYS if request.args.get(key)}


def context_url(endpoint, **values):
    return url_for(endpoint, **(list_context() | values))


def workspace_zone():
    try:
        return ZoneInfo(g.workspace.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo('UTC')


def record_summary(record):
    parts = []
    if getattr(record, 'business_id', None):
        business = db.session.get(m.Business, record.business_id)
        if business and business.workspace_id == g.workspace.id:
            parts.append(business.name)
    if isinstance(record, m.Task):
        if record.due_at:
            parts.append('Due ' + record.due_at.astimezone(workspace_zone()).strftime('%b %d, %H:%M'))
        if record.assignee_id:
            assignee = db.session.get(m.User, record.assignee_id)
            if assignee:
                parts.append(assignee.display_name)
    elif isinstance(record, m.Opportunity):
        parts.append(f'{record.currency} {Decimal(record.estimated_value_minor) / 100:,.2f}')
    elif isinstance(record, m.Invoice):
        parts.append(f'{record.currency} {Decimal(core.outstanding(record)) / 100:,.2f} outstanding')
    return ' · '.join(parts)


def history_actor(event):
    actor = db.session.get(m.User, event.actor_id) if event.actor_id else None
    return actor.display_name if actor else 'System'


def transition_label(key, value):
    model = {'stage_id': m.PipelineStage, 'section_id': m.ProjectSection}.get(key)
    if model and value not in (None, '', 'None'):
        item = db.session.get(model, value)
        if item and item.workspace_id == g.workspace.id:
            return item.name
    return str(value or 'Not set').replace('_', ' ')


def title(resource):
    return dict(NAV).get(resource, resource.replace('_', ' ').title())


def label(record):
    if isinstance(record, m.DocumentVersion):
        return f'{record.original_name} · version {record.version_number}'
    if isinstance(record, m.BusinessContact):
        person = db.session.get(m.Person, record.person_id)
        return f'{person.name} · {record.title or "Contact"}'
    if isinstance(record, m.Payment):
        return f'{record.currency} {record.amount_minor / 100:.2f} · {record.method}'
    if isinstance(record, m.AssetAccess):
        return f'Owner: {record.owner_type} · Payer: {record.payer_type}'
    if isinstance(record, m.Membership):
        return db.session.get(m.User, record.user_id).display_name
    return (getattr(record, 'name', None) or getattr(record, 'title', None) or
            getattr(record, 'invoice_number', None) or getattr(record, 'display_name', None) or
            getattr(record, 'summary', None) or getattr(record, 'description', None) or
            getattr(record, 'party_name', None) or getattr(record, 'vendor_name', None) or
            getattr(record, 'provider', None) or record.id)


@bp.before_request
def authorize():
    if not current_app.config['HUB_ENABLED']:
        abort(404)
    response = admin_authenticate()
    if response:
        return redirect(url_for('admin.login', next='/hub'), code=303)
    g.hub_user = db.session.scalar(db.select(m.User).where(m.User.admin_user_id == g.admin_user.id))
    if not g.hub_user or not g.hub_user.is_active:
        return render_template('hub/unavailable.html'), 403
    g.membership = db.session.scalar(db.select(m.Membership).where(
        m.Membership.user_id == g.hub_user.id).order_by(m.Membership.created_at))
    if not g.membership:
        abort(403)
    g.workspace = db.session.get(m.Workspace, g.membership.workspace_id)


@bp.after_request
def private(response):
    response.headers['Cache-Control'] = 'no-store, private'
    response.headers['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
    response.headers['Referrer-Policy'] = 'same-origin'
    return response


@bp.context_processor
def context():
    return {'hub_nav': NAV, 'hub_label': label, 'hub_title': title, 'hub_models': m.MODELS,
            'finance_resources': core.FINANCE, 'hub_context_url': context_url,
            'hub_list_context': list_context, 'hub_summary': record_summary,
            'hub_actor': history_actor, 'hub_transition_label': transition_label}


@bp.errorhandler(ValueError)
@bp.errorhandler(IntegrityError)
def invalid(error):
    db.session.rollback()
    message = str(error) if isinstance(error, ValueError) else 'That change conflicts with a required value, relationship, or existing record.'
    if request.path.startswith('/hub/api/'):
        return jsonify(error=message), 400
    return render_template('hub/error.html', message=message), 400


@bp.errorhandler(HTTPException)
def http_error(error):
    if request.path.startswith('/hub/api/'):
        return jsonify(error=error.name), error.code
    return render_template('hub/error.html', message=error.description), error.code


def access(resource, write=False):
    if resource not in core.RESOURCES:
        abort(404)
    core.membership(g.workspace.id, g.hub_user.id, write=write,
                    admin=write and resource in core.ADMIN_ONLY,
                    finance=resource in core.FINANCE)


def query_for(resource):
    access(resource)
    model = core.RESOURCES[resource]
    query = db.select(model).where(model.workspace_id == g.workspace.id)
    if resource == 'documents' and g.membership.role not in {'owner', 'admin'}:
        query = query.where(m.Document.confidential.is_(False))
    for key in ('business_id', 'project_id', 'document_id', 'invoice_id', 'task_id', 'asset_id', 'contract_id', 'pipeline_id', 'status'):
        value = request.args.get(key)
        if value and hasattr(model, key):
            query = query.where(getattr(model, key) == value)
    term = request.args.get('q', '').strip()[:150]
    columns = [getattr(model, key) for key in ('name', 'title', 'summary', 'email', 'invoice_number') if hasattr(model, key)]
    if term and columns:
        query = query.where(or_(*(col.icontains(term, autoescape=True) for col in columns)))
    return query.order_by(model.created_at.desc(), model.id)


@bp.get('')
@bp.get('/')
def dashboard():
    scope = g.workspace.id
    tasks = db.session.scalars(db.select(m.Task).where(
        m.Task.workspace_id == scope, m.Task.status.notin_(['done', 'canceled']),
        or_(m.Task.due_at <= m.now() + timedelta(days=7), m.Task.status == 'blocked'))
        .order_by(m.Task.due_at).limit(20)).all()
    activities = db.session.scalars(db.select(m.Activity).where(m.Activity.workspace_id == scope,
        m.Activity.next_action_at <= m.now() + timedelta(days=7)).order_by(m.Activity.next_action_at).limit(10)).all()
    opportunities = db.session.scalars(db.select(m.Opportunity).join(m.PipelineStage).where(
        m.Opportunity.workspace_id == scope, m.PipelineStage.is_terminal.is_(False))
        .order_by(m.Opportunity.created_at.desc()).limit(10)).all()
    counts = {name: db.session.scalar(db.select(db.func.count()).select_from(model).where(
        model.workspace_id == scope)) for name, model in (
            ('Businesses', m.Business), ('People', m.Person), ('Projects', m.Project))}
    counts['Open tasks'] = db.session.scalar(db.select(db.func.count()).select_from(m.Task).where(
        m.Task.workspace_id == scope, m.Task.status.notin_(['done', 'canceled'])))
    invoices = []
    if g.membership.role in {'owner', 'admin'}:
        invoices = [item for item in db.session.scalars(db.select(m.Invoice).where(
            m.Invoice.workspace_id == scope, m.Invoice.status == 'issued', m.Invoice.due_date < m.now().date()))
            if core.outstanding(item) > 0][:10]
    backup = db.session.scalar(db.select(m.BackupRun).where(m.BackupRun.workspace_id == scope)
                               .order_by(m.BackupRun.started_at.desc()))
    return render_template('hub/dashboard.html', tasks=tasks, opportunities=opportunities,
                           activities=activities, counts=counts, invoices=invoices, backup=backup,
                           backup_current=bool(backup and backup.status == 'protected' and
                               backup.offsite_verified_at and backup.offsite_verified_at > m.now() - timedelta(hours=24)),
                           outstanding=core.outstanding, now=m.now(), timezone=str(workspace_zone()))


@bp.get('/search')
def search():
    term = request.args.get('q', '').strip()[:150]
    groups = {}
    if term:
        for resource in ('businesses', 'people', 'projects', 'tasks', 'documents'):
            groups[resource] = db.session.scalars(query_for(resource).limit(20)).all()
    return render_template('hub/search.html', groups=groups, term=term)


@bp.get('/settings')
def settings():
    core.membership(g.workspace.id, g.hub_user.id, admin=True)
    groups = {name: db.session.scalars(db.select(model).where(model.workspace_id == g.workspace.id)
              .order_by(model.created_at.desc()).limit(30)).all() for name, model in (
                  ('workspace_memberships', m.Membership), ('pipelines', m.Pipeline),
                  ('pipeline_stages', m.PipelineStage), ('job_outbox', m.Job),
                  ('backup_runs', m.BackupRun), ('restore_tests', m.RestoreTest))}
    return render_template('hub/settings.html', groups=groups)


def form_fields(resource, record=None, posted=None, errors=None):
    result = []
    for column in core.fields_for(resource):
        name = column.name
        if record and ((resource == 'invoices' and record.status != 'draft') or
                       (resource == 'contracts' and record.executed_version_id)) and name != 'status':
            continue
        # Once created, fixed parent links are displayed on the detail page.
        if record and column.foreign_keys and name not in {
            'stage_id', 'section_id', 'parent_task_id', 'assignee_id', 'owner_id', 'executed_version_id'
        }:
            continue
        value = getattr(record, name) if record else request.args.get(name, '')
        if value is None:
            value = ''
        if not record and value == '' and column.default and column.default.is_scalar:
            value = column.default.arg
        options, kind = [], 'text'
        if resource == 'approvals' and name == 'subject_type':
            kind = 'select'
            options = [(key, title(key)) for key in ('projects', 'tasks', 'milestones', 'contracts')]
        elif resource == 'approvals' and name == 'subject_id':
            kind = 'select'
            for key in ('projects', 'tasks', 'milestones', 'contracts'):
                model = m.MODELS[key]
                options.extend((item.id, f'{title(key)}: {label(item)}') for item in db.session.scalars(
                    db.select(model).where(model.workspace_id == g.workspace.id).limit(1000)))
        elif column.foreign_keys:
            foreign = next(iter(column.foreign_keys)).column.table.name.removeprefix('hub_')
            model = m.MODELS[foreign]
            if foreign == 'users':
                query = db.select(model).join(m.Membership).where(m.Membership.workspace_id == g.workspace.id,
                                                                model.is_active.is_(True))
            else:
                query = db.select(model).where(model.workspace_id == g.workspace.id)
                if foreign == 'documents' and g.membership.role not in {'owner', 'admin'}:
                    query = query.where(m.Document.confidential.is_(False))
                if foreign == 'document_versions' and g.membership.role not in {'owner', 'admin'}:
                    query = query.join(m.Document, m.Document.id == m.DocumentVersion.document_id).where(
                        m.Document.confidential.is_(False))
                for parent in ('business_id', 'project_id', 'pipeline_id'):
                    parent_value = getattr(record, parent, None) if record else request.args.get(parent)
                    if parent_value and hasattr(model, parent):
                        query = query.where(getattr(model, parent) == parent_value)
            options = [(obj.id, label(obj)) for obj in db.session.scalars(query.limit(1000))]
            kind = 'select'
        elif isinstance(column.type, Boolean):
            kind, options = 'select', [('true', 'Yes'), ('false', 'No')]
            value = 'true' if value is True else 'false'
        else:
            for constraint in core.RESOURCES[resource].__table__.constraints:
                if isinstance(constraint, CheckConstraint):
                    match = re.fullmatch(rf"{name} IN \((.+)\)", str(constraint.sqltext))
                    if match:
                        kind = 'select'
                        options = [(item, item.replace('_', ' ').title()) for item in re.findall("'([^']+)'", match[1])]
            if kind != 'select':
                if isinstance(column.type, Date):
                    kind = 'date'
                elif isinstance(column.type, (Integer, Numeric)):
                    kind = 'number'
                elif isinstance(column.type, db.Text):
                    kind = 'textarea'
        field_label = name.removesuffix('_id').removesuffix('_minor').replace('_', ' ').title()
        step = '0.0001' if isinstance(column.type, Numeric) else '1'
        hint = ''
        if name.endswith('_minor'):
            kind, step = 'number', '0.01'
            if value != '':
                # URL prefills are untrusted and still use the domain's minor units.
                # Ignore invalid suggestions rather than failing before the form loads.
                try:
                    if not re.fullmatch(r'\d{1,13}', str(value)):
                        raise ValueError('Invalid money prefill')
                    minor = Decimal(str(value))
                    if minor > 9_000_000_000_000:
                        raise ValueError('Money prefill is too large')
                    value = f'{minor / 100:.2f}'
                except (InvalidOperation, ValueError):
                    value = ''
            hint = 'Amount in the record currency, for example 500.00. No currency symbol.'
        elif isinstance(column.type, m.UTCDateTime):
            kind, step = 'datetime-local', 'any'
            hint = f'Local date and time in {workspace_zone()}. Saved with its timezone.'
            if value and hasattr(value, 'astimezone'):
                value = value.astimezone(workspace_zone()).replace(tzinfo=None).isoformat()
        if posted is not None and name in posted:
            value = posted[name]
        result.append({'name': name, 'label': field_label,
                       'kind': kind, 'value': value, 'options': options,
                       'required': not column.nullable and column.default is None,
                       'step': step, 'hint': hint, 'error': (errors or {}).get(name, '')})
    return result


@bp.get('/<resource>')
def index(resource):
    query = query_for(resource)
    page = db.paginate(query, page=max(1, request.args.get('page', 1, type=int) or 1),
                       per_page=30, error_out=False)
    return render_template('hub/index.html', resource=resource, page=page)


@bp.route('/<resource>/new', methods=['GET', 'POST'])
@bp.route('/<resource>/<record_id>/edit', methods=['GET', 'POST'])
def edit(resource, record_id=None):
    access(resource, write=True)
    record = core.get_record(resource, record_id, g.workspace.id) if record_id else None
    if resource == 'documents' and record:
        storage.may_read(record, g.workspace.id, g.hub_user.id)
    fields = form_fields(resource, record)
    if request.method == 'POST':
        posted = {key: value for key, value in request.form.items()
                  if key not in {'csrf_token', '_hub_units'}}
        values, errors = dict(posted), {}
        columns = {column.name: column for column in core.fields_for(resource)}
        for name, value in posted.items():
            if name not in columns:
                continue  # The domain layer rejects unrecognized fields.
            column = columns[name]
            try:
                if value and request.form.get('_hub_units') == 'major':
                    if name.endswith('_minor'):
                        if not re.fullmatch(r'-?\d+(?:\.\d{1,2})?', value.strip()):
                            raise ValueError('Enter an amount with at most two decimal places.')
                        amount = Decimal(value.strip()) * 100
                        if abs(amount) > 9_000_000_000_000:
                            raise ValueError('Amount is too large.')
                        values[name] = str(int(amount))
                    elif isinstance(column.type, m.UTCDateTime):
                        local = datetime.fromisoformat(value)
                        if local.tzinfo is not None:
                            raise ValueError('Use the local date and time shown on this form.')
                        zone = workspace_zone()
                        aware = local.replace(tzinfo=zone)
                        current = getattr(record, name, None) if record else None
                        if current and current.astimezone(zone).replace(tzinfo=None) == local:
                            aware = current  # Preserve an existing repeated-hour choice.
                        elif aware.astimezone(UTC).astimezone(zone).replace(tzinfo=None) != local:
                            raise ValueError('This time does not exist because the clocks change. Choose another time.')
                        elif aware.utcoffset() != local.replace(tzinfo=zone, fold=1).utcoffset():
                            raise ValueError('This time occurs twice when the clocks change. Choose a time outside that repeated hour.')
                        values[name] = aware.isoformat()
                if values[name] != '' or (not column.nullable and not column.default):
                    core.convert(column, values[name])
            except (ValueError, InvalidOperation, OverflowError) as error:
                errors[name] = str(error) if not isinstance(error, InvalidOperation) else 'Enter a valid amount.'
        if not record:
            values = {key: value for key, value in values.items() if value != ''}
        message = None
        if not errors:
            try:
                with core.write_lock():
                    saved = core.save(resource, values, g.workspace.id, g.hub_user.id, record_id)
                    db.session.commit()
                flash('Changes saved.')
                return redirect(context_url('hub.detail', resource=resource, record_id=saved.id), code=303)
            except (ValueError, IntegrityError) as error:
                db.session.rollback()
                message = str(error) if isinstance(error, ValueError) else 'That change conflicts with an existing record or required relationship. Review your values and try again.'
        fields = form_fields(resource, record, posted=posted, errors=errors)
        return render_template('hub/form.html', resource=resource, record=record, fields=fields,
                               errors=errors, form_error=message), 400
    return render_template('hub/form.html', resource=resource, record=record, fields=fields)



@bp.get('/<resource>/<record_id>')
def detail(resource, record_id):
    access(resource)
    record = core.get_record(resource, record_id, g.workspace.id)
    if resource == 'documents':
        storage.may_read(record, g.workspace.id, g.hub_user.id)
    related = {}
    reference = {'businesses': 'business_id', 'projects': 'project_id', 'tasks': 'task_id',
                 'invoices': 'invoice_id', 'payments': 'payment_id', 'digital_assets': 'asset_id',
                 'contracts': 'contract_id', 'pipelines': 'pipeline_id'}.get(resource)
    if reference:
        for name, model in core.RESOURCES.items():
            if not hasattr(model, reference) or (name in core.FINANCE and g.membership.role not in {'owner', 'admin'}):
                continue
            statement = db.select(model).where(model.workspace_id == g.workspace.id,
                                                getattr(model, reference) == record.id)
            if name == 'documents' and g.membership.role not in {'owner', 'admin'}:
                statement = statement.where(m.Document.confidential.is_(False))
            related[name] = db.session.scalars(statement.order_by(model.created_at).limit(100)).all()
    versions = db.session.scalars(db.select(m.DocumentVersion).where(m.DocumentVersion.document_id == record.id)
                                  .order_by(m.DocumentVersion.version_number.desc())).all() if resource == 'documents' else []
    history = db.session.scalars(db.select(m.AuditEvent).where(m.AuditEvent.workspace_id == g.workspace.id,
        m.AuditEvent.entity_id == record.id).order_by(m.AuditEvent.occurred_at.desc()).limit(20)).all()
    values = []
    for col in record.__table__.columns:
        if col.name in {'id', 'workspace_id', 'created_at', 'updated_at'}:
            continue
        value, link = getattr(record, col.name), None
        if value and col.foreign_keys:
            kind = next(iter(col.foreign_keys)).column.table.name.removeprefix('hub_')
            if kind in core.RESOURCES and not (kind in core.FINANCE and g.membership.role not in {'owner', 'admin'}):
                linked = core.get_record(kind, value, g.workspace.id)
                value, link = label(linked), url_for('hub.detail', resource=kind, record_id=linked.id)
        if value is not None:
            display_name = col.name.replace('_', ' ').title()
            if col.name.endswith('_minor'):
                display_name = col.name.removesuffix('_minor').replace('_', ' ').title()
                value = f'{getattr(record, "currency", "")} {Decimal(value) / 100:,.2f}'.strip()
            elif isinstance(col.type, m.UTCDateTime):
                value = value.astimezone(workspace_zone()).strftime('%b %d, %Y · %H:%M %Z')
            values.append((display_name, value, link))
    return render_template('hub/detail.html', resource=resource, record=record, values=values,
                           related=related, reference=reference, versions=versions, history=history,
                           editable=resource not in core.IMMUTABLE, outstanding=core.outstanding)


@bp.post('/documents/<record_id>/versions')
def upload_version(record_id):
    file = request.files.get('file')
    if not file:
        raise ValueError('Select a document to upload.')
    with core.write_lock():
        storage.upload(record_id, file, g.workspace.id, g.hub_user.id)
    flash('A new immutable version was saved.')
    return redirect(url_for('hub.detail', resource='documents', record_id=record_id), code=303)


@bp.get('/documents/<record_id>/versions/<version_id>/download')
def download(record_id, version_id):
    document = core.get_record('documents', record_id, g.workspace.id)
    storage.may_read(document, g.workspace.id, g.hub_user.id)
    version = core.get_record('document_versions', version_id, g.workspace.id)
    if version.document_id != document.id:
        abort(404)
    core.audit(g.workspace.id, g.hub_user.id, 'download', version)
    db.session.commit()
    response = send_file(storage.StorageService().path(version.storage_key), as_attachment=True,
                         download_name=version.original_name, mimetype='application/octet-stream', conditional=False)
    response.headers['Content-Security-Policy'] = "sandbox; default-src 'none'"
    return response


@bp.route('/api/<resource>', methods=['GET', 'POST'])
@bp.route('/api/<resource>/<record_id>', methods=['GET', 'PATCH'])
def api(resource, record_id=None):
    access(resource, write=request.method != 'GET')
    if record_id and resource == 'documents':
        storage.may_read(core.get_record(resource, record_id, g.workspace.id), g.workspace.id, g.hub_user.id)
    if request.method == 'GET':
        if record_id:
            return jsonify(core.serialize(core.get_record(resource, record_id, g.workspace.id)))
        page = db.paginate(query_for(resource), per_page=50, max_per_page=100, error_out=False)
        return jsonify(items=[core.serialize(item) for item in page.items], total=page.total, page=page.page)
    values = request.get_json()
    with core.write_lock():
        record = core.save(resource, values, g.workspace.id, g.hub_user.id, record_id)
        db.session.commit()
    return jsonify(core.serialize(record)), 200 if record_id else 201


@bp.get('/export/<resource>')
def export(resource):
    access(resource)
    core.membership(g.workspace.id, g.hub_user.id, admin=True)
    records = db.session.scalars(query_for(resource).limit(10001)).all()
    if len(records) > 10000:
        raise ValueError('Filter the export to at most 10,000 records.')
    core.audit(g.workspace.id, g.hub_user.id, 'export', g.workspace)
    db.session.commit()
    response = jsonify([core.serialize(record) for record in records])
    response.headers['Content-Disposition'] = f'attachment; filename="{resource}.json"'
    return response


@bp.post('/projects/<record_id>/website-template')
def website_template(record_id):
    core.membership(g.workspace.id, g.hub_user.id, write=True)
    project = core.get_record('projects', record_id, g.workspace.id)
    with core.write_lock():
        if db.session.scalar(db.select(m.Task.id).where(m.Task.project_id == project.id)):
            raise ValueError('Apply the template to an empty project.')
        for index, name in enumerate(('Discovery', 'Content & design', 'Build', 'Review & launch')):
            section = core.save('project_sections', {'project_id': project.id, 'name': name, 'sort_order': index},
                                g.workspace.id, g.hub_user.id)
            for position, task in enumerate({
                'Discovery': ['Discovery call', 'Confirm scope and contract'],
                'Content & design': ['Collect client content', 'Record design approval'],
                'Build': ['Build website', 'Accessibility and device checks'],
                'Review & launch': ['Record client launch approval', 'Launch and handoff'],
            }[name]):
                core.save('tasks', {'project_id': project.id, 'section_id': section.id, 'title': task,
                                    'position': position}, g.workspace.id, g.hub_user.id)
        db.session.commit()
    return redirect(url_for('hub.detail', resource='projects', record_id=record_id), code=303)


@bp.get('/pipeline')
@bp.get('/projects/<record_id>/board')
def board(record_id=None):
    scope = g.workspace.id
    if record_id:
        project = core.get_record('projects', record_id, scope)
        sections = db.session.scalars(db.select(m.ProjectSection).where(
            m.ProjectSection.project_id == project.id).order_by(m.ProjectSection.sort_order)).all()
        items = db.session.scalars(db.select(m.Task).where(m.Task.project_id == project.id)
                                  .order_by(m.Task.position, m.Task.created_at)).all()
        lanes = [(section.id, section.name) for section in sections] + [('', 'Unassigned')]
        return render_template('hub/board.html', resource='tasks', heading=project.title,
            lanes=lanes, items=items, lane_field='section_id', parent={'project_id': project.id},
            project=project)
    pipeline_id = request.args.get('pipeline_id')
    pipeline = core.get_record('pipelines', pipeline_id, scope) if pipeline_id else db.session.scalar(
        db.select(m.Pipeline).where(m.Pipeline.workspace_id == scope).order_by(m.Pipeline.created_at))
    if pipeline is None:
        return redirect(url_for('hub.index', resource='pipelines'))
    stages = db.session.scalars(db.select(m.PipelineStage).where(
        m.PipelineStage.pipeline_id == pipeline.id).order_by(m.PipelineStage.sort_order)).all()
    items = db.session.scalars(db.select(m.Opportunity).where(m.Opportunity.pipeline_id == pipeline.id)
                              .order_by(m.Opportunity.created_at)).all()
    return render_template('hub/board.html', resource='opportunities', heading=pipeline.name,
        lanes=[(stage.id, stage.name) for stage in stages], items=items, lane_field='stage_id',
        parent={'pipeline_id': pipeline.id}, project=None)


@bp.post('/<resource>/<record_id>/move')
def move(resource, record_id):
    if resource not in {'tasks', 'opportunities'}:
        abort(404)
    field = 'section_id' if resource == 'tasks' else 'stage_id'
    with core.write_lock():
        record = core.get_record(resource, record_id, g.workspace.id)
        values = {field: request.form.get(field)}
        if resource == 'tasks':
            values['position'] = db.session.scalar(db.select(db.func.coalesce(db.func.max(m.Task.position), 0)).where(
                m.Task.project_id == record.project_id, m.Task.section_id == (values[field] or None))) + 1
        core.save(resource, values, g.workspace.id, g.hub_user.id, record_id)
        db.session.commit()
    if request.headers.get('Accept') == 'application/json':
        return jsonify(ok=True)
    return redirect(url_for('hub.board', record_id=record.project_id) if resource == 'tasks'
                    else url_for('hub.board', pipeline_id=record.pipeline_id), code=303)


@bp.post('/<resource>/<record_id>/transition')
def transition(resource, record_id):
    if resource not in {'invoices', 'payments', 'businesses'}:
        abort(404)
    field = 'lifecycle_status' if resource == 'businesses' else 'status'
    with core.write_lock():
        core.save(resource, {field: request.form.get('status')}, g.workspace.id, g.hub_user.id, record_id)
        db.session.commit()
    return redirect(url_for('hub.detail', resource=resource, record_id=record_id), code=303)
