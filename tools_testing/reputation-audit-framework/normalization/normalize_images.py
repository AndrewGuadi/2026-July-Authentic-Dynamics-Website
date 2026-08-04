"""Normalise image metadata (ExifTool) and asset secret scans (TruffleHog)."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

from normalization.schema import dedupe, make_finding

GPS_KEYS = (
    "GPSLatitude", "GPSLongitude", "GPSPosition", "GPSAltitude",
    "GPSCoordinates", "GPSLatitudeRef", "GPSLongitudeRef",
)
PII_KEYS = (
    "Artist", "Creator", "Author", "OwnerName", "CameraOwnerName", "SerialNumber",
    "InternalSerialNumber", "LensSerialNumber", "By-line", "Copyright", "UserComment",
    "HostComputer", "XPAuthor",
)
CONTEXT_KEYS = (
    "Make", "Model", "Software", "CreateDate", "DateTimeOriginal", "ModifyDate",
    "FileSize", "MIMEType", "ImageSize",
)


def from_exiftool(payload: Any, evidence_file: str) -> List[Dict[str, Any]]:
    """Convert ExifTool ``-j`` output into canonical image findings.

    One finding per file. GPS presence outranks PII, which outranks a plain
    informational record.
    """
    findings: List[Dict[str, Any]] = []
    for record in _iter(payload):
        if not isinstance(record, dict):
            continue
        source = str(record.get("SourceFile") or record.get("FileName") or "unknown")
        gps = {k: record[k] for k in GPS_KEYS if k in record and record[k] not in ("", None)}
        pii = {k: record[k] for k in PII_KEYS if k in record and record[k] not in ("", None)}
        context = {k: record[k] for k in CONTEXT_KEYS if k in record}

        if gps:
            hint = "gps_metadata"
        elif pii:
            hint = "pii_metadata"
        else:
            hint = "informational"

        findings.append(
            make_finding(
                finding_type="image",
                source_tool="exiftool",
                value=source,
                risk_hint=hint,
                evidence_file=evidence_file,
                details={
                    "gps": gps,
                    "identifiers": pii,
                    "context": context,
                    "tag_count": len(record),
                },
            )
        )
    return dedupe(findings)


def from_trufflehog(payload: Any, evidence_file: str) -> List[Dict[str, Any]]:
    """Convert TruffleHog filesystem JSON output into image/asset findings.

    Only local, client-supplied assets are scanned; the raw secret value is
    never written to the report — a redacted fingerprint is stored instead.
    """
    findings: List[Dict[str, Any]] = []
    for record in _iter(payload):
        if not isinstance(record, dict):
            continue
        detector = str(record.get("DetectorName") or record.get("detector_name") or "unknown")
        metadata = record.get("SourceMetadata") or {}
        location = ""
        if isinstance(metadata, dict):
            data = metadata.get("Data") or {}
            filesystem = data.get("Filesystem") if isinstance(data, dict) else None
            if isinstance(filesystem, dict):
                location = str(filesystem.get("file", ""))
        raw = str(record.get("Raw") or record.get("RawV2") or "")
        findings.append(
            make_finding(
                finding_type="image",
                source_tool="trufflehog",
                value=location or f"{detector}-match",
                risk_hint="secret_exposure",
                evidence_file=evidence_file,
                details={
                    "detector": detector,
                    "verified": bool(record.get("Verified", False)),
                    "redacted_fingerprint": _fingerprint(raw),
                },
            )
        )
    return dedupe(findings)


def _fingerprint(raw: str) -> str:
    """Return a non-reversible, human-checkable stub of a secret."""
    if not raw:
        return "n/a"
    if len(raw) <= 8:
        return f"{raw[0]}***{raw[-1]} (len {len(raw)})"
    return f"{raw[:4]}…{raw[-4:]} (len {len(raw)})"


def _iter(payload: Any) -> Iterable[Any]:
    """Yield records from list / single-object / wrapped payloads."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("results", "findings", "data"):
            if isinstance(payload.get(key), list):
                return payload[key]
        return [payload]
    return []
