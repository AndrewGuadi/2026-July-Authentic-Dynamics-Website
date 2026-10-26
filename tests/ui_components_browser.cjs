// Run through scripts/test_ui_components.py, which serves an isolated test app.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const {chromium} = require('playwright');
const base = process.env.AD_UI_BASE_URL;
if (!base || !/^http:\/\/127\.0\.0\.1:\d+$/.test(base)) throw new Error('Use the isolated UI test runner');

(async () => {
  const output = process.env.AD_UI_SCREENSHOTS || '/tmp/ad-ui-components';
  await fs.mkdir(output, {recursive: true});
  const browser = await chromium.launch({headless: true,
    ...(process.env.CHROMIUM_PATH ? {executablePath: process.env.CHROMIUM_PATH} : {})});
  try {
    for (const width of [320, 390, 768, 1024, 1440]) {
      const context = await browser.newContext({viewport: {width, height: 1000},
        isMobile: width < 600, hasTouch: width < 600});
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      for (const route of ['/', '/about-community', '/websites', '/growth-technology', '/tools/']) {
        assert.equal((await page.goto(base + route)).status(), 200);
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${route}: overflow at ${width}`);
      }
      await page.goto(base + '/');
      const primary = page.getByRole('link', {name: 'Let’s build something', exact: true});
      const secondary = page.getByRole('link', {name: 'See our work', exact: true});
      for (const control of [primary, secondary]) {
        await control.focus();
        await page.keyboard.press('Tab');
        await page.keyboard.press('Shift+Tab');
        assert(await control.evaluate(el => el.matches(':focus-visible')), 'Keyboard focus must remain visible');
        assert.equal(await control.evaluate(el => getComputedStyle(el).outlineStyle), 'solid');
        assert((await control.boundingBox()).height >= 44);
      }
      if (width >= 600) {
        await secondary.hover();
        await page.waitForFunction(() => {
          const el = document.querySelector('.hero .ui-expand');
          return Math.abs(parseFloat(getComputedStyle(el, '::before').width) - el.clientWidth) < 2
            && getComputedStyle(el).color === 'rgb(9, 9, 9)';
        });
        assert.equal(await secondary.evaluate(el => getComputedStyle(el).color), 'rgb(9, 9, 9)');
      }
      const highlighted = page.getByRole('button', {name: 'Highlight this card', exact: true});
      if (width < 600) await highlighted.tap(); else await highlighted.click();
      assert.equal(await highlighted.getAttribute('aria-pressed'), 'true');
      assert(await page.locator('#showcase-frame').evaluate(el => el.classList.contains('is-highlighted')));
      await highlighted.click();
      assert.equal(await highlighted.getAttribute('aria-pressed'), 'false');
      const showcasePlanner = page.getByRole('button', {name: 'Try the planner', exact: true});
      await showcasePlanner.click();
      assert(await page.locator('#tool-dialog').isVisible());
      await page.keyboard.press('Escape');
      assert(await showcasePlanner.evaluate(el => el === document.activeElement));
      await page.locator('#showcase-business').fill('Keystone Garden Care');
      assert.equal(await page.locator('#showcase-business').inputValue(), 'Keystone Garden Care');
      assert.equal(await page.locator('#showcase-business').evaluate(el => el.form), null);
      // A dynamic panel must keep the bordered treatment and launch the right tool.
      await page.getByRole('tab', {name: 'Food, retail & makers'}).click();
      assert.equal(await page.locator('#industry-panel .ui-expand').count(), 2);
      await page.locator('#industry-panel').getByRole('button', {name: 'Plan your homepage', exact: true}).click();
      await page.getByRole('button', {name: 'Try a fictional business example'}).click();
      await page.getByRole('button', {name: 'Build my homepage outline'}).click();
      assert.match(await page.locator('#tool-output').innerText(), /Keystone Garden Care/);
      await page.keyboard.press('Escape');
      assert.equal(await page.locator('#tool-dialog').isVisible(), false);
      await page.getByRole('button', {name: 'Compare my options', exact: true}).click();
      assert.match(await page.locator('#tool-output').innerText(), /Your estimated costs/);
      await page.keyboard.press('Escape');
      // Exercise actual server validation without saving or sending an inquiry.
      await page.locator('#contact-form').evaluate(form => { form.noValidate = true; });
      await page.getByRole('button', {name: 'Send my inquiry', exact: true}).click();
      await page.waitForURL('**/contact#contact');
      assert(await page.locator('#contact-errors').isVisible());
      await page.locator('#contact-name').focus();
      await page.waitForFunction(() => getComputedStyle(document.querySelector('#contact-name')).borderTopColor === 'rgb(255, 182, 167)');
      assert.equal(await page.locator('#contact-name').evaluate(el => getComputedStyle(el).borderTopColor), 'rgb(255, 182, 167)');
      await page.goto(base + '/');
      if ([390, 1440].includes(width)) {
        await page.screenshot({path: `${output}/hero-${width}.png`});
        if (width >= 1000) {
          await page.locator('#interaction-showcase').screenshot({path: `${output}/showcase-${width}.png`});
        } else {
          // Capture the viewport to avoid stitching sticky headers over tall sections.
          await page.locator('#showcase-title').click();
          await page.locator('#interaction-showcase').evaluate(el => el.scrollIntoView({block: 'start', behavior: 'instant'}));
          await page.screenshot({path: `${output}/showcase-${width}.png`});
        }
      }
      assert.deepEqual(errors, []);
      await context.close();
      console.log(`${width}px: routes, overflow, focus, tap, industry updates, planner, calculator, form errors passed`);
    }
    const reduced = await browser.newContext({reducedMotion: 'reduce'});
    const page = await reduced.newPage();
    await page.goto(base + '/');
    for (const selector of ['.hero .ui-explore', '.hero .ui-expand', '.ui-frame', '.ui-field']) {
      assert.equal(await page.locator(selector).first().evaluate(el => getComputedStyle(el).transitionDuration), '0s');
    }
    await page.getByRole('button', {name: 'Highlight this card', exact: true}).click();
    assert.equal(await page.locator('#showcase-frame').evaluate(el => getComputedStyle(el).transform), 'none');
    await reduced.close();
    const noJS = await browser.newContext({javaScriptEnabled: false, viewport: {width: 390, height: 844}});
    const fallback = await noJS.newPage();
    await fallback.goto(base + '/');
    assert(await fallback.getByRole('heading', {name: 'Built to be interacted with.'}).isVisible());
    assert.equal(await fallback.locator('#showcase-highlight').isVisible(), false);
    assert.equal(await fallback.locator('#contact-form').getAttribute('method'), 'post');
    assert.equal(await fallback.getByRole('link', {name: 'Let’s build something', exact: true}).getAttribute('href'), '#contact');
    assert(await fallback.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await noJS.close();
    console.log('Reduced-motion and JavaScript-disabled fallbacks passed');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
