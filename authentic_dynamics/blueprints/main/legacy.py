"""Explicit replacements for relevant retired URLs seen in Search Console."""

from flask import redirect, url_for

from . import bp


@bp.get("/services/web-development", strict_slashes=False)
def legacy_web_development():
    return redirect(url_for("main.websites"), code=301)


@bp.get("/services/digital-marketing", strict_slashes=False)
def legacy_digital_marketing():
    return redirect(url_for("main.growth_technology", _anchor="services"), code=301)


@bp.get("/pricing", strict_slashes=False)
def legacy_pricing():
    return redirect(url_for("main.websites", _anchor="starter"), code=301)


@bp.get("/contact", strict_slashes=False)
def legacy_contact():
    # GET only: the existing POST validation/submission route remains intact.
    return redirect(url_for("main.about_community", _anchor="contact"), code=301)


@bp.get("/about", strict_slashes=False)
def legacy_about():
    return redirect(url_for("main.about_community"), code=301)


@bp.get("/portfolio", strict_slashes=False)
def legacy_portfolio():
    return redirect(url_for("main.work"), code=301)
