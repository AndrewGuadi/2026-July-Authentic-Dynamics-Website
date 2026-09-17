"""Local commands for reviewing stored contact inquiries."""

import click
from flask.cli import with_appcontext

from .extensions import db
from .models import ContactSubmission


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
