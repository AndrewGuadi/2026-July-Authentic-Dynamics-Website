"""theHarvester collector (plugin, disabled by default).

Queries passive OSINT sources (certificate transparency, public DNS datasets,
threat-intel feeds) for hostnames and published contact addresses. Search
engines requiring CAPTCHA solving or paid API abuse are excluded by config.
"""
from __future__ import annotations

from typing import Any, List

from core.runner import run_command
from core.validator import Scope
from core.workspace import Workspace
from modules.base import ModuleResult, OSINTModule
from normalization.normalize_domains import from_theharvester

#: Sources known to require CAPTCHA solving or authenticated scraping.
BLOCKED_SOURCES = {"google", "bing", "baidu", "yahoo", "linkedin", "twitter", "instagram"}


class TheHarvesterModule(OSINTModule):
    """Collect hostnames and published addresses from passive feeds."""

    name = "theharvester"
    scope_field = "domain"
    category = "domain"
    passive = True
    description = "Passive hostname/e-mail discovery from public datasets."

    @property
    def binary(self) -> str:
        """Native executable name."""
        return "theHarvester"

    def sources(self) -> List[str]:
        """Return the configured sources minus any CAPTCHA/auth-gated engine."""
        requested = [str(s).strip().lower() for s in (self.options.get("sources") or ["crtsh"])]
        return [s for s in requested if s and s not in BLOCKED_SOURCES]

    def run(self, scope: Scope, workspace: Workspace) -> ModuleResult:
        """Execute theHarvester and return normalised domain findings."""
        domain = self.target_value(scope)
        if not domain:
            return ModuleResult.skipped(self.name, "no domain in scope")

        sources = self.sources()
        if not sources:
            return ModuleResult.skipped(self.name, "all configured sources are CAPTCHA/auth gated and were rejected")

        mode = self.execution_mode()
        blocked = self.unavailable(mode)
        if blocked:
            return blocked

        outdir = workspace.domain / "theharvester_raw"
        outdir.mkdir(parents=True, exist_ok=True)

        if mode == "docker":
            command = self.docker_command(
                args=["-d", domain, "-b", ",".join(sources), "-f", "/output/theharvester"],
                volumes={outdir: "/output"},
            )
        else:
            command = ["theHarvester", "-d", domain, "-b", ",".join(sources), "-f", str(outdir / "theharvester")]

        self.log.info("theharvester querying %d passive source(s) for %s", len(sources), domain)
        result = run_command(command, timeout=self.timeout)
        raw_files = self.save_raw(workspace, result)

        payload: Any = None
        for candidate in sorted(outdir.glob("theharvester*.json")):
            payload = self.load_json_file(candidate)
            if payload:
                break
        if payload is None:
            return ModuleResult(
                module=self.name,
                status="ok" if result.ok else "error",
                error=None if result.ok else (result.error or f"exit {result.returncode}"),
                note="no passive records returned" if result.ok else None,
                raw_files=raw_files,
                command=result.printable,
                execution=mode,
                duration=result.duration,
            )

        evidence = next((str(workspace.relative(p)) for p in outdir.glob("theharvester*.json")), raw_files[0])
        findings = from_theharvester(payload=payload, apex=domain, evidence_file=evidence)
        return ModuleResult(
            module=self.name,
            status="ok",
            findings=findings,
            raw_files=raw_files + [evidence],
            command=result.printable,
            execution=mode,
            duration=result.duration,
            note=f"{len(findings)} artefact(s) from {len(sources)} source(s)",
        )
