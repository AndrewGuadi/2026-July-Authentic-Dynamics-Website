# Reputation Audit Report — Andrew Guasch

**Engagement ID:** `RAF-20260804-040928`  
**Prepared by:** Your Security Practice, LLC (Unassigned)  
**Collection window:** 2026-08-04T04:09:28.017776+00:00 → 2026-08-04T04:09:53.157748+00:00  
**Methodology:** Passive open-source reconnaissance only  
**Overall risk:** 🟢 **Low** (score 0)

> This assessment used publicly available information only. No authentication
> control, paywall or CAPTCHA was bypassed; no intrusive or brute-force testing
> was performed against any system.

## 1. Scope confirmation

| Item | Value |
| --- | --- |
| Audit subject | Andrew Guasch |
| Domain in scope | andrewguasch.com |
| Handle in scope | omyguasch |
| Image set | /app/images (1 file(s)) |
| Authorization attested | yes @ 2026-08-04T04:09:28.017271+00:00 |
| Operator | auditor@8b9add5c19df |
| Platform | Linux 6.8.0-1052-azure |

## 2. Executive summary

Passive collection produced **15 normalised finding(s)** across 14 account, 0 infrastructure and 1 media observation(s).

**Indicators requiring attention**

- No elevated-risk indicators were identified.

The heuristic engine scored the engagement **0** which maps to the **Low** band using the thresholds in `config.yaml` (moderate ≥ 3, elevated ≥ 5, high ≥ 8).

## 3. Risk score

**Score:** 0 — **Low**

No scoring rule fired. Only informational, corroborating data was collected.

## 4. Findings by category

### 4.1 Identity & account surface


| # | Value | Source | Risk hint | Evidence | Collected |
| ---: | --- | --- | --- | --- | --- |
| 1 | `https://atcoder.jp/users/omyguasch` | maigret | Informational — corroborating context | `usernames/maigret_raw/report_omyguasch_simple.json` | 2026-08-04T04:09:47.420079+00:00 |
| 2 | `https://giphy.com/channel/omyguasch` | maigret | Informational — corroborating context | `usernames/maigret_raw/report_omyguasch_simple.json` | 2026-08-04T04:09:47.420023+00:00 |
| 3 | `https://huggingface.co/omyguasch` | maigret | Informational — corroborating context | `usernames/maigret_raw/report_omyguasch_simple.json` | 2026-08-04T04:09:47.420032+00:00 |
| 4 | `https://profil.chatujme.cz/omyguasch` | maigret | Informational — corroborating context | `usernames/maigret_raw/report_omyguasch_simple.json` | 2026-08-04T04:09:47.420076+00:00 |
| 5 | `https://untappd.com/user/omyguasch` | maigret | Informational — corroborating context | `usernames/maigret_raw/report_omyguasch_simple.json` | 2026-08-04T04:09:47.420059+00:00 |
| 6 | `https://venmo.com/omyguasch` | maigret | Informational — corroborating context | `usernames/maigret_raw/report_omyguasch_simple.json` | 2026-08-04T04:09:47.420067+00:00 |
| 7 | `https://www.cnet.com/profiles/omyguasch/` | maigret | Informational — corroborating context | `usernames/maigret_raw/report_omyguasch_simple.json` | 2026-08-04T04:09:47.420013+00:00 |
| 8 | `https://www.codechef.com/users/omyguasch` | maigret | Informational — corroborating context | `usernames/maigret_raw/report_omyguasch_simple.json` | 2026-08-04T04:09:47.420070+00:00 |
| 9 | `https://www.digitalpoint.com/members/?username=omyguasch` | maigret | Informational — corroborating context | `usernames/maigret_raw/report_omyguasch_simple.json` | 2026-08-04T04:09:47.420073+00:00 |
| 10 | `https://www.geeksforgeeks.org/profile/omyguasch` | maigret | Informational — corroborating context | `usernames/maigret_raw/report_omyguasch_simple.json` | 2026-08-04T04:09:47.420046+00:00 |
| 11 | `https://www.hackerrank.com/profile/omyguasch` | maigret | Informational — corroborating context | `usernames/maigret_raw/report_omyguasch_simple.json` | 2026-08-04T04:09:47.420050+00:00 |
| 12 | `https://www.instapaper.com/p/omyguasch` | maigret | Informational — corroborating context | `usernames/maigret_raw/report_omyguasch_simple.json` | 2026-08-04T04:09:47.420042+00:00 |
| 13 | `https://www.reverbnation.com/omyguasch` | maigret | Informational — corroborating context | `usernames/maigret_raw/report_omyguasch_simple.json` | 2026-08-04T04:09:47.420028+00:00 |
| 14 | `https://www.tbank.ru/invest/social/profile/omyguasch/` | maigret | Informational — corroborating context | `usernames/maigret_raw/report_omyguasch_simple.json` | 2026-08-04T04:09:47.420063+00:00 |

