"""Evidence workspace creation and artefact persistence."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

SUBDIRECTORIES: tuple[str, ...] = (
    "usernames",
    "domain",
    "images",
    "entities",
    "integrations",
    "manual_review",
    "logs",
    "normalized",
    "report",
)


@dataclass(slots=True)
class Workspace:
    """A per-engagement evidence directory tree.

    Layout::

        output/{client_slug}_{YYYY-MM-DD}/
            usernames/  domain/  images/  logs/  normalized/  report/
    """

    root: Path
    created_at: str

    # -- construction ----------------------------------------------------
    @classmethod
    def create(cls, output_root: Path, client_slug: str, timestamp: datetime | None = None) -> "Workspace":
        """Create (or reuse) the workspace tree and return the handle.

        Args:
            output_root: Base ``output/`` directory.
            client_slug: Filesystem-safe client identifier.
            timestamp: Override the folder date (defaults to now, UTC).
        """
        stamp = timestamp or datetime.now(timezone.utc)
        root = Path(output_root).expanduser().resolve() / f"{client_slug}_{stamp.strftime('%Y-%m-%d')}"
        suffix = 1
        while root.exists() and any(root.iterdir()) and (root / "report" / "report.md").exists():
            suffix += 1
            root = root.with_name(f"{client_slug}_{stamp.strftime('%Y-%m-%d')}_{suffix:02d}")
        for sub in SUBDIRECTORIES:
            (root / sub).mkdir(parents=True, exist_ok=True)
        return cls(root=root, created_at=stamp.isoformat())

    # -- paths -----------------------------------------------------------
    @property
    def usernames(self) -> Path:
        """Raw username-enumeration evidence."""
        return self.root / "usernames"

    @property
    def domain(self) -> Path:
        """Raw domain/infrastructure evidence."""
        return self.root / "domain"

    @property
    def images(self) -> Path:
        """Raw image metadata evidence."""
        return self.root / "images"

    @property
    def entities(self) -> Path:
        """Raw identity/entity-screening evidence."""
        return self.root / "entities"

    @property
    def integrations(self) -> Path:
        """Artifacts produced for or by external platforms."""
        return self.root / "integrations"

    @property
    def manual_review(self) -> Path:
        """Analyst task queues and imported review decisions."""
        return self.root / "manual_review"

    @property
    def logs(self) -> Path:
        """Execution logs, including ``audit.log``."""
        return self.root / "logs"

    @property
    def normalized(self) -> Path:
        """Normalised finding documents."""
        return self.root / "normalized"

    @property
    def report(self) -> Path:
        """Rendered Markdown/PDF deliverables."""
        return self.root / "report"

    def category_dir(self, category: str) -> Path:
        """Map a finding category to its raw-evidence directory."""
        return {
            "username": self.usernames,
            "domain": self.domain,
            "image": self.images,
            "entity": self.entities,
            "screening": self.entities,
            "relationship": self.entities,
            "document": self.integrations,
            "manual_review": self.manual_review,
        }.get(category, self.root / "misc")

    def relative(self, path: Path | str) -> str:
        """Return ``path`` relative to the workspace root (POSIX style)."""
        try:
            return Path(path).resolve().relative_to(self.root).as_posix()
        except ValueError:
            return str(path)

    # -- writers ---------------------------------------------------------
    def write_text(self, path: Path, content: str) -> Path:
        """Write UTF-8 text, creating parents. Returns the path."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_json(self, path: Path, payload: Any) -> Path:
        """Write pretty-printed JSON, creating parents. Returns the path."""
        return self.write_text(path, json.dumps(payload, indent=2, ensure_ascii=False, default=str))

    def write_findings(self, name: str, findings: Iterable[Dict[str, Any]]) -> Path:
        """Persist a normalised finding collection under ``normalized/``."""
        items: List[Dict[str, Any]] = list(findings)
        return self.write_json(
            self.normalized / f"{name}.json",
            {"count": len(items), "generated_at": datetime.now(timezone.utc).isoformat(), "findings": items},
        )

    def tree(self) -> str:
        """Return an ASCII listing of the workspace for the report appendix."""
        lines: List[str] = [f"{self.root.name}/"]
        for path in sorted(self.root.rglob("*")):
            depth = len(path.relative_to(self.root).parts) - 1
            prefix = "    " * depth + ("├── " if depth >= 0 else "")
            lines.append(f"{prefix}{path.name}{'/' if path.is_dir() else ''}")
        return "\n".join(lines)
