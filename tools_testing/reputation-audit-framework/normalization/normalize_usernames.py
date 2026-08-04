"""Normalise username-enumeration output (Maigret, Blackbird) to findings."""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Sequence

from normalization.schema import dedupe, make_finding

CLAIMED_STATES = {"claimed", "found", "exists", "true", "yes"}
TOKEN_RE = re.compile(r"[^a-z0-9]+")


def tokenize(value: str) -> List[str]:
    """Split a handle into lowercase alphanumeric tokens."""
    return [t for t in TOKEN_RE.split(str(value).lower()) if t]


def classify_handle(handle: str, base_username: str, keywords: Sequence[str]) -> str:
    """Return a risk hint for a discovered handle.

    A handle that is not an exact match for the client's own username but does
    contain brand/impersonation keywords is flagged for analyst review.

    Args:
        handle: Discovered account handle.
        base_username: The client's authorised handle.
        keywords: Impersonation keyword fragments from config.

    Returns:
        ``impersonation_keyword`` or ``informational``.
    """
    normalized = str(handle).lower()
    if normalized == str(base_username).lower():
        return "informational"
    tokens = set(tokenize(normalized))
    for keyword in keywords:
        keyword = keyword.lower()
        if keyword in tokens or (len(keyword) > 4 and keyword in normalized):
            return "impersonation_keyword"
    return "informational"


def from_maigret(
    payload: Any,
    username: str,
    evidence_file: str,
    keywords: Sequence[str],
) -> List[Dict[str, Any]]:
    """Convert a Maigret JSON report into canonical username findings.

    Maigret emits ``{site_name: {"status": {"status": "Claimed"}, "url_user": ...}}``
    in its "simple"/"json" reports; NDJSON records are also accepted.
    """
    findings: List[Dict[str, Any]] = []
    for site, record in _iter_site_records(payload):
        if not isinstance(record, dict):
            continue
        status = record.get("status")
        state = ""
        if isinstance(status, dict):
            state = str(status.get("status", "")).lower()
        elif status is not None:
            state = str(status).lower()
        if state and state not in CLAIMED_STATES:
            continue
        url = record.get("url_user") or record.get("url") or record.get("url_main") or ""
        if not url and not state:
            continue
        handle = record.get("username") or username
        findings.append(
            make_finding(
                finding_type="username",
                source_tool="maigret",
                value=str(url or f"{site}:{handle}"),
                risk_hint=classify_handle(str(handle), username, keywords),
                evidence_file=evidence_file,
                details={
                    "site": site,
                    "handle": handle,
                    "status": state or "claimed",
                    "ownership": "unverified_handle_match",
                    "tags": record.get("tags", []),
                },
            )
        )
    return dedupe(findings)


def from_blackbird(
    payload: Any,
    username: str,
    evidence_file: str,
    keywords: Sequence[str],
) -> List[Dict[str, Any]]:
    """Convert Blackbird JSON results into canonical username findings.

    Blackbird writes ``{"username": ..., "found": [{"name":..., "url":...}]}``
    or a flat list of result objects depending on version.
    """
    findings: List[Dict[str, Any]] = []
    records: Iterable[Any]
    if isinstance(payload, dict):
        records = (
            payload.get("found")
            or payload.get("results")
            or payload.get("data")
            or payload.get("sites")
            or []
        )
    elif isinstance(payload, list):
        records = payload
    else:
        records = []

    for record in records:
        if not isinstance(record, dict):
            continue
        if str(record.get("status", "found")).lower() not in CLAIMED_STATES | {"200", "ok"}:
            continue
        url = record.get("url") or record.get("link") or ""
        site = record.get("name") or record.get("app") or record.get("site") or "unknown"
        handle = record.get("username") or username
        if not url:
            continue
        findings.append(
            make_finding(
                finding_type="username",
                source_tool="blackbird",
                value=str(url),
                risk_hint=classify_handle(str(handle), username, keywords),
                evidence_file=evidence_file,
                details={
                    "site": site,
                    "handle": handle,
                    "ownership": "unverified_handle_match",
                    "category": record.get("category", ""),
                    "response_status": record.get("response-status") or record.get("response_status"),
                    "metadata": record.get("metadata", []),
                },
            )
        )
    return dedupe(findings)


def from_social_analyzer(
    payload: Any,
    username: str,
    evidence_file: str,
    keywords: Iterable[str],
) -> List[Dict[str, Any]]:
    """Convert Social Analyzer's JSON ``detected`` list into account leads."""
    findings: List[Dict[str, Any]] = []
    if not isinstance(payload, dict):
        return findings
    for record in payload.get("detected") or []:
        if not isinstance(record, dict):
            continue
        url = str(record.get("link") or record.get("url") or "").strip()
        if not url.startswith(("http://", "https://")):
            continue
        handle = str(record.get("username") or username)
        findings.append(
            make_finding(
                finding_type="username",
                source_tool="social-analyzer",
                value=url,
                risk_hint=classify_handle(handle, username, list(keywords)),
                evidence_file=evidence_file,
                details={
                    "site": record.get("site") or record.get("title"),
                    "handle": handle,
                    "status": record.get("status"),
                    "rate": record.get("rate"),
                    "method": record.get("method"),
                    "metadata": record.get("metadata") or {},
                    "ownership": "unverified_handle_match",
                },
            )
        )
    return dedupe(findings)


def _iter_site_records(payload: Any) -> Iterable[tuple[str, Any]]:
    """Yield ``(site, record)`` pairs from the several Maigret report shapes."""
    if isinstance(payload, dict):
        container = payload.get("sites") if isinstance(payload.get("sites"), (dict, list)) else payload
        if isinstance(container, dict):
            for site, record in container.items():
                yield str(site), record
        elif isinstance(container, list):
            for record in container:
                if isinstance(record, dict):
                    yield str(record.get("site_name") or record.get("site") or "unknown"), record
    elif isinstance(payload, list):
        for record in payload:
            if isinstance(record, dict):
                site = record.get("site_name") or record.get("site") or record.get("name") or "unknown"
                yield str(site), record
