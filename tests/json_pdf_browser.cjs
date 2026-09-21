const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const base = process.env.JSON_BASE_URL || 'http://127.0.0.1:5056';
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    const errors = [], posts = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => { if (request.method() === 'POST') posts.push(request.url()); });
    await page.goto(`${base}/tools/json-converter`);
    await page.locator('#output-format').selectOption('pdf');
    assert.equal(await page.locator('[data-xlsx-options]').isHidden(), true);
    assert.equal(await page.locator('[data-pdf-options]').isVisible(), true);
    await page.locator('[data-pdf-sample]').click();
    assert.match(await page.locator('#json-text').inputValue(), /Maya/);
    const panel = page.locator('#json-pdf-preview');
    const status = page.locator('.tool-status');
    async function preview() {
      const waiting = page.waitForResponse(response => response.url() === `${base}/tools/json-converter`
        && response.request().method() === 'POST');
      await page.locator('button[value="pdf_preview"]').click();
      const response = await waiting;
      assert.equal(response.status(), 200);
      const result = await response.json();
      await panel.waitFor({ state: 'visible' });
      await page.waitForFunction(() => {
        const image = document.querySelector('[data-pdf-image]');
        return image.complete && image.naturalWidth > 0;
      });
      assert.match(await status.textContent(), /PDF ready/);
      return result;
    }
    await page.locator('#pdf-long-cells').selectOption('appendix');
    const result = await preview();
    assert.ok(result.summary.page_count >= 2);
    assert.equal(result.summary.appendix_values, 1);
    const beforeDownload = posts.length;
    const waiting = page.waitForEvent('download');
    await page.locator('button[type="submit"]:not([name="action"])').click();
    const download = await waiting;
    assert.equal(download.suggestedFilename(), 'converted.pdf');
    assert.deepEqual(await fs.readFile(await download.path()), Buffer.from(result.pdf, 'base64'));
    assert.equal(posts.length, beforeDownload, 'Downloading the reviewed PDF must not regenerate it');
    const nextResponse = page.waitForResponse(response => response.url().endsWith('/pdf-page'));
    await page.locator('[data-pdf-next]').click();
    assert.equal((await nextResponse).status(), 200);
    await page.waitForFunction(() => document.querySelector('[data-pdf-page-status]').textContent.startsWith('Page 2'));
    assert.match(await page.locator('[data-pdf-image]').getAttribute('alt'), /Page 2/);

    await page.locator('#pdf-font-size').selectOption('12');
    assert.equal(await panel.isHidden(), true);
    await page.locator('[data-pdf-columns-load]').click();
    await page.locator('[data-pdf-columns] input').first().waitFor();
    await page.getByRole('button', { name: 'Move notes up', exact: true }).click();
    await page.locator('[data-pdf-columns] input[data-key="customer"]').uncheck();
    assert.deepEqual(JSON.parse(await page.locator('input[name="pdf_columns"]').inputValue()), ['order', 'notes', 'details']);
    await page.locator('#pdf-orientation').selectOption('landscape');
    const selected = await preview();
    assert.equal(selected.summary.orientation, 'landscape');
    assert.equal(selected.summary.font_size, 12);
    assert.equal(selected.summary.column_count, 3);

    await page.locator('#pdf-long-cells').selectOption('shorten');
    const shortened = await preview();
    assert.equal(shortened.summary.shortened_cells, 1);
    assert.match(await page.locator('[data-pdf-warnings]').textContent(), /incomplete/);

    await page.locator('#json-text').fill(JSON.stringify(Object.fromEntries(
      Array.from({ length: 15 }, (_, index) => [`Field${index}`, `Value${index}`])
    )));
    await page.locator('button[value="pdf_preview"]').click();
    await page.waitForFunction(() => document.querySelector('.tool-status').textContent.includes('1–12 columns'));
    assert.equal(await panel.isHidden(), true);
    await page.locator('[data-pdf-columns-load]').click();
    await page.waitForFunction(() => document.querySelectorAll('[data-pdf-columns] input').length === 15);
    for (let index = 3; index < 15; index += 1) {
      await page.locator(`[data-pdf-columns] input[data-key="Field${index}"]`).uncheck();
    }
    assert.equal((await preview()).summary.column_count, 3);

    await page.locator('#json-text').fill('');
    await page.locator('#tool-file').setInputFiles({ name: 'uploaded.json', mimeType: 'application/json',
      buffer: Buffer.from(JSON.stringify([{ id: '001', body: 'Long content '.repeat(3000) }])) });
    await page.locator('#pdf-long-cells').selectOption('wrap');
    await page.locator('#pdf-font-size').selectOption('10');
    const long = await preview();
    assert.ok(long.summary.page_count > 1);
    assert.equal(long.filename, 'uploaded.pdf');
    assert.equal(long.summary.shortened_cells, 0);

    // Changes during an in-flight PDF request must discard its response.
    await page.locator('#tool-file').setInputFiles([]);
    await page.locator('#json-text').fill('{"field":"original"}');
    let release, started;
    const gate = new Promise(resolve => { release = resolve; });
    const intercepted = new Promise(resolve => { started = resolve; });
    await page.route('**/tools/json-converter', async route => {
      const response = await route.fetch(); started(); await gate; await route.fulfill({ response });
    });
    await page.locator('button[value="pdf_preview"]').click();
    await intercepted;
    await page.locator('#json-text').fill('{"field":"updated"}');
    release();
    await page.waitForFunction(() => document.querySelector('.tool-status').textContent.includes('Your input changed'));
    assert.equal(await panel.isHidden(), true);
    await page.unroute('**/tools/json-converter');

    await page.setViewportSize({ width: 390, height: 844 });
    await preview();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await panel.screenshot({ path: '/tmp/json-pdf-mobile.png' });
    await page.locator('#output-format').selectOption('xlsx');
    assert.equal(await panel.isHidden(), true);
    assert.equal(await page.locator('[data-pdf-options]').isHidden(), true);
    assert.deepEqual(errors, []);
    console.log('PDF browser checks passed: actual preview pages, identical download bytes, column selection/order, large cells, stale responses, and mobile layout.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
