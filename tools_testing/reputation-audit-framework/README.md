# Reputation Audit Framework

Version 1.1.0 is a containerized, passive OSINT pipeline for authorized reputation audits. It validates scope, runs bounded collectors, preserves raw evidence, normalizes records, generates analyst workflows, and builds Markdown/JSON reports.

See [TOOL_INTEGRATION_PIPELINE.md](TOOL_INTEGRATION_PIPELINE.md) for every upstream GitHub project, the data it collects, and its exact pipeline boundary.

> Authorized use only. The framework does not bypass authentication, CAPTCHAs, paywalls, or access controls. Username, image, graph, and screening matches are leads requiring analyst confirmation.

## Integrated tools

| Framework role | Upstream tool | Mode | Input/output |
| --- | --- | --- | --- |
| `maigret` | Maigret | Automatic collector | Username → candidate public profiles |
| `blackbird` | Blackbird | Automatic collector | Username → second-source profile candidates |
| `social_analyzer` | Social Analyzer | Automatic collector | Username → bounded JSON profile candidates |
| `amass` | OWASP Amass | Automatic collector | Domain → passive host/domain evidence |
| `spiderfoot` | SpiderFoot 4.0 | Automatic collector | Domain → allowlisted passive events |
| `recon_ng` | Recon-ng 5.1.2 | Automatic collector | Domain → allowlisted module JSON report |
| `exiftool` | ExifTool | Local collector | Authorized image directory → metadata findings |
| `yente` | OpenSanctions/yente | Internal service | Structured identity → unreviewed screening candidates |
| `search_by_image` | Search by Image | Analyst-assisted | Hashed image tasks → imported analyst decisions |
| `linkscope` | LinkScope Client | Analyst-assisted | Findings → native GraphML database + decision import |
| `openaleph` | OpenAleph/alephclient | Evidence integration | Workspace → package or authenticated upload |

LinkScope and Search by Image are intentionally not represented as unattended collectors: they are interactive desktop/browser products. The framework creates native inputs, stable IDs, review templates, and a validated result-import path.

## Full Docker setup

Run from this directory:

```bash
mkdir -p output images
export DOCKER_GID="$(stat -c '%g' /var/run/docker.sock)"

docker compose --profile tools build \
  audit social-analyzer recon-ng spiderfoot alephclient
docker compose --profile tools pull maigret blackbird amass exiftool
```

Start the optional local OpenSanctions/yente service:

```bash
docker compose --profile entity up -d yente-index yente
docker compose ps
curl -fsS http://127.0.0.1:8000/healthz
```

The first yente start downloads and indexes the configured OpenSanctions manifest. It requires substantial disk/RAM and can take many minutes. Wait for both services to be healthy before running `doctor`.

Check every configured role:

```bash
docker compose run --rm --no-deps audit doctor \
  --config /app/config.all-integrations.yaml
```

`doctor` exits `1` if any enabled binary, image, service, or integration is not ready.

## Run an authorized full audit

Put only client-authorized files in `images/`, then run:

```bash
docker compose run --rm --no-deps audit run \
  --full-name "Authorized Client" \
  --domain "client-owned.example.org" \
  --username "authorized_handle" \
  --email "public-address@example.org" \
  --birth-date "1985" \
  --country "US" \
  --subject-type person \
  --image-dir /app/images \
  --authorized yes \
  --config /app/config.all-integrations.yaml \
  --engagement-id "MATTER-123" \
  --no-pdf
```

Use only the identity attributes authorized for the engagement. `--birth-date` accepts `YYYY` or `YYYY-MM-DD`; `--country` is a two-letter code; `--subject-type` is `person`, `organization`, or `company`.

The included profiles are:

| Config | Purpose |
| --- | --- |
| `config.yaml` | Conservative default: proven core collectors; optional roles disabled |
| `config.all-integrations.yaml` | All requested automatic and analyst-assisted roles |
| `config.smoke.yaml` | Bounded live acceptance profile |
| `config.adapter-smoke.yaml` | SpiderFoot and Recon-ng regression profile |
| `config.amass-smoke.yaml` | Passive Amass regression profile |
| `config.maigret-only.yaml` | Small native username check |

