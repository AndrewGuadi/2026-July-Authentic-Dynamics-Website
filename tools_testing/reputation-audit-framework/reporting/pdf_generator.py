"""Optional PDF rendering via wkhtmltopdf.

If ``wkhtmltopdf`` is not installed the generator returns ``None`` and the
engagement continues with the Markdown deliverable only.
"""
from __future__ import annotations

import html
from pathlib import Path
from typing import Optional

from core.logger import get_logger
from core.runner import binary_available, run_command

CSS = """
:root { color-scheme: light; }
body { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
       color: #14181d; margin: 40px; line-height: 1.55; font-size: 12px; }
h1 { font-size: 24px; border-bottom: 3px solid #16a34a; padding-bottom: 8px; }
h2 { font-size: 17px; margin-top: 28px; border-bottom: 1px solid #d5dbe2; padding-bottom: 4px; }
h3 { font-size: 14px; margin-top: 20px; color: #334155; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 10.5px; }
th, td { border: 1px solid #cbd5e1; padding: 6px 8px; text-align: left; vertical-align: top; }
th { background: #f1f5f9; }
code { background: #f1f5f9; padding: 1px 4px; border-radius: 3px; font-size: 10.5px; }
blockquote { border-left: 4px solid #16a34a; margin: 12px 0; padding: 6px 14px;
             background: #f0fdf4; color: #14532d; }
"""


class PdfGenerator:
    """Convert the Markdown report to PDF when the toolchain is available."""

    def __init__(self, binary: str = "wkhtmltopdf") -> None:
        """Bind to the converter binary (override for testing)."""
        self.binary = binary
        self.log = get_logger("pdf")

    def available(self) -> bool:
        """Return True when the converter binary is on PATH."""
        return binary_available(self.binary)

    def generate(self, markdown: str, destination: Path, title: str = "Reputation Audit") -> Optional[Path]:
        """Render ``markdown`` to ``destination`` as PDF.

        Args:
            markdown: Report source text.
            destination: Target ``.pdf`` path.
            title: Document title used in the HTML head.

        Returns:
            The PDF path, or ``None`` when rendering was skipped or failed.
        """
        if not self.available():
            self.log.warning("wkhtmltopdf not found; skipping PDF rendering")
            return None

        destination.parent.mkdir(parents=True, exist_ok=True)
        html_path = destination.with_suffix(".html")
        html_path.write_text(self._to_html(markdown, title), encoding="utf-8")

        result = run_command(
            [
                self.binary,
                "--quiet",
                "--enable-local-file-access",
                "--margin-top", "16mm",
                "--margin-bottom", "16mm",
                "--footer-right", "[page]/[topage]",
                "--footer-font-size", "8",
                str(html_path),
                str(destination),
            ],
            timeout=180,
        )
        if not result.ok or not destination.exists():
            self.log.error("pdf rendering failed: %s", result.error or result.stderr[:200])
            return None
        self.log.info("pdf written to %s", destination)
        return destination

    # -- conversion ------------------------------------------------------
    def _to_html(self, markdown_text: str, title: str) -> str:
        """Convert Markdown to a standalone HTML document."""
        try:
            import markdown as md  # type: ignore import-not-found

            body = md.markdown(markdown_text, extensions=["tables", "fenced_code", "toc"])
        except ImportError:  # pragma: no cover - fallback path
            body = f"<pre>{html.escape(markdown_text)}</pre>"
        return (
            "<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
            f"<body>{body}</body></html>"
        )
