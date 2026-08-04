"""Validate analyst decisions and fold them back into a completed workspace."""
from __future__ import annotations

import json
import shutil
from dataclasses import asdict, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from core.config import AppConfig
from core.risk import RiskEngine
from core.validator import Scope
from core.workspace import Workspace
from modules.base import ModuleResult
from normalization.schema import FINDING_TYPES, dedupe, make_finding
from reporting.markdown_report import MarkdownReportBuilder

REVIEW_STATES = {"confirmed", "rejected", "candidate_match", "no_match", "inconclusive"}


class ReviewImportError(ValueError):
    """Raised when an analyst review document does not match the workspace."""


def import_review_document(
    workspace_root: Path,
    review_file: Path,
    config: AppConfig,
) -> Dict[str, Any]:
    """Import reverse-image or LinkScope decisions and regenerate normalized reports."""
    root = Path(workspace_root).expanduser().resolve()
    source = Path(review_file).expanduser().resolve()
    if not source.is_file():
        raise ReviewImportError(f"review file does not exist: {source}")
    scope_doc = _load_json(root / "scope.json")
    report_doc = _load_json(root / "report" / "report.json")
    findings_doc = _load_json(root / "normalized" / "all_findings.json")
    review = _load_json(source)
    scope_data = scope_doc.get("scope")
    if not isinstance(scope_data, dict):
        raise ReviewImportError("workspace scope.json is malformed")
    scope = Scope(**scope_data)
    if review.get("engagement_id") != scope.engagement_id:
        raise ReviewImportError("review engagement_id does not match the workspace")
    kind = str(review.get("kind") or "")
    if kind not in {"reverse_image", "linkscope"}:
        raise ReviewImportError("review kind must be reverse_image or linkscope")
    reviewer = str(review.get("reviewer") or "").strip()
    if not reviewer:
        raise ReviewImportError("reviewer is required")

    workspace = Workspace(root=root, created_at=str(scope_doc.get("collection_started") or scope.authorized_at))
    import_dir = workspace.manual_review / "imports"
    import_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    imported_path = import_dir / f"{kind}_{stamp}.json"
    shutil.copy2(source, imported_path)
    evidence = workspace.relative(imported_path)

    existing = findings_doc.get("findings")
    if not isinstance(existing, list):
        raise ReviewImportError("normalized/all_findings.json is malformed")
    new_findings = _review_findings(kind, review, root, evidence, reviewer)
    reviewed_task_ids = {
        str(f.get("details", {}).get("task_id"))
        for f in new_findings
        if isinstance(f.get("details"), dict) and f.get("details", {}).get("task_id")
    }
    retained = [
        finding
        for finding in existing
        if not (
            finding.get("type") == "manual_review"
            and finding.get("risk_hint") == "review_pending"
            and str((finding.get("details") or {}).get("task_id")) in reviewed_task_ids
        )
    ]
    findings = dedupe([*retained, *new_findings])

    module_fields = {item.name for item in fields(ModuleResult)}
    results: List[ModuleResult] = []
    for item in report_doc.get("modules") or []:
        if isinstance(item, dict):
            results.append(ModuleResult(**{key: value for key, value in item.items() if key in module_fields}))
    if kind == "reverse_image" and not any(
        finding.get("risk_hint") == "review_pending" for finding in findings
    ):
        for result in results:
            if result.module == "search_by_image":
                result.status = "ok"
                result.note = "all generated reverse-image tasks have imported decisions"
    results.append(
        ModuleResult(
            module=f"{kind}_review_import",
            status="ok",
            findings=new_findings,
            raw_files=[evidence],
            execution="analyst-import",
            note=f"{len(new_findings)} reviewed record(s) imported by {reviewer}",
        )
    )

    for finding_type in FINDING_TYPES:
        workspace.write_findings(
            f"{finding_type}s",
            [finding for finding in findings if finding.get("type") == finding_type],
        )
    workspace.write_findings("all_findings", findings)
    risk = RiskEngine(config).assess(findings)
    workspace.write_json(workspace.normalized / "risk.json", risk.to_dict())

    started_raw = str(scope_doc.get("collection_started") or scope.authorized_at)
    try:
        started = datetime.fromisoformat(started_raw)
    except ValueError:
        started = datetime.now(timezone.utc)
    builder = MarkdownReportBuilder(config, scope, workspace, results, findings, risk, started)
    workspace.write_text(workspace.report / "report.md", builder.build())
    workspace.write_json(
        workspace.report / "report.json",
        {
            "scope": scope.to_dict(),
            "risk": risk.to_dict(),
            "modules": [asdict(result) for result in results],
            "findings": findings,
        },
    )
    summary_path = root / "summary.json"
    summary = _load_json(summary_path)
    summary["modules"] = [asdict(result) | {"findings": len(result.findings)} for result in results]
    summary["finding_counts"] = risk.counts
    summary["risk"] = {"score": risk.score, "band": risk.band}
    if any(result.status == "error" for result in results):
        summary["status"] = "completed_with_errors"
    elif any(result.status == "skipped" for result in results):
        summary["status"] = "completed_with_gaps"
    elif any(result.status == "review_required" for result in results):
        summary["status"] = "completed_with_review"
    else:
        summary["status"] = "completed"
    workspace.write_json(summary_path, summary)
    return {
        "kind": kind,
        "reviewer": reviewer,
        "imported_file": evidence,
        "new_findings": len(new_findings),
        "total_findings": len(findings),
        "status": summary["status"],
    }


