"""Create a deterministic analyst queue for the Search by Image extension."""
from __future__ import annotations

import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from core.config import AppConfig
from core.validator import Scope
from core.workspace import Workspace
from modules.base import ModuleResult
from normalization.schema import make_finding


class ReverseImageReview:
    """Prepare local image copies, hashes, and review/result templates."""

    name = "search_by_image"

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.options = config.integration_options(self.name)

    def run(self, scope: Scope, workspace: Workspace) -> ModuleResult:
        if not scope.image_dir:
            return ModuleResult.skipped(self.name, "no image directory in scope")
        started = datetime.now(timezone.utc)
        directory = workspace.manual_review / "reverse_image"
        assets = directory / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        allowed = {
            str(ext).lower()
            for ext in self.options.get("extensions", [".jpg", ".jpeg", ".png", ".webp", ".gif"])
        }
        tasks: List[Dict[str, Any]] = []
        findings: List[Dict[str, Any]] = []
        for source in sorted(Path(scope.image_dir).rglob("*")):
            if not source.is_file() or source.suffix.lower() not in allowed:
                continue
            digest = _sha256(source)
            task_id = f"reverse-image-{digest[:16]}"
            destination = assets / f"{digest}{source.suffix.lower()}"
            if not destination.exists():
                shutil.copy2(source, destination)
            evidence = workspace.relative(destination)
            tasks.append(
                {
                    "task_id": task_id,
                    "status": "pending",
                    "sha256": digest,
                    "original_name": source.name,
                    "review_asset": evidence,
                    "workflow": "Use the dessant/search-by-image browser extension and record each engine checked.",
                }
            )
            findings.append(
                make_finding(
                    finding_type="manual_review",
                    source_tool="search-by-image",
                    value=task_id,
                    risk_hint="review_pending",
                    evidence_file=evidence,
                    details={"task_id": task_id, "sha256": digest, "status": "pending"},
                )
            )

        queue_path = workspace.write_json(
            directory / "tasks.json",
            {
                "kind": "reverse_image",
                "engagement_id": scope.engagement_id,
                "extension": "https://github.com/dessant/search-by-image",
                "tasks": tasks,
            },
        )
        template_path = workspace.write_json(
            directory / "results.template.json",
            {
                "kind": "reverse_image",
                "engagement_id": scope.engagement_id,
                "reviewer": "",
                "reviewed_at": None,
                "reviews": [
                    {
                        "task_id": task["task_id"],
                        "status": "candidate_match|no_match|inconclusive",
                        "engines_checked": [],
                        "result_urls": [],
                        "notes": "",
                    }
                    for task in tasks
                ],
            },
        )
        instructions_path = workspace.write_text(
            directory / "REVIEW.md",
            "# Reverse-image review\n\n"
            "Install the official `dessant/search-by-image` extension in the managed analyst browser. "
            "For every asset in `assets/`, launch the approved engines, then complete "
            "`results.template.json`. A missing or blocked engine is not a negative result.\n",
        )
        raw_files = [workspace.relative(path) for path in (queue_path, template_path, instructions_path)]
        raw_files.extend(task["review_asset"] for task in tasks)
        return ModuleResult(
            module=self.name,
            status="review_required" if tasks else "ok",
            findings=findings,
            raw_files=list(dict.fromkeys(raw_files)),
            command="analyst review queue generation",
            execution="analyst-assisted",
            duration=round((datetime.now(timezone.utc) - started).total_seconds(), 2),
            note=f"{len(tasks)} image review task(s) generated",
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
