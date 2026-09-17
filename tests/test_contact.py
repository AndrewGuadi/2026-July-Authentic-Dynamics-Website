"""Contact inquiries should be validated, protected, and persisted."""

import re

import pytest

from authentic_dynamics import create_app
from authentic_dynamics.extensions import db
from authentic_dynamics.models import ContactSubmission


@pytest.fixture
def contact_app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'contacts.db'}",
            "SESSION_COOKIE_SECURE": False,
        }
    )
    result = app.test_cli_runner().invoke(args=["db", "upgrade"])
    assert result.exit_code == 0, result.output
    return app


def csrf_token(client, page):
    response = client.get(page)
    assert response.status_code == 200
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
    assert match
    return match.group(1)


def valid_contact(source_page, token):
    return {
        "csrf_token": token,
        "source_page": source_page,
        "name": "Taylor Example",
        "business": "Local Business",
        "email": "taylor@example.com",
        "interest": "Small business website — from $500",
        "message": "I would like to discuss a new business website.",
    }


@pytest.mark.parametrize(("page", "source"), [("/", "home"), ("/about-community", "about")])
def test_contact_form_saves_to_sqlite_and_redirects(contact_app, page, source):
    client = contact_app.test_client()
    response = client.post("/contact", data=valid_contact(source, csrf_token(client, page)))

    assert response.status_code == 303
    assert response.headers["Location"] == f"{page}#contact"
    with contact_app.app_context():
        records = db.session.execute(db.select(ContactSubmission)).scalars().all()
        assert len(records) == 1
        assert records[0].email == "taylor@example.com"
        assert records[0].source_page == source

    confirmation = client.get(page)
    assert b"Your inquiry was saved" in confirmation.data


def test_contact_form_rejects_invalid_data_without_saving(contact_app):
    client = contact_app.test_client()
    payload = valid_contact("home", csrf_token(client, "/"))
    payload.update(email="not-an-email", message="short")

    response = client.post("/contact", data=payload)

    assert response.status_code == 400
    assert b"Enter a valid email address" in response.data
    assert b"Tell us a little more" in response.data
    with contact_app.app_context():
        assert db.session.execute(db.select(ContactSubmission)).first() is None


def test_contact_form_requires_csrf_token(contact_app):
    response = contact_app.test_client().post(
        "/contact", data=valid_contact("home", "")
    )

    assert response.status_code == 400
    with contact_app.app_context():
        assert db.session.execute(db.select(ContactSubmission)).first() is None


def test_saved_contact_can_be_reviewed_from_cli(contact_app):
    client = contact_app.test_client()
    client.post("/contact", data=valid_contact("about", csrf_token(client, "/about-community")))
    runner = contact_app.test_cli_runner()

    listing = runner.invoke(args=["contacts", "list"])
    detail = runner.invoke(args=["contacts", "show", "1"])

    assert listing.exit_code == 0
    assert "taylor@example.com" in listing.output
    assert detail.exit_code == 0
    assert "I would like to discuss a new business website." in detail.output
