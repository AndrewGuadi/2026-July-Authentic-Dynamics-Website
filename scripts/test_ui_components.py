"""Serve an isolated app and exercise the Uiverse adaptations in Chromium.

Requires Playwright in NODE_PATH and its Chromium browser (or CHROMIUM_PATH).
Screenshots default to /tmp/ad-ui-components; AD_UI_SCREENSHOTS overrides it.
"""
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path

from werkzeug.serving import make_server

# Test this checkout even when another worktree is installed in editable mode.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from authentic_dynamics import create_app  # noqa: E402

app = create_app({
    "TESTING": True, "SECRET_KEY": "ui-component-browser-test",
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "CANONICAL_HOST": "",
    "HUB_ENABLED": False,
})
logging.getLogger("werkzeug").setLevel(logging.ERROR)
server = make_server("127.0.0.1", 0, app, threaded=True)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    result = subprocess.run(
        ["node", "tests/ui_components_browser.cjs"], check=False,
        cwd=ROOT,
        env={**os.environ, "AD_UI_BASE_URL": f"http://127.0.0.1:{server.server_port}"},
    )
finally:
    server.shutdown()
raise SystemExit(result.returncode)
