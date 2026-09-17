"""Persistent website data."""

from datetime import UTC, datetime

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
