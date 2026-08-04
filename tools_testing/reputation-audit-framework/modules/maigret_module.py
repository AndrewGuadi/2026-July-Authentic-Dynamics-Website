"""Maigret collector — passive public account enumeration for a handle.

Maigret checks whether a handle is *publicly* claimed on OSINT-friendly sites.
No credentials are supplied, no login walls are bypassed and no CAPTCHA is
solved: unreachable or gated sites are simply reported as unknown and dropped.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, List

from core.runner import run_command
from core.validator import Scope
from core.workspace import Workspace
from modules.base import ModuleResult, OSINTModule
from normalization.normalize_usernames import from_maigret


class MaigretModule(OSINTModule):
    """Enumerate publicly claimed accounts for the in-scope username."""

    name = "maigret"
    scope_field = "username"
    category = "username"
    passive = True
    description = "Public account presence for a handle across OSINT-indexed sites."

    @property
    def binary(self) -> str:
        """Native executable name."""
        return "maigret"

    def run(self, scope: Scope, workspace: Workspace) -> ModuleResult:
        """Execute Maigret and return normalised username findings."""
        username = self.target_value(scope)
        if not username:
            return ModuleResult.skipped(self.name, "no username in scope")

        mode = self.execution_mode()
        blocked = self.unavailable(mode)
        if blocked:
            return blocked

        outdir = workspace.usernames / "maigret_raw"
        outdir.mkdir(parents=True, exist_ok=True)

        tool_args: List[str] = [
            username,
            "--json", "simple",
            "--no-progressbar",
            "--no-color",
            "--no-recursion",
            "--no-extracting",
            "--no-autoupdate",
            "--timeout", str(int(self.options.get("request_timeout", 10))),
            "--top-sites", str(int(self.options.get("top_sites", 500))),
        ]
        for tag in self.options.get("tags") or []:
            tool_args += ["--tags", str(tag)]

        if mode == "docker":
            command = self.docker_command(
                args=tool_args + ["--folderoutput", "/reports"],
                volumes={outdir: "/reports"},
            )
        else:
            command = ["maigret", *tool_args, "--folderoutput", str(outdir)]

        self.log.info("maigret enumerating handle '%s' (%s)", username, mode)
        result = run_command(command, timeout=self.timeout)
        raw_files = self.save_raw(workspace, result)

        payload = self._load_report(outdir) or self.parse_json(result.stdout)
        if payload is None:
            status = "ok" if result.ok else "error"
            return ModuleResult(
                module=self.name,
                status=status,
                error=None if status == "ok" else (result.error or f"no parsable report (exit {result.returncode})"),
                note="no public matches returned in the bounded site set" if status == "ok" else None,
                raw_files=raw_files,
                command=result.printable,
                execution=mode,
                duration=result.duration,
            )

        evidence = next((f for f in raw_files if f.endswith(".stdout.txt")), raw_files[-1] if raw_files else "")
        report_files = sorted(str(workspace.relative(p)) for p in outdir.glob("*.json"))
        findings = from_maigret(
            payload=payload,
            username=username,
            evidence_file=report_files[0] if report_files else evidence,
            keywords=self.config.impersonation_keywords(),
        )
        status = "ok" if result.ok else "error"
        return ModuleResult(
            module=self.name,
            status=status,
            findings=findings,
            raw_files=raw_files + report_files,
            command=result.printable,
            execution=mode,
            duration=result.duration,
            error=None if result.ok else (result.error or f"collector exited {result.returncode}; findings are partial"),
            note=f"{len(findings)} potential handle match(es)",
        )

    def _load_report(self, outdir: Path) -> Any:
        """Load the newest Maigret JSON report from ``outdir``."""
        reports = sorted(outdir.glob("*.json"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
        for report in reports:
            payload = self.load_json_file(report)
            if payload:
                return payload
        return None
