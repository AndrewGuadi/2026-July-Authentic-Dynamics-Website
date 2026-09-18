import re
from xml.etree import ElementTree

from flask import flash, make_response, redirect, render_template, request, url_for

from authentic_dynamics.extensions import db
from authentic_dynamics.models import ContactSubmission

from . import bp


@bp.get("/")
def index():
    return render_template("main/index.html", contact_source="home")


@bp.get("/sitemap.xml")
def sitemap():
    """List the public pages using the host and scheme serving this request."""
    endpoints = (
        "main.index",
        "main.websites",
        "main.growth_technology",
        "main.work",
        "main.about_community",
        "tools.catalog",
        "tools.pdf",
        "tools.csv",
    )
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ElementTree.register_namespace("", namespace)
    root = ElementTree.Element(f"{{{namespace}}}urlset")
    for endpoint in endpoints:
        page = ElementTree.SubElement(root, f"{{{namespace}}}url")
        ElementTree.SubElement(page, f"{{{namespace}}}loc").text = url_for(endpoint, _external=True)
    response = make_response(ElementTree.tostring(root, encoding="utf-8", xml_declaration=True))
    response.mimetype = "application/xml"
    return response


@bp.get("/websites")
def websites():
    return render_template("main/websites.html", active_page="websites")


@bp.get("/growth-technology")
def growth_technology():
    return render_template("main/growth_technology.html", active_page="growth")


@bp.get("/work")
def work():
    return render_template("main/work.html", active_page="work")


@bp.get("/about-community")
def about_community():
    return render_template(
        "main/about_community.html", active_page="about", contact_source="about"
    )


INTERESTS = {
    "Not sure yet — let’s talk",
    "Small business website — from $500",
    "Website rebuild or larger platform",
    "Local visibility & marketing",
    "AI, automation & custom systems",
    "Community project or nonprofit",
}

CONTACT_PAGES = {
    "home": ("main/index.html", "main.index", None),
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

    db.session.add(ContactSubmission(source_page=source, **values))
    db.session.commit()
    flash("Thanks. Your inquiry was saved and we’ll be in touch using the email you provided.", "success")
    return redirect(f"{url_for(endpoint)}#contact", code=303)
