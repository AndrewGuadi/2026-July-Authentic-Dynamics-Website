/** Real mobile navigation regression: iOS WebKit touch, not just menu visibility. */
const assert = require('node:assert/strict');
const { webkit, devices } = require('playwright');

const base = process.env.TEST_BASE_URL || 'http://127.0.0.1:5055';
const scenarios = [
  { name: 'iPhone 13', config: devices['iPhone 13'] },
  { name: 'iPhone 13 Pro Max', config: devices['iPhone 13 Pro Max'] },
];

(async () => {
  const browser = await webkit.launch({ headless: true });
  try {
    for (const scenario of scenarios) {
      const context = await browser.newContext(scenario.config);
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));

      async function tapMenu() {
        const button = page.locator('button.menu');
        assert.equal(await button.isVisible(), true);
        await button.tap();
        assert.equal(await button.getAttribute('aria-expanded'), 'true');
        assert.equal(await page.locator('#nav').isVisible(), true);
      }

      await page.goto(base + '/');
      await tapMenu();

      // A focus loss with relatedTarget=null must not hide a menu during touch.
      await page.locator('#nav').dispatchEvent('focusout', { relatedTarget: null });
      assert.equal(await page.locator('button.menu').getAttribute('aria-expanded'), 'true');

      // Regression: actually TAP the destination in a touch-capable WebKit context.
      // Previous tests only opened the menu, then closed it via the button.
      await page.locator('#nav a[href="/websites"]').tap();
      await page.waitForURL('**/websites');
      assert.equal(new URL(page.url()).pathname, '/websites');
      await tapMenu();
      await page.locator('#nav a[href="/blog"]').tap();
      await page.waitForURL('**/blog');
      assert.equal(new URL(page.url()).pathname, '/blog');
      await tapMenu();
      await page.locator('#nav a[href="/growth-technology"]').tap();
      await page.waitForURL('**/growth-technology');
      assert.equal(new URL(page.url()).pathname, '/growth-technology');

      // A second tap on Menu should close the menu, with state synchronized.
      await tapMenu();
      await page.locator('button.menu').tap();
      assert.equal(await page.locator('button.menu').getAttribute('aria-expanded'), 'false');
      assert.equal(await page.locator('#nav').isVisible(), false);

      // Outside taps close the menu, without changing the page.
      await tapMenu();
      const navBox = await page.locator('#nav').boundingBox();
      const viewport = page.viewportSize();
      const outsideY = Math.min(viewport.height - 16, Math.ceil(navBox.y + navBox.height + 30));
      assert.ok(outsideY > navBox.y + navBox.height, 'Expected a tappable region below the open menu');
      await page.touchscreen.tap(14, outsideY);
      assert.equal(await page.locator('button.menu').getAttribute('aria-expanded'), 'false');

      // Accessibility: the keyboard can open and dismiss the same menu.
      const button = page.locator('button.menu');
      await button.focus();
      await page.keyboard.press('Enter');
      assert.equal(await button.getAttribute('aria-expanded'), 'true');
      await page.keyboard.press('Escape');
      assert.equal(await button.getAttribute('aria-expanded'), 'false');

      // Wider viewport cannot leave a stale expanded state behind.
      await tapMenu();
      await page.setViewportSize({ width: 1300, height: 900 });
      assert.equal(await button.getAttribute('aria-expanded'), 'false');

      assert.deepEqual(errors, [], 'Unexpected browser errors: ' + errors.join('; '));
      console.log(scenario.name + ': tap-to-navigate, focus, outside taps, Escape, and resize passed');
      await context.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
