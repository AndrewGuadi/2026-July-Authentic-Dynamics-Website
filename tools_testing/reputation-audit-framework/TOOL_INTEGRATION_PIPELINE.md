# OSINT Tool Integration and Pipeline Guide

Last verified: 2026-08-04

This document lists every requested GitHub project, what it collects, how it is integrated, and where it runs. “Integrated” means the framework has an explicit adapter or analyst handoff, preserves evidence, and reports an honest status. It does not mean every third-party source will answer on every run.

## Integration matrix

| Tool and GitHub | What it collects or produces | Framework setup | Pipeline stage | Verified status |
| --- | --- | --- | --- | --- |
| [smicallef/spiderfoot](https://github.com/smicallef/spiderfoot) | Correlated domain, host, DNS, WHOIS, certificate, contact, and other OSINT events | Pinned v4.0 source image; strict passive module denylist/selection; JSON normalization | Domain enrichment | Integrated. Image/entrypoint tested; `sfp_dnsresolve` returned a live normalized event. Slow sources such as `sfp_crt` are opt-in. |
| [AccentuSoft/LinkScope_Client](https://github.com/AccentuSoft/LinkScope_Client) | Interactive investigation graph, relationships, analyst annotations | Native GraphML Database export with LinkScope entity/edge attributes, node map, instructions, and validated decision import | Analyst correlation | Integrated analyst handoff. Graph schema contract and stable IDs tested; desktop GUI is not run headlessly. |
| [soxoj/maigret](https://github.com/soxoj/maigret) | Candidate public username profiles and profile metadata | Native/package adapter, bounded site count, JSON evidence, no recursion/autoupdate | Username discovery | Integrated and live-tested. Empty bounded sets are recorded as successful zero results. |
| [qeeqbox/social-analyzer](https://github.com/qeeqbox/social-analyzer) | Candidate profiles, links, detection rate, optional metadata/extraction | Pinned Python image, JSON-only CLI, good/detected filter, bounded top sites | Username corroboration | Integrated and live-tested; returned three candidates in the authorized smoke run. |
| [p1ngul1n0/blackbird](https://github.com/p1ngul1n0/blackbird) | Candidate username/email profiles with structured site status | Pinned image digest, non-permuting username execution, JSON evidence normalization | Username corroboration | Integrated and live-tested; returned 22 candidates in the authorized smoke run. |
| [dessant/search-by-image](https://github.com/dessant/search-by-image) | Launches an image into multiple reverse-image engines | Hashed/copied review assets, task queue, engine/result template, validated decision import | Analyst image review | Integrated analyst handoff. Task generation and end-to-end result import/report rebuild tested. The extension is not an independent image index. |
| [openaleph/openaleph](https://github.com/openaleph/openaleph) and [alephdata/alephclient](https://github.com/alephdata/alephclient) | Evidence/document ingestion, indexing, entity extraction, cross-document investigation | Deterministic package mode or authenticated `alephclient crawldir` upload; pinned client image; secret-safe command evidence | Evidence repository | Package path and client image tested. Upload requires an operator-provided OpenAleph host/API key and cannot be live-tested without that authorized deployment. |
| [opensanctions/opensanctions](https://github.com/opensanctions/opensanctions) and [opensanctions/yente](https://github.com/opensanctions/yente) | Normalized sanctions/PEP/related-person data and entity matching candidates | yente 5.5.0 + Elasticsearch 9.4.2 Compose profile; official match API body; structured identity fields; analyst-review labeling | Entity screening | Integrated and live-tested. Local service indexed 4,319,233 entities and returned structured candidates from a known-positive query. |
| [owasp-amass/amass](https://github.com/owasp-amass/amass) | Domains, subdomains, and passive external attack-surface evidence | Pinned image digest, `enum` passive-only, active flags blocked, host scope filter, outer timeout, partial-evidence retention | Domain discovery | Integrated and previously completed live runs. Upstream v4.2 may overrun its own timeout when sources stall; wrapper timeout is reported as incomplete, never clean. |
| [lanmaster53/recon-ng](https://github.com/lanmaster53/recon-ng) and [recon-ng-modules](https://github.com/lanmaster53/recon-ng-modules) | Modular workspace/database reconnaissance and JSON reports | Pinned source commits; image contains only approved import, CT/HackerTarget, and JSON reporting modules; isolated workspace | Controlled domain enrichment | Integrated and live-tested. Full import/module/report sequence completed cleanly. |
| ExifTool | EXIF/IPTC/XMP metadata, including GPS and author/device fields | Native package in audit image; authorized image directory mounted read-only | Local asset review | Integrated and live-tested against the supplied WebP asset. |

## Pipeline

```text
Written authorization + validated scope
                 |
                 v
       Isolated engagement workspace
        /             |              \
       v              v               v
  Username         Domain          Local assets
  Maigret          Amass           ExifTool
  Blackbird        SpiderFoot      Search-by-Image tasks
  Social Analyzer  Recon-ng
       \              |               /
        +-------------+--------------+
                      v
         Raw evidence and command provenance
                      |
                      v
        Normalize, filter scope, and deduplicate
              /             |              \
             v              v               v
      yente screening   LinkScope graph   OpenAleph package/upload
             \              |               /
              +-------------+--------------+
                            v
               Risk rules + Markdown/JSON report
                            |
                            v
              Import analyst decisions and rebuild
```

Automatic collectors run before reporting. Search by Image and LinkScope create `review_required` work rather than silently blocking or claiming that human analysis occurred. OpenAleph package/upload is post-collection so an evidence-platform outage does not erase collector evidence.

## Setup by boundary

### Ephemeral collector boundary

The audit process invokes Maigret, Blackbird, Social Analyzer, Amass, SpiderFoot, Recon-ng, and ExifTool. Each adapter has a scope field, timeout, evidence directory, normalized parser, and `ModuleResult`.

Build/pull:

```bash
export DOCKER_GID="$(stat -c '%g' /var/run/docker.sock)"
docker compose --profile tools build \
  audit social-analyzer recon-ng spiderfoot alephclient
docker compose --profile tools pull maigret blackbird amass exiftool
```

Collector safeguards:

- validated inputs are passed as argument-vector elements;
- active Amass flags and intrusive SpiderFoot modules are rejected;
- Recon-ng can run only image-bundled modules in `PASSIVE_MODULES`;
- username ownership remains `unverified_handle_match`;
- non-zero exits/timeouts retain raw and partial evidence but mark coverage incomplete.

### Entity service boundary

Start yente separately because it is persistent and resource-intensive:

```bash
docker compose --profile entity up -d yente-index yente
docker compose ps
curl -fsS http://127.0.0.1:8000/healthz
```

`YENTE_BASE_URL` defaults to `http://yente:8000` inside Compose. `YENTE_API_KEY` is optional for an internal unprotected instance. Production deployments should authenticate the service, restrict it to an internal network, pin a reviewed dataset manifest, and apply retention/access controls.

The framework sends:

```json
{
  "queries": {
    "subject": {
      "schema": "Person",
      "properties": {
        "name": ["Authorized Name"],
        "birthDate": ["1985"],
        "country": ["US"]
      }
    }
  }
}
```

Every returned record is a screening candidate. A score or `match: true` is not an adverse conclusion; an analyst must resolve identity using authorized attributes.

### Analyst workstation boundary

LinkScope and Search by Image stay on a managed analyst workstation:

1. Import the generated graph or open the copied/hash-verified image task.
2. Record decisions only in the generated template using its stable IDs.
3. Run `main.py import-review`.
4. The importer verifies engagement ID, record ID, allowed state, and duplicates.
5. Normalized files, risk, report, and summary are regenerated.

Allowed review states are `confirmed`, `rejected`, `candidate_match`, `no_match`, and `inconclusive`.

### Evidence platform boundary

OpenAleph is not embedded in the default audit process. In `package` mode, every engagement gets a deterministic collection foreign ID and instructions. In `upload` mode, the adapter requires:

```bash
export ALEPH_HOST="https://authorized-aleph.example"
export ALEPH_API_KEY="..."
```

Secrets are forwarded by environment-variable name and excluded from evidence. The adapter records exit code, timeout, stdout/stderr, and command metadata.

## Normalized record types

All findings use:

```json
{
  "type": "username",
  "source_tool": "social-analyzer",
  "value": "https://public.example/authorized_handle",
  "risk_hint": "informational",
  "evidence_file": "usernames/social_analyzer_raw/results.json",
  "timestamp": "2026-08-04T00:00:00+00:00",
  "details": {
    "ownership": "unverified_handle_match"
  }
}
```

Supported types are `username`, `domain`, `image`, `entity`, `relationship`, `screening`, `document`, and `manual_review`. Raw source confidence stays in `details`; the framework does not fabricate certainty.

## Acceptance evidence

The 2026-08-04 acceptance run included:

- five framework/custom images built successfully;
- every custom tool entrypoint executed from its real container;
- all requested roles shown in `modules`/`doctor`;
- live Blackbird, Social Analyzer, SpiderFoot, Recon-ng, ExifTool, and yente execution;
- previous live Maigret, Blackbird, Amass, and ExifTool runs with all commands returning zero;
- Search by Image task-to-decision import and report regeneration;
- LinkScope GraphML structural/import-contract test;
- OpenAleph package/client command contract;
- 15 passing unit/regression/contract tests.

External sites, passive APIs, sanctions datasets, and image engines change over time. Operational success means the adapter invokes the pinned tool correctly, bounds it, preserves evidence, and reports source failure honestly—not that the internet will return the same records forever.

## Definition of integrated

A new tool is not integrated until it has:

1. a pinned package, image digest, release, or source commit;
2. a validated scope-to-input mapping;
3. code-enforced passive/authorization restrictions;
4. a bounded runtime and evidence-preserving failure path;
5. raw output plus command/version provenance;
6. normalized records linked to evidence;
7. fixture/contract tests for expected output;
8. an exact `doctor` readiness check;
9. a live or operator-dependent acceptance statement that does not overclaim;
10. report language distinguishing no result, not checked, failed, and pending review.
