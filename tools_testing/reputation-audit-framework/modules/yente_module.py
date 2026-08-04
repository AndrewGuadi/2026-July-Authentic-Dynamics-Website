"""OpenSanctions/yente entity matching service connector."""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from core.validator import Scope
from core.workspace import Workspace
from modules.base import ModuleResult, OSINTModule
from normalization.normalize_entities import from_yente

DATASET_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
SCHEMAS = {"person": "Person", "organization": "Organization", "company": "Company"}


class YenteModule(OSINTModule):
    """Submit a structured identity example to an internal yente matcher."""

    name = "yente"
    scope_field = "full_name"
    category = "screening"
    passive = True
    description = "Structured OpenSanctions/yente candidate matching; analyst disposition required."

    def execution_mode(self) -> str:
        return "service"

    def run(self, scope: Scope, workspace: Workspace) -> ModuleResult:
        base_url = str(os.environ.get("YENTE_BASE_URL") or self.options.get("base_url") or "").rstrip("/")
        dataset = str(self.options.get("dataset", "default"))
        if not base_url:
            return ModuleResult.skipped(self.name, "YENTE_BASE_URL/module_options.yente.base_url is not configured")
        if not DATASET_RE.fullmatch(dataset):
            return ModuleResult.failed(self.name, f"invalid yente dataset name: {dataset!r}")

        properties: Dict[str, list[str]] = {"name": [scope.full_name]}
        if scope.birth_date:
            properties["birthDate"] = [scope.birth_date]
        if scope.country:
            country_field = "nationality" if scope.subject_type == "person" else "country"
            properties[country_field] = [scope.country]
        if scope.email:
            properties["email"] = [scope.email]
        body = {
            "queries": {
                "subject": {
                    "schema": SCHEMAS[scope.subject_type],
                    "properties": properties,
                }
            }
        }
        limit = max(1, min(int(self.options.get("limit", 5)), 50))
        threshold = max(0.0, min(float(self.options.get("threshold", 0.7)), 1.0))
        endpoint = f"{base_url}/match/{dataset}?{urlencode({'limit': limit, 'threshold': threshold})}"
        request_path = workspace.write_json(
            workspace.entities / "yente_raw" / "request.json",
            {"endpoint": endpoint, "body": body, "authorization_header_present": bool(os.environ.get("YENTE_API_KEY"))},
        )

        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        api_key = os.environ.get("YENTE_API_KEY")
        if api_key:
            headers["Authorization"] = f"ApiKey {api_key}"
        request = Request(endpoint, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        started = time.monotonic()
        error = "yente request failed"
        try:
            with urlopen(request, timeout=self.timeout) as response:  # nosec: authorized configured service
                raw = response.read().decode("utf-8", errors="replace")
                status_code = int(response.status)
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            status_code = int(exc.code)
            error = f"yente HTTP {exc.code}: {raw[:300]}"
        except (URLError, TimeoutError, OSError) as exc:
            duration = round(time.monotonic() - started, 2)
            return ModuleResult.failed(self.name, f"yente request failed: {exc}", command=endpoint, duration=duration)
        duration = round(time.monotonic() - started, 2)
        if status_code < 200 or status_code >= 300:
            error_path = workspace.write_text(workspace.entities / "yente_raw" / "response.txt", raw)
            return ModuleResult(
                module=self.name,
                status="error",
                raw_files=[workspace.relative(request_path), workspace.relative(error_path)],
                command=endpoint,
                execution="service",
                duration=duration,
                error=error,
            )
        try:
            payload: Any = json.loads(raw)
        except json.JSONDecodeError:
            response_path = workspace.write_text(workspace.entities / "yente_raw" / "response.txt", raw)
            return ModuleResult(
                module=self.name,
                status="error",
                raw_files=[workspace.relative(request_path), workspace.relative(response_path)],
                command=endpoint,
                execution="service",
                duration=duration,
                error="yente returned invalid JSON",
            )

        response_path = workspace.write_json(workspace.entities / "yente_raw" / "response.json", payload)
        evidence = workspace.relative(response_path)
        findings = from_yente(payload, evidence)
        return ModuleResult(
            module=self.name,
            status="ok",
            findings=findings,
            raw_files=[workspace.relative(request_path), evidence],
            command=endpoint,
            execution="service",
            duration=duration,
            note=f"{len(findings)} screening candidate(s); analyst disposition required",
        )
