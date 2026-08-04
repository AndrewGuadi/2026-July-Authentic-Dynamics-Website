"""SpiderFoot collector — passive OSINT modules only.

Only modules on the configured allowlist run, and any module on the active
denylist (spidering, port scanning, DNS brute force, credential checks) is
rejected before execution.
"""
from __future__ import annotations

from typing import Any, List

from core.runner import run_command
from core.validator import Scope
from core.workspace import Workspace
from modules.base import ModuleResult, OSINTModule
from normalization.normalize_domains import from_spiderfoot

#: Modules that touch the target directly or perform intrusive work.
ACTIVE_DENYLIST = {
    "sfp_portscan_tcp", "sfp_dnsbrute", "sfp_spider", "sfp_intfiles", "sfp_dnszonexfer",
    "sfp_sslcert_scan", "sfp_webframework", "sfp_webserver", "sfp_wappalyzer",
    "sfp_dnscommonsrv", "sfp_fileextensions", "sfp_bruteforce",
    "sfp_pageinfo", "sfp_socialprofiles",
}
DEFAULT_MODULES = [
    "sfp_dnsresolve", "sfp_hackertarget", "sfp_whois",
]


class SpiderFootModule(OSINTModule):
    """Correlate passive OSINT sources for the in-scope domain."""

    name = "spiderfoot"
    scope_field = "domain"
    category = "domain"
    passive = True
    description = "Multi-source passive OSINT correlation (allowlisted modules only)."

    @property
    def binary(self) -> str:
        """Native executable name (SpiderFoot CLI entry point)."""
        return "sf.py"

    def selected_modules(self) -> List[str]:
        """Return the validated, passive-only SpiderFoot module list."""
        requested = [str(m).strip() for m in (self.options.get("modules") or DEFAULT_MODULES)]
        return [m for m in requested if m.startswith("sfp_") and m not in ACTIVE_DENYLIST]

    def run(self, scope: Scope, workspace: Workspace) -> ModuleResult:
        """Execute SpiderFoot headlessly and return normalised domain findings."""
        domain = self.target_value(scope)
        if not domain:
            return ModuleResult.skipped(self.name, "no domain in scope")

        modules = self.selected_modules()
        rejected = sorted(set(str(m) for m in (self.options.get("modules") or [])) - set(modules))
        if not modules:
            return ModuleResult.skipped(self.name, "no passive modules left after allowlist filtering")
        if rejected:
            self.log.warning("spiderfoot rejected non-passive modules: %s", ", ".join(rejected))

        mode = self.execution_mode()
        blocked = self.unavailable(mode)
        if blocked:
            return blocked

        outdir = workspace.domain / "spiderfoot_raw"
        outdir.mkdir(parents=True, exist_ok=True)
        tool_args = ["-s", domain, "-m", ",".join(modules), "-o", "json", "-q"]

        if mode == "docker":
            command = self.docker_command(
                # The pinned image entrypoint is already ``python sf.py`` and
                # its working directory is /opt/spiderfoot. Passing sf.py a
                # second time makes Python look for /opt/spiderfoot/sf.py as a
                # positional CLI input after an overridden workdir.
                args=tool_args,
                volumes={},
            )
        else:
            command = ["sf.py", *tool_args]

        self.log.info("spiderfoot passive scan of %s with %d module(s)", domain, len(modules))
        result = run_command(command, timeout=self.timeout)
        raw_files = self.save_raw(workspace, result)

        payload: Any = self.parse_json(result.stdout)
        if payload is None:
            status = "ok" if result.ok else "error"
            return ModuleResult(
                module=self.name,
                status=status,
                error=None if status == "ok" else (result.error or f"exit {result.returncode}"),
                note="no events returned" if status == "ok" else None,
                raw_files=raw_files,
                command=result.printable,
                execution=mode,
                duration=result.duration,
            )

        evidence_path = workspace.write_json(outdir / "spiderfoot.json", payload)
        evidence = workspace.relative(evidence_path)
        findings = from_spiderfoot(payload=payload, apex=domain, evidence_file=evidence)
        status = "ok" if result.ok else "error"
        return ModuleResult(
            module=self.name,
            status=status,
            findings=findings,
            raw_files=raw_files + [evidence],
            command=result.printable,
            execution=mode,
            duration=result.duration,
            error=None if result.ok else (result.error or f"collector exited {result.returncode}; findings are partial"),
            note=f"{len(findings)} passive event(s) from {len(modules)} module(s)",
        )
