import re
from xml.etree import ElementTree

from flask import current_app, flash, make_response, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from authentic_dynamics.extensions import db
from authentic_dynamics.models import ContactSubmission

from . import bp


@bp.get("/")
def index():
    return render_template("main/index.html", contact_source="home", active_page="home",
                           form_values=_contact_prefill())


@bp.get("/llms.txt")
def llms():
    """Serve the published AI reference file at the site root."""
    return current_app.send_static_file("llms.txt")


@bp.get("/robots.txt")
def robots():
    """Direct cooperative crawlers to business pages and away from utilities."""
    canonical_host = current_app.config["CANONICAL_HOST"]
    sitemap_url = (
        f"https://{canonical_host}{url_for('main.sitemap')}"
        if canonical_host else url_for("main.sitemap", _external=True)
    )
    response = make_response(render_template("main/robots.txt", sitemap_url=sitemap_url))
    response.mimetype = "text/plain"
    return response


@bp.get("/sitemap.xml")
def sitemap():
    """List business and policy pages on the configured canonical host, when set."""
    # Keep tools, Browser X-Ray, and games out of sitemap discovery intentionally.
    endpoints = (
        "main.index",
        "main.websites",
        "main.growth_technology",
        "main.work",
        "main.about_community",
        "main.privacy_policy",
        "main.terms",
    )
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ElementTree.register_namespace("", namespace)
    root = ElementTree.Element(f"{{{namespace}}}urlset")
    canonical_host = current_app.config["CANONICAL_HOST"]
    for endpoint in endpoints:
        page = ElementTree.SubElement(root, f"{{{namespace}}}url")
        path = url_for(endpoint)
        ElementTree.SubElement(page, f"{{{namespace}}}loc").text = (
            f"https://{canonical_host}{path}" if canonical_host else url_for(endpoint, _external=True)
        )
    response = make_response(ElementTree.tostring(root, encoding="utf-8", xml_declaration=True))
    response.mimetype = "application/xml"
    return response


@bp.get("/websites")
def websites():
    return render_template("main/websites.html", active_page="websites")


@bp.get("/browser-xray")
def browser_xray():
    return render_template("main/browser_xray.html", active_page="browser_xray")


@bp.get("/growth-technology")
def growth_technology():
    return render_template("main/growth_technology.html", active_page="growth")


@bp.get("/work")
def work():
    return render_template("main/work.html", active_page="work")


@bp.get("/about-community")
def about_community():
    return render_template(
        "main/about_community.html", active_page="about", contact_source="about",
        form_values=_contact_prefill(),
    )


@bp.get("/privacy-policy")
def privacy_policy():
    return render_template("main/privacy_policy.html", active_page="privacy")


@bp.get("/terms")
def terms():
    return render_template("main/terms.html", active_page="terms")


INTERESTS = {
    "Not sure yet — let’s talk",
    "Small business website — from $500",
    "Website rebuild or larger platform",
    "Local visibility & marketing",
    "AI, automation & custom systems",
    "Community project or nonprofit",
}

INTEREST_KEYS = {
    "website": "Small business website — from $500",
    "custom": "Website rebuild or larger platform",
    "growth": "Local visibility & marketing",
    "automation": "AI, automation & custom systems",
    "community": "Community project or nonprofit",
}


def _contact_prefill():
    """Only explicit public service keys can prefill an editable form field."""
    interest = INTEREST_KEYS.get(request.args.get("interest", ""))
    return {"interest": interest} if interest else {}


CONTACT_PAGES = {
    "home": ("main/index.html", "main.index", "home"),
    "about": ("main/about_community.html", "main.about_community", "about"),
}


@bp.post("/contact")
def submit_contact():
    source = request.form.get("source_page", "")
    if source not in CONTACT_PAGES:
        return "Invalid contact form source.", 400

    values = {
        key: request.form.get(key, "").strip()
        for key in ("name", "business", "email", "interest", "message")
    }
    errors = {}
    if not 2 <= len(values["name"]) <= 120 or any(c in values["name"] for c in "\r\n"):
        errors["name"] = "Enter your name (2–120 characters)."
    if len(values["business"]) > 120 or any(c in values["business"] for c in "\r\n"):
        errors["business"] = "Keep the business name under 120 characters."
    if len(values["email"]) > 254 or not re.fullmatch(
        r"[^\s@]+@[^\s@]+\.[^\s@]+", values["email"]
    ):
        errors["email"] = "Enter a valid email address."
    if values["interest"] not in INTERESTS:
        errors["interest"] = "Choose an interest from the list."
    if not 10 <= len(values["message"]) <= 4000:
        errors["message"] = "Tell us a little more (10–4000 characters)."

    template, endpoint, active_page = CONTACT_PAGES[source]
    if errors:
        return render_template(
            template,
            active_page=active_page,
            contact_source=source,
            form_values=values,
            form_errors=errors,
        ), 400

    try:
        db.session.add(ContactSubmission(source_page=source, **values))
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        # Do not put contact content or database credentials in error messages/logs.
        current_app.logger.error("Contact inquiry could not be saved.")
        return render_template(
            template, active_page=active_page, contact_source=source,
            form_values=values,
            form_errors={"_form": "Your inquiry was not saved. Your text is still below. "
                         "Please try again, or contact us by email."},
        ), 503
    flash("Thanks. Your inquiry was saved and we’ll be in touch using the email you provided.", "success")
    return redirect(f"{url_for(endpoint)}#contact", code=303)
