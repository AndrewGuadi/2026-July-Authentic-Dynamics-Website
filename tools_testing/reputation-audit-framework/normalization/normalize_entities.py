"""Normalize entity screening and modular OSINT records."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

from normalization.normalize_domains import HOSTNAME_RE, _hint_for_host
from normalization.schema import dedupe, make_finding


def from_yente(payload: Any, evidence_file: str, query_key: str = "subject") -> List[Dict[str, Any]]:
    """Convert a yente ``/match/{dataset}`` response into unverified candidates."""
    if not isinstance(payload, dict):
        return []
    responses = payload.get("responses")
    if not isinstance(responses, dict):
        return []
    response = responses.get(query_key)
    if not isinstance(response, dict):
        return []

    findings: List[Dict[str, Any]] = []
    for result in response.get("results") or []:
        if not isinstance(result, dict):
            continue
        entity_id = str(result.get("id") or "").strip()
        caption = str(result.get("caption") or entity_id).strip()
        if not entity_id:
            continue
        findings.append(
            make_finding(
                finding_type="screening",
                source_tool="yente",
                value=entity_id,
                risk_hint="screening_candidate",
                evidence_file=evidence_file,
                details={
                    "caption": caption,
                    "schema": result.get("schema"),
                    "score": result.get("score"),
                    "match": result.get("match"),
                    "datasets": result.get("datasets") or [],
                    "properties": result.get("properties") or {},
                    "explanations": result.get("explanations") or {},
                    "target": result.get("target"),
                    "review_state": "unreviewed",
                    "disposition": None,
                },
            )
        )
    return dedupe(findings)


def from_recon_ng(payload: Any, apex: str, evidence_file: str) -> List[Dict[str, Any]]:
    """Convert Recon-ng JSON report tables into canonical passive findings."""
    if not isinstance(payload, dict):
        return []
    findings: List[Dict[str, Any]] = []

    for row in _records(payload.get("hosts")):
        host = str(row.get("host") or "").strip().lower()
        if not host or not HOSTNAME_RE.match(host):
            continue
        if host != apex.lower() and not host.endswith(f".{apex.lower()}"):
            continue
        findings.append(
            make_finding(
                finding_type="domain",
                source_tool="recon-ng",
                value=host,
                risk_hint=_hint_for_host(host, apex),
                evidence_file=evidence_file,
                details={
                    "ip_address": row.get("ip_address"),
                    "module": row.get("module"),
                    "notes": row.get("notes"),
                    "mode": "allowlisted_passive_module",
                },
            )
        )

    for row in _records(payload.get("contacts")):
        email = str(row.get("email") or "").strip().lower()
        if not email:
            continue
        findings.append(
            make_finding(
                finding_type="entity",
                source_tool="recon-ng",
                value=email,
                risk_hint="informational",
                evidence_file=evidence_file,
                details={
                    "entity_type": "email",
                    "first_name": row.get("first_name") or row.get("fname"),
                    "last_name": row.get("last_name") or row.get("lname"),
                    "module": row.get("module"),
                },
            )
        )

    return dedupe(findings)


def _records(value: Any) -> Iterable[Dict[str, Any]]:
    """Yield dictionary rows from a Recon-ng report table."""
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]
