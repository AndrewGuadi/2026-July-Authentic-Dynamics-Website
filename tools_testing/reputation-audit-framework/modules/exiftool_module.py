"""ExifTool collector — metadata review of client-supplied images.

Operates only on files the client provided locally (``--image-dir``). Nothing is
downloaded, and no remote asset is fetched by this module.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, List

from core.runner import run_command
from core.validator import Scope
from core.workspace import Workspace
from modules.base import ModuleResult, OSINTModule
from normalization.normalize_images import from_exiftool


class ExifToolModule(OSINTModule):
    """Extract EXIF/XMP/IPTC metadata and surface GPS or identity leakage."""

    name = "exiftool"
    scope_field = "image_dir"
    category = "image"
    passive = True
    description = "Metadata (EXIF/IPTC/XMP) review of client-supplied imagery."

    @property
    def binary(self) -> str:
        """Native executable name."""
        return "exiftool"

    def run(self, scope: Scope, workspace: Workspace) -> ModuleResult:
        """Execute ExifTool and return normalised image findings."""
        image_dir = self.target_value(scope)
        if not image_dir:
            return ModuleResult.skipped(self.name, "no image directory in scope")

        mode = self.execution_mode()
        blocked = self.unavailable(mode)
        if blocked:
            return blocked

        extensions: List[str] = [
            str(ext).lstrip(".") for ext in self.options.get("extensions", [".jpg", ".jpeg", ".png"])
        ]
        ext_args: List[str] = []
        for ext in extensions:
            ext_args += ["-ext", ext]

        tool_args = ["-json", "-n", "-a", "-G:0:1", "-charset", "filename=utf8", *ext_args]
        if self.options.get("recursive", True):
            tool_args.append("-r")

        if mode == "docker":
            command = self.docker_command(
                args=[*tool_args, "/images"],
                volumes={Path(image_dir): "/images:ro"},
            )
        else:
            command = ["exiftool", *tool_args, image_dir]

        self.log.info("exiftool reviewing %s (%s)", image_dir, mode)
        result = run_command(command, timeout=self.timeout)
        raw_files = self.save_raw(workspace, result)

        payload: Any = self.parse_json(result.stdout)
        if payload is None:
            status = "ok" if result.ok else "error"
            return ModuleResult(
                module=self.name,
                status=status,
                error=None if status == "ok" else (result.error or f"exit {result.returncode}"),
                note="no metadata records parsed" if status == "ok" else None,
                raw_files=raw_files,
                command=result.printable,
                execution=mode,
                duration=result.duration,
            )

        payload = _flatten_group_keys(payload)
        evidence_path = workspace.write_json(workspace.images / "exiftool_metadata.json", payload)
        evidence = workspace.relative(evidence_path)
        findings = from_exiftool(payload=payload, evidence_file=evidence)
        gps_hits = sum(1 for f in findings if f["risk_hint"] == "gps_metadata")
        return ModuleResult(
            module=self.name,
            status="ok",
            findings=findings,
            raw_files=raw_files + [evidence],
            command=result.printable,
            execution=mode,
            duration=result.duration,
            note=f"{len(findings)} file(s) reviewed, {gps_hits} with GPS",
        )


def _flatten_group_keys(payload: Any) -> Any:
    """Strip ExifTool ``Group:Tag`` prefixes so normalisation sees plain tags."""
    if not isinstance(payload, list):
        return payload
    flattened = []
    for record in payload:
        if not isinstance(record, dict):
            continue
        clean = {}
        for key, value in record.items():
            clean[key.split(":")[-1]] = value
        flattened.append(clean)
    return flattened
