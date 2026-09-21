const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const base = process.env.JSON_BASE_URL || 'http://127.0.0.1:5055';
  const input = JSON.stringify([{ id: '001', customer: { name: 'Maya' },
    items: [{ sku: 'A1', tags: ['red'] }, { sku: 'B4' }] }]);
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`${base}/tools/json-converter`);
    const text = page.locator('#json-text');
    const mode = page.locator('#nesting-mode');
    const preview = page.locator('[data-workbook-preview]');
    const previewButton = page.locator('button[value="preview"]');
    const downloadButton = page.locator('button[type="submit"]:not([name="action"])');
    const status = page.locator('.tool-status');
    async function previewSheets() {
      await previewButton.click();
      await preview.waitFor({ state: 'visible' });
      assert.match(await status.textContent(), /Preview ready/);
    }
    assert.equal(await mode.inputValue(), 'combined');
    await text.fill(input);
    for (const [value, count] of [['combined', 3], ['keep', 1], ['flatten', 1], ['related', 3]]) {
      await mode.selectOption(value);
      assert.equal(await preview.isHidden(), true);
      await previewSheets();
      assert.equal(await preview.locator('article').count(), count);
      assert.equal(await page.locator('#nesting-depth').isDisabled(), value === 'keep');
    }
    await mode.selectOption('combined');
    await page.locator('#nesting-depth').selectOption('1');
    await previewSheets();
    assert.equal(await preview.locator('article').count(), 2);
    assert.match(await preview.textContent(), /deeper/);
    await page.locator('#nesting-depth').selectOption('5');
    await previewSheets();
    const downloadWaiting = page.waitForEvent('download');
    await downloadButton.click();
    const download = await downloadWaiting;
    assert.equal(download.suggestedFilename(), 'converted.xlsx');
    assert.equal((await fs.readFile(await download.path())).subarray(0, 2).toString(), 'PK');
    await page.locator('#output-format').selectOption('csv');
    assert.equal(await page.locator('[data-xlsx-options]').isHidden(), true);
    assert.equal(await preview.isHidden(), true);
    assert.equal(await page.locator('.tool-download').isHidden(), true);
    const csvWaiting = page.waitForEvent('download');
    await downloadButton.click();
    const csv = await csvWaiting;
    assert.equal(csv.suggestedFilename(), 'converted.csv');
    assert.match(await fs.readFile(await csv.path(), 'utf8'), /customer,items/);

    await page.locator('#output-format').selectOption('xlsx');
    await text.fill('');
    await page.locator('#tool-file').setInputFiles({ name: 'orders.json',
      mimeType: 'application/json', buffer: Buffer.from(input) });
    await previewSheets();
    assert.equal(await preview.locator('article').count(), 3);
    await text.fill('{}');
    await previewButton.click();
    assert.match(await status.textContent(), /either a file or pasted/);
    await page.locator('#tool-file').setInputFiles([]);
    await text.fill('{broken');
    await previewButton.click();
    await page.waitForFunction(() => document.querySelector('.tool-status').textContent.includes('Invalid JSON'));
    assert.equal(await preview.isHidden(), true);

    await text.fill('{"<img src=x onerror=alert(1)>":[1]}');
    await previewSheets();
    assert.equal(await preview.locator('img').count(), 0);
    assert.match(await preview.textContent(), /<img/);

    // An old response must not restore a preview after the user changes their input.
    await text.fill(input);
    let release, intercepted;
    const gate = new Promise(resolve => { release = resolve; });
    const started = new Promise(resolve => { intercepted = resolve; });
    await page.route('**/tools/json-converter', async route => {
      const response = await route.fetch();
      intercepted();
      await gate;
      await route.fulfill({ response });
    });
    await previewButton.click();
    await started;
    await text.fill('{"new":true}');
    release();
    await page.waitForFunction(() => document.querySelector('.tool-status').textContent.includes('Your input changed'));
    assert.equal(await preview.isHidden(), true);
    await page.unroute('**/tools/json-converter');

    await page.setViewportSize({ width: 390, height: 844 });
    await text.fill(input);
    await previewSheets();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await page.screenshot({ path: '/tmp/json-converter-mobile.png', fullPage: true });
    assert.deepEqual(errors, []);

    const context = await browser.newContext({ javaScriptEnabled: false, reducedMotion: 'reduce' });
    const plainPage = await context.newPage();
    await plainPage.goto(`${base}/tools/json-converter`);
    await plainPage.locator('#json-text').fill(input);
    await plainPage.locator('#nesting-mode').selectOption('flatten');
    await plainPage.locator('button[value="preview"]').focus();
    await Promise.all([
      plainPage.waitForNavigation({ waitUntil: 'load' }),
      plainPage.keyboard.press('Enter')
    ]);
    assert.equal(await plainPage.locator('[data-workbook-preview] article').count(), 1);
    assert.equal(await plainPage.locator('#json-text').inputValue(), input);
    assert.equal(await plainPage.locator('#nesting-mode').inputValue(), 'flatten');
    await context.close();
    console.log('JSON converter browser checks passed: layouts, preview, downloads, uploads, errors, stale responses, mobile, and no-JavaScript fallback.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
