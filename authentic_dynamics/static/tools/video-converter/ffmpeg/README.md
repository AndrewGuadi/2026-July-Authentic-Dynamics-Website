# Vendored conversion engine

Unmodified ESM assets from `@ffmpeg/core@0.12.10` (single thread), authored by
Jerome Wu and the FFmpeg.wasm contributors. Runtime requests are same-origin.
No CDN, npm installation, Node runtime, or native FFmpeg is needed in production.

- Package: https://registry.npmjs.org/@ffmpeg/core/-/core-0.12.10.tgz
- Project and build sources: https://github.com/ffmpegwasm/ffmpeg.wasm
- Core build instructions: https://ffmpegwasm.netlify.app/docs/contribution/core/
- License: GPL-2.0-or-later; see `LICENSE`. The compiled engine includes FFmpeg
  and its codec libraries; it is not covered by the wrapper's MIT license.
- npm integrity: `sha512-dzNplnn2Nxle2c2i2rrDhqcB19q9cglCkWnoMTDN9Q9l3PvdjZWd1HfSPjCNWc/p8Q3CT+Es9fWOR0UhAeYQZA==`

SHA-256 checksums:

```text
67a48f11645f85439f3fde4f2119042c16b374b910206b7a7a24f342e28dcae3  ffmpeg-core.js
9f57947a5bd530d8f00c5b3f2cb2a3492faa7e5d823315342d6a8656d0a6b7b7  ffmpeg-core.wasm
```

To update, install an explicitly pinned `@ffmpeg/core` in a temporary directory,
copy its `dist/esm/ffmpeg-core.js` and `.wasm` here, update provenance/checksums,
and run the browser conversion matrix. Keep the files together and serve `.wasm`
as `application/wasm`. Preserve license notices and corresponding-source access
when redistributing the GPL engine.
