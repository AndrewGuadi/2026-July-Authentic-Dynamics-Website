// Run against a local Flask server. Native FFmpeg independently verifies browser outputs.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const playwright = require('playwright');
const ffmpeg = process.env.FFMPEG_BINARY || require('ffmpeg-static');
const base = process.env.VIDEO_BASE_URL || 'http://127.0.0.1:5056';
const native = args => execFileSync(ffmpeg, ['-hide_banner', '-y', ...args], {encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe']});

(async () => {
  const temp = await fs.mkdtemp(path.join(os.tmpdir(), 'ad-video-test-'));
  function fixture(name, dimensions, audio = true, duration = '1') {
    const dest = path.join(temp, name);
    native(['-f', 'lavfi', '-i', `testsrc2=size=${dimensions}:rate=24`, ...(audio ? ['-f', 'lavfi', '-i', 'sine=frequency=440'] : []), '-t', duration,
      '-c:v', name.endsWith('webm') ? 'libvpx-vp9' : 'libx264', '-threads', '1', ...(audio ? ['-c:a', name.endsWith('webm') ? 'libopus' : 'aac'] : []), dest]);
    return dest;
  }
  const small = fixture('private-small.mp4', '320x180');
  const webm = fixture('private-input.webm', '640x360');
  const mov = fixture('private-portrait.mov', '720x1280');
  const silent = fixture('private-silent.mp4', '1280x720', false);
  const hd = fixture('private-hd.mp4', '1920x1080');
  const medium = fixture('private-medium.mp4', '1280x720', true, '12');
  const shortMedium = fixture('private-compatibility.mp4', '1280x720', true, '3');
  const browsers = (process.env.VIDEO_BROWSERS || 'chromium').split(',');
  for (const name of browsers) {
    const browser = await playwright[name].launch({headless: true});
    try {
      const page = await browser.newPage({viewport: {width: 1400, height: 950}});
      const requests = [], errors = [];
      page.on('request', r => requests.push({url: r.url(), method: r.method(), body: r.postData()}));
      page.on('pageerror', e => errors.push(e.message));
      await page.goto(base + '/tools/video-converter');
      await page.waitForFunction(() => document.querySelector('#preset-note').textContent.length > 0);
      assert.ok(!requests.some(r => r.url.includes('ffmpeg-core')));
      async function select(input) {
        await page.locator('#video-file').setInputFiles(input);
        await page.waitForFunction(() => !document.querySelector('#convert').disabled);
      }
      async function convert(format = 'mp4', intent = 'custom', resolution = 'original', quality = 'balanced', fps = 'original') {
        console.log(`${name}: testing ${format}, ${intent}, ${resolution}, ${quality}`);
        await page.locator('#intent').selectOption(intent);
        await page.locator('#settings details').evaluate(d => { d.open = true; });
        await page.locator(intent === 'extract' ? '#audio-format' : '#format').selectOption(format);
        if (intent !== 'extract') await page.locator('#resolution').selectOption(resolution);
        if (intent !== 'extract') await page.locator('#fps').selectOption(fps);
        await page.locator('#quality').selectOption(quality);
        await page.locator('#convert').click();
        const statusTimer = setInterval(async () => console.log(await page.locator('#status').innerText().catch(() => 'Page closed')), 20000);
        try {
          await page.waitForFunction(() => !document.querySelector('#result').hidden || document.querySelector('#status').classList.contains('is-error'), null, {timeout: 300000});
        } catch (error) {
          console.error('Conversion status:', await page.locator('#status').innerText());
          throw error;
        } finally {
          clearInterval(statusTimer);
        }
        assert.match(await page.locator('#status').innerText(), /Conversion complete/);
        const waiting = page.waitForEvent('download');
        await page.locator('#download').click();
        const download = await waiting;
        const dest = path.join(temp, `${name}-${Date.now()}.${format}`);
        await download.saveAs(dest);
        assert.ok((await fs.stat(dest)).size > 0);
        // Decode complete output independently; catch malformed media and wrong codecs/dimensions.
        const inspection = execFileSync(ffmpeg, ['-hide_banner', '-i', dest, '-f', 'null', '-'], {encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe']});
        void inspection;
        let info;
        try { native(['-i', dest]); } catch (error) { info = error.stderr.toString(); }
        return {dest, info};
      }
      await select(small);
      await page.locator('#video-file').evaluate(input => {
        const transfer = new DataTransfer(); transfer.items.add(input.files[0]);
        document.querySelector('#drop-zone').dispatchEvent(new DragEvent('drop', {dataTransfer: transfer, bubbles: true, cancelable: true}));
      });
      assert.match(await page.locator('#file-info').innerText(), /private-small.mp4/);
      assert.ok(!requests.some(r => r.url.includes('ffmpeg-core')));
      let out = await convert();
      assert.match(out.info, /Video: h264/); assert.match(out.info, /Audio: aac/); assert.match(out.info, /320x180/);
      out = await convert('webm', 'silent');
      assert.match(out.info, /Video: vp8/);
      out = await convert('webm'); assert.match(out.info, /Audio: opus/);
      out = await convert('mp3', 'extract'); assert.match(out.info, /Audio: mp3/);
      out = await convert('wav', 'extract'); assert.match(out.info, /Audio: pcm_s16le/);
      for (const fps of ['24', '30', '60']) {
        out = await convert('mp4', 'custom', 'original', 'balanced', fps);
        assert.match(out.info, new RegExp(`${fps} fps`));
      }
      await select(webm); out = await convert('mp4'); assert.match(out.info, /Video: h264/);
      await select(mov); out = await convert('mp4', 'resize', '480'); assert.match(out.info, /480x85[24]/);
      await select(silent); out = await convert('mp4', 'website', '1080'); assert.doesNotMatch(out.info, /Audio:/); assert.match(out.info, /1280x720/);
      await page.locator('#intent').selectOption('extract');
      await page.locator('#convert').click();
      await page.waitForFunction(() => document.querySelector('#status').classList.contains('is-error'));
      assert.match(await page.locator('#status').innerText(), /audio track/);
      await select(hd); out = await convert('mp4', 'silent', '720'); assert.doesNotMatch(out.info, /Audio:/); assert.match(out.info, /1280x720/);
      // Chromium covers the longer fixture; other engines exercise the same settings
      // on a shorter clip because single-threaded WASM throughput varies greatly.
      await select(name === 'chromium' ? medium : shortMedium);
      const higher = await convert('mp4', 'custom', '480', 'higher');
      const smaller = await convert('mp4', 'custom', '480', 'smaller');
      assert.ok((await fs.stat(smaller.dest)).size < (await fs.stat(higher.dest)).size);
      await page.locator('#fps').selectOption('30'); await page.locator('#convert').click();
      await page.locator('#cancel').click();
      await page.waitForFunction(() => document.querySelector('#status').textContent.includes('cancelled'));
      out = await convert(); assert.match(out.info, /Video: h264/);
      await select({name: 'private-corrupt.mp4', mimeType: 'video/mp4', buffer: Buffer.from('not a video')});
      await page.locator('#convert').click();
      await page.waitForFunction(() => document.querySelector('#status').classList.contains('is-error'));
      await page.locator('#video-file').setInputFiles({name: 'no.txt', mimeType: 'text/plain', buffer: Buffer.from('not video')});
      assert.ok(await page.locator('#convert').isDisabled());
      // A sparse browser File exercises size warning without a 200 MB disk fixture.
      await page.evaluate(() => {
        const dt = new DataTransfer(); dt.items.add(new File([new Uint8Array(200 * 1048576)], 'large.mp4', {type: 'video/mp4'}));
        const input = document.querySelector('#video-file'); input.files = dt.files; input.dispatchEvent(new Event('change'));
      });
      assert.ok(await page.locator('#large-warning').isVisible()); assert.ok(await page.locator('#convert').isDisabled());
      await page.locator('#large-confirm').check(); assert.ok(await page.locator('#convert').isEnabled());
      await page.locator('#clear').click();
      await select(small); await convert();
      await page.evaluate(() => { document.activeElement.blur(); window.scrollTo(0, 0); });
      await page.screenshot({path: path.join(temp, `${name}-desktop.png`), fullPage: true});
      await page.setViewportSize({width: 375, height: 812});
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.evaluate(() => { document.activeElement.blur(); window.scrollTo(0, 0); });
      await page.screenshot({path: path.join(temp, `${name}-mobile.png`), fullPage: true});
      const network = requests.filter(r => /^https?:/.test(r.url));
      assert.ok(network.every(r => r.method === 'GET' && !r.body && new URL(r.url).origin === base));
      assert.ok(network.every(r => !r.url.includes('private-')));
      assert.ok(network.some(r => r.url.endsWith('ffmpeg-core.wasm')));
      assert.deepEqual(errors, []);
      // Missing APIs and worker load failure degrade gracefully, with no upload fallback.
      const unsupported = await browser.newPage();
      await unsupported.addInitScript(() => { window.Worker = undefined; });
      await unsupported.goto(base + '/tools/video-converter');
      await unsupported.waitForFunction(() => document.querySelector('#status').textContent.includes('WebAssembly and Web Workers'));
      assert.ok(await unsupported.locator('#video-file').isDisabled());
      await unsupported.close();
      await page.route('**/video-worker.js', route => route.abort());
      await page.locator('#convert').click();
      await page.waitForFunction(() => document.querySelector('#status').classList.contains('is-error'));
      assert.ok(await page.locator('#convert').isEnabled());
      console.log(`${name}: real conversions, output decoding, resize, quality, audio, cancellation/retry, errors, warning, mobile and privacy passed. ${network.length} same-origin GETs; zero uploads/POSTs/external processing.`);
    } finally { await browser.close(); }
  }
  console.log(`Fixtures, downloads and screenshots: ${temp}`);
})().catch(error => { console.error(error); process.exitCode = 1; });
