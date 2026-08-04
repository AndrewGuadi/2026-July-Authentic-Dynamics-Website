"""Contract tests for the extended OSINT and analyst integrations."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

from core.config import AppConfig
from core.runner import CommandResult
from core.validator import Scope
from core.workspace import Workspace
from integrations.linkscope import GRAPHML_NS, LinkScopeExporter
from integrations.openaleph import OpenAlephExporter
from integrations.reverse_image import ReverseImageReview
from integrations.reviews import import_review_document
from modules.yente_module import YenteModule
from normalization.normalize_entities import from_recon_ng, from_yente
from normalization.normalize_usernames import from_social_analyzer


def scope(image_dir: str | None = None, image_count: int = 0) -> Scope:
    return Scope(
        full_name="Andrew Guasch",
        client_slug="andrew_guasch",
        domain="authenticdynamics.com",
        username="omyguasch",
        email="andrew@example.org",
        birth_date="1985",
        country="us",
        subject_type="person",
        image_dir=image_dir,
        image_count=image_count,
        engagement_id="RAF-INTEGRATION-TEST",
        authorized=True,
        authorized_at=datetime.now(timezone.utc).isoformat(),
        operator="tester",
        hostname="test-host",
        platform="test",
        targets=["authenticdynamics.com", "omyguasch"],
    )


class NormalizerContractTests(unittest.TestCase):
    def test_social_analyzer_detected_shape(self) -> None:
        payload = {
            "detected": [
                {"link": "https://example.social/omyguasch", "title": "Example", "rate": "%100", "status": "good"}
            ],
            "unknown": [{"link": "https://unknown.invalid/omyguasch"}],
        }
        findings = from_social_analyzer(payload, "omyguasch", "social.json", [])
        self.assertEqual(1, len(findings))
        self.assertEqual("social-analyzer", findings[0]["source_tool"])
        self.assertEqual("unverified_handle_match", findings[0]["details"]["ownership"])

    def test_yente_match_response_stays_unverified(self) -> None:
        payload = {
            "responses": {
                "subject": {
                    "results": [
                        {
                            "id": "Q-123",
                            "caption": "Andrew Guasch",
                            "schema": "Person",
                            "score": 0.88,
                            "match": True,
                            "datasets": ["example"],
                            "properties": {"name": ["Andrew Guasch"]},
                        }
                    ]
                }
            }
        }
        findings = from_yente(payload, "yente.json")
        self.assertEqual(1, len(findings))
        self.assertEqual("screening_candidate", findings[0]["risk_hint"])
        self.assertEqual("unreviewed", findings[0]["details"]["review_state"])

    def test_recon_ng_report_rejects_out_of_scope_hosts(self) -> None:
        payload = {
            "hosts": [
                {"host": "www.authenticdynamics.com", "module": "certificate_transparency"},
                {"host": "outside.example", "module": "certificate_transparency"},
            ],
            "contacts": [{"email": "public@authenticdynamics.com", "module": "certificate_transparency"}],
        }
        findings = from_recon_ng(payload, "authenticdynamics.com", "recon.json")
        self.assertEqual(
            {"www.authenticdynamics.com", "public@authenticdynamics.com"},
            {finding["value"] for finding in findings},
        )


class _YenteResponse:
    status = 200

    def __init__(self) -> None:
        self.payload = {
            "responses": {
                "subject": {
                    "results": [
                        {
                            "id": "ENTITY-1",
                            "caption": "Andrew Guasch",
                            "schema": "Person",
                            "score": 0.91,
                            "match": True,
                            "datasets": ["test"],
                            "properties": {"name": ["Andrew Guasch"]},
                        }
                    ]
                }
            },
            "limit": 5,
        }

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self) -> "_YenteResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class YenteHTTPContractTests(unittest.TestCase):
    def test_module_posts_official_match_query_shape(self) -> None:
        captured: dict = {}

        def fake_urlopen(request: object, timeout: int) -> _YenteResponse:
            captured["body"] = json.loads(getattr(request, "data").decode("utf-8"))
            captured["timeout"] = timeout
            return _YenteResponse()

        with patch("modules.yente_module.urlopen", side_effect=fake_urlopen):
            with tempfile.TemporaryDirectory() as temp_dir:
                workspace = Workspace.create(Path(temp_dir), "subject")
                config = AppConfig(
                    modules={"yente": True},
                    module_options={"yente": {"base_url": "http://yente.test", "dataset": "default"}},
                    timeouts={"yente": 5},
                )
                result = YenteModule(config).run(scope(), workspace)
        self.assertEqual("ok", result.status)
        self.assertEqual("Person", captured["body"]["queries"]["subject"]["schema"])
        self.assertEqual(["1985"], captured["body"]["queries"]["subject"]["properties"]["birthDate"])
        self.assertEqual(1, len(result.findings))


class AnalystIntegrationTests(unittest.TestCase):
    def test_linkscope_graphml_matches_database_import_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Workspace.create(Path(temp_dir), "subject")
            config = AppConfig(integrations={"linkscope": {"enabled": True}})
            findings = [
                {
                    "type": "domain",
                    "source_tool": "amass",
                    "value": "www.authenticdynamics.com",
                    "risk_hint": "informational",
                    "evidence_file": "domain/amass.txt",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "details": {},
                }
            ]
            result = LinkScopeExporter(config).run(scope(), workspace, findings)
            graph_path = workspace.root / "integrations" / "linkscope" / "reputation_audit.graphml"
            root = ET.parse(graph_path).getroot()
            nodes = root.findall(f".//{{{GRAPHML_NS}}}node")
            edges = root.findall(f".//{{{GRAPHML_NS}}}edge")
        self.assertEqual("ok", result.status)
        self.assertEqual(2, len(nodes))
        self.assertEqual(1, len(edges))

    def test_reverse_image_workflow_hashes_and_copies_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_dir = Path(temp_dir) / "images"
            image_dir.mkdir()
            (image_dir / "portrait.png").write_bytes(b"not-a-real-png-but-a-stable-test-fixture")
            workspace = Workspace.create(Path(temp_dir) / "output", "subject")
            config = AppConfig(integrations={"search_by_image": {"enabled": True}})
            result = ReverseImageReview(config).run(scope(str(image_dir), 1), workspace)
            tasks = json.loads((workspace.root / "manual_review" / "reverse_image" / "tasks.json").read_text())
        self.assertEqual("review_required", result.status)
        self.assertEqual(1, len(tasks["tasks"]))
        self.assertEqual(64, len(tasks["tasks"][0]["sha256"]))

    def test_openaleph_package_mode_is_deterministic_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Workspace.create(Path(temp_dir), "subject")
            config = AppConfig(integrations={"openaleph": {"enabled": True, "mode": "package"}})
            result = OpenAlephExporter(config).run(scope(), workspace)
            manifest = json.loads((workspace.root / "integrations" / "openaleph" / "manifest.json").read_text())
        self.assertEqual("ok", result.status)
        self.assertEqual("raf-raf_integration_test", manifest["foreign_id"])
        self.assertNotIn("api_key", json.dumps(manifest).lower())

    def test_openaleph_upload_forwards_secret_names_without_values(self) -> None:
        captured: dict = {}

        def fake_run(command: list[str], timeout: int) -> CommandResult:
            captured["command"] = list(command)
            captured["timeout"] = timeout
            return CommandResult(command=list(command), returncode=0, stdout="uploaded")

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Workspace.create(Path(temp_dir), "subject")
            config = AppConfig(
                integrations={
                    "openaleph": {
                        "enabled": True,
                        "mode": "upload",
                        "execution": "docker",
                        "image": "alephclient:test",
                        "timeout": 30,
                    }
                }
            )
            with patch.dict(
                os.environ,
                {"ALEPH_HOST": "https://aleph.test", "ALEPH_API_KEY": "top-secret-value"},
                clear=False,
            ), patch("integrations.openaleph.run_command", side_effect=fake_run):
                result = OpenAlephExporter(config).run(scope(), workspace)
        rendered = " ".join(captured["command"])
        self.assertEqual("ok", result.status)
        self.assertIn("--env ALEPH_HOST", rendered)
        self.assertIn("--env ALEPH_API_KEY", rendered)
        self.assertNotIn("top-secret-value", rendered)

    def test_reverse_image_decision_import_closes_review_and_rebuilds_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_dir = root / "images"
            image_dir.mkdir()
            (image_dir / "portrait.png").write_bytes(b"stable-review-fixture")
            workspace = Workspace.create(root / "output", "subject")
            subject = scope(str(image_dir), 1)
            config = AppConfig(
                integrations={"search_by_image": {"enabled": True}},
                reporting={"company": "Test", "analyst": "Tester"},
            )
            collection = ReverseImageReview(config).run(subject, workspace)
            workspace.write_json(
                workspace.root / "scope.json",
                {"scope": subject.to_dict(), "collection_started": subject.authorized_at},
            )
            workspace.write_findings("all_findings", collection.findings)
            workspace.write_json(
                workspace.report / "report.json",
                {"modules": [asdict(collection)], "findings": collection.findings},
            )
            workspace.write_json(
                workspace.root / "summary.json",
                {"status": "completed_with_review", "modules": [], "finding_counts": {}, "risk": {}},
            )
            tasks = json.loads(
                (workspace.root / "manual_review" / "reverse_image" / "tasks.json").read_text()
            )
            review_path = workspace.write_json(
                workspace.root / "review.json",
                {
                    "kind": "reverse_image",
                    "engagement_id": subject.engagement_id,
                    "reviewer": "Analyst One",
                    "reviews": [
                        {
                            "task_id": tasks["tasks"][0]["task_id"],
                            "status": "no_match",
                            "engines_checked": ["test-engine"],
                            "result_urls": [],
                            "notes": "No candidate retained.",
                        }
                    ],
                },
            )
            result = import_review_document(workspace.root, review_path, config)
            rebuilt = json.loads((workspace.normalized / "all_findings.json").read_text())
        self.assertEqual("completed", result["status"])
        self.assertFalse(any(item["risk_hint"] == "review_pending" for item in rebuilt["findings"]))
        self.assertTrue(any(item["source_tool"] == "search-by-image" for item in rebuilt["findings"]))


if __name__ == "__main__":
    unittest.main()
