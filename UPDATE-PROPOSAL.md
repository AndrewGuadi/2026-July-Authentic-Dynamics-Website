# Proposed update — October 20, 2026

## Homepage depth and motion

Status: proposal for Andrew's review; visual changes are not implemented in this PR.

The homepage already uses hover zoom on project and industry images. Add restrained
scroll depth to its existing hero imagery to make the opening feel more polished
without adding another section or distracting from the inquiry buttons.

### Scope

- Apply a maximum 12 px vertical parallax offset to the hero photo group on desktop.
  Keep text, navigation, and calls to action stationary.
- Use existing images and the ink, paper, and lime palette. No additional video,
  image downloads, animation framework, or full-page background effect.
- Add a brief, subtle opacity transition when switching industry panels, without
  delaying content, shifting layout, or disrupting keyboard tab selection.
- Disable parallax on touch devices, narrow viewports, and when reduced motion is
  requested. Keep all content visible if JavaScript or animation support fails.

### Implementation approach

Use a separate homepage motion module. Update transforms in a single scheduled
animation frame only when the hero is visible and scrolling changes its position.
Stop work when the document is hidden. Reset transforms and remove active animation
work when viewport or motion preferences change. Apply depth to a wrapper so it
does not overwrite existing image hover transforms.

### Acceptance checks before implementation is offered for merge

- Compare the initial screen before and after: copy and inquiry buttons remain
  equally visible; no new layout shift or horizontal overflow.
- Check desktop plus 390 px and 360 px mobile viewports, keyboard navigation,
  industry tabs, tool dialogs, and contact links. Do not send real inquiries.
- Confirm reduced motion both at page load and when changed while the page is open.
- Confirm the page remains readable with JavaScript disabled.
- Inspect runtime errors and scrolling performance; verify no animation loop keeps
  running offscreen or while idle. Check Chromium and WebKit where available and
  report viewport emulation separately from physical-device tests.

This update aims for a more deliberate first impression. Conversion improvement
is a hypothesis to evaluate with usage data, not a promised outcome.

## Existing work

PR #9 (event break-even calculator) remains separate. Its sitemap addition must be
reconciled with main's newer decision to exclude public tools from sitemap discovery.
This proposal does not require changing crawler policy or that pending tool.
