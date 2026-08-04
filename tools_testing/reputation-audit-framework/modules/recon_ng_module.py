"""Recon-ng adapter for an explicit passive-module allowlist."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from core.runner import CommandResult, run_command
from core.validator import Scope, slugify
from core.workspace import Workspace
from modules.base import ModuleResult, OSINTModule
from normalization.normalize_entities import from_recon_ng

PASSIVE_MODULES = {
    "recon/domains-hosts/certificate_transparency",
    "recon/domains-hosts/hackertarget",
}


class ReconNGModule(OSINTModule):
    """Run selected, preinstalled Recon-ng modules in an isolated workspace."""

    name = "recon_ng"
    scope_field = "domain"
    category = "domain"
    passive = True
    description = "Allowlisted Recon-ng web OSINT with deterministic JSON export."

    @property
    def binary(self) -> str:
        return "recon-cli"

    def run(self, scope: Scope, workspace: Workspace) -> ModuleResult:
        domain = self.target_value(scope)
        if not domain:
            return ModuleResult.skipped(self.name, "no domain in scope")
        mode = self.execution_mode()
        blocked = self.unavailable(mode)
        if blocked:
            return blocked

        selected = [str(m) for m in self.options.get("modules", ["recon/domains-hosts/certificate_transparency"])]
        rejected = sorted(set(selected) - PASSIVE_MODULES)
        if rejected:
            return ModuleResult.failed(self.name, f"non-allowlisted Recon-ng module(s): {', '.join(rejected)}")
        if not selected:
            return ModuleResult.skipped(self.name, "no Recon-ng modules selected")

        outdir = workspace.domain / "recon_ng_raw"
        workspaces_root = outdir / "workspaces"
        workspaces_root.mkdir(parents=True, exist_ok=True)
        input_path = workspace.write_text(outdir / "domain.txt", f"{domain}\n")
        workspace_name = slugify(scope.engagement_id)[:60]
        container_workspace = f"/home/recon/.recon-ng/workspaces/{workspace_name}"
        report_path = workspaces_root / workspace_name / "results.json"
        commands: List[List[str]] = []

        common = ["--no-version", "--no-analytics", "--no-marketplace", "-w", workspace_name]
        commands.append([
            *common, "-m", "import/list",
            "-o", "filename=/input/domain.txt", "-o", "table=domains", "-o", "column=domain", "-x",
        ])
        for module in selected:
            commands.append([*common, "-m", module, "-x"])
        commands.append([
            *common, "-m", "reporting/json",
            "-o", "tables=domains,hosts,contacts",
            "-o", f"filename={container_workspace}/results.json", "-x",
        ])

        raw_files: List[str] = []
        results: List[CommandResult] = []
        for index, args in enumerate(commands, start=1):
            if mode == "docker":
                command = self.docker_command(
                    args=args,
                    volumes={
                        # Mount the parent, not the named workspace itself.
                        # Recon-ng decides whether to create or migrate a DB by
                        # checking if the workspace directory exists. An empty
                        # pre-created mount was misdetected as a legacy DB.
                        workspaces_root: "/home/recon/.recon-ng/workspaces",
                        input_path: "/input/domain.txt:ro",
                    },
                )
            else:
                command = ["recon-cli", *args]
            result = run_command(command, timeout=self.timeout)
            results.append(result)
            raw_files.extend(self.save_raw(workspace, result, suffix=f"step_{index}"))
            if not result.ok:
                break

        failed = next((result for result in results if not result.ok), None)
        payload: Any = self.load_json_file(report_path)
        if payload is None:
            return ModuleResult(
                module=self.name,
                status="error",
                raw_files=raw_files,
                command=" ; ".join(result.printable for result in results),
                execution=mode,
                duration=round(sum(result.duration for result in results), 2),
                error=(failed.error if failed else None) or "Recon-ng produced no JSON report",
            )

        evidence = workspace.relative(report_path)
        findings = from_recon_ng(payload, domain, evidence)
        return ModuleResult(
            module=self.name,
            status="error" if failed else "ok",
            findings=findings,
            raw_files=list(dict.fromkeys([*raw_files, evidence])),
            command=" ; ".join(result.printable for result in results),
            execution=mode,
            duration=round(sum(result.duration for result in results), 2),
            error=(failed.error or f"step exited {failed.returncode}") if failed else None,
            note=f"{len(findings)} normalized record(s) from {len(selected)} passive module(s)",
        )
