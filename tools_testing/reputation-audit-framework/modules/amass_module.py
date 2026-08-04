"""OWASP Amass collector — passive subdomain enumeration only.

``-passive`` is hard-coded: Amass only queries third-party data sources
(certificate transparency, passive DNS, public archives). Brute forcing,
zone walking and active resolution are never enabled by this module.
"""
from __future__ import annotations

import math
import re
from typing import Any, List

from core.runner import run_command
from core.validator import Scope
from core.workspace import Workspace
from modules.base import ModuleResult, OSINTModule
from normalization.normalize_domains import from_amass

FORBIDDEN_FLAGS = {"-active", "-brute", "-w", "-rf", "-p"}
FQDN_GRAPH_RE = re.compile(r"(?<![A-Za-z0-9_-])([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+)\s+\(FQDN\)")


class AmassModule(OSINTModule):
    """Enumerate the client's public attack surface from passive sources."""

    name = "amass"
    scope_field = "domain"
    category = "domain"
    passive = True
    description = "Passive subdomain/attack-surface enumeration via third-party datasets."

    @property
    def binary(self) -> str:
        """Native executable name."""
        return "amass"

    def run(self, scope: Scope, workspace: Workspace) -> ModuleResult:
        """Execute Amass in passive mode and return normalised domain findings."""
        domain = self.target_value(scope)
        if not domain:
            return ModuleResult.skipped(self.name, "no domain in scope")
        if not self.options.get("passive_only", True):
            return ModuleResult.skipped(
                self.name,
                "refusing to run: module_options.amass.passive_only must remain true (passive-only policy)",
            )

        mode = self.execution_mode()
        blocked = self.unavailable(mode)
        if blocked:
            return blocked

        outdir = workspace.domain / "amass_raw"
        outdir.mkdir(parents=True, exist_ok=True)
        # Leave at least one minute between Amass's own deadline and the
        # wrapper deadline. Otherwise the wrapper can kill Amass while it is
        # flushing its SQLite/text evidence after an internal timeout.
        minutes = self._internal_timeout_minutes(self.timeout)

        if mode == "docker":
            tool_args: List[str] = [
                "enum", "-passive", "-nocolor", "-d", domain,
                "-timeout", str(minutes), "-dir", "/data", "-o", "/data/amass.txt",
            ]
            command = self.docker_command(args=tool_args, volumes={outdir: "/data"})
        else:
            tool_args = [
                "enum", "-passive", "-nocolor", "-d", domain,
                "-timeout", str(minutes), "-dir", str(outdir), "-o", str(outdir / "amass.txt"),
            ]
            command = ["amass", *tool_args]

        if FORBIDDEN_FLAGS.intersection(tool_args):
            return ModuleResult.failed(self.name, "active Amass flags detected — execution aborted")

        self.log.info("amass passive enumeration for %s (%s)", domain, mode)
        result = run_command(command, timeout=self.timeout)
        raw_files = self.save_raw(workspace, result)
        generated_files = sorted(
            workspace.relative(path) for path in outdir.rglob("*") if path.is_file()
        )
        raw_files = list(dict.fromkeys(raw_files + generated_files))

        output_file = outdir / "amass.txt"
        payload: Any = self._load_hostname_lines(output_file)
        if not payload:
            payload = self._hostname_lines(result.stdout)
        if not payload:
            status = "ok" if result.ok else "error"
            return ModuleResult(
                module=self.name,
                status=status,
                error=None if status == "ok" else (result.error or f"exit {result.returncode}"),
                note="no passive records returned" if status == "ok" else None,
                raw_files=raw_files,
                command=result.printable,
                execution=mode,
                duration=result.duration,
            )

        evidence = workspace.relative(output_file) if output_file.exists() else next(
            (path for path in raw_files if path.endswith(".stdout.txt")),
            raw_files[-1] if raw_files else "",
        )
        findings = from_amass(payload=payload, apex=domain, evidence_file=evidence)
        status = "ok" if result.ok else "error"
        return ModuleResult(
            module=self.name,
            status=status,
            findings=findings,
            raw_files=raw_files + ([evidence] if evidence and evidence not in raw_files else []),
            command=result.printable,
            execution=mode,
            duration=result.duration,
            error=None if result.ok else (result.error or f"collector exited {result.returncode}; findings are partial"),
            note=f"{len(findings)} unique hostname(s)",
        )

    @staticmethod
    def _hostname_lines(text: str) -> List[str]:
        """Extract hostnames from Amass v4 graph output or legacy line output."""
        records: List[str] = []
        for line in (text or "").splitlines():
            clean = line.strip()
            if not clean:
                continue
            graph_hosts = FQDN_GRAPH_RE.findall(clean)
            records.extend(graph_hosts or [clean])
        return list(dict.fromkeys(records))

    @staticmethod
    def _internal_timeout_minutes(wrapper_timeout: int) -> int:
        """Return an Amass deadline with cleanup grace before wrapper kill."""
        return max(1, math.floor(int(wrapper_timeout) / 60) - 1)

    def _load_hostname_lines(self, path: Any) -> List[str]:
        """Read Amass v4's text output without treating it as JSON."""
        try:
            return self._hostname_lines(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            return []
