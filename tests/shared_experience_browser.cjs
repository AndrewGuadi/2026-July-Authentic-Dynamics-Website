const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const {chromium} = require('playwright');
const base = process.env.EXPERIENCE_BASE_URL || 'http://127.0.0.1:5055';
const routes = ['/', '/websites', '/work', '/growth-technology', '/about-community',
  '/privacy-policy', '/terms', '/tools/', '/tools/pdf-to-image', '/tools/csv-converter',
  '/tools/json-converter', '/tools/video-converter', '/tools/list-cleaner',
  '/tools/free-invoice-maker', '/tools/qr-code-maker', '/tools/local-ai', '/browser-xray',
  '/games/', '/games/maze-chase'];

(async () => {
  const output = process.env.EXPERIENCE_SCREENSHOTS || '/tmp/ad-experience-screenshots';
  await fs.mkdir(output, {recursive: true});
  const browser = await chromium.launch({headless: true,
    ...(process.env.CHROMIUM_PATH ? {executablePath: process.env.CHROMIUM_PATH} : {})});
  try {
    for (const width of [390, 1440]) {
      const context = await browser.newContext({viewport: {width, height: 900},
        isMobile: width < 600, hasTouch: width < 600});
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      for (const path of routes) {
        const response = await page.goto(base + path);
        assert.equal(response.status(), 200, path);
        assert.equal(await page.locator('h1').count(), 1, path);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `Overflow: ${path} at ${width}`);
        assert.deepEqual(errors, [], path);
        if (path === '/about-community') {
          assert.equal(await page.locator('.community-jumps').evaluate(element => getComputedStyle(element).position), 'static');
          assert.equal(await page.locator('.community-jumps').evaluate(element => element.getBoundingClientRect().top >= document.querySelector('.page-hero').getBoundingClientRect().bottom - 1), true, 'Community jumps must follow the hero, not cover it');
        }
        if (['/', '/websites', '/work', '/about-community', '/tools/'].includes(path)) {
          await page.screenshot({path: `${output}/${path.replaceAll('/', '_') || 'home'}-${width}.png`});
        }
        // Shared menu must close and return focus reliably at touch widths.
        if (width < 600) {
          const menu = page.locator('button.menu');
          await menu.click();
          assert.equal(await menu.getAttribute('aria-expanded'), 'true', path);
          await page.keyboard.press('Escape');
          assert.equal(await menu.getAttribute('aria-expanded'), 'false', path);
          assert.equal(await menu.evaluate(element => element === document.activeElement), true);
        }
      }
      await page.goto(base + '/about-community?interest=automation#contact');
      assert.equal(await page.locator('#interest').inputValue(), 'AI, automation & custom systems');
      await page.locator('#interest').selectOption('Community project or nonprofit');
      assert.equal(await page.locator('#interest').inputValue(), 'Community project or nonprofit');
      await page.getByRole('button', {name: 'Send my inquiry'}).click();
      assert.equal(await page.locator('[name="name"]').evaluate(element => element.validity.valueMissing), true);
      // Exercise the server error response and its native #contact navigation.
      // Empty required fields guarantee this cannot create an inquiry.
      await page.locator('#contact-form').evaluate(form => { form.noValidate = true; });
      const rejectedInquiry = page.waitForResponse(response =>
        response.request().method() === 'POST' && new URL(response.url()).pathname === '/contact');
      await page.getByRole('button', {name: 'Send my inquiry'}).click();
      assert.equal((await rejectedInquiry).status(), 400);
      await page.waitForLoadState('networkidle');
      await page.waitForFunction(() => document.activeElement?.id === 'contact-errors');
      assert.equal(await page.locator('#interest').inputValue(), 'Community project or nonprofit');
      await page.locator('#contact-errors a[href="#contact-name"]').click();
      assert.equal(await page.locator('#contact-name').evaluate(element => element === document.activeElement), true);
      await page.goto(base + '/');
      await page.getByRole('tab', {name: 'Food, retail & makers'}).click();
      await page.locator('#industry-panel [data-interest]').click();
      assert.equal(await page.locator('#interest').inputValue(), 'Small business website — from $500');
      await page.getByRole('button', {name: 'Plan my homepage'}).click();
      const dialog = page.locator('dialog');
      assert.equal(await dialog.isVisible(), true);
      await page.keyboard.press('Escape');
      assert.equal(await dialog.isVisible(), false);
      assert.deepEqual(errors, []);
      console.log(`${width}px: all 19 public routes, one H1, overflow, runtime errors, shared menu, inquiry context and planner checked`);
      await context.close();
    }
    const noJS = await browser.newContext({javaScriptEnabled: false, viewport: {width: 390, height: 844}});
    const page = await noJS.newPage();
    for (const path of ['/', '/privacy-policy', '/tools/']) {
      await page.goto(base + path);
      assert.equal(await page.getByRole('navigation', {name: 'Main navigation'}).isVisible(), true);
      assert.equal(await page.getByRole('button', {name: 'Open menu'}).isVisible(), false);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    }
    await noJS.close();
    console.log('No-JS mobile navigation passed');
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode = 1;});
