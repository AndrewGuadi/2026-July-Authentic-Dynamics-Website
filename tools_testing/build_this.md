# OSINT Reputation Audit Framework — Build, Run, and Verify

The unpacked audit application is in:

```text
tools_testing/reputation-audit-framework/
```

The Vite/React files in `tools_testing/` are a separate presentation. They do not execute OSINT tools.

## Authorization requirement

Run this framework only for a person, organization, domain, handle, email, and image set covered by written permission. The CLI requires `--authorized yes`, records the attestation and operator, and rejects collection without it.

The pipeline is passive-only: no login or CAPTCHA bypass, credential testing, brute force, active Amass mode, intrusive SpiderFoot modules, or unrestricted Recon-ng modules.

## Prerequisites

- Linux/macOS with Python 3.11+
- Docker Engine and Docker Compose v2 for the full profile
- Internet access for image pulls and public passive sources
- Approximately 8 GB free RAM and several GB disk if running local yente/Elasticsearch
- Client-authorized image files placed in `reputation-audit-framework/images/`

## 1. Build all integrations

```bash
cd tools_testing/reputation-audit-framework
mkdir -p output images

export DOCKER_GID="$(stat -c '%g' /var/run/docker.sock)"

docker compose --profile tools build \
  audit social-analyzer recon-ng spiderfoot alephclient

docker compose --profile tools pull maigret blackbird amass exiftool
```

Why `DOCKER_GID` matters: the non-root `auditor` user must belong to the host Docker socket’s group so it can start ephemeral sibling collectors. Do not routinely solve socket errors by running the audit as root.

## 2. Start OpenSanctions/yente

This step is required only when `modules.yente: true`, including the all-integrations profile.

```bash
docker compose --profile entity up -d yente-index yente
docker compose ps
curl -fsS http://127.0.0.1:8000/healthz
```

Expected health response:

```json
{"status":"ok"}
```

The first start downloads a large Elasticsearch image and indexes the configured OpenSanctions manifest. Health can become available before indexing finishes, so allow the initial index job to complete before relying on match results. The verified local build indexed 4,319,233 entities.

## 3. Verify readiness

```bash
docker compose run --rm --no-deps audit doctor \
  --config /app/config.all-integrations.yaml
```

Every enabled row should say `Ready: yes`. The command exits `1` if an enabled collector image, native tool, service, or post-collection integration is unavailable.

Also inspect the execution plan:

```bash
docker compose run --rm --no-deps audit run \
  --full-name "Authorized Client" \
  --domain "client-owned-domain.org" \
  --username "authorized_handle" \
  --image-dir /app/images \
  --authorized yes \
  --config /app/config.all-integrations.yaml \
  --dry-run \
  --no-pdf
```

The plan should contain these eleven roles:

1. Maigret
2. Blackbird
3. Social Analyzer
4. Amass
5. SpiderFoot
6. Recon-ng
7. ExifTool
8. OpenSanctions/yente
9. Search by Image review tasking
10. LinkScope graph export
11. OpenAleph package/upload

## 4. Run the full profile

```bash
docker compose run --rm --no-deps audit run \
  --full-name "Andrew Guasch" \
  --domain "authenticdynamics.com" \
  --username "infinitegrasp" \
  --email "gershwinfire13@gmail.com" \
  --birth-date "1990" \
  --country "US" \
  --subject-type person \
  --image-dir /app/images \
  --authorized yes \
  --config /app/config.all-integrations.yaml \
  --engagement-id "MATTER-123" 
```

```bash
docker compose run --rm --no-deps audit run \
  --full-name "Rho Sigma" \
  --username "irresistibleswitch" \
  --email "jaamesdeean@gmail.com" \
  --birth-date "1990" \
  --country "US" \
  --subject-type person \
  --image-dir /app/images \
  --authorized yes \
  --config /app/config.all-integrations.yaml \
  --engagement-id "MATTER-124" 
```
Identity-screening inputs are optional. Supply only attributes covered by the engagement:

| Option | Format/purpose |
| --- | --- |
| `--full-name` | Required client/brand name; yente name query |
| `--domain` | Client-controlled domain for Amass, SpiderFoot, Recon-ng |
| `--username` | Authorized handle for Maigret, Blackbird, Social Analyzer |
| `--email` | Optional public identity-matching attribute |
| `--birth-date` | Optional `YYYY` or `YYYY-MM-DD` |
| `--country` | Optional ISO two-letter country code |
| `--subject-type` | `person`, `organization`, or `company` |
| `--image-dir` | Client-supplied local images |
| `--engagement-id` | Matter/ticket ID propagated to evidence and review files |

## Configuration profiles

| File | Use |
| --- | --- |
| `config.yaml` | Conservative default collector set |
| `config.all-integrations.yaml` | All requested tool roles |
| `config.smoke.yaml` | Bounded all-role live acceptance |
| `config.adapter-smoke.yaml` | SpiderFoot + Recon-ng live regression |
| `config.amass-smoke.yaml` | Amass passive-wrapper regression |
| `config.maigret-only.yaml` | Minimal native username audit |

