"""Content, publication, and read-only route contract checks."""
import json
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from authentic_dynamics import create_app
from authentic_dynamics.blueprints import coding

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(coding, 'today', lambda: date(2026, 10, 24))
    return create_app({'TESTING': True, 'SECRET_KEY': 'calendar-tests',
                       'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})


def test_published_calendar_and_future_pages(app):
    client = app.test_client()
    page = client.get('/coding-calendar/').get_data(as_text=True)
    for language in coding.LANGUAGES:
        assert f'/coding-calendar/{language}/2026-10-24/' in page
        assert client.get(f'/coding-calendar/{language}/2026-10-24/').status_code == 200
        assert client.get(f'/coding-calendar/{language}/2026-10-25/').status_code == 404
    assert '2026-10-25' not in page
    assert client.get('/coding-calendar/ruby/2026-10-24/').status_code == 404
    assert client.get('/coding-calendar/python/2026-02-30/').status_code == 404
    assert client.get('/coding-calendar/python/20261024/').status_code == 404
    assert client.get('/coding-calendar/python/2026-10-23/').status_code == 404
    assert client.post('/coding-calendar/python/2026-10-24/', json={'code': 'bad'}).status_code in (400, 405)


def test_expired_schedule_is_explicit(app, monkeypatch):
    monkeypatch.setattr(coding, 'today', lambda: date(2026, 11, 1))
    page = app.test_client().get('/coding-calendar/').get_data(as_text=True)
    assert 'no new lesson scheduled for today' in page
    assert 'LATEST PUBLISHED' in page


def test_sandbox_policy_and_assets(app):
    client = app.test_client()
    response = client.get('/coding-calendar/sandbox')
    policy = response.headers['Content-Security-Policy']
    assert "connect-src 'none'" in policy
    assert 'sandbox allow-scripts' in policy
    assert 'allow-same-origin' not in policy
    assert response.headers['X-Robots-Tag'] == 'noindex, nofollow'
    for name in ('calendar.js', 'worker.js', 'runtime-manifest.json', 'editor.bundle.js'):
        assert client.get('/static/js/coding/' + name).status_code == 200
    assert client.get('/static/css/coding.css').status_code == 200
    assert b'Coding Calendar' in client.get('/tools/').data


def test_all_lesson_content_and_reference_solutions(app):
    reference = json.loads((ROOT / 'tests/fixtures/coding/solutions.json').read_text())
    with app.app_context():
        items = coding.lessons()
    assert len(items) >= 21
    assert {f"{item['language']}/{item['date']}" for item in items} == set(reference)
    assert len({(item['language'], item['date']) for item in items}) == len(items)
    for item in items:
        assert len(item['scenarios']) >= 3
        assert len(item['tests']) >= 3
        assert item['docs_url'].startswith(('https://developer.mozilla.org/', 'https://docs.python.org/', 'https://www.sqlite.org/'))
        solution = reference[f"{item['language']}/{item['date']}"]
        for test in item['tests']:
            if item['language'] == 'python':
                scope = {}
                exec(solution, scope)  # noqa: S102 - trusted repository-owned reference fixture
                assert scope['solve'](test['input']) == test['expected']
            elif item['language'] == 'sql':
                with sqlite3.connect(':memory:') as db:
                    db.executescript(test['setup'])
                    cursor = db.execute(solution)
                    result = [{'columns': [col[0] for col in cursor.description],
                               'values': [list(row) for row in cursor.fetchall()]}]
                    assert result == test['expected']