def _review_findings(
    kind: str,
    review: Dict[str, Any],
    workspace_root: Path,
    evidence: str,
    reviewer: str,
) -> List[Dict[str, Any]]:
    if kind == "reverse_image":
        tasks_doc = _load_json(workspace_root / "manual_review" / "reverse_image" / "tasks.json")
        valid_ids = {str(task.get("task_id")) for task in tasks_doc.get("tasks") or [] if isinstance(task, dict)}
        records = review.get("reviews")
        id_field = "task_id"
    else:
        node_doc = _load_json(workspace_root / "integrations" / "linkscope" / "node_map.json")
        valid_ids = {str(node.get("node_id")) for node in node_doc.get("nodes") or [] if isinstance(node, dict)}
        records = review.get("decisions")
        id_field = "finding_id"
    if not isinstance(records, list):
        raise ReviewImportError(f"{kind} review records must be a list")

    findings: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ReviewImportError("every review record must be an object")
        record_id = str(record.get(id_field) or "")
        status = str(record.get("status") or "")
        if record_id not in valid_ids:
            raise ReviewImportError(f"unknown {id_field}: {record_id!r}")
        if record_id in seen:
            raise ReviewImportError(f"duplicate {id_field}: {record_id!r}")
        if status not in REVIEW_STATES:
            raise ReviewImportError(f"invalid review status for {record_id}: {status!r}")
        seen.add(record_id)
        details = dict(record)
        details.update({"reviewer": reviewer, "review_state": "reviewed"})
        if kind == "reverse_image":
            details["task_id"] = record_id
        findings.append(
            make_finding(
                finding_type="manual_review",
                source_tool="search-by-image" if kind == "reverse_image" else "linkscope",
                value=record_id,
                risk_hint="informational",
                evidence_file=evidence,
                details=details,
            )
        )
        if kind == "reverse_image" and status == "candidate_match":
            for url in record.get("result_urls") or []:
                url = str(url).strip()
                if url.startswith(("http://", "https://")):
                    findings.append(
                        make_finding(
                            finding_type="image",
                            source_tool="search-by-image",
                            value=url,
                            risk_hint="informational",
                            evidence_file=evidence,
                            details={"task_id": record_id, "reviewer": reviewer, "ownership": "unverified_visual_match"},
                        )
                    )
    return findings


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewImportError(f"cannot read JSON document {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReviewImportError(f"JSON document must contain an object: {path}")
    return payload
