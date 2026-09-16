"""Production WSGI entry point: gunicorn wsgi:app."""

from authentic_dynamics import create_app

app = create_app()
