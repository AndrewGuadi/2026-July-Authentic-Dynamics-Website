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
coding.today = lambda: date(2030, 1, 1)
app = create_app({'TESTING': True, 'SECRET_KEY': 'coding-browser-tests',
                  'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
logging.getLogger('werkzeug').setLevel(logging.ERROR)
server = make_server('127.0.0.1', 5073, app, threaded=True)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    result = subprocess.run(
        ['node', 'tests/coding_calendar_browser.cjs'], check=False,
        cwd=Path(__file__).resolve().parents[1], env=os.environ.copy(),
    )
finally:
    server.shutdown()
raise SystemExit(result.returncode)
