const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const {chromium} = require('playwright');
const base = process.env.TOOL_BASE_URL || 'http://127.0.0.1:5055';

(async () => {
  const browser = await chromium.launch({headless: true,
    ...(process.env.CHROMIUM_PATH ? {executablePath: process.env.CHROMIUM_PATH} : {})});
  try {
    for (const width of [360, 390, 412, 1440]) {
      const context = await browser.newContext({viewport: {width, height: 900},
        isMobile: width < 600, hasTouch: width < 600, reducedMotion: 'reduce'});
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(`${base}/tools/`);
      assert.equal(await page.locator('[data-tool-job]:visible').count(), 12);
      await page.getByRole('button', {name: 'Get paid', exact: true}).click();
      assert.equal(await page.locator('[data-tool-job]:visible').count(), 2);
      assert.match(await page.locator('[data-tool-count]').innerText(), /2 tools/);
      await page.getByRole('button', {name: 'Prepare files', exact: true}).click();
      assert.equal(await page.locator('[data-tool-job]:visible').count(), 5);
      await page.getByRole('button', {name: 'All tools', exact: true}).focus();
      await page.keyboard.press('Enter');
      assert.equal(await page.locator('[data-tool-job]:visible').count(), 12);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.evaluate(() => { document.activeElement?.blur(); window.scrollTo(0, 0); });
      await page.screenshot({path: `/tmp/ad-tool-catalog-${width}.png`, fullPage: true});

      await page.goto(`${base}/tools/csv-converter`);
      const requests = [];
      page.on('request', request => { if (request.method() === 'POST') requests.push(request.url()); });
      await page.getByRole('button', {name: 'Use an inventory sample'}).click();
      assert.equal(requests.length, 0, 'Sample must not upload automatically');
      await page.getByRole('button', {name: 'Preview rows', exact: true}).click();
      await page.locator('[data-csv-preview]').waitFor({state: 'visible'});
      assert.match(await page.locator('[data-csv-preview]').innerText(), /001/);
      assert.match(await page.locator('[data-csv-preview]').innerText(), /3 data rows/);
      await page.evaluate(() => { document.activeElement?.blur(); window.scrollTo(0, 0); });
      await page.screenshot({path: `/tmp/ad-csv-preview-${width}.png`, fullPage: true});
      await page.locator('#delimiter').selectOption(';');
      assert.equal(await page.locator('[data-csv-preview]').isVisible(), false);
      assert.equal(await page.locator('.tool-download').isVisible(), false);
      await page.locator('#tool-file').setInputFiles({name: 'sample.csv', mimeType: 'text/csv',
        buffer: Buffer.from('code;description\r\n001;"two\nlines"\r\n002;"<script>bad()</script>"\r\n')});
      await page.getByRole('button', {name: 'Preview rows', exact: true}).click();
      await page.locator('[data-csv-preview]').waitFor({state: 'visible'});
      assert.equal(await page.locator('[data-csv-preview] tbody tr').count(), 2);
      assert.equal(await page.locator('[data-csv-preview] tbody tr').nth(1).locator('td').nth(1).innerText(), '<script>bad()</script>');
      assert.equal(await page.locator('[data-csv-preview] script').count(), 0);
      await page.locator('#output-format').selectOption('tsv');
      const downloadPromise = page.waitForEvent('download');
      await page.getByRole('button', {name: 'Convert & download'}).click();
      const download = await downloadPromise;
      const contents = await fs.readFile(await download.path(), 'utf8');
      assert.match(contents, /001/);
      assert.match(contents, /two\nlines/);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.locator('h1').scrollIntoViewIfNeeded();
      await page.evaluate(() => { document.activeElement?.blur(); window.scrollTo(0, 0); });
      await page.screenshot({path: `/tmp/ad-csv-workspace-${width}.png`, fullPage: true});

      await page.goto(`${base}/tools/json-converter`);
      await page.getByRole('button', {name: 'Use nested orders'}).click();
      assert.equal(JSON.parse(await page.locator('#json-text').inputValue())[0].customer.city, 'Harrisburg');
      assert.equal(await page.locator('#tool-file').evaluate(input => input.files.length), 0);
      await page.goto(`${base}/tools/pdf-to-image`);
      await page.getByRole('button', {name: 'For a website · WebP / 72 DPI'}).click();
      assert.equal(await page.locator('#output-format').inputValue(), 'webp');
      assert.equal(await page.locator('#dpi').inputValue(), '72');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      assert.deepEqual(errors, []);
      console.log(`${width}px: catalog filtering, no sample upload, exact CSV interpretation, safe text rendering, invalidation, export, JSON sample and PDF preset passed`);
      await context.close();
    }
    const nojs = await browser.newContext({javaScriptEnabled: false, viewport: {width: 390, height: 844}});
    const page = await nojs.newPage();
    await page.goto(`${base}/tools/`);
    assert.equal(await page.locator('[data-tool-job]:visible').count(), 12);
    assert.equal(await page.locator('[data-tool-filters]').isVisible(), false);
    await page.goto(`${base}/tools/csv-converter`);
    assert.equal(await page.getByRole('button', {name: 'Convert & download'}).isVisible(), true);
    await nojs.close();
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
