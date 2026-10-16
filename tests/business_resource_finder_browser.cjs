const assert = require('node:assert/strict');
const { chromium } = require('playwright');

(async () => {
  const baseUrl = process.env.RESOURCE_BASE_URL || 'http://127.0.0.1:5055';
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    const requests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => requests.push({ method: request.method(), url: request.url() }));
    await page.goto(`${baseUrl}/about-community`, { waitUntil: 'networkidle' });

    assert.equal(await page.locator('[data-resource-finder]').isVisible(), true);
    assert.equal(await page.locator('[data-results-head]').isHidden(), true);
    await page.locator('a[href="#business-resources"]').click();
    assert.equal(await page.evaluate(() => location.hash), '#business-resources');
    await page.locator('#resource-county').selectOption('dauphin');
    assert.match(await page.locator('[data-result-count]').textContent(), /4 trusted starting points.*Dauphin County/);
    assert.equal(await page.locator('.resource-card').count(), 4);
    assert.equal(await page.locator('.resource-card').first().locator('h3').textContent(), 'Dauphin County Community & Economic Development');
    assert.equal(await page.locator('.resource-card').nth(1).locator('h3').textContent(), 'Pennsylvania Business One-Stop Shop');
    assert.equal(await page.locator('.resource-card').nth(2).locator('h3').textContent(), 'Kutztown University SBDC');

    await page.locator('#resource-need').selectOption('training');
    assert.equal(await page.locator('.resource-card').count(), 1);
    assert.equal(await page.locator('.resource-card h3').textContent(), 'Kutztown University SBDC');
    assert.match(await page.locator('[data-result-count]').textContent(), /^1 trusted starting point /);
    await page.locator('#resource-county').selectOption('perry');
    assert.equal(await page.locator('.resource-card').count(), 2);
    assert.equal(await page.locator('.resource-card').first().locator('h3').textContent(), 'Perry County Economic Development Authority');

    const externalLinks = page.locator('.resource-card a');
    for (let index = 0; index < await externalLinks.count(); index += 1) {
      assert.equal(await externalLinks.nth(index).getAttribute('target'), '_blank');
      assert.equal(await externalLinks.nth(index).getAttribute('rel'), 'noopener noreferrer');
    }

    await page.locator('[data-resource-reset]').click();
    assert.equal(await page.locator('#resource-county').inputValue(), '');
    assert.equal(await page.locator('[data-resource-empty]').isVisible(), true);
    assert.equal(await page.locator('#contact-form').evaluate(form => form.checkValidity()), false);

    for (const viewport of [
      { name: 'iphone', width: 390, height: 844 },
      { name: 'android', width: 360, height: 800 },
      { name: 'narrow', width: 320, height: 720 }
    ]) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, viewport.name);
      const menu = page.locator('.menu');
      await menu.click();
      assert.equal(await menu.getAttribute('aria-expanded'), 'true');
      await page.keyboard.press('Escape');
      assert.equal(await menu.getAttribute('aria-expanded'), 'false');
      await page.locator('#resource-county').selectOption('york');
      await page.locator('#resource-need').selectOption('funding');
      assert.equal(await page.locator('.resource-card').count(), 3);
      for (const selector of ['#resource-county', '#resource-need', '[data-resource-reset]']) {
        const box = await page.locator(selector).boundingBox();
        assert.ok(box.height >= 44, `${viewport.name}: ${selector} is ${box.height}px tall`);
      }
    }

    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: '/tmp/business-resource-finder-mobile.png', fullPage: true });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.screenshot({ path: '/tmp/business-resource-finder-desktop.png', fullPage: true });

    assert.deepEqual(errors, []);
    assert.ok(requests.every(request => request.method === 'GET'), JSON.stringify(requests));
    assert.equal(await page.evaluate(() => localStorage.length), 0);
    console.log('Business resource finder browser checks passed: filters, trusted links, reset, navigation, tap targets and responsive layout.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
