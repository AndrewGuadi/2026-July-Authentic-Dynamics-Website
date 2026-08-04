"""Structured logging (console + rotating file + optional JSON lines)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console
from rich.logging import RichHandler

LOGGER_NAME = "raf"


class JsonLineFormatter(logging.Formatter):
    """Emit one JSON object per log record for machine ingestion."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D102 - inherited
        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": getattr(record, "audit_module", record.module),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key in ("event", "target", "duration", "status"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(
    log_file: Path,
    level: str = "INFO",
    verbose: bool = False,
    json_lines: bool = True,
    console: Optional[Console] = None,
) -> logging.Logger:
    """Configure and return the framework logger.

    Two handlers are attached: a human-friendly Rich console handler and a
    file handler writing ``logs/audit.log``. INFO/WARNING/ERROR records are all
    persisted; DEBUG is only shown on the console when ``verbose`` is set.

    Args:
        log_file: Destination log file (parent dirs are created).
        level: Base log level name from config.
        verbose: Lower the console handler to DEBUG.
        json_lines: Write the file log as JSON lines instead of plain text.
        console: Optional Rich console to reuse.

    Returns:
        The configured :class:`logging.Logger`.
    """
    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    file_handler.setFormatter(
        JsonLineFormatter()
        if json_lines
        else logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )
    logger.addHandler(file_handler)

    console_handler = RichHandler(
        console=console or Console(stderr=True),
        rich_tracebacks=True,
        show_path=False,
        markup=False,
    )
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
    logger.addHandler(console_handler)

    logger.debug("logging initialised at %s", log_file)
    return logger


def get_logger(module: Optional[str] = None) -> logging.LoggerAdapter:
    """Return a logger adapter tagged with an audit module name."""
    base = logging.getLogger(LOGGER_NAME if not module else f"{LOGGER_NAME}.{module}")
    return logging.LoggerAdapter(base, {"audit_module": module or "core"})
