# Search Console audit and two-query improvement plan

Reviewed October 23, 2026. Source: Andrew's `authenticdynamics.com-Performance-on-Search-2026-10-23 (1).zip`. The original export is not committed to this public repository.

## What the export establishes

The export contains 1,281 query rows, 166 page rows, countries, devices, an empty search-appearance table and filters. Its filter says Web (text-based), Last 6 months. Metric columns compare Last 6 months with Previous 6 months. It has **no daily chart, explicit start/end dates, latest complete data date, query-by-page cross-tab or indexing report**. Do not infer exact dates from the filename or label these figures as current 28-day rankings. A zero in the previous position column with zero impressions is not a prior rank of zero.

Totals below are summed from mutually exclusive device rows. Overall positions are impression-weighted estimates from rounded device averages.

| Metric | Previous six months | Last six months |
| --- | ---: | ---: |
| Clicks | 76 | 35 |
| Impressions | 14,484 | 31,764 |
| CTR, recomputed | 0.525% | 0.110% |
| Approximate average position | 11.55 | 56.25 |
| Homepage clicks | 60 | 24 |
| Homepage impressions | 6,865 | 25,151 |

Clicks declined 53.9% while impressions increased 119.3%. That is broader visibility with much less traffic per impression; it does not establish the cause. The six-month windows can mix different site versions, query distributions, locations and result types. They cannot tell us when the change happened or prove that every keyword fell by the overall position difference.

- Desktop contributes 30,230 of 31,764 impressions (95.2%), but only 14 clicks. Mobile contributes 1,467 impressions and 21 clicks (1.43% CTR). Inspect query, country, date and device intersections before deciding whether this is audience mismatch, ranking loss or another cause. Search Console alone cannot establish bots or manipulation.
- The homepage receives 24 of 35 clicks and 25,151 impressions. The current `/websites` and `/growth-technology` paths do not appear in the exported page table. This suggests a historical architecture mismatch worth investigating; it does not prove they are currently unindexed.
- Query rows total only 16 clicks and 25,452 impressions. Do not substitute their sum for the property totals: query tables can omit data and use different aggregation. Branded `authentic dynamics` supplies 15 of those visible query clicks.
- Generic phrases such as `web developers near me` (501 impressions, position 1.12, no clicks) and `website development company` (458, position 1.61, no clicks) are not reliable evidence of present-day local first-place visibility. Average position describes observed search appearances, not a fixed rank in Harrisburg.
- Some queries have irrelevant geography or entire prompt-like wording. Their origin is unknown. They should not determine new service areas or keyword-stuffed content.

## The two selected queries

| Exact query | Last impressions / clicks / CTR / position | Previous impressions / clicks / position | Proposed destination |
| --- | --- | --- | --- |
| web design harrisburg | 325 / 0 / 0% / 47.69 | 143 / 0 / 1.28 | `/websites` |
| website analytics services central pa | 225 / 0 / 0% / 35.04 | 28 / 0 / 22.07 | `/growth-technology#website-analytics` |

These are chosen for commercial relevance, existing demand signals and a credible service fit, not because they are easy wins. There are no query-filtered page rows in this export; destination mapping is a content/intent decision, not an observed attribution. The anchor is a section of the existing growth page, not a separately indexed landing page.

`website design harrisburg pa` (305 impressions, no clicks, position 44.97) supports the first query's intent naturally. It is not a third campaign. `web design mechanicsburg` is closer to page one at position 17 but has just 26 six-month impressions and no clicks, so its apparent proximity offers less evidence for the main effort. Generic `web development` has 1,587 impressions at 5.47 but no clicks and is less specific to qualified local inquiries.

## Changes in this branch

1. `/websites`: Harrisburg-focused title, description, H1 and introduction; concise local service explanation, written scope/handoff expectations, existing project links and an analytics cross-link. No fake office, client result or ranking promise.
2. `/growth-technology`: distinct analytics/growth metadata and an anchored service section describing Search Console, GA4, event validation, reporting, account ownership and limits. A phone-link tap is explicitly distinguished from a completed inquiry or sale. Existing broader growth services remain present.
3. Homepage: descriptive internal links to the two destinations. No menu expansion, dependency, tracking script or new location page.
4. Four narrowly mapped legacy GET URLs receive 301 redirects, including trailing-slash variants:

