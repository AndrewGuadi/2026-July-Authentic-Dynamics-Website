# Uiverse interactions

Four MIT-licensed components are adapted to Authentic Dynamics' ink, paper and
lime palette. Styles are local and opt-in; no React, Tailwind runtime, network
requests, accounts, storage or additional dependencies are introduced.

## Component map

| Source | Actual placement | Adaptation |
| --- | --- | --- |
| [Alexruix input](https://uiverse.io/alexruix/jolly-emu-80) | Home/about inquiry fields, homepage planner/calculator fields, showcase sample input | Border/background feedback; existing labels, native validation and error descriptions retained. Hidden fields and checklist checkboxes are excluded. |
| [Adamgiebl card](https://uiverse.io/adamgiebl/new-lionfish-4) | Three demonstration cards after Selected Work | Original gradient frame/inset panel construction in AD colors; AD adds hover/focus glow and a touch-accessible highlight toggle. No continuous animation. |
| [CSSButtons arrow](https://uiverse.io/cssbuttons-io/massive-mayfly-74) | Hero secondary action, hero project link, three free-tool launchers, dynamic industry tool/example actions | Visible outer border, expanding circle and arrow feedback; intrinsic sizing and wrapping replace fixed width. |
| [NathAd17 Explore](https://uiverse.io/nathAd17/heavy-warthog-57) | Shared header CTA, home hero primary CTA, shared interior-page CTA, contact submit, showcase planner launcher | Contained sweep and circular arrow rotation using existing CTA destinations and button semantics. |

The shared Jinja `action_content` macro and the dynamic industry-panel helper
keep labels and decorative, accessibility-hidden arrows consistent. CSS is in
`static/css/ui-components.css`; source notices ship in
`static/licenses/uiverse-components.txt`.

## Behavior and accessibility

- Hover and keyboard focus expose the button effects; touch users can operate every action normally.
- The showcase highlight has an `aria-pressed` toggle for tapping or keyboard activation. Its label stays constant. The sample field is outside any form and is not submitted or persisted.
- Reduced-motion preferences remove transitions and card lift while retaining visual state feedback. Forced-color styles keep control boundaries visible.
- Native form validation, error summaries, submission state, inquiry destinations, industry context and tool calculations are preserved.
- Without JavaScript, content and inquiry links/forms remain available. The showcase's JavaScript-only highlight control stays hidden; the existing interactive planning tools require JavaScript.

## Verification

Run the existing Python suite:

```bash
python -m pytest -q
```

With Playwright installed and Chromium available, run:

```bash
python scripts/test_ui_components.py
```

The runner starts an isolated, ephemeral local test app and never sends an
inquiry to the public website. `NODE_PATH` can identify an existing Playwright
installation; `CHROMIUM_PATH` can select a browser executable. Screenshots are
written to `/tmp/ad-ui-components` (`AD_UI_SCREENSHOTS` overrides it).

The browser suite covers widths 320, 390, 768, 1024 and 1440; public page loading,
horizontal overflow, keyboard focus, touch highlighting, dynamic industry
buttons, planner output, calculator output and server-side contact errors. It
also checks reduced-motion and JavaScript-disabled fallbacks. The existing
Coding Calendar CI workflow runs this suite alongside the full Python suite.
