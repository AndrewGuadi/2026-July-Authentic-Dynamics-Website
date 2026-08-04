"""TruffleHog collector (plugin, disabled by default).

Scans **client-supplied local assets only** for accidentally embedded secrets.
Verification is disabled by default so no credential is ever replayed against a
live service. Remote/authenticated sources are intentionally not supported.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, List

from core.runner import run_command
from core.validator import Scope
from core.workspace import Workspace
from modules.base import ModuleResult, OSINTModule
from normalization.normalize_images import from_trufflehog


class TruffleHogModule(OSINTModule):
    """Detect secret material inside the client's own asset bundle."""

    name = "trufflehog"
    scope_field = "image_dir"
    category = "image"
    passive = True
    description = "Secret detection across client-supplied local assets (no verification)."

    @property
    def binary(self) -> str:
        """Native executable name."""
        return "trufflehog"

    def run(self, scope: Scope, workspace: Workspace) -> ModuleResult:
        """Execute TruffleHog against the local asset directory."""
        asset_dir = self.target_value(scope)
        if not asset_dir:
            return ModuleResult.skipped(self.name, "no asset directory in scope")

        mode = self.execution_mode()
        blocked = self.unavailable(mode)
        if blocked:
            return blocked

        tool_args: List[str] = ["filesystem", "--json", "--no-update"]
        if self.options.get("no_verification", True):
            tool_args.append("--no-verification")

        if mode == "docker":
            command = self.docker_command(
                args=[*tool_args, "/assets"],
                volumes={Path(asset_dir): "/assets:ro"},
            )
        else:
            command = ["trufflehog", *tool_args, asset_dir]

        self.log.info("trufflehog scanning local assets at %s (%s)", asset_dir, mode)
        result = run_command(command, timeout=self.timeout)
        raw_files = self.save_raw(workspace, result)

        payload: Any = self.parse_json(result.stdout)
        if payload is None:
            return ModuleResult(
                module=self.name,
                status="ok" if result.ok else "error",
                error=None if result.ok else (result.error or f"exit {result.returncode}"),
                note="no secret candidates detected" if result.ok else None,
                raw_files=raw_files,
                command=result.printable,
                execution=mode,
                duration=result.duration,
            )

        evidence_path = workspace.write_json(workspace.images / "trufflehog_findings.json", payload)
        evidence = workspace.relative(evidence_path)
        findings = from_trufflehog(payload=payload, evidence_file=evidence)
        return ModuleResult(
            module=self.name,
            status="ok",
            findings=findings,
            raw_files=raw_files + [evidence],
            command=result.printable,
            execution=mode,
            duration=result.duration,
            note=f"{len(findings)} secret candidate(s)",
        )
