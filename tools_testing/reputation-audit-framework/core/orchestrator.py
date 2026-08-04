"""Engagement orchestrator: plans, executes, normalises, scores and reports."""
from __future__ import annotations

import json
import platform
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.config import AppConfig
from core.logger import configure_logging
from core.risk import RiskAssessment, RiskEngine
from core.runner import docker_available
from core.validator import Scope
from core.workspace import Workspace
from modules import MODULE_ORDER, MODULE_REGISTRY
from modules.base import ModuleResult, OSINTModule
from integrations import LinkScopeExporter, OpenAlephExporter, ReverseImageReview
from normalization.schema import FINDING_TYPES
from reporting.markdown_report import MarkdownReportBuilder
from reporting.pdf_generator import PdfGenerator

BAND_COLOURS = {"Low": "green", "Moderate": "yellow", "Elevated": "dark_orange", "High": "red"}


class Orchestrator:
    """Coordinates the full passive audit lifecycle for one engagement."""

    def __init__(
        self,
        config: AppConfig,
        scope: Scope,
        output_root: Path,
        console: Console,
        verbose: bool = False,
        render_pdf: bool = True,
    ) -> None:
        """Wire up config, scope and output destinations.

        Args:
            config: Loaded application config.
            scope: Validated, authorized engagement scope.
            output_root: Root directory for evidence workspaces.
            console: Rich console for operator feedback.
            verbose: Enable DEBUG console logging.
            render_pdf: Attempt PDF rendering when wkhtmltopdf is present.
        """
        self.config = config
        self.scope = scope
        self.output_root = Path(output_root)
        self.console = console
        self.verbose = verbose
        self.render_pdf = render_pdf and bool(config.reporting.get("pdf", True))
        self.workspace: Optional[Workspace] = None
        self.results: List[ModuleResult] = []

    # -- planning --------------------------------------------------------
    def planned_modules(self) -> List[OSINTModule]:
        """Instantiate enabled modules that have the scope input they need."""
        planned: List[OSINTModule] = []
        ordered = [n for n in MODULE_ORDER if n in MODULE_REGISTRY]
        ordered += [n for n in sorted(MODULE_REGISTRY) if n not in ordered]
        for name in ordered:
            if not self.config.modules.get(name, False):
                continue
            module = MODULE_REGISTRY[name](self.config)
            planned.append(module)
        return planned

    def print_plan(self) -> None:
        """Print the execution plan without running anything (``--dry-run``)."""
        table = Table(title="Execution plan (dry run)", header_style="bold green")
        table.add_column("Order")
        table.add_column("Module")
        table.add_column("Target")
        table.add_column("Execution")
        table.add_column("State")
        for index, module in enumerate(self.planned_modules(), start=1):
            target = module.target_value(self.scope)
            state = "[green]ready[/green]" if target else "[yellow]skip (no scope input)[/yellow]"
            table.add_row(str(index), module.name, str(target or "—"), module.execution_mode(), state)
        next_index = len(self.planned_modules()) + 1
        integration_targets = {
            "search_by_image": self.scope.image_dir,
            "linkscope": self.scope.full_name,
            "openaleph": self.scope.engagement_id,
        }
        for name in ("search_by_image", "linkscope", "openaleph"):
            if not self.config.integration_enabled(name):
                continue
            target = integration_targets[name]
            state = "[green]ready[/green]" if target else "[yellow]skip (no scope input)[/yellow]"
            table.add_row(str(next_index), name, str(target or "—"), "integration", state)
            next_index += 1
        self.console.print(table)
        self.console.print(
            Panel(
                f"Client: [bold]{self.scope.full_name}[/bold]\n"
                f"Engagement: {self.scope.engagement_id}\n"
                f"Targets: {', '.join(self.scope.targets)}\n"
                f"Docker daemon: {'available' if docker_available() else 'unavailable'}\n"
                f"Output root: {self.output_root}",
                title="Scope",
                border_style="green",
            )
        )

    # -- execution -------------------------------------------------------
    def execute(self) -> Dict[str, Any]:
        """Run the engagement end to end.

        Returns:
            A summary dictionary (also written to ``summary.json``).
        """
        started = datetime.now(timezone.utc)
        self.workspace = Workspace.create(self.output_root, self.scope.client_slug, started)
        workspace = self.workspace

        log_conf = self.config.logging
        logger = configure_logging(
            log_file=workspace.logs / str(log_conf.get("file", "audit.log")),
            level=str(log_conf.get("level", "INFO")),
            verbose=self.verbose,
            json_lines=bool(log_conf.get("json_lines", True)),
            console=self.console,
        )

        logger.info("engagement %s started by %s", self.scope.engagement_id, self.scope.operator)
        logger.info("authorization attested at %s", self.scope.authorized_at)
        logger.info("scope targets: %s", ", ".join(self.scope.targets))
        workspace.write_json(
            workspace.root / "scope.json",
            {
                "scope": self.scope.to_dict(),
                "config_file": str(self.config.source_path),
                "framework_version": "1.1.0",
                "python": sys.version.split()[0],
                "platform": platform.platform(),
                "collection_started": started.isoformat(),
            },
        )

        modules = self.planned_modules()
        if not modules:
            logger.warning("no modules enabled in %s", self.config.source_path)

        for module in modules:
            target = module.target_value(self.scope)
            if not target:
                logger.warning("%s skipped: no matching scope input (%s)", module.name, module.scope_field)
                self.results.append(ModuleResult.skipped(module.name, f"no {module.scope_field} in scope"))
                continue
            self.console.print(f"[bold green]▸[/bold green] running [bold]{module.name}[/bold] → {target}")
            logger.info("module %s starting (execution=%s)", module.name, module.execution_mode())
            try:
                result = module.run(self.scope, workspace)
            except Exception as exc:  # defensive: modules must never break the run
                logger.exception("module %s crashed: %s", module.name, exc)
                result = ModuleResult.failed(module.name, f"unhandled exception: {exc}")
            self.results.append(result)
            level = logger.info if result.status == "ok" else logger.warning
            level(
                "module %s finished status=%s findings=%d duration=%.2fs",
                result.module,
                result.status,
                len(result.findings),
                result.duration,
            )

        findings = [f for result in self.results for f in result.findings]

        if self.config.integration_enabled("search_by_image"):
            result = self._run_postprocessor(
                "search_by_image",
                lambda: ReverseImageReview(self.config).run(self.scope, workspace),
                logger,
            )
            self.results.append(result)
            findings.extend(result.findings)

        self._persist_findings(workspace, findings)

        risk = RiskEngine(self.config).assess(findings)
        workspace.write_json(workspace.normalized / "risk.json", risk.to_dict())
        logger.info("risk score %d (%s)", risk.score, risk.band)

        if self.config.integration_enabled("linkscope"):
            result = self._run_postprocessor(
                "linkscope",
                lambda: LinkScopeExporter(self.config).run(self.scope, workspace, findings),
                logger,
            )
            self.results.append(result)

        report_paths = self._render_reports(workspace, findings, risk, started)

        if self.config.integration_enabled("openaleph"):
            result = self._run_postprocessor(
                "openaleph",
                lambda: OpenAlephExporter(self.config).run(self.scope, workspace),
                logger,
            )
            self.results.append(result)
            # Render once more so the final report contains the export/upload status.
            report_paths = self._render_reports(workspace, findings, risk, started)
        finished = datetime.now(timezone.utc)

        summary: Dict[str, Any] = {
            "status": "completed",
            "engagement_id": self.scope.engagement_id,
            "client": self.scope.full_name,
            "workspace": str(workspace.root),
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "duration_seconds": round((finished - started).total_seconds(), 2),
            "modules": [asdict(r) | {"findings": len(r.findings)} for r in self.results],
            "finding_counts": risk.counts,
            "risk": {"score": risk.score, "band": risk.band},
            "reports": {k: str(v) for k, v in report_paths.items() if v},
        }
        collector_results = [r for r in self.results if r.module in MODULE_REGISTRY]
        if not any(r.status == "ok" for r in collector_results):
            summary["status"] = "incomplete_no_collectors"
        elif any(r.status == "error" for r in self.results):
            summary["status"] = "completed_with_errors"
        elif any(r.status == "skipped" for r in self.results):
            summary["status"] = "completed_with_gaps"
        elif any(r.status == "review_required" for r in self.results):
            summary["status"] = "completed_with_review"
        workspace.write_json(workspace.root / "summary.json", summary)
        logger.info("engagement %s %s", self.scope.engagement_id, summary["status"])
        return summary

    # -- helpers ---------------------------------------------------------
    def _persist_findings(self, workspace: Workspace, findings: List[Dict[str, Any]]) -> None:
        """Write normalised findings split by type plus a combined document."""
        buckets: Dict[str, List[Dict[str, Any]]] = {name: [] for name in FINDING_TYPES}
        for finding in findings:
            buckets.setdefault(str(finding.get("type", "other")), []).append(finding)
        for name, items in buckets.items():
            workspace.write_findings(f"{name}s", items)
        workspace.write_findings("all_findings", findings)

    @staticmethod
    def _run_postprocessor(name: str, callback: Any, logger: Any) -> ModuleResult:
        """Run an integration without allowing it to abort report generation."""
        logger.info("integration %s starting", name)
        try:
            result: ModuleResult = callback()
        except Exception as exc:  # defensive boundary around third-party connectors
            logger.exception("integration %s crashed: %s", name, exc)
            return ModuleResult.failed(name, f"unhandled integration exception: {exc}")
        logger.info(
            "integration %s finished status=%s findings=%d",
            name,
            result.status,
            len(result.findings),
        )
        return result

    def _render_reports(
        self,
        workspace: Workspace,
        findings: List[Dict[str, Any]],
        risk: RiskAssessment,
        started: datetime,
    ) -> Dict[str, Optional[Path]]:
        """Render Markdown (always) and PDF (best effort) deliverables."""
        paths: Dict[str, Optional[Path]] = {"markdown": None, "pdf": None, "json": None}
        builder = MarkdownReportBuilder(
            config=self.config,
            scope=self.scope,
            workspace=workspace,
            results=self.results,
            findings=findings,
            risk=risk,
            started=started,
        )
        markdown = builder.build()
        paths["markdown"] = workspace.write_text(workspace.report / "report.md", markdown)
        paths["json"] = workspace.write_json(
            workspace.report / "report.json",
            {
                "scope": self.scope.to_dict(),
                "risk": risk.to_dict(),
                "modules": [asdict(r) for r in self.results],
                "findings": findings,
            },
        )
        if self.render_pdf:
            generator = PdfGenerator()
            paths["pdf"] = generator.generate(
                markdown=markdown,
                destination=workspace.report / "report.pdf",
                title=f"Reputation Audit — {self.scope.full_name}",
            )
            if paths["pdf"] is None:
                self.console.print("[yellow]wkhtmltopdf unavailable — PDF skipped (Markdown written).[/yellow]")
        return paths

    def print_summary(self, summary: Dict[str, Any]) -> None:
        """Render the post-run operator summary."""
        table = Table(title="Module results", header_style="bold green")
        table.add_column("Module")
        table.add_column("Status")
        table.add_column("Findings", justify="right")
        table.add_column("Seconds", justify="right")
        table.add_column("Detail")
        status_colour = {
            "ok": "green",
            "review_required": "cyan",
            "skipped": "yellow",
            "error": "red",
        }
        for entry in summary["modules"]:
            colour = status_colour.get(entry["status"], "white")
            table.add_row(
                entry["module"],
                f"[{colour}]{entry['status']}[/{colour}]",
                str(entry["findings"]),
                f"{entry['duration']:.1f}",
                (entry.get("error") or entry.get("note") or "—")[:60],
            )
        self.console.print(table)

        band = summary["risk"]["band"]
        colour = BAND_COLOURS.get(band, "white")
        self.console.print(
            Panel(
                f"Risk score: [bold]{summary['risk']['score']}[/bold]   "
                f"Band: [bold {colour}]{band}[/bold {colour}]\n"
                f"Findings: {json.dumps(summary['finding_counts'])}\n"
                f"Workspace: {summary['workspace']}\n"
                f"Report: {summary['reports'].get('markdown', 'n/a')}",
                title=f"Engagement {summary['engagement_id']}",
                border_style=colour,
            )
        )
