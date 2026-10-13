const assert = require('node:assert/strict');
const {chromium} = require('playwright');

const base = process.env.REVIEW_BASE_URL || 'http://127.0.0.1:5055';
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
      await context.grantPermissions(['clipboard-read', 'clipboard-write'], {origin: base});
      const page = await context.newPage();
      const errors = [];
      const methods = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('request', request => methods.push(request.method()));

      await page.goto(`${base}/growth-technology`);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);

      if (size.mobile) {
        const menu = page.locator('button.menu');
        await menu.click();
        assert.equal(await menu.getAttribute('aria-expanded'), 'true');
        assert.equal(await page.getByRole('navigation', {name: 'Main navigation'}).isVisible(), true);
        await page.keyboard.press('Escape');
        assert.equal(await menu.getAttribute('aria-expanded'), 'false');
      }

      const jumpLink = page.getByRole('link', {name: 'Build a review request'});
      assert.equal(await jumpLink.getAttribute('href'), '#review-request');
      await jumpLink.click();
      assert.equal(new URL(page.url()).hash, '#review-request');

      const form = page.locator('#review-request-form');
      await form.scrollIntoViewIfNeeded();
      await form.locator('#review-business').fill('Keystone Home Services');
      await form.locator('#review-link').fill('https://g.page/r/example/review');
      await form.locator('#review-customer').fill('Maria');
      await form.locator('#review-service').fill('your gutter cleaning');
      await form.locator('#review-remember').check();
      await form.getByRole('button', {name: 'Build my request'}).click();

      const message = page.locator('#review-message');
      assert.match(await message.inputValue(), /^Hi Maria,/);
      assert.match(await message.inputValue(), /honest Google review/);
      assert.match(await message.inputValue(), /https:\/\/g\.page\/r\/example\/review/);
      assert.doesNotMatch(await message.inputValue(), /five-star|5-star|positive review/i);
      assert.match(await page.locator('#review-status').innerText(), /Text message ready/);

      await page.locator('#review-copy').click();
      await page.waitForFunction(() => document.querySelector('#review-status').textContent.includes('Copied'));
      assert.match(await page.locator('#review-status').innerText(), /Copied/);
      assert.equal(await page.evaluate(() => navigator.clipboard.readText()), await message.inputValue());

      await form.getByRole('radio', {name: 'Email'}).check();
      await form.getByRole('button', {name: 'Build my request'}).click();
      assert.equal(await page.locator('#review-subject-wrap').isVisible(), true);
      assert.equal(await page.locator('#review-subject').inputValue(), 'A quick question from Keystone Home Services');
      await page.screenshot({path: `/tmp/review-builder-${size.name}-filled.png`, fullPage: true});

      await page.reload();
      assert.equal(await page.locator('#review-business').inputValue(), 'Keystone Home Services');
      assert.equal(await page.locator('#review-link').inputValue(), 'https://g.page/r/example/review');
      assert.equal(await page.locator('#review-remember').isChecked(), true);

      await page.locator('#review-link').fill('http://example.com/review');
      await page.getByRole('button', {name: 'Build my request'}).click();
      assert.equal(
        await page.locator('#review-link').evaluate(element => element.validationMessage),
        'Enter the full secure review link beginning with https://.',
      );
      await page.locator('#review-clear').click();
      assert.equal(await page.locator('#review-business').inputValue(), '');
      assert.equal(await page.evaluate(() => localStorage.getItem('authentic-dynamics.review-request.v1')), null);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);

      const tapTargets = await page.locator('#review-request button:visible, #review-request input[type="text"]:visible, #review-request input[type="url"]:visible, #review-request select:visible, #review-request .review-choice label:visible, #review-request .review-remember:visible').all();
      for (const target of tapTargets) {
        const box = await target.evaluate(element => {
          const rect = element.getBoundingClientRect();
          return {width: rect.width, height: rect.height};
        });
        assert.ok(box.width >= 44 && box.height >= 44, `Small tap target at ${size.name}: ${JSON.stringify(box)}`);
      }

      assert.deepEqual(errors, []);
      assert.equal(methods.every(method => ['GET', 'HEAD'].includes(method)), true);
      await page.screenshot({path: `/tmp/review-builder-${size.name}.png`, fullPage: true});
      console.log(`${size.name}: generation, clipboard, persistence, validation, navigation and layout passed`);
      await context.close();
    }
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
