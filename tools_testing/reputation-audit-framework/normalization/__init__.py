"""Normalisation layer: tool-specific output -> one canonical finding schema."""

from normalization.schema import FINDING_TYPES, RISK_HINTS, dedupe, make_finding

__all__ = ["make_finding", "dedupe", "FINDING_TYPES", "RISK_HINTS"]
