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
    assert '/coding-calendar/javascript/2026-10-25/' not in page
    assert client.get('/coding-calendar/ruby/2026-10-24/').status_code == 404
    assert client.get('/coding-calendar/python/2026-02-30/').status_code == 404
    assert client.get('/coding-calendar/python/20261024/').status_code == 404
    assert client.get('/coding-calendar/python/1900-01-01/').status_code == 404
    assert client.post('/coding-calendar/python/2026-10-24/', json={'code': 'bad'}).status_code in (400, 405)


def test_expired_schedule_is_explicit(app, monkeypatch):
    monkeypatch.setattr(coding, 'today', lambda: date(2099, 12, 31))
    page = app.test_client().get('/coding-calendar/').get_data(as_text=True)
    assert 'No lesson is scheduled for this date' in page
    assert 'LATEST PUBLISHED' not in page


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


def test_index_defaults_to_real_day_without_latest_fallback(app, monkeypatch):
    monkeypatch.setattr(coding, 'today', lambda: date(2099, 12, 31))
    response = app.test_client().get('/coding-calendar/')
    page = response.get_data(as_text=True)
    assert 'value="2099-12-31"' in page
    assert 'No lesson is scheduled for this date' in page
    assert 'LATEST PUBLISHED' not in page
    assert 'no-store' in response.headers['Cache-Control']


def test_explicit_dates_navigation_and_archive_filters(app):
    client = app.test_client()
    page = client.get('/coding-calendar/?date=2026-10-23&language=python&category=strings&track=python').get_data(as_text=True)
    assert 'value="2026-10-23"' in page
    assert 'id="calendar-tab-python"' in page
    assert 'id="calendar-previous"' in page
    assert 'id="calendar-next"' in page
    assert 'id="calendar-today"' in page
    assert 'aria-controls="calendar-panel-python"' in page
    assert 'String.trim()' not in page  # Python-only archive filter.
    assert 'str.lower()' in page
    future = client.get('/coding-calendar/?date=2026-11-02').get_data(as_text=True)
    assert 'UPCOMING' in future
    assert 'Available on 2026-11-02' in future
    assert 'href="/coding-calendar/javascript/2026-11-02/"' not in future
    assert client.get('/coding-calendar/?date=bad').status_code == 400
    assert client.get('/coding-calendar/?category=nonexistent').status_code == 400
    assert client.get('/coding-calendar/?page=0').status_code == 400
    assert client.get('/coding-calendar/?language=ruby').status_code == 400


def test_lesson_has_adjacent_date_and_language_links(app):
    page = app.test_client().get('/coding-calendar/javascript/2026-10-23/').get_data(as_text=True)
    assert '/coding-calendar/javascript/2026-10-22/' in page
    assert '/coding-calendar/javascript/2026-10-24/' in page
    assert '/coding-calendar/python/2026-10-23/' in page
    assert 'id="lesson-date"' in page
    assert 'id="calendar-today"' in page


def test_daily_batch_has_three_days_each_side_and_categories(app):
    with app.app_context():
        items = coding.lessons()
    days = sorted({item['date'] for item in items})
    assert days[0] <= '2026-10-21'
    assert days[-1] >= '2026-11-02'
    assert len(items) >= 39
    for item in items:
        assert item['category'] in coding.CATEGORIES
        assert item['level'] in coding.LEVELS


@pytest.mark.parametrize(('instant', 'expected'), [
    ('2026-10-25T03:59:00+00:00', date(2026, 10, 24)),
    ('2026-10-25T04:00:00+00:00', date(2026, 10, 25)),
    ('2026-11-01T05:59:00+00:00', date(2026, 11, 1)),
    ('2026-11-01T06:00:00+00:00', date(2026, 11, 1)),
])
def test_calendar_uses_new_york_midnight_and_daylight_saving(monkeypatch, instant, expected):
    from datetime import datetime

    class Clock:
        @staticmethod
        def now(tz):
            return datetime.fromisoformat(instant).astimezone(tz)

    monkeypatch.setattr(coding, 'datetime', Clock)
    assert coding.today() == expected


def test_default_follows_new_day_instead_of_caching_yesterday(app, monkeypatch):
    client = app.test_client()
    assert 'value="2026-10-24"' in client.get('/coding-calendar/').get_data(as_text=True)
    monkeypatch.setattr(coding, 'today', lambda: date(2026, 10, 25))
    assert 'value="2026-10-25"' in client.get('/coding-calendar/').get_data(as_text=True)


def test_daily_program_plan_is_bounded_and_does_not_repeat(tmp_path):
    import runpy

    plan = runpy.run_path(str(ROOT / 'scripts/coding_calendar_plan.py'))['plan']
    content = tmp_path / 'coding'
    content.mkdir()
    ledger = {'program_start': '2026-10-24', 'program_end': '2026-11-22',
              'total_batches': 30, 'days_per_direction': 3,
              'batches': [{'run_date': '2026-10-24'}]}
    (content / 'maintenance.json').write_text(json.dumps(ledger))
    for language in coding.LANGUAGES:
        directory = content / language
        directory.mkdir()
        for day in ['2026-10-21', '2026-11-02']:
            (directory / (day + '.json')).write_text(json.dumps({'language': language, 'date': day}))
    assert plan(content, date(2026, 10, 24))['status'] == 'already-recorded'
    result = plan(content, date(2026, 10, 25))
    assert result['status'] == 'new-batch'
    assert result['older_dates'] == ['2026-10-18', '2026-10-19', '2026-10-20']
    assert result['forward_dates'] == ['2026-11-03', '2026-11-04', '2026-11-05']
    assert result['lesson_count'] == 18
    assert plan(content, date(2026, 11, 23))['status'] == 'closed'
    ledger['batches'] = [{'run_date': f'2026-10-{day:02d}'} for day in range(1, 31)]
    (content / 'maintenance.json').write_text(json.dumps(ledger))
    assert plan(content, date(2026, 11, 1))['status'] == 'closed'


def test_archive_paginates_dates_without_losing_filters(app, monkeypatch):
    from datetime import timedelta

    with app.app_context():
        seed = coding.lessons()[0]
    items = [{**seed, 'date': (date(2026, 9, 1) + timedelta(days=offset)).isoformat(),
              'language': language} for offset in range(40) for language in coding.LANGUAGES]
    monkeypatch.setattr(coding, 'lessons', lambda: items)
    client = app.test_client()
    first = client.get('/coding-calendar/?category=' + seed['category']).get_data(as_text=True)
    second = client.get('/coding-calendar/?category=' + seed['category'] + '&page=2').get_data(as_text=True)
    assert '<span>Page 1 of 2</span>' in first
    assert '<span>Page 2 of 2</span>' in second
    assert '2026-09-01' not in first.split('<tbody>')[1]
    assert '2026-09-01' in second.split('<tbody>')[1]
    assert client.get('/coding-calendar/?page=3').status_code == 400