### 4.2 Domain & infrastructure surface


_No findings recorded for this category._

### 4.3 Media & metadata surface


| # | Value | Source | Risk hint | Evidence | Collected |
| ---: | --- | --- | --- | --- | --- |
| 1 | `/app/images/andrew-guasch.webp` | exiftool | Informational — corroborating context | `images/exiftool_metadata.json` | 2026-08-04T04:09:53.153977+00:00 |

## 5. Collection coverage

| Module | Status | Execution | Findings | Duration | Note |
| --- | --- | --- | ---: | ---: | --- |
| maigret | ok | native | 14 | 19.4s | 14 claimed profile(s) |
| blackbird | error | docker | 0 | 2.0s | no parsable results (exit 2) |
| amass | error | docker | 0 | 3.3s | exit 1 |
| spiderfoot | error | docker | 0 | 0.2s | exit 125 |
| exiftool | ok | native | 1 | 0.2s | 1 file(s) reviewed, 0 with GPS |

## 6. Remediation checklist

- [ ] No remediation required. Re-run this audit quarterly to detect drift.
**Standing hygiene**

- [ ] Enable MFA on every verified profile discovered in section 4.1.
- [ ] Register brand-adjacent handles you do not yet control.
- [ ] Schedule this passive audit on a recurring 90-day cadence.
- [ ] Store this report and its evidence per your data-retention policy.

## 7. Evidence index

All artefacts are stored under `andrew_guasch_2026-08-04/`.

- `domain/amass.command.json`
- `domain/amass.stderr.txt`
- `domain/spiderfoot.command.json`
- `domain/spiderfoot.stderr.txt`
- `images/exiftool.command.json`
- `images/exiftool.stderr.txt`
- `images/exiftool.stdout.txt`
- `images/exiftool_metadata.json`
- `usernames/blackbird.command.json`
- `usernames/blackbird.stderr.txt`
- `usernames/blackbird.stdout.txt`
- `usernames/maigret.command.json`
- `usernames/maigret.stderr.txt`
- `usernames/maigret.stdout.txt`
- `usernames/maigret_raw/report_omyguasch_simple.json`

Normalised documents: `normalized/usernames.json`, `normalized/domains.json`, `normalized/images.json`, `normalized/all_findings.json`, `normalized/risk.json`.  
Execution log: `logs/audit.log`.

## 8. Appendix — method & legal basis

- **Enabled modules:** amass, blackbird, exiftool, maigret, spiderfoot
- **Configuration:** `/app/config.yaml`
- **Technique:** passive OSINT collection from public datasets, certificate transparency, public profile endpoints and client-supplied files.
- **Excluded by design:** authentication bypass, CAPTCHA solving, paywall circumvention, credential testing, brute force, active/intrusive scanning.
- **Data handling:** every artefact carries a UTC collection timestamp; the scope, operator identity and authorization attestation are recorded in `scope.json`.

_Findings reflect publicly observable data at the time of collection and may change without notice._
