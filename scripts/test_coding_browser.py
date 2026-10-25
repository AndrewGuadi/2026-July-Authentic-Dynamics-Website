"""Serve all seeded lessons locally and run the real-browser regression suite."""
import logging
import os
import subprocess
import threading
from datetime import date
from pathlib import Path

from werkzeug.serving import make_server

from authentic_dynamics import create_app
from authentic_dynamics.blueprints import coding

# Test process only: allow future seed content without changing production logic.
coding.today = lambda: date.fromisoformat(os.environ.get('CODING_TEST_DATE', '2030-01-01'))
app = create_app({'TESTING': True, 'SECRET_KEY': 'coding-browser-tests',
                  'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
logging.getLogger('werkzeug').setLevel(logging.ERROR)
server = make_server('127.0.0.1', 5073, app, threaded=True)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    suite = os.environ.get('CODING_BROWSER_SUITE', 'coding_calendar_browser.cjs')
    if suite not in {'coding_calendar_browser.cjs', 'coding_calendar_navigation.cjs'}:
        raise ValueError('Choose a known coding browser suite')
    result = subprocess.run(
        ['node', 'tests/' + suite], check=False,
        cwd=Path(__file__).resolve().parents[1], env=os.environ.copy(),
    )
finally:
    server.shutdown()
raise SystemExit(result.returncode)
