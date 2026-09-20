const assert = require('node:assert/strict');
const {chromium} = require('playwright');

(async () => {
  const browser = await chromium.launch({headless: true});
  const base = process.env.GAMES_BASE_URL || 'http://127.0.0.1:5055';
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1050}});
    const errors = [], requests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => requests.push(request.url()));
    await page.goto(`${base}/games`);
    assert.equal(await page.locator('nav a[href^="/games"]').count(), 0);
    assert.equal(await page.locator('footer a[href^="/games"]').count(), 0);
    await page.getByRole('link', {name: 'Play Maze Chase'}).click();
    await page.locator('#game-start').click();
    await page.waitForFunction(() => Number(document.getElementById('game-score').textContent) > 0);
    assert.equal(await page.locator('#game-overlay').isHidden(), true);
    await page.locator('#maze').press('ArrowUp');
    await page.locator('#maze').press('p');
    assert.equal(await page.locator('#game-pause').textContent(), 'Resume');
    const pausedScore = await page.locator('#game-score').textContent();
    await page.waitForTimeout(180);
    assert.equal(await page.locator('#game-score').textContent(), pausedScore);
    assert.ok(Number(await page.evaluate(() => localStorage.getItem('ad-maze-chase-best'))) > 0);
    await page.locator('#game-start').click();
    await page.evaluate(() => window.dispatchEvent(new Event('blur')));
    assert.equal(await page.locator('#game-overlay').isVisible(), true);
    await page.locator('#game-start').click();
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', {configurable: true, get: () => true});
      document.dispatchEvent(new Event('visibilitychange'));
      delete document.hidden;
    });
    assert.equal(await page.locator('#game-pause').textContent(), 'Resume');
    page.once('dialog', dialog => dialog.accept());
    await page.locator('#game-restart').click();
    assert.equal(await page.locator('#game-score').textContent(), '0');
    assert.equal(await page.locator('#game-lives').textContent(), '3');
    await page.locator('#game-start').click();
    await page.locator('#maze').press('ArrowDown');
    await page.locator('#maze').press(' ');
    assert.equal(await page.locator('#game-pause').textContent(), 'Resume');
    await page.evaluate(() => { document.activeElement.blur(); window.scrollTo({top: 0, behavior: 'instant'}); });
    await page.screenshot({path: '/tmp/maze-desktop.png', fullPage: true});
    await page.locator('#game-start').click();
    await page.locator('#maze').screenshot({path: '/tmp/maze-playing.png'});
    assert.deepEqual(errors, []);
    assert.ok(requests.every(url => url.startsWith(base)));

    const mobile = await browser.newContext({viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true});
    const phone = await mobile.newPage();
    const phoneErrors = [];
    phone.on('pageerror', error => phoneErrors.push(error.message));
    await phone.goto(`${base}/games/maze-chase`);
    await phone.locator('#game-start').tap();
    await phone.waitForFunction(() => Number(document.getElementById('game-score').textContent) > 0);
    await phone.locator('[data-direction="down"]').tap();
    assert.equal(await phone.locator('#game-overlay').isHidden(), true);
    const board = phone.locator('#maze');
    await board.scrollIntoViewIfNeeded();
    const box = await board.boundingBox();
    const touch = await mobile.newCDPSession(phone);
    await touch.send('Input.dispatchTouchEvent', {type: 'touchStart', touchPoints: [{x: box.x + 50, y: box.y + 50}]});
    await touch.send('Input.dispatchTouchEvent', {type: 'touchMove', touchPoints: [{x: box.x + 110, y: box.y + 50}]});
    await touch.send('Input.dispatchTouchEvent', {type: 'touchEnd', touchPoints: []});
    await phone.locator('#game-pause').tap();
    assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await phone.evaluate(() => window.scrollTo({top: 0, behavior: 'instant'}));
    await phone.screenshot({path: '/tmp/maze-mobile.png', fullPage: true});
    assert.deepEqual(phoneErrors, []);
    await mobile.close();

    const blocked = await browser.newContext();
    await blocked.addInitScript(() => {
      Object.defineProperty(window, 'localStorage', {get() { throw new Error('Storage blocked'); }});
    });
    const fallback = await blocked.newPage();
    await fallback.goto(`${base}/games/maze-chase`);
    await fallback.locator('#game-start').click();
    await fallback.waitForFunction(() => Number(document.getElementById('game-score').textContent) > 0);
    assert.match(await fallback.locator('#game-storage').textContent(), /unavailable/);
    await blocked.close();
    console.log('Maze browser checks passed: catalog, play, keyboard/touch, pause, restart, privacy, storage fallback, desktop/mobile.');
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode = 1;});
