"""Admin authentication and inquiry access must preserve the privacy boundary."""

import re
from datetime import UTC, datetime, timedelta

import pytest

from authentic_dynamics import create_app
from authentic_dynamics.extensions import db
from authentic_dynamics.models import AdminLoginAttempt, AdminSession, AdminUser, ContactSubmission

PASSWORD = "test-only-admin-password"


@pytest.fixture
def app(tmp_path):
    application = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-only-secret",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'admin.db'}",
        "SESSION_COOKIE_SECURE": False,
    })
    runner = application.test_cli_runner()
    result = runner.invoke(args=["db", "upgrade"])
    assert result.exit_code == 0, result.output
    result = runner.invoke(
        args=["admin", "create", "--email", "owner@example.com"],
        input=f"{PASSWORD}\n{PASSWORD}\n",
    )
    assert result.exit_code == 0, result.output
    with application.app_context():
        db.session.add(ContactSubmission(
            name="Local Owner", business="Example Business", email="client@example.com",
            interest="Small business website — from $500", source_page="home",
            message="Please help with our site. <script>alert('unsafe')</script>",
        ))
        db.session.commit()
    return application


def token(client, path="/admin/login"):
    response = client.get(path)
    assert response.status_code == 200
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match
    return match[1]


def login(client, password=PASSWORD, email="owner@example.com"):
    return client.post("/admin/login", data={
        "csrf_token": token(client), "email": email, "password": password,
    })


@pytest.mark.parametrize("path", ["/admin", "/admin/", "/admin/inquiries/1", "/admin/password"])
def test_anonymous_visitors_cannot_read_private_data(app, path):
    response = app.test_client().get(path)
    assert response.status_code == 303
    assert response.location == "/admin/login"
    assert "client@example.com" not in response.text
    assert "no-store" in response.headers["Cache-Control"]
    assert "noindex" in response.headers["X-Robots-Tag"]


def test_successful_login_search_detail_and_review(app):
    client = app.test_client()
    assert login(client, email=" OWNER@EXAMPLE.COM ").status_code == 303
    assert "Example Business" in client.get("/admin/?q=example").text
    assert "Example Business" not in client.get("/admin/?q=missing").text
    detail = client.get("/admin/inquiries/1")
    assert "&lt;script&gt;" in detail.text
    assert "<script>alert" not in detail.text
    assert "no-store" in detail.headers["Cache-Control"]
    with app.app_context():
        assert db.session.get(ContactSubmission, 1).reviewed_at is None
    response = client.post("/admin/inquiries/1/status", data={
        "csrf_token": token(client, "/admin/inquiries/1"), "status": "reviewed",
    })
    assert response.status_code == 303
    assert "Local Owner" not in client.get("/admin/?status=new").text
    assert "Local Owner" in client.get("/admin/?status=reviewed").text


def test_password_hash_and_session_revocation_on_logout(app):
    client = app.test_client()
    login(client)
    with client.session_transaction() as session:
        saved_session = dict(session)
    with app.app_context():
        user = db.session.scalar(db.select(AdminUser))
        assert user.password_hash != PASSWORD
        assert user.password_hash.startswith("scrypt:")
        assert user.check_password(PASSWORD)
    assert client.get("/admin/logout").status_code == 405
    assert client.post("/admin/logout", data={
        "csrf_token": token(client, "/admin/"),
    }).status_code == 303
    with client.session_transaction() as session:
        session.update(saved_session)
    assert client.get("/admin/").location == "/admin/login"


def test_csrf_required_for_login_and_admin_actions(app):
    client = app.test_client()
    assert client.post("/admin/login", data={
        "email": "owner@example.com", "password": PASSWORD,
    }).status_code == 400
    login(client)
    for path in ("/admin/logout", "/admin/password", "/admin/inquiries/1/status"):
        assert client.post(path, data={"status": "reviewed"}).status_code == 400
    with app.app_context():
        assert db.session.get(ContactSubmission, 1).reviewed_at is None


def test_login_throttling_survives_new_client_and_expires(app):
    client = app.test_client()
    for _ in range(5):
        assert login(client, password="wrong").status_code == 401
    response = login(app.test_client())
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "900"
    with app.app_context():
        db.session.execute(db.update(AdminLoginAttempt).values(
            created_at=datetime.now(UTC) - timedelta(minutes=16)
        ))
        db.session.commit()
    assert login(client).status_code == 303


