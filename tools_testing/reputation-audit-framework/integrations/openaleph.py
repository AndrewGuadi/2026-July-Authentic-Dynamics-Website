"""Package or upload completed evidence to OpenAleph through alephclient."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from core.config import AppConfig
from core.runner import binary_available, build_docker_command, current_user_spec, run_command
from core.validator import Scope, slugify
from core.workspace import Workspace
from modules.base import ModuleResult


class OpenAlephExporter:
    """Create an import manifest and optionally upload the workspace."""

    name = "openaleph"

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.options = config.integration_options(self.name)
        self.timeout = int(self.options.get("timeout", 1800))

    def run(self, scope: Scope, workspace: Workspace) -> ModuleResult:
        started = datetime.now(timezone.utc)
        directory = workspace.integrations / "openaleph"
        directory.mkdir(parents=True, exist_ok=True)
        foreign_id = str(self.options.get("foreign_id_prefix", "raf")) + "-" + slugify(scope.engagement_id)
        mode = str(self.options.get("mode", "package")).lower()
        manifest_path = workspace.write_json(
            directory / "manifest.json",
            {
                "integration": "openaleph",
                "mode": mode,
                "foreign_id": foreign_id,
                "engagement_id": scope.engagement_id,
                "subject": scope.full_name,
                "workspace": workspace.root.name,
                "created_at": started.isoformat(),
                "source": "https://github.com/openaleph/openaleph",
                "client": "https://github.com/alephdata/alephclient",
            },
        )
        manifest = workspace.relative(manifest_path)
        if mode == "package":
            instructions = workspace.write_text(
                directory / "UPLOAD.md",
                "# OpenAleph upload package\n\n"
                f"Set `ALEPH_HOST` and `ALEPH_API_KEY`, then run the framework with "
                f"`integrations.openaleph.mode: upload`. The collection foreign ID is `{foreign_id}`.\n",
            )
            return ModuleResult(
                module=self.name,
                status="ok",
                raw_files=[manifest, workspace.relative(instructions)],
                command="OpenAleph import package generation",
                execution="package",
                duration=round((datetime.now(timezone.utc) - started).total_seconds(), 2),
                note="import-ready package generated; network upload not requested",
            )
        if mode != "upload":
            return ModuleResult.failed(self.name, f"unknown OpenAleph mode: {mode!r}")
        if not os.environ.get("ALEPH_HOST") or not os.environ.get("ALEPH_API_KEY"):
            return ModuleResult.skipped(self.name, "ALEPH_HOST and ALEPH_API_KEY are required for upload mode")

        execution = str(self.options.get("execution", "docker"))
        args = ["crawldir", "--nojunk", "--foreign-id", foreign_id, "/evidence"]
        if execution == "native":
            if not binary_available("alephclient"):
                return ModuleResult.skipped(self.name, "native alephclient binary not found")
            command = ["alephclient", *args]
        elif execution == "docker":
            image = str(self.options.get("image", "reputation-audit-framework-alephclient:2.7.0"))
            command = build_docker_command(
                image=image,
                args=args,
                volumes={workspace.root: "/evidence:ro"},
                user=current_user_spec(),
                environment=["ALEPH_HOST", "ALEPH_API_KEY"],
            )
        else:
            return ModuleResult.failed(self.name, f"invalid OpenAleph execution mode: {execution!r}")

        result = run_command(command, timeout=self.timeout)
        stdout_path = workspace.write_text(directory / "alephclient.stdout.txt", result.stdout)
        stderr_path = workspace.write_text(directory / "alephclient.stderr.txt", result.stderr)
        command_path = workspace.write_json(
            directory / "alephclient.command.json",
            {
                "command": result.command,
                "returncode": result.returncode,
                "duration_seconds": result.duration,
                "timed_out": result.timed_out,
                "error": result.error,
                "secrets_embedded": False,
            },
        )
        raw_files = [
            manifest,
            workspace.relative(stdout_path),
            workspace.relative(stderr_path),
            workspace.relative(command_path),
        ]
        return ModuleResult(
            module=self.name,
            status="ok" if result.ok else "error",
            raw_files=raw_files,
            command=result.printable,
            execution=execution,
            duration=result.duration,
            error=None if result.ok else (result.error or f"alephclient exited {result.returncode}"),
            note=f"workspace uploaded to OpenAleph collection {foreign_id}" if result.ok else None,
        )