`config.all-integrations.yaml` uses safe OpenAleph `package` mode. To upload to an existing authorized OpenAleph deployment, change `integrations.openaleph.mode` to `upload` and export:

```bash
export ALEPH_HOST="https://aleph.internal.example"
export ALEPH_API_KEY="..."
```

The secrets are not written into command evidence.

## Analyst-assisted stages

### Search by Image

The framework does not pretend a browser extension is a server-side collector. It creates hash-addressed tasks under:

```text
manual_review/reverse_image/
```

Install [dessant/search-by-image](https://github.com/dessant/search-by-image) in the managed analyst browser, review each copied asset, fill out a copy of `results.template.json`, and import it:

```bash
python main.py import-review \
  --workspace output/client_YYYY-MM-DD \
  --review-file output/client_YYYY-MM-DD/manual_review/reverse_image/results.completed.json \
  --config config.all-integrations.yaml
```

### LinkScope

In LinkScope, choose **Import → From GraphML – Database** and load:

```text
integrations/linkscope/reputation_audit.graphml
```

Use `node_map.json` and `review_decisions.template.json` for analyst decisions, then import the completed JSON with `main.py import-review`. Unknown IDs, duplicate IDs, wrong engagements, and invalid states are rejected.

### OpenAleph

Package mode creates:

```text
integrations/openaleph/manifest.json
integrations/openaleph/UPLOAD.md
```

Upload mode invokes the pinned `alephclient crawldir` image and records its result. OpenAleph itself is a persistent external service and is not bundled into the audit’s critical path.

## Output and result interpretation

```text
output/client_YYYY-MM-DD/
├── scope.json
├── summary.json
├── usernames/
├── domain/
├── images/
├── entities/
├── manual_review/
├── integrations/
├── logs/audit.log
├── normalized/
└── report/
    ├── report.md
    └── report.json
```

Read `summary.json` first:

- `completed`: all automatic work complete and no analyst decision pending.
- `completed_with_review`: collectors completed, but LinkScope/image decisions remain.
- `completed_with_errors`: one or more tools failed or timed out.
- `completed_with_gaps`: one or more tools were skipped.
- `incomplete_no_collectors`: no automatic collector succeeded.

Do not interpret `0 findings`, a Low risk score, or a timed-out collector as proof that nothing exists. The report’s coverage table is part of the conclusion.

## Automated verification

```bash
cd tools_testing/reputation-audit-framework
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m compileall -q .
python -m unittest discover -s tests -v
python -m pip check
python main.py version
python main.py modules --config config.all-integrations.yaml
docker compose --profile tools --profile entity config --quiet
```

The current suite has 15 passing tests covering:

- Social Analyzer, Blackbird, Recon-ng, Amass, and yente output contracts;
- Docker host/container volume translation;
- Docker daemon readiness behavior;
- honest incomplete-coverage reporting;
- LinkScope GraphML structure;
- reverse-image hashing/task generation;
- reverse-image decision import and report regeneration;
- OpenAleph package/secret handling;
- yente’s official match request shape.

## Verified live results on 2026-08-04

- All five built images succeeded: audit, Social Analyzer, Recon-ng, SpiderFoot, and alephclient.
- Real `--help` entrypoints succeeded for every custom image.
- Framework `doctor` recognized all automatic images and the live yente service.
- Blackbird returned 22 and Social Analyzer 3 unverified candidate profiles for the authorized scope.
- SpiderFoot returned one normalized passive DNS finding.
- Recon-ng completed import, allowlisted collection, and JSON report generation.
- ExifTool reviewed the supplied WebP without GPS leakage.
- yente’s local service indexed 4,319,233 entities and returned known-positive structured screening candidates.
- Reverse-image task creation/import, LinkScope graph export, and OpenAleph package generation completed.
- Previous pinned Amass runs completed successfully and normalized the in-scope domain.

### Amass operational note

Amass v4.2 passive collection depends on third-party sources. In this environment it has both completed successfully and, on later runs, ignored its own `-timeout` while a source stalled. The framework’s outer deadline prevents indefinite execution and marks the module incomplete while preserving any partial files. Rerun Amass when the coverage table shows a timeout; do not treat partial results as complete.

## Troubleshooting

### `Unable to find group 989` or another group number

```bash
export DOCKER_GID="$(stat -c '%g' /var/run/docker.sock)"
docker compose build audit
docker compose run --rm --no-deps audit doctor
```

### yente is not ready

```bash
docker compose --profile entity up -d yente-index yente
docker compose ps
docker compose logs --tail 200 yente-index yente
curl -fsS http://127.0.0.1:8000/healthz
```

Wait for initial entity indexing. Check available RAM/disk if Elasticsearch is unhealthy.

### An automatic collector times out

Inspect its `*.command.json`, stdout/stderr, generated raw directory, and `logs/audit.log`. Increase the per-tool timeout only if the engagement permits the additional duration. A timeout is an incomplete check, even when partial findings exist.

### PDF is missing

Markdown and JSON are canonical. The Debian image does not install `wkhtmltopdf`; use `--no-pdf` unless you supply a supported renderer.

### Output already exists

The framework appends `_02`, `_03`, and so on. It never overwrites a prior engagement workspace.
