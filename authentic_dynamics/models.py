"""Persistent website data."""

from datetime import UTC, datetime

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class ContactSubmission(db.Model):
    __tablename__ = "contact_submissions"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    name = db.Column(db.String(120), nullable=False)
    business = db.Column(db.String(120), nullable=False, default="")
    email = db.Column(db.String(254), nullable=False)
    interest = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    source_page = db.Column(db.String(20), nullable=False)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)


class AdminUser(db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class AdminSession(db.Model):
    __tablename__ = "admin_sessions"

    token_hash = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("admin_users.id"), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)


class AdminLoginAttempt(db.Model):
    __tablename__ = "admin_login_attempts"

    id = db.Column(db.Integer, primary_key=True)
    ip_key = db.Column(db.String(64), nullable=False, index=True)
    email_key = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
