"""Typed configuration loading for reputation-audit-framework."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml

DEFAULT_THRESHOLDS: Dict[str, int] = {"high": 8, "elevated": 5, "moderate": 3}
DEFAULT_WEIGHTS: Dict[str, int] = {
    "impersonation_keyword": 2,
    "gps_metadata": 3,
    "subdomain_exposure": 2,
    "secret_exposure": 4,
    "pii_metadata": 1,
}
VALID_EXECUTION = {"native", "docker", "auto"}


@dataclass(slots=True)
class AppConfig:
    """In-memory representation of ``config.yaml``."""

    output_root: str = "./output"
    modules: Dict[str, bool] = field(default_factory=dict)
    default_execution: str = "auto"
    execution: Dict[str, str] = field(default_factory=dict)
    docker_images: Dict[str, str] = field(default_factory=dict)
    timeouts: Dict[str, int] = field(default_factory=dict)
    module_options: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    integrations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    risk_thresholds: Dict[str, int] = field(default_factory=lambda: dict(DEFAULT_THRESHOLDS))
    risk_weights: Dict[str, int] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    risk_rules: Dict[str, Any] = field(default_factory=dict)
    reporting: Dict[str, Any] = field(default_factory=dict)
    logging: Dict[str, Any] = field(default_factory=dict)
    source_path: Path = Path("config.yaml")

    # -- helpers ---------------------------------------------------------
    def enabled_modules(self) -> List[str]:
        """Return the names of modules switched on in config."""
        return [name for name, on in self.modules.items() if on]

    def timeout_for(self, module: str) -> int:
        """Wall-clock timeout in seconds for ``module`` (default 600)."""
        return int(self.timeouts.get(module, 600))

    def options_for(self, module: str) -> Dict[str, Any]:
        """Return the ``module_options`` block for ``module``."""
        return dict(self.module_options.get(module) or {})

    def integration_options(self, integration: str) -> Dict[str, Any]:
        """Return the configuration block for a post-collection integration."""
        return dict(self.integrations.get(integration) or {})

    def integration_enabled(self, integration: str) -> bool:
        """Return whether a post-collection integration is enabled."""
        return bool(self.integration_options(integration).get("enabled", False))

    def execution_for(self, module: str) -> str:
        """Return native/docker/auto execution preference for ``module``."""
        return str(self.execution.get(module, self.default_execution))

    def image_for(self, module: str) -> str:
        """Return the container image configured for ``module``."""
        return str(self.docker_images.get(module, ""))

    def impersonation_keywords(self) -> List[str]:
        """Keyword fragments that hint at look-alike / impersonation handles."""
        return [str(k).lower() for k in self.risk_rules.get("impersonation_keywords", [])]


def load_config(path: Path) -> AppConfig:
    """Load and validate a YAML config file.

    Args:
        path: Path to ``config.yaml``.

    Returns:
        A populated :class:`AppConfig`.

    Raises:
        FileNotFoundError: If the config file is missing.
        ValueError: If the document is malformed or contains invalid values.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"configuration file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("config.yaml must contain a YAML mapping at the top level")

    config = AppConfig(
        output_root=str(data.get("output_root", "./output")),
        modules={str(k): bool(v) for k, v in (data.get("modules") or {}).items()},
        default_execution=str(data.get("default_execution", "auto")),
        execution={str(k): str(v) for k, v in (data.get("execution") or {}).items()},
        docker_images={str(k): str(v) for k, v in (data.get("docker_images") or {}).items()},
        timeouts={str(k): int(v) for k, v in (data.get("timeouts") or {}).items()},
        module_options=dict(data.get("module_options") or {}),
        integrations={
            str(k): dict(v or {}) for k, v in (data.get("integrations") or {}).items()
        },
        risk_thresholds={**DEFAULT_THRESHOLDS, **(data.get("risk_thresholds") or {})},
        risk_weights={**DEFAULT_WEIGHTS, **(data.get("risk_weights") or {})},
        risk_rules=dict(data.get("risk_rules") or {}),
        reporting=dict(data.get("reporting") or {}),
        logging=dict(data.get("logging") or {}),
        source_path=path,
    )

    bad = {m: e for m, e in config.execution.items() if e not in VALID_EXECUTION}
    if bad:
        raise ValueError(f"invalid execution modes {bad}; expected one of {sorted(VALID_EXECUTION)}")
    if config.default_execution not in VALID_EXECUTION:
        raise ValueError(f"invalid default_execution '{config.default_execution}'")

    thresholds = config.risk_thresholds
    if not thresholds["moderate"] < thresholds["elevated"] < thresholds["high"]:
        raise ValueError("risk_thresholds must satisfy moderate < elevated < high")

    return config
