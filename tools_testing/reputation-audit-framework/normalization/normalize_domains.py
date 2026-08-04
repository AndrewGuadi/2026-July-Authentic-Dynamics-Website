"""Normalise passive domain/infrastructure output to canonical findings."""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

from normalization.schema import dedupe, make_finding

HOSTNAME_RE = re.compile(r"^(?=.{4,253}$)(?:[A-Za-z0-9_](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$")

SENSITIVE_PREFIXES = (
    "dev", "test", "stage", "staging", "uat", "qa", "admin", "portal", "vpn",
    "mail", "webmail", "cpanel", "backup", "old", "legacy", "internal", "intranet",
    "git", "jenkins", "jira", "db", "sql", "ftp", "api",
)

SECRET_EVENT_TYPES = {
    "LEAKSITE_CONTENT", "PASSWORD_COMPROMISED", "ACCOUNT_EXTERNAL_OWNED_COMPROMISED",
    "CREDENTIALS_COMPROMISED", "EMAILADDR_COMPROMISED",
}


def _hint_for_host(host: str, apex: str) -> str:
    """Flag interesting subdomains; everything else is informational."""
    if host.lower() == apex.lower():
        return "informational"
    label = host.lower().split(".")[0]
    return "subdomain_exposure" if label.startswith(SENSITIVE_PREFIXES) else "informational"


def from_amass(payload: Any, apex: str, evidence_file: str) -> List[Dict[str, Any]]:
    """Convert Amass passive JSON/NDJSON output into domain findings."""
    findings: List[Dict[str, Any]] = []
    for record in _iter_records(payload):
        if isinstance(record, str):
            host, sources, addresses = record.strip(), [], []
        elif isinstance(record, dict):
            host = str(record.get("name") or record.get("domain") or "").strip()
            sources = [str(s.get("source", s)) for s in record.get("sources", [])] if record.get("sources") else []
            addresses = [
                str(a.get("ip")) for a in record.get("addresses", []) if isinstance(a, dict) and a.get("ip")
            ]
        else:
            continue
        if not host or not HOSTNAME_RE.match(host):
            continue
        if host.lower() != apex.lower() and not host.lower().endswith(f".{apex.lower()}"):
            continue
        findings.append(
            make_finding(
                finding_type="domain",
                source_tool="amass",
                value=host.lower(),
                risk_hint=_hint_for_host(host, apex),
                evidence_file=evidence_file,
                details={"sources": sources, "addresses": addresses, "mode": "passive"},
            )
        )
    return dedupe(findings)


def from_spiderfoot(payload: Any, apex: str, evidence_file: str) -> List[Dict[str, Any]]:
    """Convert SpiderFoot passive event output into domain findings.

    Accepts both the JSON array export and the CSV-ish row export shape
    ``[generated, data, module, type]``.
    """
    findings: List[Dict[str, Any]] = []
    for record in _iter_records(payload):
        event_type, data, module = "", "", ""
        if isinstance(record, dict):
            event_type = str(record.get("type") or record.get("event_type") or "")
            data = str(record.get("data") or record.get("value") or "")
            module = str(record.get("module") or record.get("source_module") or "spiderfoot")
        elif isinstance(record, (list, tuple)) and len(record) >= 4:
            data, module, event_type = str(record[1]), str(record[2]), str(record[3])
        if not data:
            continue

        upper = re.sub(r"[^A-Z0-9]+", "_", event_type.upper()).strip("_")
        if upper in SECRET_EVENT_TYPES:
            hint = "secret_exposure"
        elif "INTERNET_NAME" in upper or "SUBDOMAIN" in upper or "CO_HOSTED" in upper:
            hint = _hint_for_host(data, apex)
        elif "EMAILADDR" in upper or "HUMAN_NAME" in upper or "PHONE_NUMBER" in upper:
            hint = "pii_metadata"
        else:
            hint = "informational"

        findings.append(
            make_finding(
                finding_type="domain",
                source_tool="spiderfoot",
                value=data.lower() if HOSTNAME_RE.match(data) else data,
                risk_hint=hint,
                evidence_file=evidence_file,
                details={"event_type": event_type, "module": module},
            )
        )
    return dedupe(findings)


def from_theharvester(payload: Any, apex: str, evidence_file: str) -> List[Dict[str, Any]]:
    """Convert theHarvester passive JSON output into domain findings."""
    findings: List[Dict[str, Any]] = []
    if not isinstance(payload, dict):
        return findings
    for host in payload.get("hosts", []) or []:
        name = str(host).split(":")[0].strip().lower()
        if not HOSTNAME_RE.match(name):
            continue
        findings.append(
            make_finding(
                finding_type="domain",
                source_tool="theharvester",
                value=name,
                risk_hint=_hint_for_host(name, apex),
                evidence_file=evidence_file,
                details={"record": str(host)},
            )
        )
    for email in payload.get("emails", []) or []:
        findings.append(
            make_finding(
                finding_type="domain",
                source_tool="theharvester",
                value=str(email).strip().lower(),
                risk_hint="pii_metadata",
                evidence_file=evidence_file,
                details={"artefact": "email"},
            )
        )
    return dedupe(findings)


def _iter_records(payload: Any) -> Iterable[Any]:
    """Yield records from list / dict / NDJSON-parsed payloads."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("results", "events", "data", "findings"):
            if isinstance(payload.get(key), list):
                return payload[key]
        return [payload]
    return []
