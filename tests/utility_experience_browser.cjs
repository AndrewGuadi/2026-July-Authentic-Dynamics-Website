// Functional checks for utility UX changes, with no real uploads or AI downloads.
const assert = require('node:assert/strict');
const {chromium} = require('playwright');
const base = process.env.UTILITY_BASE_URL || 'http://127.0.0.1:5055';
(async () => {
  const browser = await chromium.launch({headless: true, ...(process.env.CHROMIUM_PATH ? {executablePath: process.env.CHROMIUM_PATH} : {})});
  try {
    for (const width of [390, 1440]) {
      const page = await browser.newPage({viewport: {width, height: 900}});
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(`${base}/tools/list-cleaner`);
      await page.locator('#list-sample').click();
      await page.locator('#list-clean').click();
      assert.equal(await page.locator('#list-output').inputValue(), 'Counter signs\nMenu cards\nWindow decals');
      assert.match(await page.locator('#list-status').innerText(), /3 items kept · 2 duplicates removed · 1 blank line removed/);
      await page.locator('#list-reset').click();
      assert.equal(await page.locator('#list-output').inputValue(), '');
      await page.locator('#list-undo').click();
      assert.equal(await page.locator('#list-case').isChecked(), true);
      assert.equal(await page.locator('#list-download').isDisabled(), true);
      await page.locator('#list-clean').click();
      assert.equal(await page.locator('#list-output').inputValue(), 'Counter signs\nMenu cards\nWindow decals');
      await page.locator('#list-reset').click();
      await page.locator('#list-input').fill('New data');
      assert.equal(await page.locator('#list-undo').isHidden(), true);
      await page.locator('#list-sample').click();
      assert.equal(await page.locator('#list-input').inputValue(), 'New data');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      await page.goto(`${base}/tools/qr-code-maker`);
      assert.equal(await page.locator('[data-download="pdf"]').evaluate(el => el.classList.contains('is-primary')), true);
      await page.locator('#qr-layout').selectOption('plain');
      assert.equal(await page.locator('[data-download="png"]').evaluate(el => el.classList.contains('is-primary')), true);
      assert.equal(await page.locator('[data-download="png"]').isDisabled(), true);
      await page.locator('#qr-url').fill('https://example.org/menu');
      await page.waitForFunction(() => !document.querySelector('[data-download="png"]').disabled);
      await page.getByText('Advanced code settings', {exact: true}).click();
      await page.locator('#qr-size').selectOption('512');
      await page.locator('#qr-url').fill('not a URL');
      assert.equal(await page.locator('[data-download="png"]').isDisabled(), true);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      await page.goto(`${base}/tools/free-invoice-maker`);
      assert.equal(await page.locator('.utility-steps').evaluate(el => getComputedStyle(el).position), 'static');
      await page.getByRole('link', {name: '2. Items', exact: true}).click();
      assert.equal(await page.locator('#im-line-items').evaluate(el => el.open), true);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      await page.goto(`${base}/browser-xray`);
      await page.locator('#xr-scan').click();
      assert.equal(await page.locator('#xr-sensitive-summary').innerText(), 'Sensitive access: none active.');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      assert.deepEqual(errors, []);
      await page.close();
    }
    const ai = await browser.newPage();
    await ai.addInitScript(() => {
      Object.defineProperty(navigator, 'gpu', {value: {requestAdapter: async () => ({features: new Set(['shader-f16'])})}});
      Object.defineProperty(navigator, 'clipboard', {value: {writeText: async () => {throw new Error('Clipboard denied');}}});
    });
    await ai.route('https://esm.run/@mlc-ai/web-llm@0.2.85', route => route.fulfill({contentType:'text/javascript', body:`
      export async function CreateMLCEngine() {return {chat:{completions:{create:async function* () {
        yield {choices:[{delta:{content:'Thanks for contacting our team.'}}]};
      }}}};}
    `}));
    await ai.goto(`${base}/tools/local-ai`);
    assert.equal(await ai.locator('#ai-example').isDisabled(), true);
    await ai.locator('#ai-load').click();
    await ai.waitForFunction(() => !document.querySelector('#ai-example').disabled);
    await ai.locator('#ai-example').click();
    assert.match(await ai.locator('#ai-prompt').inputValue(), /without adding promises/);
    await ai.locator('#ai-ask').click();
    await ai.waitForFunction(() => !document.querySelector('#ai-copy').disabled);
    await ai.locator('#ai-copy').click();
    assert.match(await ai.locator('#ai-status').innerText(), /Automatic copying is unavailable/);
    assert.equal(await ai.evaluate(() => window.getSelection().toString()), 'Thanks for contacting our team.');
    await ai.close();
    const game = await browser.newPage();
    await game.addInitScript(() => {
      const drawImage = CanvasRenderingContext2D.prototype.drawImage;
      window.mazeDraws = 0;
      CanvasRenderingContext2D.prototype.drawImage = function(...args) {
        if (this.canvas.id === 'maze') window.mazeDraws += 1;
        return drawImage.apply(this, args);
      };
    });
    await game.goto(`${base}/games/maze-chase`);
    const readyDraws = await game.evaluate(() => window.mazeDraws);
    await game.waitForTimeout(150);
    assert.equal(await game.evaluate(() => window.mazeDraws), readyDraws, 'Ready state must not render continuously');
    await game.locator('#game-start').click();
    await game.waitForFunction(() => window.mazeDraws > 3);
    await game.locator('#maze').press('ArrowDown');
    assert.match(await game.locator('#game-direction').innerText(), /down/);
    await game.locator('#maze').press(' ');
    const pausedDraws = await game.evaluate(() => window.mazeDraws);
    await game.waitForTimeout(150);
    assert.equal(await game.evaluate(() => window.mazeDraws), pausedDraws, 'Paused state must not render continuously');
    await game.locator('#game-start').click();
    await game.waitForFunction(previous => window.mazeDraws > previous, pausedDraws);
    await game.close();
    console.log('Utility UX checks passed: sample/undo/stale results, QR priority/validation, invoice anchors, Xray access, responsive overflow, game idle/pause/resume.');
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode = 1;});
