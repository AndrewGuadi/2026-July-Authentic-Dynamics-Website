"""Canonical finding schema shared by every module.

Every collector, regardless of tool, emits records shaped like::

    {
      "type": "username" | "domain" | "image" | "entity" |
              "relationship" | "screening" | "document" | "manual_review",
      "source_tool": "maigret",
      "value": "https://example.tld/handle",
      "risk_hint": "impersonation_keyword",
      "evidence_file": "usernames/maigret.stdout.txt",
      "timestamp": "2026-02-14T09:31:07+00:00"
    }

``details`` is an optional, additive field carrying tool-specific context; it is
ignored by the risk engine and rendered only in the appendix.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

FINDING_TYPES = (
    "username",
    "domain",
    "image",
    "entity",
    "relationship",
    "screening",
    "document",
    "manual_review",
)

RISK_HINTS = (
    "informational",
    "impersonation_keyword",
    "gps_metadata",
    "pii_metadata",
    "subdomain_exposure",
    "secret_exposure",
    "screening_candidate",
    "review_pending",
)


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp for collection provenance."""
    return datetime.now(timezone.utc).isoformat()


def make_finding(
    finding_type: str,
    source_tool: str,
    value: str,
    risk_hint: str = "informational",
    evidence_file: str = "",
    timestamp: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a validated finding dictionary.

    Args:
        finding_type: One of :data:`FINDING_TYPES`.
        source_tool: Collector that produced the observation.
        value: The observed artefact (URL, hostname, file path).
        risk_hint: One of :data:`RISK_HINTS`.
        evidence_file: Workspace-relative path to the raw evidence.
        timestamp: Override the collection timestamp.
        details: Optional tool-specific context.

    Returns:
        A canonical finding dictionary.

    Raises:
        ValueError: If the type or risk hint is outside the allowed vocabulary.
    """
    if finding_type not in FINDING_TYPES:
        raise ValueError(f"unknown finding type '{finding_type}' (expected {FINDING_TYPES})")
    if risk_hint not in RISK_HINTS:
        raise ValueError(f"unknown risk hint '{risk_hint}' (expected {RISK_HINTS})")
    return {
        "type": finding_type,
        "source_tool": source_tool,
        "value": str(value),
        "risk_hint": risk_hint,
        "evidence_file": evidence_file,
        "timestamp": timestamp or utc_now(),
        "details": details or {},
    }


def dedupe(findings: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate (type, source_tool, value) tuples, preserving order."""
    seen: set[tuple[str, str, str]] = set()
    unique: List[Dict[str, Any]] = []
    for finding in findings:
        key = (
            str(finding.get("type")),
            str(finding.get("source_tool")),
            str(finding.get("value")).lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique
