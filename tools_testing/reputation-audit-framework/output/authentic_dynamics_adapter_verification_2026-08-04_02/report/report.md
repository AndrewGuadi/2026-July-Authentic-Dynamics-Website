# Reputation Audit Report — Authentic Dynamics Adapter Verification

**Engagement ID:** `RAF-ADAPTER-SMOKE-2-20260804`  
**Prepared by:** Authentic Dynamics (Andrew Guasch)  
**Collection window:** 2026-08-04T22:02:41.597690+00:00 → 2026-08-04T22:03:08.561226+00:00  
**Methodology:** Passive open-source reconnaissance only  
**Collection status:** **COMPLETE — every enabled collector finished successfully**  
**Observed-indicator risk:** 🟢 **Low** (score 0)

> This assessment used publicly available information only. No authentication
> control, paywall or CAPTCHA was bypassed; no intrusive or brute-force testing
> was performed against any system.



## 1. Scope confirmation

| Item | Value |
| --- | --- |
| Audit subject | Authentic Dynamics Adapter Verification |
| Domain in scope | authenticdynamics.com |
| Handle in scope | — not supplied — |
| Email in scope | — not supplied — |
| Identity type | person |
| Identity attributes | — not supplied — |
| Image set | — not supplied — |
| Authorization attested | yes @ 2026-08-04T22:02:41.596745+00:00 |
| Operator | auditor@94e01c9fba6c |
| Platform | Linux 6.8.0-1052-azure |

## 2. Executive summary

Passive collection produced **1 normalised finding(s)** across 0 account-match, 1 infrastructure, 0 media, 0 entity, 0 screening and 0 review observation(s).

**Indicators requiring attention**

- No elevated-risk indicators were identified.

The heuristic engine scored the evidence actually collected **0** which maps to the **Low** band using the thresholds in `config.yaml` (moderate ≥ 3, elevated ≥ 5, high ≥ 8).

## 3. Risk score

**Score:** 0 — **Low**

No scoring rule fired in the evidence collected. Account-handle matches remain unverified.

## 4. Findings by category

### 4.1 Potential account matches (ownership unverified)


> A matching public handle is a lead, not proof that the audit subject owns the account. Verify profile content and linked official properties before taking action.

_No findings recorded for this category._

### 4.2 Domain & infrastructure surface


| # | Value | Source | Risk hint | Evidence | Collected |
| ---: | --- | --- | --- | --- | --- |
| 1 | `authenticdynamics.com` | spiderfoot | Informational — corroborating context | `domain/spiderfoot_raw/spiderfoot.json` | 2026-08-04T22:02:54.505849+00:00 |

### 4.3 Media & metadata surface


_No findings recorded for this category._

### 4.4 Entity observations


_No findings recorded for this category._

### 4.5 Screening candidates (identity unverified)


> A yente/OpenSanctions candidate is not a confirmed identity match or adverse finding. Compare stronger attributes and record an analyst disposition.

_No findings recorded for this category._

### 4.6 Evidence-backed relationships


_No findings recorded for this category._

### 4.7 Document references


_No findings recorded for this category._

### 4.8 Pending and completed analyst reviews


_No findings recorded for this category._

## 5. Collection coverage

| Module | Status | Execution | Findings | Duration | Note |
| --- | --- | --- | ---: | ---: | --- |
| spiderfoot | ok | docker | 1 | 12.5s | 1 passive event(s) from 1 module(s) |
| recon_ng | ok | docker | 0 | 14.1s | 0 normalized record(s) from 1 passive module(s) |

## 6. Remediation checklist

- [ ] No scored technical remediation was identified; manually verify account matches and re-run quarterly.

**Standing hygiene**

- [ ] Manually verify each potential profile in section 4.1; enable MFA on confirmed owned accounts.
- [ ] Register brand-adjacent handles you do not yet control.
- [ ] Schedule this passive audit on a recurring 90-day cadence.
- [ ] Store this report and its evidence per your data-retention policy.

## 7. Evidence index

All artefacts are stored under `authentic_dynamics_adapter_verification_2026-08-04_02/`.

- `domain/recon_ng_raw/workspaces/raf_adapter_smoke_2_20260804/results.json`
- `domain/recon_ng_step_1.command.json`
- `domain/recon_ng_step_1.stdout.txt`
- `domain/recon_ng_step_2.command.json`
- `domain/recon_ng_step_2.stdout.txt`
- `domain/recon_ng_step_3.command.json`
- `domain/recon_ng_step_3.stdout.txt`
- `domain/spiderfoot.command.json`
- `domain/spiderfoot.stdout.txt`
- `domain/spiderfoot_raw/spiderfoot.json`

Normalised documents: `normalized/*.json`, including `all_findings.json` and `risk.json`.  
Execution log: `logs/audit.log`.

## 8. Appendix — method & legal basis

- **Enabled modules:** recon_ng, spiderfoot
- **Configuration:** `/app/config.adapter-smoke.yaml`
- **Technique:** passive OSINT collection from public datasets, certificate transparency, public profile endpoints and client-supplied files.
- **Excluded by design:** authentication bypass, CAPTCHA solving, paywall circumvention, credential testing, brute force, active/intrusive scanning.
- **Data handling:** every artefact carries a UTC collection timestamp; the scope, operator identity and authorization attestation are recorded in `scope.json`.

_Findings reflect publicly observable data at the time of collection and may change without notice._
