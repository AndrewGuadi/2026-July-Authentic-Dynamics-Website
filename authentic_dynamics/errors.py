"""Application-wide errors, including routing errors outside a blueprint."""

from flask import Flask, render_template
from werkzeug.exceptions import HTTPException


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def http_error(error):
        response = error.get_response()
        response.data = render_template(
            "errors/error.html", code=error.code,
            title=error.name, message=error.description,
        )
        response.content_type = "text/html; charset=utf-8"
        return response

    @app.errorhandler(500)
    def server_error(error):
        # Flask logs the original exception before invoking this handler.
        return render_template(
            "errors/error.html", code=500, title="Something went wrong",
            message="Please try again shortly.",
        ), 500
