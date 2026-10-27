"""Showroom routing, source catalog completeness, and vendored preview safety."""
import json
from collections import Counter
from pathlib import Path

from authentic_dynamics import create_app

ROOT = Path(__file__).resolve().parents[1] / 'authentic_dynamics/static/builder'


def test_showroom_routes_and_sources():
    client = create_app({'TESTING': True}).test_client()
    assert client.get('/try-builder').status_code == 200
    assert client.get('/try-builder/preview').status_code == 200
    assert b'href="/try-builder"' not in client.get('/').data
    catalog = json.loads((ROOT / 'catalog.json').read_text())
    templates = catalog['templates']
    assert len(templates) == 50
    assert len({t['id'] for t in templates}) == 50
    assert Counter(t['industry'] for t in templates) == {
        industry['id']: 5 for industry in catalog['industries']
    }
    for item in templates:
        snapshot = ROOT / item['path'].split('/static/builder/')[1]
        assert snapshot.is_file()
        assert (snapshot.parent / 'LICENSE.txt').is_file()
        assert item['revision'] in item['source']
        html = snapshot.read_text()
        assert '<script' not in html.lower()
        assert "form-action 'none'" in html
        assert client.get(item['path']).status_code == 200


def test_component_catalog_has_local_snapshots_and_sources():
    components = json.loads((ROOT / 'components.json').read_text())
    assert len(components) == 48
    assert len({c['id'] for c in components}) == 48
    for component in components:
        assert component['source'].startswith('https://uiverse.io/')
        assert (ROOT / component['path'].split('/static/builder/')[1]).is_file()
