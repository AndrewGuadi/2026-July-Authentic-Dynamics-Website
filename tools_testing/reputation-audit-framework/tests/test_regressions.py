"""Regression tests for collector compatibility and honest coverage reporting."""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.risk import RiskAssessment
from core.runner import docker_available, docker_host_path
from modules.amass_module import AmassModule
from modules.base import ModuleResult
from normalization.normalize_domains import from_amass
from normalization.normalize_usernames import from_blackbird
from reporting.markdown_report import MarkdownReportBuilder


class BlackbirdNormalizationTests(unittest.TestCase):
    def test_published_v1_sites_shape_keeps_only_found_records(self) -> None:
        payload = {
            "search-params": {"username": "omyguasch"},
            "sites": [
                {"app": "Pinterest", "status": "FOUND", "url": "https://pinterest.com/omyguasch/"},
                {"app": "GitHub", "status": "NOT FOUND", "url": "https://github.com/omyguasch"},
            ],
        }

        findings = from_blackbird(payload, "omyguasch", "blackbird.json", [])

        self.assertEqual(1, len(findings))
        self.assertEqual("https://pinterest.com/omyguasch/", findings[0]["value"])
        self.assertEqual("unverified_handle_match", findings[0]["details"]["ownership"])


class DockerVolumeTranslationTests(unittest.TestCase):
    def test_container_output_path_is_translated_for_sibling_container(self) -> None:
        with patch.dict(
            os.environ,
            {
                "RAF_CONTAINER_OUTPUT_ROOT": "/app/output",
                "RAF_HOST_OUTPUT_ROOT": "/workspace/framework/output",
            },
            clear=False,
        ):
            translated = docker_host_path(Path("/app/output/client/domain/raw"))

        self.assertEqual(Path("/workspace/framework/output/client/domain/raw"), translated)


class DockerReadinessTests(unittest.TestCase):
    def test_daemon_probe_executes_docker_info(self) -> None:
        docker_available.cache_clear()
        with patch("core.runner.binary_available", return_value=True), patch(
            "core.runner.subprocess.run", return_value=SimpleNamespace(returncode=0)
        ) as run:
            self.assertTrue(docker_available())
        docker_available.cache_clear()
        self.assertEqual(["docker", "info", "--format", "{{.ServerVersion}}"], run.call_args.args[0])


class AmassV4NormalizationTests(unittest.TestCase):
    def test_graph_output_extracts_only_in_scope_fqdns(self) -> None:
        graph = (
            "andrewguasch.com (FQDN) --> ns_record --> ns58.domaincontrol.com (FQDN)\n"
            "www.andrewguasch.com (FQDN) --> a_record --> 192.0.2.1 (IPAddress)\n"
        )
        records = AmassModule._hostname_lines(graph)
        findings = from_amass(records, "andrewguasch.com", "amass.txt")

        self.assertEqual(
            ["andrewguasch.com", "www.andrewguasch.com"],
            [finding["value"] for finding in findings],
        )

    def test_internal_deadline_leaves_cleanup_grace(self) -> None:
        self.assertEqual(3, AmassModule._internal_timeout_minutes(240))
        self.assertLess(AmassModule._internal_timeout_minutes(900) * 60, 900)


class CoverageReportTests(unittest.TestCase):
    def test_failed_collector_never_yields_clean_bill_of_health(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = MarkdownReportBuilder(
                config=SimpleNamespace(
                    reporting={"company": "Authentic Dynamics", "analyst": "Andrew Guasch"},
                    risk_thresholds={"moderate": 3, "elevated": 5, "high": 8},
                ),
                scope=SimpleNamespace(full_name="Andrew Guasch", engagement_id="RAF-TEST"),
                workspace=SimpleNamespace(root=Path(temp_dir)),
                results=[ModuleResult.failed("amass", "exit 1")],
                findings=[],
                risk=RiskAssessment(
                    score=0,
                    band="Low",
                    contributions=[],
                    counts={"total": 0, "username": 0, "domain": 0, "image": 0},
                ),
                started=datetime.now(timezone.utc),
            )

            header = builder._header()
            remediation = builder._remediation()

        self.assertIn("INCOMPLETE", header)
        self.assertIn("must not be interpreted as a clean bill of health", header)
        self.assertNotIn("No remediation required", remediation)
        self.assertIn("Resolve and rerun incomplete collector", remediation)


if __name__ == "__main__":
    unittest.main()
