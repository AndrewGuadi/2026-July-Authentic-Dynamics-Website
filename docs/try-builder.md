# Try Builder showroom

Entry: `/try-builder`, with a shared main navigation link. Preview: `/try-builder/preview#<catalog-id>` opens in a new tab with `noopener noreferrer`. Business details are never put in a URL or submitted to Flask. The catalog and original design snapshots are served locally.

## Included

- 50 distinct template snapshots, five in each of ten business categories. Adjacent foundations are labeled **Adaptable foundation**. These are original source designs, not fifty finished industry-specific websites.
- Optional business name, town/service area, headline, phone, email and brand color. The supplied values appear in a preview identity strip, supported brand/contact text is replaced, and a supplied headline replaces the first H1. Other sample claims, prices, locations and reviews remain illustrative.
- New-tab preview with accent color, type choice, responsive width, saved Uiverse button style, save combination and reset controls.
- 48 Uiverse components across eight categories. Live isolated previews, original creator links, category filtering and browser favorites. Saved button designs can replace a supported first CTA through an isolated shadow root; layouts without a supported target explain the limitation.
- Local storage key `ad-showroom-v1`: profile, industry, favorites and combinations. Explicit clear control. Storage errors produce an explanation and leave exploration available. Normal browsing needs no email or account.

## Sources and notices

`static/builder/catalog.json` records pinned commit URLs, provider, industry and adaptation status. The shipped foundations are from `ColorlibHQ/bootstrap-templates` (uiCookies) and `mmrahmanbappi/100-free-html-templates`, both with MIT notices included as `LICENSE.txt` beside each snapshot. Some uiCookies foundations use Bootstrap 6 alpha and are design demonstrations, not a production dependency for the main AD site.

Uiverse components are from `uiverse-io/galaxy` commit `adbd2adde0a299a3956ea288fb444ec01891ca41`. Original creator comments are preserved; `UIVERSE-LICENSE.txt` contains the upstream notice. `components.json` records original author links. Standalone site templates from uiCookies under redistribution-restricted terms are not bundled. UIUXLabz repositories examined during discovery did not include individual MIT license files, so their code was not included.

Bundled uiCookies demo photographs were replaced with original SVG illustration placeholders after automatic upload review blocked unverified image payloads. No rejected photograph is referenced by this branch. Remote photographs already referenced by the single-file templates may still load. Fonts and vendor assets retain their own terms. These previews are not a ready-to-redistribute download product. Before adding downloads, audit every asset and remove or replace demonstration photography as necessary. README and pinned source URLs support that next review.

## Preview isolation

Upstream JavaScript and inline event handlers are removed from snapshots. The renderer removes embedded frames, executable elements and handlers again, neutralizes navigation and forms, and adds a restrictive CSP. Iframes permit same-origin DOM access by the trusted parent for personalization but do **not** permit scripts, forms, popups or top navigation. No user HTML is accepted; profile values enter via textContent. Remote fonts/images may load, with no-referrer policy. Snapshot CSPs also disable script execution and form delivery when files are opened directly. UI selection is deliberate; no arbitrary uploaded or fetched HTML is supported.

## Deferred

Accounts, email capture/delivery, downloadable personalized sites, Stripe, dashboards, arbitrary command interpretation, full component/page interchange, and Figma generation. No new migrations, credentials, background workers or dependencies are required by this feature.

## Verification

`python -m pytest tests/test_builder.py tests/test_home.py -q`

`node tests/builder_browser.cjs` with Flask on `127.0.0.1:5055` and Playwright Chromium installed. Covers the ten category counts, new-tab flow, HTML-like profile text rendered safely, persistence, saved components, customization and mobile overflow.
