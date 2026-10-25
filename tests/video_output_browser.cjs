// Run against an isolated local Flask server; never a production endpoint.
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const {mkdtemp, rm} = require('node:fs/promises');
const {tmpdir} = require('node:os');
const path = require('node:path');
const {chromium} = require('playwright');
const base = process.env.TOOL_BASE_URL || 'http://127.0.0.1:5066';

(async () => {
  assert.ok(process.env.FFMPEG_BINARY, 'Set FFMPEG_BINARY to a local FFmpeg executable');
  const dir = await mkdtemp(path.join(tmpdir(), 'ad-output-preview-'));
  const input = path.join(dir, 'synthetic.mp4');
  execFileSync(process.env.FFMPEG_BINARY, ['-v', 'error', '-f', 'lavfi', '-i',
    'testsrc2=size=160x90:rate=12', '-t', '1', '-c:v', 'libx264', input]);
  const browser = await chromium.launch({headless: true,
    ...(process.env.CHROMIUM_PATH ? {executablePath: process.env.CHROMIUM_PATH} : {})});
  try {
    const page = await browser.newPage({viewport: {width: 390, height: 844}});
    const posts = [], errors = [];
    page.on('request', request => { if (request.method() === 'POST') posts.push(request.url()); });
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`${base}/tools/video-converter`);
    await page.locator('#video-file').setInputFiles(input);
    await page.locator('#processing-mode').selectOption('server');
    assert.equal(posts.length, 0);
    assert.equal(await page.locator('#convert').isDisabled(), true);
    await page.locator('#upload-consent').check();
    await page.locator('#convert').click();
    await page.locator('#result').waitFor({state: 'visible'});
    assert.equal(posts.length, 1);
    assert.equal(await page.locator('#output-video').isVisible(), true);
    assert.equal(await page.locator('#output-audio').isVisible(), false);
    assert.equal(await page.locator('#output-video').getAttribute('src'),
      await page.locator('#download').getAttribute('href'));
    await page.waitForFunction(() => document.querySelector('#output-video').readyState >= 1);
    assert.equal(await page.locator('#output-video').evaluate(video => video.videoWidth), 160);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.locator('#clear').click();
    assert.equal(await page.locator('#output-video').getAttribute('src'), null);
    assert.equal(await page.locator('#result').isVisible(), false);
    assert.deepEqual(errors, []);
    console.log('Synthetic server video: explicit consent, actual output playback, matching download, mobile overflow and clearing media source passed');
  } finally { await browser.close(); await rm(dir, {recursive: true, force: true}); }
})().catch(error => { console.error(error); process.exitCode = 1; });
