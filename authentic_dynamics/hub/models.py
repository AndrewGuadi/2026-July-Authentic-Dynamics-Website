"""Portable Business Hub schema; legacy authentication and inquiry tables stay intact."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.types import TypeDecorator

from authentic_dynamics.extensions import db


def now():
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator):
    """Persist naive UTC on both databases and always return aware UTC values."""

    impl = db.DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("A timezone offset is required")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=UTC) if value is not None else None


def ref(table, nullable=False):
    return db.Column(db.String(36), db.ForeignKey(f"hub_{table}.id"), nullable=nullable, index=True)


def enum_check(field, values):
    return db.CheckConstraint(f"{field} IN ({','.join(repr(v) for v in values.split())})",
                              name=f"ck_{field}")


class Record:
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at = db.Column(UTCDateTime(), nullable=False, default=now)
    updated_at = db.Column(UTCDateTime(), nullable=False, default=now, onupdate=now)


class Scoped(Record):
    workspace_id = ref("workspaces")


class Workspace(Record, db.Model):
    __tablename__ = "hub_workspaces"
    name = db.Column(db.String(200), nullable=False)
    legal_name = db.Column(db.String(250), nullable=False, default="")
    timezone = db.Column(db.String(80), nullable=False, default="America/New_York")
    settings_json = db.Column(db.JSON, nullable=False, default=dict)


class User(Record, db.Model):
    __tablename__ = "hub_users"
    admin_user_id = db.Column(db.Integer, db.ForeignKey("admin_users.id"), unique=True, nullable=False)
    display_name = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class Membership(Scoped, db.Model):
    __tablename__ = "hub_workspace_memberships"
    user_id = ref("users")
    role = db.Column(db.String(20), nullable=False)
    __table_args__ = (db.UniqueConstraint("workspace_id", "user_id"),
                      enum_check("role", "owner admin staff read_only"))


class AuditEvent(Scoped, db.Model):
    __tablename__ = "hub_audit_events"
    actor_id = ref("users", True)
    action = db.Column(db.String(80), nullable=False)
    entity_type = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.String(36), nullable=False, index=True)
    occurred_at = db.Column(UTCDateTime(), nullable=False, default=now)
    change_json = db.Column(db.JSON, nullable=False, default=dict)
    request_id = db.Column(db.String(36), nullable=True)


class RecordLink(Scoped, db.Model):
    __tablename__ = "hub_record_links"
    from_type = db.Column(db.String(80), nullable=False)
    from_id = db.Column(db.String(36), nullable=False)
    to_type = db.Column(db.String(80), nullable=False)
    to_id = db.Column(db.String(36), nullable=False)
    link_type = db.Column(db.String(80), nullable=False)
    __table_args__ = (db.UniqueConstraint("workspace_id", "from_type", "from_id", "to_type", "to_id",
                                         "link_type"),)


class Business(Scoped, db.Model):
    __tablename__ = "hub_businesses"
    name = db.Column(db.String(200), nullable=False, index=True)
    website_url = db.Column(db.String(1000), nullable=True)
    industry = db.Column(db.String(150), nullable=True)
    lifecycle_status = db.Column(db.String(20), nullable=False, default="prospect")
    source = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    __table_args__ = (enum_check("lifecycle_status", "prospect active inactive archived"),)


class Person(Scoped, db.Model):
    __tablename__ = "hub_people"
    name = db.Column(db.String(200), nullable=False, index=True)
    email = db.Column(db.String(254), nullable=True)
    phone = db.Column(db.String(80), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active")
    __table_args__ = (enum_check("status", "active archived"),)


class BusinessContact(Scoped, db.Model):
    __tablename__ = "hub_business_contacts"
    business_id = ref("businesses")
    person_id = ref("people")
    title = db.Column(db.String(200), nullable=True)
    is_primary = db.Column(db.Boolean, nullable=False, default=False)
    __table_args__ = (db.UniqueConstraint("business_id", "person_id"),)


class Pipeline(Scoped, db.Model):
    __tablename__ = "hub_pipelines"
    name = db.Column(db.String(200), nullable=False)
    pipeline_type = db.Column(db.String(30), nullable=False, default="sales")
    is_default = db.Column(db.Boolean, nullable=False, default=False)


class PipelineStage(Scoped, db.Model):
    __tablename__ = "hub_pipeline_stages"
    pipeline_id = ref("pipelines")
    name = db.Column(db.String(100), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False)
    is_terminal = db.Column(db.Boolean, nullable=False, default=False)
    __table_args__ = (db.UniqueConstraint("pipeline_id", "name"),)


class Opportunity(Scoped, db.Model):
    __tablename__ = "hub_opportunities"
    business_id = ref("businesses")
    pipeline_id = ref("pipelines")
    stage_id = ref("pipeline_stages")
    title = db.Column(db.String(250), nullable=False)
    estimated_value_minor = db.Column(db.BigInteger, nullable=False, default=0)
    currency = db.Column(db.String(3), nullable=False, default="USD")
    expected_close_date = db.Column(db.Date, nullable=True)
    owner_id = ref("users", True)
    description = db.Column(db.Text, nullable=True)
    __table_args__ = (db.CheckConstraint("estimated_value_minor >= 0"),)


class Activity(Scoped, db.Model):
    __tablename__ = "hub_activities"
    business_id = ref("businesses")
    person_id = ref("people", True)
    opportunity_id = ref("opportunities", True)
    type = db.Column(db.String(30), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    occurred_at = db.Column(UTCDateTime(), nullable=False, default=now)
    next_action_at = db.Column(UTCDateTime(), nullable=True, index=True)
    __table_args__ = (enum_check("type", "call meeting follow_up note"),)


class Project(Scoped, db.Model):
    __tablename__ = "hub_projects"
    business_id = ref("businesses")
    opportunity_id = ref("opportunities", True)
    title = db.Column(db.String(250), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="planned")
    start_date = db.Column(db.Date, nullable=True)
    target_date = db.Column(db.Date, nullable=True)
    owner_id = ref("users", True)
    __table_args__ = (enum_check("status", "planned active on_hold completed canceled archived"),)


class ProjectSection(Scoped, db.Model):
    __tablename__ = "hub_project_sections"
    project_id = ref("projects")
    name = db.Column(db.String(100), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False)


class Task(Scoped, db.Model):
    __tablename__ = "hub_tasks"
    project_id = ref("projects")
    section_id = ref("project_sections", True)
    parent_task_id = ref("tasks", True)
    assignee_id = ref("users", True)
    title = db.Column(db.String(250), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), nullable=False, default="todo")
    priority = db.Column(db.String(20), nullable=False, default="normal")
    blocked_reason = db.Column(db.Text, nullable=True)
    due_at = db.Column(UTCDateTime(), nullable=True, index=True)
    position = db.Column(db.Integer, nullable=False, default=0)
    __table_args__ = (enum_check("status", "todo in_progress blocked review done canceled"),
                      enum_check("priority", "low normal high urgent"),
                      db.CheckConstraint("position >= 0"),
                      db.CheckConstraint("parent_task_id IS NULL OR parent_task_id != id"))


class TaskDependency(Scoped, db.Model):
    __tablename__ = "hub_task_dependencies"
    task_id = ref("tasks")
    depends_on_task_id = ref("tasks")
    __table_args__ = (db.UniqueConstraint("task_id", "depends_on_task_id"),
                      db.CheckConstraint("task_id != depends_on_task_id"))


class TaskComment(Scoped, db.Model):
    __tablename__ = "hub_task_comments"
    task_id = ref("tasks")
    author_id = ref("users")
    body = db.Column(db.Text, nullable=False)


class Milestone(Scoped, db.Model):
    __tablename__ = "hub_milestones"
    project_id = ref("projects")
    title = db.Column(db.String(250), nullable=False)
    due_at = db.Column(UTCDateTime(), nullable=True)
    completed_at = db.Column(UTCDateTime(), nullable=True)


class Document(Scoped, db.Model):
    __tablename__ = "hub_documents"
    title = db.Column(db.String(250), nullable=False)
    category = db.Column(db.String(30), nullable=False, default="other")
    business_id = ref("businesses", True)
    project_id = ref("projects", True)
    created_by = ref("users")
    # The immutable versions are inserted before this pointer is updated.
    current_version_id = db.Column(db.String(36), db.ForeignKey(
        "hub_document_versions.id", name="fk_document_current_version", use_alter=True), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active")
    confidential = db.Column(db.Boolean, nullable=False, default=True)
    __table_args__ = (enum_check("status", "active archived"), enum_check("category",
        "proposal signed_contract draft_contract invoice_copy client_asset creative operational receipt other"))


class DocumentVersion(Scoped, db.Model):
    __tablename__ = "hub_document_versions"
    document_id = ref("documents")
    version_number = db.Column(db.Integer, nullable=False)
    storage_key = db.Column(db.String(80), nullable=False, unique=True)
    sha256 = db.Column(db.String(64), nullable=False)
    size_bytes = db.Column(db.BigInteger, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    original_name = db.Column(db.String(250), nullable=False)
    uploaded_by = ref("users")
    uploaded_at = db.Column(UTCDateTime(), nullable=False, default=now)
    __table_args__ = (db.UniqueConstraint("document_id", "version_number"),
                      db.CheckConstraint("version_number > 0"), db.CheckConstraint("size_bytes > 0"))


class Approval(Scoped, db.Model):
    __tablename__ = "hub_approvals"
    project_id = ref("projects")
    subject_type = db.Column(db.String(80), nullable=False)
    subject_id = db.Column(db.String(36), nullable=False)
    decision = db.Column(db.String(20), nullable=False)
    decided_by_name = db.Column(db.String(200), nullable=False)
    decided_at = db.Column(UTCDateTime(), nullable=False)
    evidence_document_id = ref("documents")
    __table_args__ = (enum_check("decision", "approved rejected changes_requested"),)


class Contract(Scoped, db.Model):
    __tablename__ = "hub_contracts"
    business_id = ref("businesses")
    project_id = ref("projects", True)
    title = db.Column(db.String(250), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="draft")
    effective_date = db.Column(db.Date, nullable=True)
    signed_date = db.Column(db.Date, nullable=True)
    executed_version_id = ref("document_versions", True)
    signature_evidence = db.Column(db.Text, nullable=True)
    expires_on = db.Column(db.Date, nullable=True)
    __table_args__ = (enum_check("status", "draft sent signed expired canceled archived"),
        db.CheckConstraint("status != 'signed' OR (executed_version_id IS NOT NULL "
                           "AND signed_date IS NOT NULL AND signature_evidence IS NOT NULL)"))


class ContractParty(Scoped, db.Model):
    __tablename__ = "hub_contract_parties"
    contract_id = ref("contracts")
    person_id = ref("people", True)
    party_name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    signature_status = db.Column(db.String(30), nullable=False, default="pending")
    __table_args__ = (enum_check("signature_status", "pending recorded declined"),)


class Invoice(Scoped, db.Model):
    __tablename__ = "hub_invoices"
    business_id = ref("businesses")
    project_id = ref("projects", True)
    invoice_number = db.Column(db.String(80), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="draft")
    currency = db.Column(db.String(3), nullable=False, default="USD")
    total_minor = db.Column(db.BigInteger, nullable=False, default=0)
    __table_args__ = (db.UniqueConstraint("workspace_id", "invoice_number"),
                      db.CheckConstraint("total_minor >= 0"),
                      enum_check("status", "draft issued void"))


class InvoiceLine(Scoped, db.Model):
    __tablename__ = "hub_invoice_lines"
    invoice_id = ref("invoices")
    description = db.Column(db.String(1000), nullable=False)
    quantity_decimal = db.Column(db.Numeric(12, 4), nullable=False)
    unit_amount_minor = db.Column(db.BigInteger, nullable=False)
    line_total_minor = db.Column(db.BigInteger, nullable=False)
    __table_args__ = (db.CheckConstraint("quantity_decimal > 0"),
                      db.CheckConstraint("unit_amount_minor >= 0"),
                      db.CheckConstraint("line_total_minor >= 0"))


class Payment(Scoped, db.Model):
    __tablename__ = "hub_payments"
    business_id = ref("businesses")
    received_on = db.Column(db.Date, nullable=False)
    amount_minor = db.Column(db.BigInteger, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="USD")
    method = db.Column(db.String(80), nullable=False)
    external_reference = db.Column(db.String(250), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    __table_args__ = (db.CheckConstraint("amount_minor > 0"),
                      enum_check("status", "pending posted canceled"))


class PaymentAllocation(Scoped, db.Model):
    __tablename__ = "hub_payment_allocations"
    payment_id = ref("payments")
    invoice_id = ref("invoices")
    allocated_minor = db.Column(db.BigInteger, nullable=False)
    __table_args__ = (db.UniqueConstraint("payment_id", "invoice_id"),
                      db.CheckConstraint("allocated_minor > 0"))


class Expense(Scoped, db.Model):
    __tablename__ = "hub_expenses"
    business_id = ref("businesses", True)
    project_id = ref("projects", True)
    vendor_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    amount_minor = db.Column(db.BigInteger, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="USD")
    incurred_on = db.Column(db.Date, nullable=False)
    document_id = ref("documents", True)
    __table_args__ = (db.CheckConstraint("amount_minor > 0"),)


class DigitalAsset(Scoped, db.Model):
    __tablename__ = "hub_digital_assets"
    business_id = ref("businesses")
    asset_type = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(1000), nullable=True)
    provider = db.Column(db.String(150), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="active")
    renewal_date = db.Column(db.Date, nullable=True, index=True)
    notes = db.Column(db.Text, nullable=True)
    __table_args__ = (enum_check("status", "active inactive archived"), enum_check("asset_type",
        "domain website hosting repository analytics social service other"))


class AssetAccess(Scoped, db.Model):
    __tablename__ = "hub_asset_access"
    asset_id = ref("digital_assets")
    owner_type = db.Column(db.String(30), nullable=False)
    owner_business_id = ref("businesses", True)
    admin_contact_id = ref("people", True)
    payer_type = db.Column(db.String(30), nullable=False)
    credential_vault_reference = db.Column(db.String(500), nullable=True)
    recovery_owner_notes = db.Column(db.Text, nullable=False)
    __table_args__ = (enum_check("owner_type", "ad client third_party"),
                      enum_check("payer_type", "ad client third_party"))


class Integration(Scoped, db.Model):
    __tablename__ = "hub_integrations"
    provider = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="disconnected")
    external_account_ref = db.Column(db.String(250), nullable=True)
    last_synced_at = db.Column(UTCDateTime(), nullable=True)
    __table_args__ = (enum_check("status", "disconnected active error"),)


class ExternalRecordLink(Scoped, db.Model):
    __tablename__ = "hub_external_record_links"
    integration_id = ref("integrations")
    entity_type = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.String(36), nullable=False)
    external_id = db.Column(db.String(250), nullable=False)
    sync_status = db.Column(db.String(30), nullable=False, default="pending")
    last_synced_at = db.Column(UTCDateTime(), nullable=True)
    __table_args__ = (db.UniqueConstraint("integration_id", "entity_type", "external_id"),
                      enum_check("sync_status", "pending synced error"))


class Job(Scoped, db.Model):
    __tablename__ = "hub_job_outbox"
    job_type = db.Column(db.String(80), nullable=False)
    payload_json = db.Column(db.JSON, nullable=False, default=dict)
    status = db.Column(db.String(20), nullable=False, default="pending")
    attempt_count = db.Column(db.Integer, nullable=False, default=0)
    available_at = db.Column(UTCDateTime(), nullable=False, default=now, index=True)
    claimed_at = db.Column(UTCDateTime(), nullable=True)
    lease_until = db.Column(UTCDateTime(), nullable=True)
    idempotency_key = db.Column(db.String(250), nullable=False)
    last_error_redacted = db.Column(db.String(200), nullable=True)
    __table_args__ = (db.UniqueConstraint("workspace_id", "idempotency_key"),
                      enum_check("status", "pending running completed failed"))


class BackupRun(Scoped, db.Model):
    __tablename__ = "hub_backup_runs"
    started_at = db.Column(UTCDateTime(), nullable=False, default=now)
    finished_at = db.Column(UTCDateTime(), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="running")
    manifest_key = db.Column(db.String(80), nullable=True)
    db_sha256 = db.Column(db.String(64), nullable=True)
    file_manifest_sha256 = db.Column(db.String(64), nullable=True)
    verified_at = db.Column(UTCDateTime(), nullable=True)
    offsite_verified_at = db.Column(UTCDateTime(), nullable=True)
    error_redacted = db.Column(db.String(200), nullable=True)
    __table_args__ = (enum_check("status", "running local_verified protected failed"),)


class RestoreTest(Scoped, db.Model):
    __tablename__ = "hub_restore_tests"
    backup_run_id = ref("backup_runs")
    tested_at = db.Column(UTCDateTime(), nullable=False, default=now)
    outcome = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    __table_args__ = (enum_check("outcome", "passed failed"),)


def immutable(mapper, connection, target):
    raise ValueError("Historical records are append-only")


for _model in (AuditEvent, DocumentVersion, Approval, PaymentAllocation, RestoreTest):
    event.listen(_model, "before_update", immutable)
    event.listen(_model, "before_delete", immutable)

MODELS = {model.__tablename__.removeprefix("hub_"): model for model in (
    Workspace, User, Membership, AuditEvent, RecordLink, Business, Person, BusinessContact,
    Pipeline, PipelineStage, Opportunity, Activity, Project, ProjectSection, Task, TaskDependency,
    TaskComment, Milestone, Document, DocumentVersion, Approval, Contract, ContractParty, Invoice,
    InvoiceLine, Payment, PaymentAllocation, Expense, DigitalAsset, AssetAccess, Integration,
    ExternalRecordLink, Job, BackupRun, RestoreTest,
)}
