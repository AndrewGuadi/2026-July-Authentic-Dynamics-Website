"""Social Analyzer collector using its machine-readable CLI output."""
from __future__ import annotations

from typing import Any, List

from core.runner import run_command
from core.validator import Scope
from core.workspace import Workspace
from modules.base import ModuleResult, OSINTModule
from normalization.normalize_usernames import from_social_analyzer


class SocialAnalyzerModule(OSINTModule):
    """Corroborate an authorized username across bounded public profile sites."""

    name = "social_analyzer"
    scope_field = "username"
    category = "username"
    passive = True
    description = "Bounded public-profile corroboration through Social Analyzer JSON output."

    @property
    def binary(self) -> str:
        return "social-analyzer"

    def run(self, scope: Scope, workspace: Workspace) -> ModuleResult:
        username = self.target_value(scope)
        if not username:
            return ModuleResult.skipped(self.name, "no username in scope")

        mode = self.execution_mode()
        blocked = self.unavailable(mode)
        if blocked:
            return blocked

        top_sites = max(1, min(int(self.options.get("top_sites", 100)), 1000))
        websites = str(self.options.get("websites", "all")).strip() or "all"
        tool_args: List[str] = [
            "--username", username,
            "--output", "json",
            "--filter", "good",
            "--profiles", "detected",
            "--options", "link rate title text",
        ]
        if websites == "all":
            tool_args += ["--top", str(top_sites)]
        else:
            tool_args += ["--websites", websites]
        if bool(self.options.get("metadata", False)):
            tool_args.append("--metadata")
        if bool(self.options.get("extract", False)):
            tool_args.append("--extract")
        if int(self.options.get("request_timeout", 0)) > 0:
            tool_args += ["--timeout", str(int(self.options["request_timeout"]))]

        if mode == "docker":
            command = self.docker_command(args=tool_args, volumes={})
        else:
            command = ["social-analyzer", *tool_args]

        self.log.info("social-analyzer checking '%s' across at most %d sites", username, top_sites)
        result = run_command(command, timeout=self.timeout)
        raw_files = self.save_raw(workspace, result)
        payload: Any = self.parse_json(result.stdout)
        if payload is None:
            return ModuleResult(
                module=self.name,
                status="error",
                error=result.error or "Social Analyzer returned no parsable JSON",
                raw_files=raw_files,
                command=result.printable,
                execution=mode,
                duration=result.duration,
            )

        evidence_path = workspace.write_json(
            workspace.usernames / "social_analyzer_raw" / "results.json", payload
        )
        evidence = workspace.relative(evidence_path)
        findings = from_social_analyzer(
            payload=payload,
            username=username,
            evidence_file=evidence,
            keywords=self.config.impersonation_keywords(),
        )
        return ModuleResult(
            module=self.name,
            status="ok" if result.ok else "error",
            findings=findings,
            raw_files=list(dict.fromkeys([*raw_files, evidence])),
            command=result.printable,
            execution=mode,
            duration=result.duration,
            error=None if result.ok else (result.error or f"collector exited {result.returncode}"),
            note=f"{len(findings)} potential handle match(es)",
        )
