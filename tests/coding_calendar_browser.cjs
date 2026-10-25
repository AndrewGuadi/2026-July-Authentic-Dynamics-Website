// Run against a local Flask server with all seeded dates published; see docs/coding-calendar.md.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const base = process.env.CODING_BASE_URL || 'http://127.0.0.1:5073';
const root = path.resolve(__dirname, '..');
const solutions = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures/coding/solutions.json')));
const cache = process.env.CODING_RUNTIME_CACHE;
(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CODING_CHROMIUM_PATH ? { executablePath: process.env.CODING_CHROMIUM_PATH } : {}) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
  if (cache) await context.route('https://cdn.jsdelivr.net/**', async route => {
    const name = new URL(route.request().url()).pathname.split('/').pop();
    const file = path.join(cache, name);
    if (fs.existsSync(file)) await route.fulfill({ status: 200, body: fs.readFileSync(file), headers: { 'access-control-allow-origin': '*', 'content-type': name.endsWith('.wasm') ? 'application/wasm' : 'application/octet-stream' } });
    else await route.abort();
  });
  const page = await context.newPage();
  const errors = [], requests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => requests.push({ url: request.url(), method: request.method(), body: request.postData() }));
  async function source(code) {
    const content = page.locator('.cm-content');
    await content.click();
    await page.keyboard.press('ControlOrMeta+a');
    await page.keyboard.insertText(code);
  }
  async function run(expected) {
    await page.locator('#coding-run').click();
    await page.waitForFunction(() => !document.querySelector('#coding-run').disabled, null, { timeout: 100000 });
    const status = await page.locator('#coding-status').textContent();
    assert.match(status, expected, status);
  }
  try {
    await page.goto(base + '/coding-calendar/');
    assert.equal(await page.locator('.calendar-table tbody tr').count(), new Set(Object.keys(solutions).map(key => key.split('/')[1])).size);
    for (const [key, code] of (process.env.CODING_SKIP_REFERENCE ? [] : Object.entries(solutions))) {
      await page.goto(base + '/coding-calendar/' + key + '/');
      await source(code);
      await run(/Challenge complete/);
      assert.equal(await page.locator('[data-pass="false"]').count(), 0);
      console.log('PASS', key);
    }
    await page.goto(base + '/coding-calendar/javascript/2026-10-24/');
    await source('function solve(value) { return []; }');
    await run(/2 of 3 tests passed/);
    await source('function solve(value) { throw new Error("<img src=x onerror=alert(1)>"); }');
    await run(/0 of 3 tests passed/);
    assert.equal(await page.locator('#coding-results img').count(), 0);
    await source('function solve(value) { while(true) {} }');
    await run(/Execution stopped after 5 seconds/);
    // Native network APIs remain denied even if learner code replaces our fetch wrapper.
    await source(`function solve(value) { const xhr = typeof XMLHttpRequest; console.log('XHR=' + xhr); fetch('${base}/hub/').catch?.(() => {}); return []; }`);
    await run(/0 of 3 tests passed/);
    assert.match(await page.locator('#coding-results').textContent(), /Network access is disabled/);
    assert.ok(!requests.some(r => r.url === base + '/hub/'));
    await source(solutions['javascript/2026-10-24']);
    await run(/Challenge complete/);
    await page.reload();
    assert.match(await page.locator('.cm-content').textContent(), /value.filter/);
    const download = page.waitForEvent('download');
    await page.locator('#coding-download').click();
    assert.equal((await download).suggestedFilename(), 'coding-2026-10-24.js');
    await page.locator('#coding-reset').click();
    assert.match(await page.locator('.cm-content').textContent(), /return null/);
    await source('function solve(value) { while(true) {} }');
    await page.locator('#coding-run').click();
    await page.waitForSelector('iframe.coding-frame', { state: 'attached' });
    assert.equal(await page.locator('iframe.coding-frame').getAttribute('sandbox'), 'allow-scripts');
    assert.equal(await page.evaluate(() => document.querySelector('iframe.coding-frame').contentDocument), null);
    await page.locator('#coding-stop').click();
    assert.match(await page.locator('#coding-status').textContent(), /Stopped/);
    await source(solutions['javascript/2026-10-24']);
    await run(/Challenge complete/);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.evaluate(() => { document.activeElement?.blur(); document.documentElement.style.scrollBehavior = 'auto'; window.scrollTo({ top: 0, behavior: 'instant' }); });
    await page.waitForFunction(() => window.scrollY === 0);
    await page.screenshot({ path: process.env.CODING_SCREENSHOT || '/tmp/coding-calendar-mobile.png', fullPage: true });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
    assert.ok(await page.locator('#coding-source').isHidden());
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
    await page.waitForFunction(() => window.scrollY === 0);
    await page.screenshot({ path: '/tmp/coding-calendar-desktop.png', fullPage: true });
    assert.deepEqual(errors, []);
    assert.ok(!requests.some(r => r.method !== 'GET'));
    assert.ok(!requests.some(r => r.body));
    console.log('PASS failure, timeout, stop, network denial, drafts, download, mobile layout, no code uploads');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
