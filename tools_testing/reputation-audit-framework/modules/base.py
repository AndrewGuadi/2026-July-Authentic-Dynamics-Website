"""Abstract base class and result contract shared by every collector."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from core.config import AppConfig
from core.logger import get_logger
from core.runner import CommandResult, build_docker_command, binary_available, current_user_spec, docker_available
from core.validator import Scope
from core.workspace import Workspace

Status = str  # "ok" | "review_required" | "skipped" | "error"


@dataclass(slots=True)
class ModuleResult:
    """Uniform result envelope returned by every module."""

    module: str
    status: Status = "ok"
    findings: List[Dict[str, Any]] = field(default_factory=list)
    raw_files: List[str] = field(default_factory=list)
    command: str = ""
    execution: str = "native"
    duration: float = 0.0
    error: Optional[str] = None
    note: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def skipped(cls, module: str, note: str) -> "ModuleResult":
        """Build a 'skipped' result (missing scope input or disabled tool)."""
        return cls(module=module, status="skipped", note=note)

    @classmethod
    def failed(cls, module: str, error: str, command: str = "", duration: float = 0.0) -> "ModuleResult":
        """Build an 'error' result; the engagement continues regardless."""
        return cls(module=module, status="error", error=error, command=command, duration=duration)


class OSINTModule(ABC):
    """Base class for passive collectors.

    Subclasses declare :attr:`name`, :attr:`scope_field` and implement
    :meth:`run`. Helpers here provide execution-mode resolution, raw evidence
    persistence and consistent logging.
    """

    #: Registry key, matches the flag in ``config.yaml``.
    name: str = "base"
    #: Which :class:`~core.validator.Scope` attribute this module consumes.
    scope_field: str = "domain"
    #: Finding category produced by this module.
    category: str = "domain"
    #: Documented as passive-only; active tools are rejected by design.
    passive: bool = True
    #: Short human description used in reports.
    description: str = ""

    def __init__(self, config: AppConfig) -> None:
        """Bind config, options, timeout and logger for this module."""
        self.config = config
        self.options: Dict[str, Any] = config.options_for(self.name)
        self.timeout: int = config.timeout_for(self.name)
        self.log = get_logger(self.name)

    # -- scope -----------------------------------------------------------
    def target_value(self, scope: Scope) -> Optional[str]:
        """Return the scope value this module needs, or ``None`` when absent."""
        value = getattr(scope, self.scope_field, None)
        return str(value) if value else None

    # -- execution -------------------------------------------------------
    def execution_mode(self) -> str:
        """Resolve ``auto`` into either ``native`` or ``docker``."""
        preference = self.config.execution_for(self.name)
        if preference == "native":
            return "native"
        if preference == "docker":
            return "docker"
        return "native" if binary_available(self.binary) else ("docker" if docker_available() else "native")

    @property
    def binary(self) -> str:
        """Native executable name checked by ``auto`` execution."""
        return self.name

    def docker_command(
        self,
        args: List[str],
        volumes: Dict[Path, str],
        workdir: Optional[str] = None,
        entrypoint: Optional[str] = None,
        environment: Optional[Sequence[str]] = None,
    ) -> List[str]:
        """Build a ``docker run`` vector using the configured image."""
        return build_docker_command(
            image=self.config.image_for(self.name),
            args=args,
            volumes=volumes,
            workdir=workdir,
            entrypoint=entrypoint,
            user=current_user_spec(),
            environment=environment,
        )

    def unavailable(self, mode: str) -> Optional[ModuleResult]:
        """Return a graceful 'skipped' result when the tool cannot run."""
        if mode == "native" and not binary_available(self.binary):
            return ModuleResult.skipped(self.name, f"native binary '{self.binary}' not found on PATH")
        if mode == "docker":
            if not docker_available():
                return ModuleResult.skipped(self.name, "docker daemon unavailable")
            if not self.config.image_for(self.name):
                return ModuleResult.skipped(self.name, "no docker image configured")
        return None

    # -- evidence --------------------------------------------------------
    def save_raw(self, workspace: Workspace, result: CommandResult, suffix: str = "") -> List[str]:
        """Persist stdout/stderr/command metadata as raw evidence.

        Returns:
            Workspace-relative paths of the files written.
        """
        directory = workspace.category_dir(self.category)
        stem = f"{self.name}{('_' + suffix) if suffix else ''}"
        written: List[str] = []
        if result.stdout:
            written.append(workspace.relative(workspace.write_text(directory / f"{stem}.stdout.txt", result.stdout)))
        if result.stderr:
            written.append(workspace.relative(workspace.write_text(directory / f"{stem}.stderr.txt", result.stderr)))
        meta = {
            "module": self.name,
            "command": result.command,
            "returncode": result.returncode,
            "duration_seconds": result.duration,
            "timed_out": result.timed_out,
            "error": result.error,
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }
        written.append(workspace.relative(workspace.write_json(directory / f"{stem}.command.json", meta)))
        return written

    @staticmethod
    def parse_json(text: str) -> Any:
        """Parse JSON or NDJSON text, tolerating tool banner noise."""
        text = (text or "").strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        records: List[Any] = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line[0] not in "[{":
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records or None

    @staticmethod
    def load_json_file(path: Path) -> Any:
        """Load a JSON/NDJSON artefact from disk, returning ``None`` on failure."""
        try:
            return OSINTModule.parse_json(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            return None

    # -- contract --------------------------------------------------------
    @abstractmethod
    def run(self, scope: Scope, workspace: Workspace) -> ModuleResult:
        """Execute the collector and return normalised findings."""
        raise NotImplementedError
