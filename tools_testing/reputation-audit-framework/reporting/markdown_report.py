"""Markdown executive report builder."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Sequence

from core.config import AppConfig
from core.risk import RiskAssessment
from core.validator import Scope
from core.workspace import Workspace
from modules.base import ModuleResult

BAND_ICON = {"Low": "🟢", "Moderate": "🟡", "Elevated": "🟠", "High": "🔴"}

HINT_LABEL = {
    "impersonation_keyword": "Possible impersonation / look-alike handle",
    "gps_metadata": "GPS coordinates embedded in published imagery",
    "pii_metadata": "Personal or device identifiers in metadata",
    "subdomain_exposure": "Sensitive hostname exposed in passive datasets",
    "secret_exposure": "Credential or secret material detected",
    "screening_candidate": "Entity-screening candidate — analyst disposition required",
    "review_pending": "Manual review pending",
    "informational": "Informational — corroborating context",
}

REMEDIATION = {
    "impersonation_keyword": [
        "Submit impersonation reports on the affected platforms using the brand-owner flow.",
        "Register the look-alike handles you can claim defensively (name + realtor/homes variants).",
        "Publish an official 'where to find me' page listing verified profile URLs.",
    ],
    "gps_metadata": [
        "Strip EXIF/GPS from all listing photography before publication (`exiftool -all= -overwrite_original`).",
        "Enable metadata stripping in the CMS/media pipeline so it cannot be forgotten.",
        "Re-upload previously published imagery that still contains coordinates.",
    ],
    "pii_metadata": [
        "Remove author, owner and device serial tags from published assets.",
        "Use a studio/brand identity rather than a personal name in asset metadata.",
    ],
    "subdomain_exposure": [
        "Inventory every hostname returned and decommission or restrict non-production endpoints.",
        "Put staging/admin interfaces behind SSO or an IP allowlist.",
        "Add certificate-transparency monitoring for new hostnames on the apex domain.",
    ],
    "secret_exposure": [
        "Rotate the affected credential immediately and audit its usage logs.",
        "Purge the secret from the asset bundle and from any version-control history.",
        "Adopt a managed secret store; add pre-commit secret scanning.",
    ],
    "informational": [
        "Retain for the engagement record; no action required unless corroborated.",
    ],
}


class MarkdownReportBuilder:
    """Render the executive Markdown deliverable for one engagement."""

    def __init__(
        self,
        config: AppConfig,
        scope: Scope,
        workspace: Workspace,
        results: Sequence[ModuleResult],
        findings: Sequence[Dict[str, Any]],
        risk: RiskAssessment,
        started: datetime,
    ) -> None:
        """Capture everything the report needs; ``build`` does the rendering."""
        self.config = config
        self.scope = scope
        self.workspace = workspace
        self.results = list(results)
        self.findings = list(findings)
        self.risk = risk
        self.started = started
        self.reporting = config.reporting

    # -- public ----------------------------------------------------------
    def build(self) -> str:
        """Return the complete Markdown document."""
        sections: List[str] = [
            self._header(),
            self._scope_confirmation(),
            self._executive_summary(),
            self._risk_section(),
            self._findings_sections(),
            self._module_table(),
            self._remediation(),
            self._evidence_index(),
            self._appendix(),
        ]
        return "\n\n".join(s for s in sections if s).strip() + "\n"

    # -- sections --------------------------------------------------------
    def _header(self) -> str:
        icon = BAND_ICON.get(self.risk.band, "")
        failed = [r.module for r in self.results if r.status == "error"]
        skipped = [r.module for r in self.results if r.status == "skipped"]
        pending = [r.module for r in self.results if r.status == "review_required"]
        if failed:
            coverage = f"INCOMPLETE — failed collector(s): {', '.join(failed)}"
        elif skipped:
            coverage = f"PARTIAL — skipped collector(s): {', '.join(skipped)}"
        elif pending:
            coverage = f"COLLECTION COMPLETE — analyst review pending: {', '.join(pending)}"
        else:
            coverage = "COMPLETE — every enabled collector finished successfully"
        return (
            f"# Reputation Audit Report — {self.scope.full_name}\n\n"
            f"**Engagement ID:** `{self.scope.engagement_id}`  \n"
            f"**Prepared by:** {self.reporting.get('company', 'Security Practice')} "
            f"({self.reporting.get('analyst', 'Unassigned')})  \n"
            f"**Collection window:** {self.started.isoformat()} → "
            f"{datetime.now(timezone.utc).isoformat()}  \n"
            f"**Methodology:** Passive open-source reconnaissance only  \n"
            f"**Collection status:** **{coverage}**  \n"
            f"**Observed-indicator risk:** {icon} **{self.risk.band}** (score {self.risk.score})\n\n"
            "> This assessment used publicly available information only. No authentication\n"
            "> control, paywall or CAPTCHA was bypassed; no intrusive or brute-force testing\n"
            "> was performed against any system.\n\n"
            + (
                "> **Coverage warning:** One or more enabled collectors did not complete. The risk score\n"
                "> describes collected evidence only and must not be interpreted as a clean bill of health."
                if failed or skipped else ""
            )
        )

    def _scope_confirmation(self) -> str:
        rows = [
            ("Audit subject", self.scope.full_name),
            ("Domain in scope", self.scope.domain or "— not supplied —"),
            ("Handle in scope", self.scope.username or "— not supplied —"),
            ("Email in scope", self.scope.email or "— not supplied —"),
            ("Identity type", self.scope.subject_type),
            (
                "Identity attributes",
                ", ".join(filter(None, [self.scope.birth_date, self.scope.country])) or "— not supplied —",
            ),
            ("Image set", f"{self.scope.image_dir} ({self.scope.image_count} file(s))" if self.scope.image_dir else "— not supplied —"),
            ("Authorization attested", f"yes @ {self.scope.authorized_at}"),
            ("Operator", f"{self.scope.operator}@{self.scope.hostname}"),
            ("Platform", self.scope.platform),
        ]
        body = "\n".join(f"| {k} | {v} |" for k, v in rows)
        return "## 1. Scope confirmation\n\n| Item | Value |\n| --- | --- |\n" + body

    def _executive_summary(self) -> str:
        counts = self.risk.counts
        hint_counts = Counter(f.get("risk_hint", "informational") for f in self.findings)
        notable = [f"{HINT_LABEL.get(h, h)} ({n})" for h, n in hint_counts.most_common() if h != "informational"]
        bullet = "\n".join(f"- {item}" for item in notable) or "- No elevated-risk indicators were identified."
        failed = [r.module for r in self.results if r.status == "error"]
        skipped = [r.module for r in self.results if r.status == "skipped"]
        coverage_note = ""
        if failed or skipped:
            affected = ", ".join(failed + skipped)
            coverage_note = (
                f"\n\n**Coverage limitation:** `{affected}` did not provide a successful result. "
                "Zero findings from those modules means *not collected*, not *nothing found*."
            )
        return (
            "## 2. Executive summary\n\n"
            f"Passive collection produced **{counts['total']} normalised finding(s)** across "
            f"{counts.get('username', 0)} account-match, {counts.get('domain', 0)} infrastructure, "
            f"{counts.get('image', 0)} media, {counts.get('entity', 0)} entity, "
            f"{counts.get('screening', 0)} screening and {counts.get('manual_review', 0)} review "
            "observation(s).\n\n"
            "**Indicators requiring attention**\n\n"
            f"{bullet}\n\n"
            f"The heuristic engine scored the evidence actually collected **{self.risk.score}** which maps to the "
            f"**{self.risk.band}** band using the thresholds in `config.yaml` "
            f"(moderate ≥ {self.config.risk_thresholds['moderate']}, "
            f"elevated ≥ {self.config.risk_thresholds['elevated']}, "
            f"high ≥ {self.config.risk_thresholds['high']})."
            f"{coverage_note}"
        )

    def _risk_section(self) -> str:
        provisional = any(r.status in {"error", "skipped"} for r in self.results)
        pending = [r.module for r in self.results if r.status == "review_required"]
        qualifier = (
            "\n\n**Provisional result:** Collection coverage was incomplete; this score cannot rule out "
            "risk in sources that failed or were skipped."
            if provisional else ""
        )
        review_qualifier = (
            f"\n\n**Analyst review pending:** {', '.join(pending)} generated tasks that are not yet resolved."
            if pending else ""
        )
        if not self.risk.contributions:
            return (
                "## 3. Risk score\n\n"
                f"**Score:** {self.risk.score} — **{self.risk.band}**\n\n"
                "No scoring rule fired in the evidence collected. Account-handle matches remain unverified."
                f"{qualifier}{review_qualifier}"
            )
        rows = "\n".join(
            f"| `{c.rule}` | +{c.points} | {c.detail} | {', '.join(c.evidence[:3]) or '—'} |"
            for c in self.risk.contributions
        )
        return (
            "## 3. Risk score\n\n"
            f"**Score:** {self.risk.score} — {BAND_ICON.get(self.risk.band, '')} **{self.risk.band}**\n\n"
            "| Rule | Points | Rationale | Sample evidence |\n| --- | ---: | --- | --- |\n"
            f"{rows}{qualifier}{review_qualifier}"
        )

    def _findings_sections(self) -> str:
        titles = {
            "username": "4.1 Potential account matches (ownership unverified)",
            "domain": "4.2 Domain & infrastructure surface",
            "image": "4.3 Media & metadata surface",
            "entity": "4.4 Entity observations",
            "screening": "4.5 Screening candidates (identity unverified)",
            "relationship": "4.6 Evidence-backed relationships",
            "document": "4.7 Document references",
            "manual_review": "4.8 Pending and completed analyst reviews",
        }
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for finding in self.findings:
            grouped[str(finding.get("type"))].append(finding)

        blocks: List[str] = ["## 4. Findings by category"]
        for category in (
            "username", "domain", "image", "entity", "screening",
            "relationship", "document", "manual_review",
        ):
            items = grouped.get(category, [])
            blocks.append(f"### {titles[category]}\n")
            if category == "username":
                blocks.append(
                    "> A matching public handle is a lead, not proof that the audit subject owns the account. "
                    "Verify profile content and linked official properties before taking action."
                )
            if category == "screening":
                blocks.append(
                    "> A yente/OpenSanctions candidate is not a confirmed identity match or adverse finding. "
                    "Compare stronger attributes and record an analyst disposition."
                )
            if not items:
                blocks.append("_No findings recorded for this category._")
                continue
            ranked = sorted(items, key=lambda f: (f.get("risk_hint") == "informational", f.get("value", "")))
            head = ranked[:60]
            rows = "\n".join(
                f"| {i} | `{self._truncate(f.get('value',''))}` | {f.get('source_tool')} | "
                f"{HINT_LABEL.get(str(f.get('risk_hint')), f.get('risk_hint'))} | "
                f"`{f.get('evidence_file') or 'n/a'}` | {f.get('timestamp')} |"
                for i, f in enumerate(head, start=1)
            )
            blocks.append(
                "| # | Value | Source | Risk hint | Evidence | Collected |\n"
                "| ---: | --- | --- | --- | --- | --- |\n" + rows
            )
            if len(ranked) > len(head):
                blocks.append(
                    f"_{len(ranked) - len(head)} additional record(s) omitted for brevity — see "
                    f"`normalized/{category}s.json`._"
                )
        return "\n\n".join(blocks)

    def _module_table(self) -> str:
        rows = "\n".join(
            f"| {r.module} | {r.status} | {r.execution} | {len(r.findings)} | {r.duration:.1f}s | "
            f"{self._truncate(r.error or r.note or '—', 70)} |"
            for r in self.results
        )
        return (
            "## 5. Collection coverage\n\n"
            "| Module | Status | Execution | Findings | Duration | Note |\n"
            "| --- | --- | --- | ---: | ---: | --- |\n" + (rows or "| — | — | — | 0 | 0s | no modules ran |")
        )

    def _remediation(self) -> str:
        hints = [h for h in dict.fromkeys(f.get("risk_hint", "informational") for f in self.findings)]
        ordered = [h for h in ("secret_exposure", "gps_metadata", "impersonation_keyword", "subdomain_exposure", "pii_metadata") if h in hints]
        lines: List[str] = ["## 6. Remediation checklist\n"]
        incomplete = [r.module for r in self.results if r.status in {"error", "skipped"}]
        pending = [r.module for r in self.results if r.status == "review_required"]
        if incomplete:
            lines.append(
                f"- [ ] Resolve and rerun incomplete collector(s): {', '.join(incomplete)}."
            )
        if pending:
            lines.append(f"- [ ] Complete analyst review task(s): {', '.join(pending)}.")
        elif not ordered:
            lines.append(
                "- [ ] No scored technical remediation was identified; manually verify account matches and re-run quarterly."
            )
        for hint in ordered:
            lines.append(f"**{HINT_LABEL.get(hint, hint)}**\n")
            lines += [f"- [ ] {action}" for action in REMEDIATION.get(hint, [])]
            lines.append("")
        lines += [
            "",
            "**Standing hygiene**\n",
            "- [ ] Manually verify each potential profile in section 4.1; enable MFA on confirmed owned accounts.",
            "- [ ] Register brand-adjacent handles you do not yet control.",
            "- [ ] Schedule this passive audit on a recurring 90-day cadence.",
            "- [ ] Store this report and its evidence per your data-retention policy.",
        ]
        return "\n".join(lines)

    def _evidence_index(self) -> str:
        files: List[str] = []
        for result in self.results:
            files.extend(result.raw_files)
        unique = sorted(dict.fromkeys(files))
        listing = "\n".join(f"- `{path}`" for path in unique) or "- _no raw artefacts captured_"
        return (
            "## 7. Evidence index\n\n"
            f"All artefacts are stored under `{self.workspace.root.name}/`.\n\n"
            f"{listing}\n\n"
            "Normalised documents: `normalized/*.json`, including `all_findings.json` and `risk.json`.  \n"
            "Execution log: `logs/audit.log`."
        )

    def _appendix(self) -> str:
        modules = ", ".join(sorted(self.config.enabled_modules())) or "none"
        return (
            "## 8. Appendix — method & legal basis\n\n"
            f"- **Enabled modules:** {modules}\n"
            f"- **Configuration:** `{self.config.source_path}`\n"
            "- **Technique:** passive OSINT collection from public datasets, certificate transparency, "
            "public profile endpoints and client-supplied files.\n"
            "- **Excluded by design:** authentication bypass, CAPTCHA solving, paywall circumvention, "
            "credential testing, brute force, active/intrusive scanning.\n"
            "- **Data handling:** every artefact carries a UTC collection timestamp; the scope, operator "
            "identity and authorization attestation are recorded in `scope.json`.\n\n"
            "_Findings reflect publicly observable data at the time of collection and may change without notice._"
        )

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _truncate(value: Any, limit: int = 96) -> str:
        """Trim long values so tables stay readable."""
        text = str(value).replace("|", "\\|").replace("\n", " ")
        return text if len(text) <= limit else text[: limit - 1] + "…"


def summarise_hints(findings: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    """Count findings per risk hint (used by tests and dashboards)."""
    return dict(Counter(str(f.get("risk_hint", "informational")) for f in findings))