| Old URL | Destination | Last six-month page evidence |
| --- | --- | --- |
| `/services/web-development` | `/websites` | 151 impressions |
| `/services/digital-marketing` | `/growth-technology#services` | 73 impressions |
| `/pricing` | `/websites#starter` | 144 impressions, 1 click |
| `/contact` | `/about-community#contact` | 306 impressions, 2 clicks |

The inspected main code has no GET replacement for these paths; this is a code-level migration gap. Search retrieval for an older URL returned a historical cached version, so current production response status/deployment is not asserted. Existing contact POST behavior remains intact. Unknown retired URLs remain 404 rather than all redirecting to an unrelated page. The remaining historical guides/PDFs and other legacy routes need individual content/replacement decisions; this branch is not a complete site migration.

## Ninety-day plan

Top-three organic placement is the stretch objective, not a promised result. Six-month averages around 35–48 do not support a confident 90-day prediction. Evaluate qualified inquiries alongside visibility, and avoid buying links or publishing repetitive location pages.

- **Approval and deployment:** reconcile any pending template conflicts; deploy only after Andrew approves. Validate both canonical URLs, sitemap, relevant legacy redirects and indexing using URL Inspection. Request indexing for the two updated pages after they are live. A branch or PR does not change production.
- **First 7 days:** obtain a fresh complete daily export with exact dates. Filter each query separately, inspect Pages, then segment United States/mobile/desktop. Establish the most recent complete 28 days against the preceding 28 days. Check Pages indexing, user-declared/Google-selected canonical, manual actions and security notices; none are included in this attachment. Record form completions separately from button taps and test tracking without real inquiries.
- **Days 8–30:** verify discovery of the intended landing pages, redirect processing and title/snippet presentation. Check Google Business Profile service/site links and factual business details. Improve actual project documentation or request voluntary, honest client feedback when appropriate; do not invent local authority. No contact or public profile changes are performed by this branch.
- **Day 30 checkpoint:** November 22, 2026 if deployed October 23. Compare complete rolling 28-day windows and query families as well as exact phrases. With low volumes, report raw counts and avoid treating one click as proof of a trend. If the intended page is missing, fix indexing/canonical problems before adding copy.
- **Days 31–60:** use real query-to-page evidence to refine the weaker page once. If relevant impressions rise without clicks, review result wording and offer fit. If clicks rise without inquiries, inspect the mobile journey and form. Obtain real project evidence and relevant local mentions through legitimate relationships, with separate authorization for outreach.
- **Day 60 checkpoint:** December 22, 2026. Look for repeated page-one visibility and qualified traffic. If the pages still sit beyond position 20, investigate intent, competitive strength and verified local authority; do not prescribe keyword repetition as the fix.
- **Day 90 checkpoint:** January 21, 2027. Report each query's complete 28-day clicks, impressions, CTR, average position, landing-page ownership, device mix and qualified inquiries against baseline. Record whether top-three appearances are consistent, occasional or absent. Decide what to continue based on those results. If deployment happens later, move these checkpoints accordingly.

This plan does not create a new automation or assert future work has already run.

## Validation and integration limits

- 19 targeted Python tests passed: redirect destinations and trailing slashes, unknown 404 behavior, unchanged contact POST rejection, metadata/canonicals, home, sitemap and existing mobile-navigation regressions.
- Ruff passed for changed Python files; whitespace checks passed. Existing home/browser expectations were updated for deliberate copy changes and existing cache-busted asset URLs. A broader lint invocation found an unrelated pre-existing import-format issue in main/routes.py; this branch does not edit that file.
- New Chromium checks passed at 390/412/1440px for affected page layout, mobile menu link taps, internal route/fragment targets, FAQ disclosure, analytics CTA and native required-field validation. Existing SEO browser suite passed at 393/412px, including metadata, shared navigation, list-tool interaction and tap/overflow checks.
- Selected desktop/mobile screenshots of both new sections were visually reviewed. Testing used viewport/touch emulation, not physical iPhone/Android devices. WebKit/Safari is untested because browser downloads failed in this environment. No production inquiries, analytics configuration or deployment performed.
- PR #15 also changes the three main-page templates; reconcile these intentional SEO headings, sections and links with that PR's demos during review. PR #14 and #9 are not included. Shared mobile-menu code and current blog/AI routes remain unchanged.

## Primary-source guidance

- Google on average position: https://support.google.com/webmasters/answer/7042828 — an average across observed appearances, not a universal current ranking.
- Google on URL migrations: https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes — relevant server-side permanent redirects and canonical/sitemap checks; avoid unrelated bulk redirects. Keep mapped redirects for at least a year, ideally indefinitely where useful.
