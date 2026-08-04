"""Blackbird collector — secondary passive handle enumeration.

Runs Blackbird's public-endpoint presence checks as a cross-check against
Maigret. Authentication-gated sites are not touched.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, List

from core.runner import run_command
from core.validator import Scope
from core.workspace import Workspace
from modules.base import ModuleResult, OSINTModule
from normalization.normalize_usernames import from_blackbird


class BlackbirdModule(OSINTModule):
    """Cross-validate handle presence with Blackbird."""

    name = "blackbird"
    scope_field = "username"
    category = "username"
    passive = True
    description = "Second-source public handle presence check (corroborates Maigret)."

    @property
    def binary(self) -> str:
        """Native executable name."""
        return "blackbird"

    def run(self, scope: Scope, workspace: Workspace) -> ModuleResult:
        """Execute Blackbird and return normalised username findings."""
        username = self.target_value(scope)
        if not username:
            return ModuleResult.skipped(self.name, "no username in scope")

        mode = self.execution_mode()
        blocked = self.unavailable(mode)
        if blocked:
            return blocked

        outdir = workspace.usernames / "blackbird_raw"
        outdir.mkdir(parents=True, exist_ok=True)

        if mode == "docker":
            # The pinned v1 image accepts ``-u`` and always writes
            # ``/home/results/<username>.json``. Its README/current-master
            # flags are not compatible with the published image.
            tool_args: List[str] = ["-u", username]
            command = self.docker_command(args=tool_args, volumes={outdir: "/home/results"})
        else:
            tool_args = ["-u", username, "--json", "--no-update"]
            if self.options.get("permute"):
                tool_args.append("--permute")
            command = ["blackbird", *tool_args]

        self.log.info("blackbird cross-checking handle '%s' (%s)", username, mode)
        result = run_command(command, timeout=self.timeout, cwd=outdir if mode == "native" else None)
        raw_files = self.save_raw(workspace, result)

        payload = self._load_results(outdir) or self.parse_json(result.stdout)
        if payload is None:
            return ModuleResult(
                module=self.name,
                status="error" if not result.ok else "ok",
                error=result.error or f"no parsable results (exit {result.returncode})",
                raw_files=raw_files,
                command=result.printable,
                execution=mode,
                duration=result.duration,
            )

        report_files = sorted(str(workspace.relative(p)) for p in outdir.rglob("*.json"))
        findings = from_blackbird(
            payload=payload,
            username=username,
            evidence_file=report_files[0] if report_files else (raw_files[0] if raw_files else ""),
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

    def _load_results(self, outdir: Path) -> Any:
        """Load the newest Blackbird JSON artefact from ``outdir``."""
        candidates = sorted(outdir.rglob("*.json"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
        for candidate in candidates:
            payload = self.load_json_file(candidate)
            if payload:
                return payload
        return None
