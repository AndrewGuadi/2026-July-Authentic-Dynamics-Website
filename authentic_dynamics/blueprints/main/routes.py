from flask import render_template

from . import bp


@bp.get("/")
def index():
    return render_template("main/index.html")


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
    return render_template("main/about_community.html", active_page="about")
