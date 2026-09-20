const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [], requests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => requests.push({ url: request.url(), method: request.method() }));
    await page.goto(`${process.env.QR_BASE_URL || 'http://127.0.0.1:5055'}/tools/qr-code-maker`);
    await page.addScriptTag({ path: require.resolve('jsqr') });
    await page.waitForFunction(() => document.getElementById('qr-url'));
    const input = page.locator('#qr-url');
    const pngButton = page.locator('[data-download="png"]');
    assert.equal(await pngButton.isDisabled(), true);
    const url = 'https://example.org/menu?campaign=central-pa&item=coffee#today';
    await input.fill(url);
    await page.waitForFunction(() => !document.querySelector('[data-download="png"]').disabled);
    await page.locator('#qr-business').fill('Central PA Coffee & Co.');
    async function decodeCanvas() {
      return page.locator('#qr-artwork').evaluate(canvas => {
        const ctx = canvas.getContext('2d'), image = ctx.getImageData(0, 0, canvas.width, canvas.height);
        return window.jsQR(image.data, canvas.width, canvas.height)?.data;
      });
    }
    async function saveDownload(kind) {
      const waiting = page.waitForEvent('download');
      await page.locator(`[data-download="${kind}"]`).click();
      const download = await waiting;
      return fs.readFile(await download.path());
    }
    // Independent decoder validates every artwork layout rather than its appearance alone.
    for (const layout of ['counter', 'window', 'insert', 'social', 'plain']) {
      await page.locator('#qr-layout').selectOption(layout);
      assert.equal(await decodeCanvas(), url, layout);
    }
    const svg = (await saveDownload('svg')).toString();
    assert.ok(svg.startsWith('<svg'));
    assert.ok(!/script|href|https?:\/\/(?!www.w3.org)/.test(svg));
    for (const size of ['512', '1024', '2048']) {
      await page.locator('#qr-size').selectOption(size);
      const png = await saveDownload('png');
      assert.equal(png.readUInt32BE(16), Number(size));
      assert.equal(png.readUInt32BE(20), Number(size));
      const decoded = await page.evaluate(async base64 => {
        const img = new Image(); img.src = `data:image/png;base64,${base64}`; await img.decode();
        const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
        const ctx = c.getContext('2d'); ctx.drawImage(img, 0, 0);
        return window.jsQR(ctx.getImageData(0, 0, c.width, c.height).data, c.width, c.height)?.data;
      }, png.toString('base64'));
      assert.equal(decoded, url);
    }
    await page.locator('#qr-layout').selectOption('counter');
    const logo = await saveDownload('png');
    await page.locator('#qr-logo').setInputFiles({ name: 'logo.png', mimeType: 'image/png', buffer: logo });
    await page.waitForFunction(() => document.getElementById('qr-logo-status').textContent === 'Logo added locally.');
    await page.locator('#qr-remove-logo').click();
    assert.equal(await page.locator('#qr-remove-logo').isHidden(), true);
    const pdf = await saveDownload('pdf');
    assert.equal(pdf.subarray(0, 5).toString(), '%PDF-');
    const mediaBox = pdf.toString('latin1').match(/\/MediaBox\s*\[([^\]]+)\]/);
    assert.deepEqual(mediaBox[1].trim().split(/\s+/).map(Number), [0, 0, 612, 792]);
    const art = await saveDownload('artwork');
    assert.equal(art.readUInt32BE(16), 1500);
    await page.evaluate(() => { window.print = () => { window.printed = true; }; });
    await page.locator('[data-download="print"]').click();
    await page.waitForFunction(() => window.printed === true);
    assert.equal(await page.evaluate(() => window.printed), true);
    await page.emulateMedia({ media: 'print' });
    assert.equal(await page.locator('#qr-print').evaluate(el => getComputedStyle(el).display), 'flex');
    assert.equal(await page.locator('#main').isVisible(), false);
    await page.emulateMedia({ media: 'screen' });
    for (const invalid of ['javascript:alert(1)', 'https://name:pass@example.org', 'https://', 'https://example.org/a b']) {
      await input.fill(invalid);
      assert.equal(await pngButton.isDisabled(), true, invalid);
      assert.equal(await page.locator('#qr-artwork').isHidden(), true);
      assert.equal(await page.locator('#qr-test').getAttribute('href'), null);
    }
    await input.fill('https://例え.jp/珈琲?x=é');
    await page.locator('#qr-layout').selectOption('plain');
    assert.equal(await decodeCanvas(), new URL('https://例え.jp/珈琲?x=é').href);
    await page.locator('#qr-level').selectOption('H');
    assert.equal(await decodeCanvas(), new URL('https://例え.jp/珈琲?x=é').href);
    await page.locator('#qr-foreground').fill('#ffffff');
    assert.equal(await pngButton.isDisabled(), true);
    await page.locator('#qr-foreground').fill('#172c28');
    await input.fill('https://example.org/' + 'a'.repeat(1790));
    assert.equal(await pngButton.isDisabled(), true);
    await input.fill(url);
    await page.locator('#qr-purpose').selectOption('menu');
    assert.equal(await page.locator('#qr-headline').inputValue(), 'Find your next favorite.');
    assert.equal(await page.locator('#qr-review-help').isHidden(), true);
    await page.locator('#qr-layout').selectOption('counter');
    await page.evaluate(() => { document.activeElement.blur(); window.scrollTo({ top: 0, behavior: 'instant' }); });
    await page.screenshot({ path: '/tmp/qr-desktop.png', fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.screenshot({ path: '/tmp/qr-mobile.png', fullPage: true });
    assert.deepEqual(errors, []);
    const network = requests.filter(request => /^https?:/.test(request.url));
    assert.ok(network.every(request => request.method === 'GET' && request.url.startsWith(process.env.QR_BASE_URL || 'http://127.0.0.1:5055')), JSON.stringify(network));
    assert.equal(await page.evaluate(() => localStorage.length), 0);
    await page.reload();
    assert.equal(await input.inputValue(), '');
    console.log('QR browser checks passed: independent decoding, all layouts, exports, validation, logos, print, mobile, privacy.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
