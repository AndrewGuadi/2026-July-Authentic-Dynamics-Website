# Authentic Dynamics experience upgrade

Review branch: `feature/2026-10-20-experience-upgrade`

This implements a coordinated first pass of the page-by-page experience audit. It preserves Flask/Jinja, the ink/cream/lime identity, service positioning and $500 entry offer. It does not certify a 97/100 UX score: that target requires defined evaluation criteria, observed user tasks and browser/device evidence beyond this implementation.

## Review map

| Area | Implemented behavior |
| --- | --- |
| Home | Existing client screenshot replaces competing illustrative hero content; industry selection updates relevant proof and inquiry context; brief cancelable transitions respect reduced motion; planner example is explicitly fictional. |
| Websites | Three goal choices drive a user-stepped fictional customer journey; selected service carries through to the inquiry form. No demonstration submission sends data. |
| Growth & Technology | Problem selection and customer/owner workflow steps explain the offer through a clearly labeled simulation. Existing review-request builder remains available. |
| Work | Existing 1776 screenshot provides concrete design observations; speculative future-proof filler is removed. No invented client outcomes, testimonials or performance claims. |
| About & Community | Existing founder/community imagery, section shortcuts, less repeated copy and static official-resource links when JavaScript is unavailable. Existing source dates remain unchanged. |
| Tool catalog | Compact task filters and handling badges; original links remain usable without JavaScript. |
| PDF / CSV / JSON tools | PDF presets; bounded CSV preview using the existing server parser and explicit upload flow; useful JSON samples while retaining exact previewed-PDF download behavior. |
| Video converter | Playback of the actual converted output; invalidation clears stale preview resources. Existing consent boundary remains. |
| List cleaner | Sample input, one-step undo and clearer blank/output feedback. |
| Invoice maker | Compact introduction, accessible section links and clearer current-draft versus saved-library distinction. |
| QR maker | Output and primary actions receive priority; advanced settings remain available through native disclosure. Existing encoding/export engine retained. |
| Local AI | Example actions and copy fallback. Existing local-engine/loading constraints remain explicit. |
| Browser Xray | Compact explanation and active-access summary based on actual permission state. No automatic device access. |
| Games | Compact entry pages; maze rendering stops while idle/paused and resumes on interaction. |
| Privacy / Terms | Shorter presentation and linked contents without rewriting legal substance. |
| Shared controls | No-JavaScript mobile navigation, accurate current-page state, allowlisted inquiry context, linked error summaries with retained input/focus and safe database-failure feedback. Branded recovery pages for common errors. |
| Hub / Admin | Exact currency conversion at the HTML boundary, workspace-timezone inputs and DST validation, retained inline errors, scoped navigation, readable history, server-confirmed board moves and clearer backup evidence. No schema/authentication changes. |

## Validation performed

- Baseline: 177 Python tests passed. Integrated branch: **211 Python tests passed**; full Ruff and whitespace checks passed.
- Shared public-route browser suite: 19 routes at 390px and 1440px; HTTP responses, one H1, overflow, runtime errors, menu Escape/focus, inquiry context, planner dismissal and no-JavaScript navigation. Native invalid local contact POST returns 400, retains context and focuses its error summary. No production inquiry sent.
- Existing SEO-page browser checks passed at 393px and 412px, covering metadata, navigation, validation, links, list-tool interaction, tap targets and overflow.
- Service demos checked at 360/390/412/1440px, including goal changes, workflow steps, contact context, keyboard behavior, reduced motion and no-JavaScript fallback.
- Tool workspace checks covered samples, task filtering, bounded CSV preview/export, leading zeroes/multiline fields, safe text rendering, stale results, actual synthetic video conversion/playback and JSON preview/download consistency. Responsive checks included 360/390/412/1440px.
- Utility checks passed at 390/1440px: list undo/stale output, QR validation/output, invoice navigation, permission summary, simulated Local AI actions and game idle/pause/resume. Existing QR decoding and PNG/SVG/PDF/print/logo/privacy checks passed. Local AI's engine was stubbed; actual model inference was not tested.
- Existing resource-finder and review-request-builder browser suites passed.
- Hub/admin: 36 targeted Python tests (included in the full suite), existing authenticated browser suite and new usability suite passed with synthetic local data. Checks included money correction/save, DST errors, focus/input retention, successful and failed keyboard board moves, reduced motion and mobile overflow at 360/390/412px; forms also checked at 1440px.
- Independent review checked 19 public routes at 360/1440px, no-JavaScript navigation, keyboard behavior and contact error recovery. Invalid Hub amount prefills and contact-summary focus were found and fixed. Visual review also caught and fixed mobile invoice/community navigation collisions and Hub board overflow.
- Selected desktop/mobile screenshots were visually reviewed for Home, Websites, About, catalog/converter workspaces, utilities and Hub forms/board.

Browser testing used Chromium with viewport/touch emulation. This is not physical iPhone/Android testing or Safari/WebKit testing. No new runtime dependencies were introduced. Browser test tooling was installed only in the temporary test environment.

## Limits and deliberate boundaries

- This is a broad first implementation of the audit, not proof that every route achieves 97 points in every category. No measured conversion uplift, field Core Web Vitals, real-device coverage or human usability study is claimed.
- Motion emphasizes short feedback and reduced-motion support. Decorative parallax is not included; the earlier cleanup PR contains a proposal, not a requirement to add continuous movement everywhere.
- A full first-page PDF preview, a Local AI stop action unsupported by the current engine, searchable long Hub relationship selectors and deeper per-resource form grouping remain future refinements.
- The Work page uses an existing artifact and visible design observations. Verified business results and richer case-study material require actual evidence.
- New ambiguous daylight-saving-hour inputs receive an explanatory error; existing ambiguous timestamps remain preserved. Hub JSON API amounts remain minor units.
- Existing indexing policy, local-data boundaries, production settings and legal text remain in place. No production data was accessed, no migrations were added and no deployment was performed.

## Pull request relationships

- PR #14 changes documentation/ignore rules only. This branch starts from main and does not include or alter #14; Andrew may approve it independently.
- PR #9 remains unmerged. Its event calculator is not treated as live or included here. Both PRs touch the tool catalog, so reconcile that catalog explicitly if #9 is later merged. Preserve main's indexing policy when resolving its sitemap changes.
- Manual approval only: do not merge, enable auto-merge or deploy as part of this review.
