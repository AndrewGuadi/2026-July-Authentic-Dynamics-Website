import re
from xml.etree import ElementTree

from flask import abort, current_app, flash, make_response, redirect, render_template, request, url_for

from authentic_dynamics.blog import get_blog_post, get_blog_posts
from authentic_dynamics.extensions import db
from authentic_dynamics.models import ContactSubmission

from . import bp


@bp.get("/")
def index():
    return render_template("main/index.html", contact_source="home")


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
    """List business, policy and published blog pages on the canonical host."""
    # Keep tools, Browser X-Ray, and games out of sitemap discovery intentionally.
    endpoints = (
        "main.index",
        "main.websites",
        "main.growth_technology",
        "main.work",
        "main.about_community",
        "main.privacy_policy",
        "main.terms",
        "main.blog",
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
    for post in get_blog_posts():
        page = ElementTree.SubElement(root, f"{{{namespace}}}url")
        ElementTree.SubElement(page, f"{{{namespace}}}loc").text = _blog_url(
            "main.blog_post", slug=post["slug"]
        )
        ElementTree.SubElement(page, f"{{{namespace}}}lastmod").text = post["modified"]
    response = make_response(ElementTree.tostring(root, encoding="utf-8", xml_declaration=True))
    response.mimetype = "application/xml"
    return response


def _blog_url(endpoint, **values):
    host = current_app.config.get("CANONICAL_HOST")
    return f"https://{host}{url_for(endpoint, **values)}" if host else url_for(
        endpoint, _external=True, **values
    )


@bp.get("/blog")
def blog():
    posts = get_blog_posts()
    canonical_url = _blog_url("main.blog")
    structured_data = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Practical AI Guides for Central Pennsylvania Businesses",
        "url": canonical_url,
        "mainEntity": {
            "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "position": index, "name": post["title"],
                 "url": _blog_url("main.blog_post", slug=post["slug"])}
                for index, post in enumerate(posts, 1)
            ],
        },
    }
    return render_template(
        "blog/index.html", active_page="blog", posts=posts,
        canonical_url=canonical_url, structured_data=structured_data,
    )


@bp.get("/blog/")
def blog_redirect():
    return redirect(url_for("main.blog"), code=308)


@bp.get("/blog/<slug>")
def blog_post(slug):
    post = get_blog_post(slug)
    if post is None:
        abort(404)
    canonical_url = _blog_url("main.blog_post", slug=slug)
    structured_data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BlogPosting", "headline": post["title"],
                "description": post["description"], "url": canonical_url,
                "mainEntityOfPage": {"@type": "WebPage", "@id": canonical_url},
                "datePublished": post["published"], "dateModified": post["modified"],
                "inLanguage": "en-US", "articleSection": post["category"],
                "author": {"@type": "Organization", "name": "Authentic Dynamics",
                           "url": _blog_url("main.about_community")},
                "publisher": {"@type": "Organization", "name": "Authentic Dynamics",
                              "url": _blog_url("main.index")},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home",
                     "item": _blog_url("main.index")},
                    {"@type": "ListItem", "position": 2, "name": "Blog",
                     "item": _blog_url("main.blog")},
                    {"@type": "ListItem", "position": 3, "name": post["title"],
                     "item": canonical_url},
                ],
            },
        ],
    }
    posts = get_blog_posts()
    position = next(i for i, item in enumerate(posts) if item["slug"] == slug)
    related = [posts[(position + offset) % len(posts)] for offset in range(1, 4)]
    return render_template(
        "blog/post.html", active_page="blog", post=post, related=related,
        canonical_url=canonical_url, structured_data=structured_data,
    )


@bp.get("/blog/<slug>/")
def blog_post_redirect(slug):
    if get_blog_post(slug) is None:
        abort(404)
    return redirect(url_for("main.blog_post", slug=slug), code=308)


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
        "main/about_community.html", active_page="about", contact_source="about"
    )


@bp.get("/privacy-policy")
def privacy_policy():
    return render_template("main/privacy_policy.html")


@bp.get("/terms")
def terms():
    return render_template("main/terms.html")


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
