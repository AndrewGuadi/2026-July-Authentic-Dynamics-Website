# Reputation Audit Report — Sarah Mitchell

**Engagement ID:** `RAF-20260214-093107`  
**Prepared by:** Northgate Security Practice, LLC (a.reyes)  
**Collection window:** 2026-02-14T09:31:07+00:00 → 2026-02-14T09:37:52+00:00  
**Methodology:** Passive open-source reconnaissance only  
**Overall risk:** 🔴 **High** (score 9)

> This assessment used publicly available information only. No authentication
> control, paywall or CAPTCHA was bypassed; no intrusive or brute-force testing
> was performed against any system.

## 1. Scope confirmation

| Item | Value |
| --- | --- |
| Audit subject | Sarah Mitchell |
| Domain in scope | sarahmitchellhomes.com |
| Handle in scope | sarahmitchellrealtor |
| Image set | /work/images (12 file(s)) |
| Authorization attested | yes @ 2026-02-14T09:31:07+00:00 |
| Operator | a.reyes@ngs-audit-01 |
| Platform | Linux 6.8.0 |

## 2. Executive summary

Passive collection produced **75 normalised finding(s)** across 23 account, 40 infrastructure and 12 media observation(s).

**Indicators requiring attention**

- Possible impersonation / look-alike handle (3)
- Sensitive hostname exposed in passive datasets (5)
- GPS coordinates embedded in published imagery (4)
- Personal or device identifiers in metadata (6)

The heuristic engine scored the engagement **9** which maps to the **High** band using the thresholds in `config.yaml` (moderate ≥ 3, elevated ≥ 5, high ≥ 8).

## 3. Risk score

**Score:** 9 — 🔴 **High**

| Rule | Points | Rationale | Sample evidence |
| --- | ---: | --- | --- |
| `impersonation_keyword` | +4 | 3 discovered handle(s) contain brand/impersonation keywords (2 pts each, capped at 6) | https://example.social/sarahmitchell_realtor_official, https://profiles.example/sarahmitchellhomes_hq |
| `gps_metadata` | +3 | 4 published image(s) retain GPS coordinates in EXIF | /work/images/listing-104-oak.jpg, /work/images/open-house-3.jpg |
| `subdomain_exposure` | +2 | 17 unique hostnames exposed in passive sources (threshold 10) | admin.sarahmitchellhomes.com, dev.sarahmitchellhomes.com |
| `pii_metadata` | +1 | 6 artefact(s) leak author/device identifiers | /work/images/headshot-2025.jpg |

## 4. Findings by category

### 4.1 Identity & account surface

| # | Value | Source | Risk hint | Evidence | Collected |
| ---: | --- | --- | --- | --- | --- |
| 1 | `https://example.social/sarahmitchell_realtor_official` | maigret | Possible impersonation / look-alike handle | `usernames/maigret_raw/report_simple.json` | 2026-02-14T09:32:11+00:00 |
| 2 | `https://profiles.example/sarahmitchellhomes_hq` | maigret | Possible impersonation / look-alike handle | `usernames/maigret_raw/report_simple.json` | 2026-02-14T09:32:11+00:00 |
| 3 | `https://micro.example/sarahmitchellrealty_team` | blackbird | Possible impersonation / look-alike handle | `usernames/blackbird_raw/results.json` | 2026-02-14T09:33:02+00:00 |
| 4 | `https://photo.example/sarahmitchellrealtor` | maigret | Informational — corroborating context | `usernames/maigret_raw/report_simple.json` | 2026-02-14T09:32:11+00:00 |
| 5 | `https://video.example/@sarahmitchellrealtor` | maigret | Informational — corroborating context | `usernames/maigret_raw/report_simple.json` | 2026-02-14T09:32:11+00:00 |
| 6 | `https://forum.example/u/sarahmitchellrealtor` | blackbird | Informational — corroborating context | `usernames/blackbird_raw/results.json` | 2026-02-14T09:33:02+00:00 |

### 4.2 Domain & infrastructure surface

| # | Value | Source | Risk hint | Evidence | Collected |
| ---: | --- | --- | --- | --- | --- |
| 1 | `admin.sarahmitchellhomes.com` | amass | Sensitive hostname exposed in passive datasets | `domain/amass_raw/amass.json` | 2026-02-14T09:34:40+00:00 |
| 2 | `dev.sarahmitchellhomes.com` | amass | Sensitive hostname exposed in passive datasets | `domain/amass_raw/amass.json` | 2026-02-14T09:34:40+00:00 |
| 3 | `staging.sarahmitchellhomes.com` | amass | Sensitive hostname exposed in passive datasets | `domain/amass_raw/amass.json` | 2026-02-14T09:34:40+00:00 |
| 4 | `webmail.sarahmitchellhomes.com` | amass | Sensitive hostname exposed in passive datasets | `domain/amass_raw/amass.json` | 2026-02-14T09:34:40+00:00 |
| 5 | `old.sarahmitchellhomes.com` | spiderfoot | Sensitive hostname exposed in passive datasets | `domain/spiderfoot_raw/spiderfoot.json` | 2026-02-14T09:36:05+00:00 |
| 6 | `www.sarahmitchellhomes.com` | amass | Informational — corroborating context | `domain/amass_raw/amass.json` | 2026-02-14T09:34:40+00:00 |
| 7 | `listings.sarahmitchellhomes.com` | amass | Informational — corroborating context | `domain/amass_raw/amass.json` | 2026-02-14T09:34:40+00:00 |
| 8 | `hello@sarahmitchellhomes.com` | spiderfoot | Personal or device identifiers in metadata | `domain/spiderfoot_raw/spiderfoot.json` | 2026-02-14T09:36:05+00:00 |