def test_expired_session_cannot_access_inbox(app):
    client = app.test_client()
    login(client)
    with app.app_context():
        db.session.execute(db.update(AdminSession).values(
            expires_at=datetime.now(UTC) - timedelta(seconds=1)
        ))
        db.session.commit()
    assert client.get("/admin/").location == "/admin/login"


def test_password_change_rejects_wrong_current_and_revokes_other_sessions(app):
    client = app.test_client()
    other = app.test_client()
    login(client)
    login(other)
    values = {
        "csrf_token": token(client, "/admin/password"), "current_password": "wrong",
        "new_password": "new-test-password-only", "confirm_password": "new-test-password-only",
    }
    assert client.post("/admin/password", data=values).status_code == 400
    assert other.get("/admin/").status_code == 200
    values["current_password"] = PASSWORD
    assert client.post("/admin/password", data=values).status_code == 303
    assert client.get("/admin/").status_code == 200
    assert other.get("/admin/").location == "/admin/login"
    fresh = app.test_client()
    assert login(fresh, password=PASSWORD).status_code == 401
    assert login(fresh, password="new-test-password-only").status_code == 303


def test_cli_reset_revokes_sessions_and_duplicate_create_is_rejected(app):
    client = app.test_client()
    login(client)
    runner = app.test_cli_runner()
    duplicate = runner.invoke(args=["admin", "create", "--email", "owner@example.com"],
                              input=f"{PASSWORD}\n{PASSWORD}\n")
    assert duplicate.exit_code != 0
    result = runner.invoke(args=["admin", "reset-password", "--email", "owner@example.com"],
                           input="reset-test-password\nreset-test-password\n")
    assert result.exit_code == 0
    assert client.get("/admin/").location == "/admin/login"
    assert login(client, password="reset-test-password").status_code == 303


def test_contact_submission_appears_in_authenticated_inbox(app):
    visitor = app.test_client()
    response = visitor.post("/contact", data={
        "csrf_token": token(visitor, "/"), "name": "New Visitor", "business": "",
        "email": "new@example.com", "interest": "Not sure yet — let’s talk",
        "message": "I would like to plan a new website.", "source_page": "about",
    })
    assert response.status_code == 303
    owner = app.test_client()
    login(owner)
    assert "New Visitor" in owner.get("/admin/?status=new").text


def test_pagination_does_not_drop_inquiries(app):
    with app.app_context():
        for index in range(21):
            db.session.add(ContactSubmission(
                name=f"Owner {index}", business="", email="contact@example.com",
                interest="Local visibility & marketing", source_page="home", message="Hello there!",
            ))
        db.session.commit()
    client = app.test_client()
    login(client)
    assert "Page 1 of 2" in client.get("/admin/").text
    assert "Local Owner" not in client.get("/admin/").text
    assert "Local Owner" in client.get("/admin/?page=2").text


def test_admin_migration_keeps_existing_contact_data(tmp_path):
    application = create_app({
        "TESTING": True,
        "SECRET_KEY": "migration-test-only",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'existing.db'}",
    })
    runner = application.test_cli_runner()
    assert runner.invoke(args=["db", "upgrade", "9ddf55f2e5d2"]).exit_code == 0
    with application.app_context():
        db.session.execute(db.text(
            "INSERT INTO contact_submissions "
            "(created_at, name, business, email, interest, message, source_page) "
            "VALUES (:created, :name, '', :email, :interest, :message, 'home')"
        ), {"created": datetime.now(UTC).isoformat(), "name": "Existing Owner",
            "email": "existing@example.com", "interest": "A website",
            "message": "Please keep this existing inquiry."})
        db.session.commit()
    result = runner.invoke(args=["db", "upgrade"])
    assert result.exit_code == 0, result.output
    with application.app_context():
        item = db.session.get(ContactSubmission, 1)
        assert item.name == "Existing Owner"
        assert item.message == "Please keep this existing inquiry."
        assert item.reviewed_at is None


def test_anonymous_status_change_is_blocked_even_with_valid_csrf(app):
    client = app.test_client()
    response = client.post("/admin/inquiries/1/status", data={
        "csrf_token": token(client), "status": "reviewed",
    })
    assert response.location == "/admin/login"
    with app.app_context():
        assert db.session.get(ContactSubmission, 1).reviewed_at is None
