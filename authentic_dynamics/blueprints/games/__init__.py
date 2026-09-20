from flask import Blueprint, render_template

bp = Blueprint("games", __name__, url_prefix="/games")


@bp.get("")
@bp.get("/")
def catalog():
    return render_template("games/catalog.html", active_page="games")


@bp.get("/maze-chase")
def maze_chase():
    return render_template("games/maze_chase.html", active_page="games")
