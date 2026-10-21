const assert = require('node:assert/strict');
const {chromium} = require('playwright');

const base = process.env.SEO_BASE_URL || 'http://127.0.0.1:5055';
const devices = [
  {name: 'iPhone-sized', viewport: {width: 393, height: 852}, userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148'},
  {name: 'Android-sized', viewport: {width: 412, height: 915}, userAgent: 'Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 Chrome/145.0 Mobile Safari/537.36'},
];

(async () => {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROMIUM_PATH ? {executablePath: process.env.CHROMIUM_PATH} : {}),
  });
  try {
    for (const device of devices) {
      const context = await browser.newContext({
        viewport: device.viewport,
        userAgent: device.userAgent,
        isMobile: true,
        hasTouch: true,
      });
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));

      await page.goto(`${base}/`);
      assert.equal(await page.title(), 'Central PA Website Design & Digital Growth | Authentic Dynamics');
      assert.match(
        await page.locator('meta[name="description"]').getAttribute('content'),
        /Central Pennsylvania small businesses/,
      );
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);

      const menu = page.locator('button.menu');
      await menu.click();
      assert.equal(await menu.getAttribute('aria-expanded'), 'true');
      assert.equal(await page.getByRole('navigation', {name: 'Main navigation'}).isVisible(), true);
      await menu.click();

      const contact = page.locator('#contact-form');
      await contact.scrollIntoViewIfNeeded();
      await contact.getByRole('button', {name: 'Send my inquiry'}).click();
      assert.equal(await contact.locator('[name="name"]').evaluate(element => element.validity.valueMissing), true);
      assert.equal(new URL(page.url()).pathname, '/');

      const websiteLink = page.getByRole('link', {name: 'Explore website design'});
      assert.equal(await websiteLink.getAttribute('href'), '/websites');
      await websiteLink.click();
      assert.equal(new URL(page.url()).pathname, '/websites');
      assert.equal(await page.title(), 'Pennsylvania Website Design & Development | Authentic Dynamics');
      assert.match(
        await page.locator('meta[name="description"]').getAttribute('content'),
        /Custom website design and development for Central Pennsylvania/,
      );
      assert.match(await page.locator('.page-hero .intro').innerText(), /small businesses across Central Pennsylvania/);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      await page.screenshot({path: `/tmp/seo-websites-${device.name}.png`, fullPage: true});

      await page.getByRole('link', {name: 'Explore the $500 start'}).click();
      assert.equal(new URL(page.url()).hash, '#starter');
      await page.getByRole('link', {name: 'See custom options'}).click();
      assert.equal(new URL(page.url()).hash, '#options');
      assert.equal(await page.getByRole('link', {name: 'Talk about my website'}).getAttribute('href'), '/about-community?interest=website#contact');

      const tapTargets = await page.locator('button:visible, a.button:visible').all();
      for (const target of tapTargets) {
        const box = await target.evaluate(element => {
          const rect = element.getBoundingClientRect();
          return {width: rect.width, height: rect.height};
        });
        assert.ok(box.width >= 44 && box.height >= 44, `Small tap target: ${JSON.stringify(box)}`);
      }

      const hrefs = await page.locator('a[href]').evaluateAll(links => links.map(link => link.href));
      for (const href of [...new Set(hrefs)]) {
        const url = new URL(href);
        if (url.origin !== base || url.pathname.startsWith('/static/')) continue;
        const response = await context.request.get(url.href);
        assert.ok(response.status() < 400, `${url.href} returned ${response.status()}`);
      }

      await page.goto(`${base}/tools/list-cleaner`);
      await page.locator('#list-input').fill('Harrisburg\nharrisburg\nMechanicsburg\n\nHarrisburg');
      await page.locator('#list-case').check();
      await page.getByRole('button', {name: 'Clean my list'}).click();
      assert.equal(await page.locator('#list-output').inputValue(), 'Harrisburg\nMechanicsburg');
      assert.match(await page.locator('#list-status').innerText(), /2 items kept · 2 duplicates removed/);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      assert.deepEqual(errors, []);
      console.log(`${device.name}: metadata, navigation, validation, links, list tool, tap targets and overflow passed`);
      await context.close();
    }
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
