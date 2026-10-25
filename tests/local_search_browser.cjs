const assert = require('node:assert/strict');
const {chromium, webkit} = require('playwright');
const base = process.env.SEO_BASE_URL || 'http://127.0.0.1:5059';

(async () => {
  const engines = [['Chromium', chromium]];
  if (process.env.TEST_WEBKIT === '1') engines.push(['WebKit', webkit]);
  for (const [name, engine] of engines) {
    const browser = await engine.launch({headless: true,
      ...(name === 'Chromium' && process.env.CHROMIUM_PATH ? {executablePath: process.env.CHROMIUM_PATH} : {})});
    try {
      for (const width of [390, 412, 1440]) {
        const context = await browser.newContext({viewport: {width, height: 900},
          isMobile: width < 600, hasTouch: width < 600});
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        for (const path of ['/websites', '/growth-technology', '/about-community']) {
          assert.equal((await page.goto(base + path)).status(), 200);
          assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${name} ${width} ${path}`);
          assert.equal(await page.locator('h1').count(), 1);
          if (width < 600) {
            await page.locator('button.menu').click();
            await page.locator('#nav').getByRole('link', {name: 'Websites', exact: true}).click();
            await page.waitForURL('**/websites');
            await page.goto(base + path);
          }
          // Check all affected internal anchors and route targets without sending forms.
          const links = await page.locator('main a[href]').evaluateAll(nodes => nodes.map(n => n.getAttribute('href')));
          for (const href of new Set(links)) {
            const url = new URL(href, base + path);
            if (url.origin !== base) continue;
            const response = await page.request.get(url.href);
            assert.equal(response.status(), 200, href);
            if (url.hash) assert.match(await response.text(), new RegExp(`id=["']${url.hash.slice(1)}["']`), href);
          }
        }
        await page.goto(base + '/websites');
        const question = page.locator('details').first();
        await question.locator('summary').click();
        assert.equal(await question.getAttribute('open'), '');
        await page.goto(base + '/growth-technology#website-analytics');
        await page.getByRole('link', {name: 'Discuss my analytics setup'}).click();
        await page.waitForURL('**/about-community#contact');
        await page.locator('#contact-form button[type="submit"]').click();
        assert.equal(await page.locator('#contact-form [name="name"]').evaluate(n => n.validity.valueMissing), true);
        assert.deepEqual(errors, []);
        await page.screenshot({path: `/tmp/ad-seo-${name}-${width}.png`});
        await context.close();
        console.log(`${name} ${width}px: layout, menu link taps, internal links/anchors, FAQ, analytics CTA and native validation passed`);
      }
    } finally { await browser.close(); }
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
