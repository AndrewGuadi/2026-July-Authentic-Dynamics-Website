const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const {chromium} = require('playwright');

const pageUrl = process.env.LOCAL_PRESENCE_PAGE_URL || 'http://127.0.0.1:5055/growth-technology';
const sizes = [
  {name: 'desktop', width: 1440, height: 1000, mobile: false},
  {name: 'mobile-390', width: 390, height: 844, mobile: true},
  {name: 'mobile-320', width: 320, height: 720, mobile: true},
];

(async () => {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROMIUM_PATH ? {executablePath: process.env.CHROMIUM_PATH} : {}),
  });
  try {
    for (const size of sizes) {
      const context = await browser.newContext({
        viewport: {width: size.width, height: size.height},
        isMobile: size.mobile,
        hasTouch: size.mobile,
      });
      const page = await context.newPage();
      const errors = [];
      const methods = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('request', request => methods.push(request.method()));
      await page.goto(pageUrl);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);

      const root = page.locator('[data-local-presence-checkup]');
      assert.equal(await root.isVisible(), true);
      assert.equal(await page.locator('[data-presence-check]').count(), 10);
      assert.equal(await page.locator('[data-presence-enhanced]').isVisible(), true);
      assert.equal(await page.locator('[data-presence-fallback]').isVisible(), false);

      const type = page.locator('#presence-business-type');
      await type.selectOption('service-area');
      assert.match(await page.locator('#presence-type-guidance').innerText(), /hide it/i);
      assert.match(await page.locator('[data-presence-location-copy]').innerText(), /hide that address/i);
      await type.selectOption('hybrid');
      assert.match(await page.locator('#presence-type-guidance').innerText(), /staffed customer-facing location/i);

      await page.locator('[data-presence-check][value="identity"]').check();
      assert.equal(await page.locator('[data-presence-actions] li').count(), 4);
      assert.match(await page.locator('[data-presence-actions]').innerText(), /6 more actions/i);
      assert.equal(await page.locator('[role="progressbar"]').getAttribute('aria-valuenow'), '1');
      assert.match(await page.locator('#presence-summary-heading').innerText(), /1 of 10/);
      assert.match(await page.locator('[data-presence-actions]').innerText(), /primary category/i);

      await page.locator('#presence-remember').check();
      assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem('authentic-dynamics.local-presence-checkup.v1')).checks.identity), true);
      await page.reload();
      assert.equal(await page.locator('[data-presence-check][value="identity"]').isChecked(), true);
      assert.equal(await page.locator('#presence-business-type').inputValue(), 'hybrid');
      assert.equal(await page.locator('#presence-remember').isChecked(), true);

      const [download] = await Promise.all([
        page.waitForEvent('download'),
        page.locator('#presence-download').click(),
      ]);
      const report = await fs.readFile(await download.path(), 'utf8');
      assert.match(report, /AUTHENTIC DYNAMICS — LOCAL PRESENCE CHECKUP/);
      assert.match(report, /Checks marked ready: 1\/10/);
      assert.match(report, /Choose the most specific category/);
      assert.match(report, /not a Google score/i);

      await page.evaluate(() => { window.__printCalled = false; window.print = () => { window.__printCalled = true; }; });
      await page.locator('#presence-print').click();
      assert.equal(await page.evaluate(() => window.__printCalled), true);

      await page.locator('#presence-remember').uncheck();
      assert.equal(await page.evaluate(() => localStorage.getItem('authentic-dynamics.local-presence-checkup.v1')), null);
      await page.locator('#presence-reset').click();
      assert.equal(await page.locator('[data-presence-check]:checked').count(), 0);
      assert.equal(await page.locator('#presence-business-type').inputValue(), 'storefront');
      assert.equal(await page.locator('[role="progressbar"]').getAttribute('aria-valuenow'), '0');

      const labels = await page.locator('.presence-check').all();
      for (const label of labels) {
        const box = await label.evaluate(element => {
          const rect = element.getBoundingClientRect();
          return {width: rect.width, height: rect.height};
        });
        assert.ok(box.width >= 44 && box.height >= 44, 'Small checklist target at ' + size.name + ': ' + JSON.stringify(box));
      }
      await page.locator('a[href="#review-request"]').click();
      assert.equal(new URL(page.url()).hash, '#review-request');
      await page.locator('a[href*="interest=growth"]').click();
      assert.equal(new URL(page.url()).hash, '#contact');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);

      assert.deepEqual(errors, []);
      assert.equal(methods.every(method => ['GET', 'HEAD'].includes(method)), true);
      console.log(size.name + ': profile-type guidance, progress, download, print, opt-in persistence, reset, links and overflow passed');
      await context.close();
    }

    const noScript = await browser.newContext({viewport: {width: 390, height: 844}, javaScriptEnabled: false});
    const page = await noScript.newPage();
    await page.goto(pageUrl);
    assert.equal(await page.locator('[data-presence-fallback]').isVisible(), true);
    assert.equal(await page.locator('[data-presence-enhanced]').isVisible(), false);
    assert.equal(await page.locator('[data-presence-check]').count(), 10);
    await page.locator('[data-presence-check][value="identity"]').check();
    assert.equal(await page.locator('[data-presence-check][value="identity"]').isChecked(), true);
    await noScript.close();
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