_32 additional record(s) omitted for brevity — see `normalized/domains.json`._

### 4.3 Media & metadata surface

| # | Value | Source | Risk hint | Evidence | Collected |
| ---: | --- | --- | --- | --- | --- |
| 1 | `/work/images/listing-104-oak.jpg` | exiftool | GPS coordinates embedded in published imagery | `images/exiftool_metadata.json` | 2026-02-14T09:37:14+00:00 |
| 2 | `/work/images/open-house-3.jpg` | exiftool | GPS coordinates embedded in published imagery | `images/exiftool_metadata.json` | 2026-02-14T09:37:14+00:00 |
| 3 | `/work/images/twilight-front.jpg` | exiftool | GPS coordinates embedded in published imagery | `images/exiftool_metadata.json` | 2026-02-14T09:37:14+00:00 |
| 4 | `/work/images/kitchen-wide.jpg` | exiftool | GPS coordinates embedded in published imagery | `images/exiftool_metadata.json` | 2026-02-14T09:37:14+00:00 |
| 5 | `/work/images/headshot-2025.jpg` | exiftool | Personal or device identifiers in metadata | `images/exiftool_metadata.json` | 2026-02-14T09:37:14+00:00 |
| 6 | `/work/images/team-photo.jpg` | exiftool | Personal or device identifiers in metadata | `images/exiftool_metadata.json` | 2026-02-14T09:37:14+00:00 |

## 5. Collection coverage

| Module | Status | Execution | Findings | Duration | Note |
| --- | --- | --- | ---: | ---: | --- |
| maigret | ok | native | 14 | 62.4s | 14 claimed profile(s) |
| blackbird | ok | docker | 9 | 41.8s | 9 corroborated profile(s) |
| amass | ok | docker | 17 | 93.1s | 17 unique hostname(s) |
| spiderfoot | ok | docker | 23 | 140.6s | 23 passive event(s) from 8 module(s) |
| exiftool | ok | native | 12 | 3.2s | 12 file(s) reviewed, 4 with GPS |
| trufflehog | skipped | native | 0 | 0.0s | module disabled in config |
| theharvester | skipped | docker | 0 | 0.0s | module disabled in config |

## 6. Remediation checklist

**GPS coordinates embedded in published imagery**

- [ ] Strip EXIF/GPS from all listing photography before publication (`exiftool -all= -overwrite_original`).
- [ ] Enable metadata stripping in the CMS/media pipeline so it cannot be forgotten.
- [ ] Re-upload previously published imagery that still contains coordinates.

**Possible impersonation / look-alike handle**

- [ ] Submit impersonation reports on the affected platforms using the brand-owner flow.
- [ ] Register the look-alike handles you can claim defensively (name + realtor/homes variants).
- [ ] Publish an official 'where to find me' page listing verified profile URLs.

**Sensitive hostname exposed in passive datasets**

- [ ] Inventory every hostname returned and decommission or restrict non-production endpoints.
- [ ] Put staging/admin interfaces behind SSO or an IP allowlist.
- [ ] Add certificate-transparency monitoring for new hostnames on the apex domain.

**Personal or device identifiers in metadata**

- [ ] Remove author, owner and device serial tags from published assets.
- [ ] Use a studio/brand identity rather than a personal name in asset metadata.

**Standing hygiene**

- [ ] Enable MFA on every verified profile discovered in section 4.1.
- [ ] Register brand-adjacent handles you do not yet control.
- [ ] Schedule this passive audit on a recurring 90-day cadence.
- [ ] Store this report and its evidence per your data-retention policy.

## 7. Evidence index

All artefacts are stored under `sarah_mitchell_2026-02-14/`.

- `usernames/maigret.stdout.txt`
- `usernames/maigret.command.json`
- `usernames/maigret_raw/report_simple.json`
- `usernames/blackbird.stdout.txt`
- `usernames/blackbird_raw/results.json`
- `domain/amass.stdout.txt`
- `domain/amass_raw/amass.json`
- `domain/spiderfoot.stdout.txt`
- `domain/spiderfoot_raw/spiderfoot.json`
- `images/exiftool.stdout.txt`
- `images/exiftool_metadata.json`

Normalised documents: `normalized/usernames.json`, `normalized/domains.json`, `normalized/images.json`, `normalized/all_findings.json`, `normalized/risk.json`.  
Execution log: `logs/audit.log`.

## 8. Appendix — method & legal basis

- **Enabled modules:** amass, blackbird, exiftool, maigret, spiderfoot
- **Configuration:** `config.yaml`
- **Technique:** passive OSINT collection from public datasets, certificate transparency, public profile endpoints and client-supplied files.
- **Excluded by design:** authentication bypass, CAPTCHA solving, paywall circumvention, credential testing, brute force, active/intrusive scanning.
- **Data handling:** every artefact carries a UTC collection timestamp; the scope, operator identity and authorization attestation are recorded in `scope.json`.

_Findings reflect publicly observable data at the time of collection and may change without notice._
