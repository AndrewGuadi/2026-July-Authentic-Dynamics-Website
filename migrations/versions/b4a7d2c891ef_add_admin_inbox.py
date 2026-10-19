"""Add admin accounts, revocable sessions, login throttling and inquiry review status.

Revision ID: b4a7d2c891ef
Revises: 9ddf55f2e5d2
"""

import sqlalchemy as sa
from alembic import op

revision = "b4a7d2c891ef"
down_revision = "9ddf55f2e5d2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("contact_submissions", sa.Column("reviewed_at", sa.DateTime(timezone=True)))
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
    )
    op.create_table(
        "admin_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("admin_users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_admin_sessions_expires_at", "admin_sessions", ["expires_at"])
    op.create_table(
        "admin_login_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ip_key", sa.String(64), nullable=False),
        sa.Column("email_key", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name in ("ip_key", "email_key", "created_at"):
        op.create_index(f"ix_admin_login_attempts_{name}", "admin_login_attempts", [name])


def downgrade():
    op.drop_table("admin_login_attempts")
    op.drop_table("admin_sessions")
    op.drop_table("admin_users")
    with op.batch_alter_table("contact_submissions") as batch:
        batch.drop_column("reviewed_at")
