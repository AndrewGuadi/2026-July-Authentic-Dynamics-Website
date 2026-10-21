"""Application-wide errors, including routing errors outside a blueprint."""

from flask import Flask, render_template, request
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import HTTPException


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def http_error(error):
        recovery_endpoint = "main.index"
        recovery_label = "Back to home"
        recovery_hint = "Explore our services or start again from the homepage."
        if isinstance(error, CSRFError):
            recovery_endpoint = "main.about_community"
            recovery_label = "Open a fresh inquiry form"
            recovery_hint = "This form's security check expired or was missing. " \
                            "Reopen the form before trying again. Nothing was submitted."
            if request.path.startswith("/tools/"):
                recovery_endpoint = "tools.catalog"
                recovery_label = "Choose your tool again"
                recovery_hint = "This form's security check expired or was missing. " \
                                "Reopen the tool and select your input again."
            elif request.path.startswith(("/admin", "/hub")):
                recovery_endpoint = "admin.login"
                recovery_label = "Return to sign in"
                recovery_hint = "Your security check expired or was missing. " \
                                "Return to sign in before continuing."
        elif error.code == 413:
            recovery_endpoint = "tools.catalog"
            recovery_label = "Return to free tools"
            recovery_hint = "The upload exceeded the request limit. Check the file-size " \
                            "limit shown in your tool and select a smaller file."
        response = error.get_response()
        response.data = render_template(
            "errors/error.html", code=error.code,
            title=error.name, message=error.description, recovery_endpoint=recovery_endpoint,
            recovery_label=recovery_label, recovery_hint=recovery_hint,
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
