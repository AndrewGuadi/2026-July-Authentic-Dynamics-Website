const assert = require('node:assert/strict');
const {chromium} = require('playwright');
const base = process.env.SERVICE_BASE_URL || 'http://127.0.0.1:5055';

(async () => {
  const browser = await chromium.launch({headless: true, ...(process.env.CHROMIUM_PATH ? {executablePath: process.env.CHROMIUM_PATH} : {})});
  try {
    for (const width of [360, 390, 412, 1440]) {
      const context = await browser.newContext({viewport: {width, height: 900}, isMobile: width < 600, hasTouch: width < 600});
      const page = await context.newPage();
      const errors = [];
      const writes = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('request', request => { if (request.method() !== 'GET') writes.push(`${request.method()} ${request.url()}`); });
      await page.goto(`${base}/websites`);
      assert.equal(await page.locator('#website-demo-action').isVisible(), true);
      await page.getByRole('button', {name: 'Plan a visit', exact: true}).click();
      assert.equal(await page.getByRole('button', {name: 'Plan a visit', exact: true}).getAttribute('aria-pressed'), 'true');
      assert.match(await page.locator('#website-demo-contact').getAttribute('href'), /interest=custom#contact$/);
      await page.getByRole('button', {name: 'Choose a sample time', exact: true}).click();
      assert.match(await page.locator('#website-demo-detail').innerText(), /Tuesday at 10:00/);
      await page.getByRole('button', {name: 'Preview a visit request', exact: true}).click();
      assert.match(await page.locator('#website-demo-detail').innerText(), /No appointment was created/);
      assert.match(await page.locator('#website-demo-status').innerText(), /Nothing was sent or saved/);
      await page.getByRole('button', {name: 'Show products', exact: true}).click();
      assert.match(await page.locator('#website-demo-detail').innerText(), /pollinator plants/);
      await page.getByRole('button', {name: 'Explore a sample product', exact: true}).click();
      await page.getByRole('button', {name: 'Preview a product inquiry', exact: true}).click();
      assert.match(await page.locator('#website-demo-detail').innerText(), /No order or message was sent/);
      await page.getByRole('button', {name: 'Get inquiries', exact: true}).focus();
      await page.keyboard.press('Enter');
      assert.match(await page.locator('#website-demo-contact').getAttribute('href'), /interest=website#contact$/);
      await page.getByRole('button', {name: 'Try an inquiry', exact: true}).click();
      await page.getByRole('button', {name: 'Preview the next step', exact: true}).click();
      await page.getByRole('button', {name: 'Start this example again', exact: true}).click();
      assert.match(await page.locator('#website-demo-detail').innerText(), /Garden care/);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      await page.emulateMedia({reducedMotion: 'reduce'});
      await page.getByRole('button', {name: 'Show products', exact: true}).click();
      assert.equal(await page.locator('#website-demo-panel').evaluate(element => element.getAnimations().length), 0);
      assert.equal(await page.evaluate(() => localStorage.length), 0);
      await page.screenshot({path: `/tmp/service-websites-${width}.png`, fullPage: true});

      await page.goto(`${base}/growth-technology`);
      assert.equal(await page.locator('#review-request-form').count(), 1);
      await page.getByRole('button', {name: 'Getting found', exact: true}).click();
      assert.match(await page.locator('#growth-demo-contact').getAttribute('href'), /interest=growth#contact$/);
      await page.getByRole('button', {name: '3 · Next step', exact: true}).click();
      assert.match(await page.locator('#growth-owner-copy').innerText(), /No tracking is running/);
      await page.getByRole('button', {name: 'Following up', exact: true}).click();
      assert.equal(await page.getByRole('button', {name: '1 · Inquiry', exact: true}).getAttribute('aria-current'), 'step');
      await page.getByRole('button', {name: '2 · Review', exact: true}).click();
      assert.match(await page.locator('#growth-owner-copy').innerText(), /stays with a person/);
      await page.getByRole('button', {name: '3 · Follow-up', exact: true}).click();
      assert.match(await page.locator('#growth-owner-copy').innerText(), /manual fallback/);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      await page.screenshot({path: `/tmp/service-growth-${width}.png`, fullPage: true});

      await page.goto(`${base}/work`);
      const image = page.locator('#featured-work img');
      await image.waitFor({state: 'visible'});
      assert.equal(await image.evaluate(element => element.complete && element.naturalWidth > 0), true);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      await page.screenshot({path: `/tmp/service-work-${width}.png`, fullPage: true});
      assert.deepEqual(errors, []);
      assert.deepEqual(writes, []);
      console.log(`${width}px: service goals, staged demos, context URLs, keyboard, reduced motion, proof image, overflow and no writes passed`);
      await context.close();
    }
    const noJS = await browser.newContext({javaScriptEnabled: false, viewport: {width: 390, height: 844}});
    const page = await noJS.newPage();
    await page.goto(`${base}/websites`);
    assert.equal(await page.locator('#website-demo-action').isVisible(), false);
    assert.equal(await page.locator('#website-demo-contact').isVisible(), true);
    assert.match(await page.locator('#website-experience').innerText(), /JavaScript enables the optional examples/);
    await page.goto(`${base}/growth-technology`);
    assert.equal(await page.locator('[data-workflow-step="0"]').isVisible(), false);
    assert.equal(await page.locator('#growth-demo-contact').isVisible(), true);
    await noJS.close();
    console.log('No-JavaScript service content and contact paths passed');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
