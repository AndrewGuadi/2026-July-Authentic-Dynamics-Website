"""Browser-only showroom; no profile ingestion, accounts or remote rendering."""
from flask import render_template

from . import bp


@bp.get('/try-builder')
def try_builder():
    return render_template('builder/catalog.html', active_page='builder')


@bp.get('/try-builder/preview')
def builder_preview():
    return render_template('builder/preview.html', active_page='builder')
