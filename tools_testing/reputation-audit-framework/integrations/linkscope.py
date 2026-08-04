"""Generate a LinkScope-native GraphML database from normalized findings."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple
from xml.etree import ElementTree as ET

from core.config import AppConfig
from core.validator import Scope
from core.workspace import Workspace
from modules.base import ModuleResult

GRAPHML_NS = "http://graphml.graphdrawing.org/xmlns"
ET.register_namespace("", GRAPHML_NS)

NODE_FIELDS = (
    "uid", "Entity Type", "Full Name", "URL", "Domain Name", "Image Name",
    "File Path", "Phrase", "Notes", "Date Created", "Date Last Edited",
)
EDGE_FIELDS = ("uid", "Resolution", "Notes", "Date Created", "Date Last Edited")


class LinkScopeExporter:
    """Export findings in the exact GraphML database format LinkScope imports."""

    name = "linkscope"

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.options = config.integration_options(self.name)

    def run(
        self,
        scope: Scope,
        workspace: Workspace,
        findings: Iterable[Dict[str, Any]],
    ) -> ModuleResult:
        started = datetime.now(timezone.utc)
        directory = workspace.integrations / "linkscope"
        directory.mkdir(parents=True, exist_ok=True)
        graphml = self._build_graph(scope, list(findings), started.isoformat())
        graph_path = workspace.write_text(directory / "reputation_audit.graphml", graphml)
        node_map_path = workspace.write_json(
            directory / "node_map.json",
            {
                "engagement_id": scope.engagement_id,
                "nodes": [
                    {
                        "node_id": _stable_id(
                            str(finding.get("source_tool", "unknown")),
                            str(finding.get("type", "unknown")),
                            str(finding.get("value", "")),
                        ),
                        "type": finding.get("type"),
                        "source_tool": finding.get("source_tool"),
                        "value": finding.get("value"),
                        "evidence_file": finding.get("evidence_file"),
                    }
                    for finding in findings
                ],
            },
        )
        instructions = workspace.write_text(
            directory / "IMPORT.md",
            "# Import into LinkScope\n\n"
            "1. Open the authorized LinkScope project.\n"
            "2. Choose **Import → From GraphML – Database**.\n"
            "3. Select `reputation_audit.graphml`.\n"
            "4. Create a canvas and add the imported subject/findings for review.\n"
            "5. Record conclusions in `review_decisions.template.json`; do not edit raw evidence.\n",
        )
        decisions = workspace.write_json(
            directory / "review_decisions.template.json",
            {
                "kind": "linkscope",
                "engagement_id": scope.engagement_id,
                "reviewer": "",
                "reviewed_at": None,
                "decisions": [],
                "decision_shape": {
                    "finding_id": "GraphML node uid",
                    "status": "confirmed|rejected|inconclusive",
                    "rationale": "analyst rationale",
                    "evidence_urls": [],
                },
            },
        )
        paths = [workspace.relative(path) for path in (graph_path, node_map_path, instructions, decisions)]
        return ModuleResult(
            module=self.name,
            status="ok",
            raw_files=paths,
            command="GraphML database export",
            execution="exporter",
            duration=round((datetime.now(timezone.utc) - started).total_seconds(), 2),
            note=f"LinkScope GraphML generated with {graphml.count('<node ')} node(s)",
        )

    def _build_graph(self, scope: Scope, findings: list[Dict[str, Any]], timestamp: str) -> str:
        root = ET.Element(_tag("graphml"))
        node_keys = _add_keys(root, "node", NODE_FIELDS, "n")
        edge_keys = _add_keys(root, "edge", EDGE_FIELDS, "e")
        graph = ET.SubElement(root, _tag("graph"), {"id": scope.engagement_id, "edgedefault": "directed"})

        subject_id = _stable_id("subject", scope.engagement_id, scope.full_name)
        _add_node(
            graph,
            subject_id,
            {
                "uid": subject_id,
                "Entity Type": "Person" if scope.subject_type == "person" else "Phrase",
                "Full Name": scope.full_name if scope.subject_type == "person" else "",
                "Phrase": scope.full_name if scope.subject_type != "person" else "",
                "Notes": f"Authorized audit subject; engagement {scope.engagement_id}",
                "Date Created": timestamp,
                "Date Last Edited": timestamp,
            },
            node_keys,
        )

        for finding in findings:
            node_id = _stable_id(
                str(finding.get("source_tool", "unknown")),
                str(finding.get("type", "unknown")),
                str(finding.get("value", "")),
            )
            attrs = _finding_node(finding, node_id, timestamp)
            _add_node(graph, node_id, attrs, node_keys)
            edge_attrs = {
                "uid": repr((subject_id, node_id)),
                "Resolution": f"Observed by {finding.get('source_tool', 'unknown')}",
                "Notes": f"Evidence: {finding.get('evidence_file') or 'n/a'}",
                "Date Created": str(finding.get("timestamp") or timestamp),
                "Date Last Edited": timestamp,
            }
            _add_edge(graph, subject_id, node_id, edge_attrs, edge_keys)

        ET.indent(root, space="  ")
        return ET.tostring(root, encoding="unicode", xml_declaration=True) + "\n"


def _tag(name: str) -> str:
    return f"{{{GRAPHML_NS}}}{name}"


def _add_keys(root: ET.Element, target: str, fields: Tuple[str, ...], prefix: str) -> Dict[str, str]:
    keys: Dict[str, str] = {}
    for index, field in enumerate(fields):
        key_id = f"{prefix}{index}"
        keys[field] = key_id
        ET.SubElement(
            root,
            _tag("key"),
            {"id": key_id, "for": target, "attr.name": field, "attr.type": "string"},
        )
    return keys


def _add_node(graph: ET.Element, uid: str, attrs: Dict[str, Any], keys: Dict[str, str]) -> None:
    node = ET.SubElement(graph, _tag("node"), {"id": uid})
    for field, value in attrs.items():
        if field in keys and value not in (None, ""):
            ET.SubElement(node, _tag("data"), {"key": keys[field]}).text = str(value)


def _add_edge(
    graph: ET.Element,
    source: str,
    target: str,
    attrs: Dict[str, Any],
    keys: Dict[str, str],
) -> None:
    edge = ET.SubElement(graph, _tag("edge"), {"source": source, "target": target})
    for field, value in attrs.items():
        if field in keys and value not in (None, ""):
            ET.SubElement(edge, _tag("data"), {"key": keys[field]}).text = str(value)


def _stable_id(*parts: str) -> str:
    digest = hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"raf_{digest}"


def _finding_node(finding: Dict[str, Any], uid: str, timestamp: str) -> Dict[str, Any]:
    finding_type = str(finding.get("type"))
    value = str(finding.get("value", ""))
    details = finding.get("details") if isinstance(finding.get("details"), dict) else {}
    common: Dict[str, Any] = {
        "uid": uid,
        "Notes": json.dumps(
            {
                "source_tool": finding.get("source_tool"),
                "risk_hint": finding.get("risk_hint"),
                "evidence_file": finding.get("evidence_file"),
                "details": details,
            },
            ensure_ascii=False,
            default=str,
        ),
        "Date Created": str(finding.get("timestamp") or timestamp),
        "Date Last Edited": timestamp,
    }
    if finding_type == "username" and value.startswith(("http://", "https://")):
        return {**common, "Entity Type": "Website", "URL": value}
    if finding_type == "domain":
        return {**common, "Entity Type": "Domain", "Domain Name": value}
    if finding_type == "image":
        return {
            **common,
            "Entity Type": "Image",
            "Image Name": Path(value).name or value,
            "File Path": value,
        }
    return {**common, "Entity Type": "Phrase", "Phrase": details.get("caption") or value}
