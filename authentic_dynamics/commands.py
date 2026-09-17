"""Local commands for reviewing stored contact inquiries."""

import click
from flask.cli import with_appcontext

from .extensions import db
from .models import AdminSession, AdminUser, ContactSubmission


@click.group("contacts")
def contacts():
    """Review locally stored contact inquiries."""


@contacts.command("list")
@click.option("--limit", type=click.IntRange(min=1, max=500), default=20, show_default=True)
@with_appcontext
def list_contacts(limit: int):
    """List the newest inquiries."""
    submissions = db.session.execute(
        db.select(ContactSubmission).order_by(ContactSubmission.id.desc()).limit(limit)
    ).scalars()
    for item in submissions:
        click.echo(f"{item.id}\t{item.created_at.isoformat()}\t{item.name}\t{item.email}\t{item.interest}")


@contacts.command("show")
@click.argument("submission_id", type=int)
@with_appcontext
def show_contact(submission_id: int):
    """Show one inquiry, including its message."""
    item = db.session.get(ContactSubmission, submission_id)
    if item is None:
        raise click.ClickException(f"No submission with ID {submission_id}.")
    click.echo(
        f"ID: {item.id}\nCreated: {item.created_at.isoformat()} UTC\n"
        f"Name: {item.name}\nBusiness: {item.business}\nEmail: {item.email}\n"
        f"Interest: {item.interest}\nSource: {item.source_page}\n\n{item.message}"
    )


@click.group("admin")
def admin():
    """Manage private admin accounts without storing plaintext credentials."""


def validate_credentials(email, password):
    email = email.strip().lower()
    if not email or "@" not in email or len(email) > 254:
        raise click.ClickException("Enter a valid email address.")
    if not 12 <= len(password) <= 128:
        raise click.ClickException("Use a password between 12 and 128 characters.")
    return email


@admin.command("create")
@click.option("--email", prompt=True)
@click.password_option()
@with_appcontext
def create_admin(email, password):
    """Create an admin; the password prompt is hidden."""
    email = validate_credentials(email, password)
    if db.session.scalar(db.select(AdminUser).where(AdminUser.email == email)):
        raise click.ClickException("This admin already exists. Use admin reset-password.")
    user = AdminUser(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo("Admin created. Sign in at /admin/login.")


@admin.command("reset-password")
@click.option("--email", prompt=True)
@click.password_option()
@with_appcontext
def reset_admin_password(email, password):
    """Reset a forgotten password and revoke all existing sessions."""
    email = validate_credentials(email, password)
    user = db.session.scalar(db.select(AdminUser).where(AdminUser.email == email))
    if not user:
        raise click.ClickException("No admin exists with that email.")
    user.set_password(password)
    db.session.execute(db.delete(AdminSession).where(AdminSession.user_id == user.id))
    db.session.commit()
    click.echo("Password reset. All existing sessions have been signed out.")
