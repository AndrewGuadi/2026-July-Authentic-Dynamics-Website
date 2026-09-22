const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {chromium} = require('playwright');

(async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'video-modes-'));
  const input = path.join(dir, 'private-name.mp4');
  const long = path.join(dir, 'long.mp4');
  const tooLong = path.join(dir, 'too-long.mp4');
  execFileSync(require('ffmpeg-static'), ['-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=24', '-t', '1', '-c:v', 'libx264', input]);
  for (const [seconds, dest] of [[61, long], [181, tooLong]]) {
    execFileSync(require('ffmpeg-static'), ['-v', 'error', '-f', 'lavfi', '-i', 'color=black:size=32x32:rate=1',
      '-t', String(seconds), '-c:v', 'libx264', dest]);
  }
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage();
    const posts = [], errors = [];
    page.on('request', request => { if (request.method() === 'POST') posts.push(request.url()); });
    page.on('pageerror', error => errors.push(error.message));
    await page.goto((process.env.VIDEO_BASE_URL || 'http://127.0.0.1:5057') + '/tools/video-converter');
    assert.equal(await page.locator('#processing-mode').inputValue(), 'browser');
    await page.locator('#video-file').setInputFiles(input);
    await page.locator('#processing-mode').selectOption('server');
    assert.equal(posts.length, 0);
    assert.ok(await page.locator('#convert').isDisabled());
    await page.locator('#upload-consent').check();
    await page.locator('#convert').click();
    await page.waitForFunction(() => !document.querySelector('#result').hidden);
    assert.equal(posts.length, 1);
    assert.ok(posts[0].endsWith('/tools/video-converter/convert'));
    assert.match(await page.locator('#status').innerText(), /Server conversion complete/);
    const downloaded = page.waitForEvent('download');
    await page.locator('#download').click();
    const download = await downloaded;
    assert.ok((await fs.stat(await download.path())).size > 0);
    await page.locator('#processing-mode').selectOption('browser');
    await page.locator('#video-file').setInputFiles(long);
    await page.waitForFunction(() => document.querySelector('#preview').duration > 60);
    assert.ok(await page.locator('#browser-limit-warning').isVisible());
    assert.ok(await page.locator('#convert').isDisabled());
    const probedLimit = await page.evaluate(async () => {
      const {convertVideo} = await import('/static/tools/video-converter/conversion-service.js');
      const job = convertVideo({file: document.querySelector('#video-file').files[0],
        options: {format: 'mp4', quality: 'balanced', resolution: 'original', fps: 'original', audio: 'keep'},
        maxSeconds: 60, onUpdate() {}});
      try { await job.promise; return 'unexpected success'; } catch (error) { return error.message; }
    });
    assert.equal(probedLimit, 'duration');
    await page.locator('#processing-mode').selectOption('server');
    await page.locator('#upload-consent').check();
    assert.ok(await page.locator('#convert').isEnabled());
    await page.locator('#video-file').setInputFiles(tooLong);
    await page.waitForFunction(() => document.querySelector('#preview').duration > 180);
    assert.ok(await page.locator('#server-size-warning').isVisible());
    assert.ok(await page.locator('#convert').isDisabled());
    await page.locator('#video-file').setInputFiles(input);
    await page.locator('#upload-consent').check();
    await page.locator('#processing-mode').selectOption('browser');
    assert.ok(await page.locator('#result').isHidden());
    await page.locator('#convert').click();
    await page.waitForFunction(() => !document.querySelector('#result').hidden, null, {timeout: 60000});
    assert.match(await page.locator('#status').innerText(), /never uploaded/);
    assert.equal(posts.length, 1);
    const limitError = await page.evaluate(async () => {
      const {convertVideo} = await import('/static/tools/video-converter/conversion-service.js');
      const job = convertVideo({file: document.querySelector('#video-file').files[0],
        options: {format: 'mp4', quality: 'balanced', resolution: 'original', fps: 'original', audio: 'keep'},
        maxSeconds: 0.001, onUpdate() {}});
      try { await job.promise; return 'unexpected success'; } catch (error) { return error.message; }
    });
    assert.equal(limitError, 'limit');
    await page.evaluate(() => {
      const input = document.querySelector('#video-file');
      const selected = new DataTransfer();
      selected.items.add(new File([new Uint8Array(64 * 1048576 + 1)], 'over-limit.mov',
        {type: 'video/quicktime'}));
      input.files = selected.files;
      input.dispatchEvent(new Event('change'));
    });
    assert.ok(await page.locator('#browser-limit-warning').isVisible());
    assert.ok(await page.locator('#convert').isDisabled());
    await page.locator('#processing-mode').selectOption('server');
    assert.ok(await page.locator('#convert').isDisabled());
    await page.setViewportSize({width: 375, height: 812});
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert.deepEqual(errors, []);
    console.log('PASS: real server and browser conversion, explicit consent, download, local 60-second and server three-minute limits, no automatic uploads, consent reset and mobile layout.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
