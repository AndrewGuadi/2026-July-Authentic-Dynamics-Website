"""Deterministic risk heuristic engine.

Scoring rules (weights and thresholds are config-driven)::

    impersonation keyword in a discovered handle   +2 (capped)
    image metadata containing GPS coordinates      +3
    more than N exposed subdomains (default 10)    +2
    secret / credential material found             +4
    residual PII in metadata (author, serial)      +1

Bands: Low < moderate <= Moderate < elevated <= Elevated < high <= High
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List

from core.config import AppConfig
from normalization.schema import FINDING_TYPES

BANDS = ("Low", "Moderate", "Elevated", "High")


@dataclass(slots=True)
class RiskContribution:
    """A single scored rule hit."""

    rule: str
    points: int
    detail: str
    evidence: List[str] = field(default_factory=list)


@dataclass(slots=True)
class RiskAssessment:
    """Aggregate risk outcome for an engagement."""

    score: int
    band: str
    contributions: List[RiskContribution]
    counts: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        """Serialise for ``normalized/risk.json`` and the report."""
        return {
            "score": self.score,
            "band": self.band,
            "counts": self.counts,
            "contributions": [asdict(c) for c in self.contributions],
        }


class RiskEngine:
    """Convert normalised findings into a score and a qualitative band."""

    def __init__(self, config: AppConfig) -> None:
        """Bind the engine to config-supplied weights, thresholds and rules."""
        self.weights = config.risk_weights
        self.thresholds = config.risk_thresholds
        self.rules = config.risk_rules
        self.subdomain_threshold = int(self.rules.get("subdomain_exposure_threshold", 10))
        self.max_impersonation = int(self.rules.get("max_impersonation_points", 6))

    # -- public ----------------------------------------------------------
    def assess(self, findings: Iterable[Dict[str, Any]]) -> RiskAssessment:
        """Score a collection of normalised findings.

        Args:
            findings: Normalised finding dictionaries.

        Returns:
            A :class:`RiskAssessment` with score, band and per-rule breakdown.
        """
        items = list(findings)
        counts = {"total": len(items)}
        counts.update(
            {name: sum(1 for f in items if f.get("type") == name) for name in FINDING_TYPES}
        )
        contributions: List[RiskContribution] = []
        contributions += self._score_impersonation(items)
        contributions += self._score_gps(items)
        contributions += self._score_subdomains(items)
        contributions += self._score_secrets(items)
        contributions += self._score_pii(items)

        score = sum(c.points for c in contributions)
        return RiskAssessment(score=score, band=self.band_for(score), contributions=contributions, counts=counts)

    def band_for(self, score: int) -> str:
        """Map a numeric score onto a qualitative band."""
        if score >= self.thresholds["high"]:
            return "High"
        if score >= self.thresholds["elevated"]:
            return "Elevated"
        if score >= self.thresholds["moderate"]:
            return "Moderate"
        return "Low"

    # -- rules -----------------------------------------------------------
    def _score_impersonation(self, items: List[Dict[str, Any]]) -> List[RiskContribution]:
        hits = [f for f in items if f.get("risk_hint") == "impersonation_keyword"]
        if not hits:
            return []
        unit = int(self.weights.get("impersonation_keyword", 2))
        points = min(unit * len(hits), self.max_impersonation)
        return [
            RiskContribution(
                rule="impersonation_keyword",
                points=points,
                detail=(
                    f"{len(hits)} discovered handle(s) contain brand/impersonation keywords "
                    f"({unit} pts each, capped at {self.max_impersonation})"
                ),
                evidence=[str(f.get("value")) for f in hits][:10],
            )
        ]

    def _score_gps(self, items: List[Dict[str, Any]]) -> List[RiskContribution]:
        hits = [f for f in items if f.get("risk_hint") == "gps_metadata"]
        if not hits:
            return []
        return [
            RiskContribution(
                rule="gps_metadata",
                points=int(self.weights.get("gps_metadata", 3)),
                detail=f"{len(hits)} published image(s) retain GPS coordinates in EXIF",
                evidence=[str(f.get("value")) for f in hits][:10],
            )
        ]

    def _score_subdomains(self, items: List[Dict[str, Any]]) -> List[RiskContribution]:
        subdomains = {
            str(f.get("value")).lower()
            for f in items
            if f.get("type") == "domain" and f.get("risk_hint") in {"subdomain_exposure", "informational"}
        }
        if len(subdomains) <= self.subdomain_threshold:
            return []
        return [
            RiskContribution(
                rule="subdomain_exposure",
                points=int(self.weights.get("subdomain_exposure", 2)),
                detail=(
                    f"{len(subdomains)} unique hostnames exposed in passive sources "
                    f"(threshold {self.subdomain_threshold})"
                ),
                evidence=sorted(subdomains)[:10],
            )
        ]

    def _score_secrets(self, items: List[Dict[str, Any]]) -> List[RiskContribution]:
        hits = [f for f in items if f.get("risk_hint") == "secret_exposure"]
        if not hits:
            return []
        return [
            RiskContribution(
                rule="secret_exposure",
                points=int(self.weights.get("secret_exposure", 4)),
                detail=f"{len(hits)} candidate secret(s)/credential artefact(s) identified",
                evidence=[str(f.get("value")) for f in hits][:10],
            )
        ]

    def _score_pii(self, items: List[Dict[str, Any]]) -> List[RiskContribution]:
        hits = [f for f in items if f.get("risk_hint") == "pii_metadata"]
        if not hits:
            return []
        return [
            RiskContribution(
                rule="pii_metadata",
                points=int(self.weights.get("pii_metadata", 1)),
                detail=f"{len(hits)} artefact(s) leak author/device identifiers",
                evidence=[str(f.get("value")) for f in hits][:10],
            )
        ]
