"""Authenticated inquiry review with revocable, time-limited sessions."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from flask import abort, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash

from authentic_dynamics.extensions import db
from authentic_dynamics.models import (
    AdminLoginAttempt,
    AdminSession,
    AdminUser,
    ContactSubmission,
)

from . import bp

# Equal-cost password verification even when an email does not exist.
DUMMY_PASSWORD_HASH = generate_password_hash(secrets.token_urlsafe(32), method="scrypt")
SESSION_DURATION = timedelta(hours=8)
LOGIN_WINDOW = timedelta(minutes=15)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def start_session(user):
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    db.session.execute(db.delete(AdminSession).where(AdminSession.expires_at <= now))
    db.session.add(AdminSession(
        token_hash=digest(token), user_id=user.id, expires_at=now + SESSION_DURATION
    ))
    session.clear()
    session["admin_token"] = token


@bp.before_request
def authenticate():
    g.admin_user = None
    token = session.get("admin_token")
    if token:
        record = db.session.get(AdminSession, digest(token))
        if record and record.expires_at.replace(tzinfo=UTC) > datetime.now(UTC):
            g.admin_user = db.session.get(AdminUser, record.user_id)
        if not g.admin_user:
            session.clear()
    if request.endpoint != "admin.login" and not g.admin_user:
        return redirect(url_for("admin.login"), code=303)


@bp.after_request
def private_response(response):
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    # Flask-WTF's HTTPS CSRF check needs the same-origin referrer on form posts.
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.admin_user:
        return redirect(url_for("admin.inbox"), code=303)
    error = None
    status = 200
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()[:254]
        password = request.form.get("password", "")
        now = datetime.now(UTC)
        cutoff = now - LOGIN_WINDOW
        ip_key = digest(request.remote_addr or "unknown")
        email_key = digest(email)
        db.session.execute(db.delete(AdminLoginAttempt).where(
            AdminLoginAttempt.created_at < cutoff
        ))
        ip_failures = db.session.scalar(db.select(db.func.count()).select_from(
            AdminLoginAttempt
        ).where(AdminLoginAttempt.ip_key == ip_key))
        email_failures = db.session.scalar(db.select(db.func.count()).select_from(
            AdminLoginAttempt
        ).where(AdminLoginAttempt.email_key == email_key))
        if ip_failures >= 5 or email_failures >= 10:
            db.session.commit()
            response = render_template(
                "admin/login.html", error="Too many attempts. Please try again in 15 minutes."
            )
            return response, 429, {"Retry-After": "900"}
        user = db.session.scalar(db.select(AdminUser).where(AdminUser.email == email))
        password_valid = check_password_hash(
            user.password_hash if user else DUMMY_PASSWORD_HASH, password[:1024]
        )
        if user and password_valid and len(password) <= 1024:
            start_session(user)
            db.session.commit()
            return redirect(url_for("admin.inbox"), code=303)
        db.session.add(AdminLoginAttempt(ip_key=ip_key, email_key=email_key, created_at=now))
        db.session.commit()
        error = "Email or password is incorrect."
        status = 401
    return render_template("admin/login.html", error=error), status


@bp.post("/logout")
def logout():
    db.session.execute(db.delete(AdminSession).where(
        AdminSession.token_hash == digest(session["admin_token"])
    ))
    db.session.commit()
    session.clear()
    return redirect(url_for("admin.login"), code=303)


@bp.get("")
@bp.get("/")
def inbox():
    query = request.args.get("q", "").strip()[:200]
    status = request.args.get("status", "all")
    if status not in {"all", "new", "reviewed"}:
        status = "all"
    statement = db.select(ContactSubmission)
    if query:
        statement = statement.where(or_(
            *(column.icontains(query, autoescape=True) for column in (
                ContactSubmission.name, ContactSubmission.business,
                ContactSubmission.email, ContactSubmission.message,
            ))
        ))
    if status == "new":
        statement = statement.where(ContactSubmission.reviewed_at.is_(None))
    elif status == "reviewed":
        statement = statement.where(ContactSubmission.reviewed_at.is_not(None))
    page = max(1, request.args.get("page", 1, type=int) or 1)
    inquiries = db.paginate(
        statement.order_by(ContactSubmission.id.desc()),
        page=page, per_page=20, error_out=False,
    )
    new_count = db.session.scalar(db.select(db.func.count()).select_from(
        ContactSubmission
    ).where(ContactSubmission.reviewed_at.is_(None)))
    return render_template(
        "admin/inbox.html", inquiries=inquiries, query=query, status=status, new_count=new_count
    )


@bp.get("/inquiries/<int:submission_id>")
def detail(submission_id):
    item = db.get_or_404(ContactSubmission, submission_id)
    return render_template("admin/detail.html", item=item)


@bp.post("/inquiries/<int:submission_id>/status")
def update_status(submission_id):
    item = db.get_or_404(ContactSubmission, submission_id)
    state = request.form.get("status")
    if state not in {"new", "reviewed"}:
        abort(400)
    item.reviewed_at = datetime.now(UTC) if state == "reviewed" else None
    db.session.commit()
    flash("Inquiry marked as reviewed." if state == "reviewed" else "Inquiry marked as new.")
    return redirect(url_for("admin.detail", submission_id=item.id), code=303)


@bp.route("/password", methods=["GET", "POST"])
def password():
    error = None
    if request.method == "POST":
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        confirmation = request.form.get("confirm_password", "")
        if len(current) > 1024 or not g.admin_user.check_password(current):
            error = "Your current password is incorrect."
        elif not 12 <= len(new) <= 128:
            error = "Use a password between 12 and 128 characters."
        elif new != confirmation:
            error = "The new passwords do not match."
        elif new == current:
            error = "Choose a different password."
        else:
            g.admin_user.set_password(new)
            db.session.execute(db.delete(AdminSession).where(
                AdminSession.user_id == g.admin_user.id
            ))
            start_session(g.admin_user)
            db.session.commit()
            flash("Password updated. Other sessions have been signed out.")
            return redirect(url_for("admin.inbox"), code=303)
    return render_template("admin/password.html", error=error), 400 if error else 200