## Analyst workflows

### Reverse image

When Search by Image is enabled, the run creates:

```text
manual_review/reverse_image/
├── assets/
├── tasks.json
├── results.template.json
└── REVIEW.md
```

Use the managed browser and the official Search by Image extension, complete a copy of the result template, then import it:

```bash
python main.py import-review \
  --workspace output/client_YYYY-MM-DD \
  --review-file output/client_YYYY-MM-DD/manual_review/reverse_image/results.completed.json \
  --config config.all-integrations.yaml
```

### LinkScope

Import `integrations/linkscope/reputation_audit.graphml` in LinkScope with **Import → From GraphML – Database**. Complete `review_decisions.template.json` using the exported stable node IDs, then use the same `import-review` command. The importer rejects wrong engagement IDs, unknown IDs, duplicate decisions, and invalid states.

### OpenAleph

`config.all-integrations.yaml` defaults to safe `package` mode. It produces a manifest and upload instructions without requiring secrets.

For an existing authorized OpenAleph deployment, change the integration to `mode: upload` and set secrets only at runtime:

```bash
export ALEPH_HOST="https://aleph.internal.example"
export ALEPH_API_KEY="..."
```

The adapter invokes `alephclient crawldir`, forwards secret names through the environment, and never embeds their values in command evidence.

## Output

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
│   ├── all_findings.json
│   ├── usernames.json
│   ├── domains.json
│   ├── images.json
│   ├── entities.json
│   ├── relationships.json
│   ├── screenings.json
│   ├── documents.json
│   ├── manual_reviews.json
│   └── risk.json
└── report/
    ├── report.md
    └── report.json
```

Possible final states:

| Status | Meaning |
| --- | --- |
| `completed` | All enabled automatic work completed; no review remains |
| `completed_with_review` | Collection completed, but analyst decisions are pending |
| `completed_with_errors` | At least one collector errored or timed out |
| `completed_with_gaps` | At least one configured input/tool was skipped |
| `incomplete_no_collectors` | No automatic collector completed successfully |

A zero-finding or Low-risk report is not a clean bill of health when coverage is incomplete. The report explicitly marks errors, timeouts, skipped checks, and pending review.

## Local development and verification

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m compileall -q .
python -m unittest discover -s tests -v
python -m pip check
python main.py version
python main.py modules --config config.all-integrations.yaml
python main.py run --full-name "Test" --username test-handle \
  --authorized yes --config config.all-integrations.yaml --dry-run --no-pdf
```

The August 4, 2026 acceptance work verified:

- all custom images build and their real entrypoints run;
- framework `doctor` recognizes every image plus a live yente service;
- Blackbird returned 22 and Social Analyzer 3 candidate profile records for the authorized smoke scope;
- SpiderFoot returned a normalized passive DNS event and Recon-ng completed its import/module/report sequence;
- yente indexed 4,319,233 entities and returned structured match candidates from a live query;
- ExifTool, reverse-image tasking/import, LinkScope GraphML, and OpenAleph package mode completed;
- 15 automated regression/contract tests pass.

Amass is correctly pinned, passive-only, evidence-preserving, and has completed previous live runs. Its v4.2 process can ignore its own `-timeout` when third-party passive sources stall; the framework therefore enforces an outer timeout and marks partial results as incomplete rather than claiming success.

## Security notes

- The audit container runs as a non-root user.
- Third-party collector commands are argument vectors, not shell-interpolated strings.
- Docker sibling mounts translate container paths back to the real host workspace.
- The Docker socket grants host-daemon control; use native execution if that boundary is unacceptable.
- yente and OpenAleph should remain internal, authenticated services with explicit retention policies.
- Treat `output/` as sensitive and encrypt, restrict, and delete it according to the engagement agreement.
