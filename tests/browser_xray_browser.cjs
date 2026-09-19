// Optional Playwright regression suite. Requires a running Flask server.
// Native Chromium fake camera/microphone devices; simulated motion, location and screen chooser.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = process.env.XRAY_BASE_URL || 'http://127.0.0.1:5056';

(async () => {
  const browser = await chromium.launch({ headless: true, args: [
    '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', '--autoplay-policy=no-user-gesture-required',
  ] });
  try {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    await context.addInitScript(() => {
      const nativeMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      window.probe = { calls: [], tracks: [], permission: 'granted', error: null, pending: false, audioClosed: 0, activation: [] };
      const p = window.probe;
      const permission = () => {
        p.calls.push('motion permission'); p.activation.push(navigator.userActivation.isActive);
        return p.pending ? new Promise(resolve => { p.resolveMotion = resolve; }) : Promise.resolve(p.permission);
      };
      Object.defineProperty(window, 'DeviceOrientationEvent', { value: class { static requestPermission = permission; }, configurable: true });
      Object.defineProperty(window, 'DeviceMotionEvent', { value: class {}, configurable: true });
      const obtain = async constraints => {
        if (p.error) throw new DOMException('Sensitive exception payload must not appear', p.error);
        const stream = await nativeMedia(constraints);
        p.tracks.push(...stream.getTracks());
        if (p.pending) await new Promise(resolve => { p.resolveMedia = resolve; });
        return stream;
      };
      navigator.mediaDevices.getUserMedia = constraints => {
        p.calls.push(constraints.video ? 'camera' : 'microphone');
        return obtain(constraints);
      };
      navigator.mediaDevices.getDisplayMedia = constraints => {
        p.calls.push('screen'); p.activation.push(navigator.userActivation.isActive);
        return obtain(constraints);
      };
      Object.defineProperty(navigator, 'geolocation', { value: { getCurrentPosition(success, error) {
        p.calls.push('location');
        const complete = () => p.locationError ? error({ code: p.locationError }) : success({ coords: {
          latitude: 40.123456, longitude: -76.654321, accuracy: 18, altitude: null, heading: null, speed: null,
        }, timestamp: Date.now() });
        if (p.pending) p.resolveLocation = complete; else setTimeout(complete, 0);
      } }, configurable: true });
      const NativeAudio = window.AudioContext;
      window.AudioContext = class extends NativeAudio {
        close() { p.audioClosed += 1; return super.close(); }
      };
      window.sensorEvent = (name, values) => {
        const event = new Event(name);
        for (const [key, value] of Object.entries(values)) Object.defineProperty(event, key, { value });
        window.dispatchEvent(event);
      };
    });
    const page = await context.newPage();
    const errors = [], requests = [], consoleErrors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
    page.on('request', request => requests.push({ url: request.url(), body: request.postData(), method: request.method() }));
    await page.goto(`${base}/browser-xray`, { waitUntil: 'networkidle' });
    const networkStart = requests.length;
    assert.deepEqual(await page.evaluate(() => probe.calls), []);
    await page.locator('#xr-scan').click();
    assert.deepEqual(await page.evaluate(() => probe.calls), []);
    assert.equal(await page.locator('#xr-capabilities details').count(), 24);
    assert.match(await page.locator('#xr-count').textContent(), /2 \/ 7/);
    await page.locator('#xr-server-path').click();
    assert.match(await page.locator('#xr-path-label').textContent(), /SIMULATION ONLY/);

    async function start(key) {
      const before = await page.evaluate(() => probe.calls.length);
      await page.locator(`[data-enable="${key}"]`).click();
      assert.equal(await page.evaluate(() => probe.calls.length), before);
      await page.locator(`[data-confirm="${key}"]`).click();
    }
    async function state(key, expected) {
      await page.waitForFunction(([key, expected]) => document.querySelector(`#${key}-status`).dataset.state === expected, [key, expected]);
    }
    await page.locator('#xr-technical summary').click();
    await start('motion');
    await state('motion', 'Granted');
    await page.evaluate(() => {
      sensorEvent('deviceorientation', { alpha: 182.94, beta: 12.11, gamma: -70 });
      sensorEvent('devicemotion', { acceleration: { x: 14, y: 1, z: 1 }, accelerationIncludingGravity: { x: 14, y: 1, z: 10 } });
    });
    await state('motion', 'Active');
    assert.match(await page.locator('#xr-orientation').textContent(), /182.9/);
    assert.match(await page.locator('#challenge-shake').textContent(), /Completed/);
    await page.setViewportSize({ width: 844, height: 390 });
    await page.evaluate(() => sensorEvent('deviceorientation', { alpha: 10, beta: 30, gamma: 5 }));
    await page.waitForFunction(() => document.querySelector('#xr-orientation').textContent.includes('10.0'));
    await page.locator('[data-stop="motion"]').click();
    await page.evaluate(() => sensorEvent('deviceorientation', { alpha: 999, beta: 999, gamma: 999 }));
    assert.equal((await page.locator('#xr-orientation').textContent()).includes('999'), false);
    await page.evaluate(() => { probe.permission = 'denied'; delete window.DeviceMotionEvent; });
    await start('motion'); await state('motion', 'Denied');
    await page.evaluate(() => { probe.permission = 'granted'; });
    await start('motion'); await state('motion', 'Granted');
    await state('motion', 'Unavailable'); // API exists but no readings arrive.
    await page.evaluate(() => { probe.pending = true; });
    await start('motion');
    await page.locator('#xr-reset').click();
    await page.evaluate(() => { probe.resolveMotion('granted'); probe.pending = false; });
    await page.evaluate(() => sensorEvent('deviceorientation', { alpha: 999, beta: 999, gamma: 999 }));
    assert.equal((await page.locator('#xr-orientation').textContent()).includes('999'), false);

    await start('location'); await state('location', 'Granted');
    assert.match(await page.locator('#xr-location').textContent(), /40.123456/);
    assert.match(await page.locator('#xr-location').textContent(), /Not provided/);
    assert.match(await page.locator('#xr-log').textContent(), /geolocation/);
    await page.locator('[data-stop="location"]').click();
    assert.equal((await page.locator('#xr-log').textContent()).includes('40.123456'), false);
    await page.evaluate(() => { probe.locationError = 1; });
    await start('location'); await state('location', 'Denied');
    await page.evaluate(() => { probe.locationError = 3; });
    await start('location'); await state('location', 'Error');
    await page.evaluate(() => { probe.locationError = null; probe.pending = true; });
    await start('location');
    await page.locator('#xr-reset').click();
    await page.evaluate(() => { probe.resolveLocation(); probe.pending = false; });
    assert.equal(await page.locator('#location-has').textContent(), 'No');

    for (const key of ['camera', 'microphone', 'screen']) {
      await start(key); await state(key, 'Active');
      if (key === 'camera') {
        assert.match(await page.locator('#xr-camera-settings').textContent(), /Resolution/);
        assert.equal((await page.locator('#xr-log').textContent()).includes('deviceId'), false);
      }
      if (key === 'microphone') assert.match(await page.locator('#xr-volume-label').textContent(), /Relative amplitude/);
      await page.locator(`[data-stop="${key}"]`).click();
      assert.equal(await page.evaluate(() => probe.tracks.every(track => track.readyState === 'ended')), true);
    }
    assert.ok(await page.evaluate(() => probe.audioClosed > 0));
    assert.ok(await page.evaluate(() => probe.activation.every(Boolean)));
    for (const [key, error, expected] of [
      ['camera', 'NotAllowedError', 'Denied'], ['microphone', 'NotAllowedError', 'Denied'],
      ['camera', 'NotFoundError', 'Error'], ['microphone', 'NotFoundError', 'Error'],
      ['camera', 'NotReadableError', 'Error'], ['screen', 'InvalidStateError', 'Error'],
    ]) {
      await page.evaluate(error => { probe.error = error; }, error);
      await start(key); await state(key, expected);
      assert.equal((await page.locator(`#${key}-status`).textContent()).includes('Sensitive exception'), false);
    }
    await page.evaluate(() => { probe.error = null; probe.pending = true; });
    await start('camera');
    await page.waitForFunction(() => typeof probe.resolveMedia === 'function');
    await page.locator('#xr-reset').click();
    await page.evaluate(() => { probe.resolveMedia(); probe.pending = false; });
    await page.waitForFunction(() => probe.tracks.every(track => track.readyState === 'ended'));
    assert.equal(await page.locator('#xr-camera').isVisible(), false);
    await page.evaluate(() => { probe.pending = true; probe.resolveMedia = null; });
    await start('microphone');
    await page.waitForFunction(() => typeof probe.resolveMedia === 'function');
    await page.locator('#xr-reset').click();
    await page.evaluate(() => { probe.resolveMedia(); probe.pending = false; });
    await page.waitForFunction(() => probe.tracks.every(track => track.readyState === 'ended'));

    await start('screen'); await state('screen', 'Active');
    await page.evaluate(() => probe.tracks.at(-1).dispatchEvent(new Event('ended')));
    await state('screen', 'Stopped');
    await start('camera'); await state('camera', 'Active');
    await start('microphone'); await state('microphone', 'Active');
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', { value: true, configurable: true });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    assert.equal(await page.evaluate(() => probe.tracks.every(track => track.readyState === 'ended')), true);
    await state('camera', 'Stopped'); await state('microphone', 'Stopped');
    await page.evaluate(() => { delete document.hidden; });
    await start('camera'); await state('camera', 'Active');
    await page.evaluate(() => window.dispatchEvent(new Event('pagehide')));
    assert.equal(await page.evaluate(() => probe.tracks.every(track => track.readyState === 'ended')), true);
    assert.equal(await page.locator('#xr-log').textContent(), 'No events retained.');
    assert.deepEqual(requests.slice(networkStart), []);
    assert.deepEqual(errors, []);
    assert.deepEqual(consoleErrors, []);
    console.log('PASS: permission boundaries, sensor values, denials, missing/busy devices, timeouts, late results, hidden/pagehide cleanup, screen ended, no network requests');

    await page.locator('#xr-scan').click();
    for (const width of [320, 390, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `overflow at ${width}px`);
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: `/tmp/browser-xray-${width}.png` });
    }
    await page.locator('#motion-lab').screenshot({ path: '/tmp/browser-xray-motion.png' });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await start('motion'); await state('motion', 'Granted');
    await page.evaluate(() => sensorEvent('deviceorientation', { alpha: 50, beta: 20, gamma: -40 }));
    await state('motion', 'Active');
    assert.equal(await page.locator('#xr-phone').evaluate(element => element.style.transform), '');
    await page.locator('#xr-reset').click();
    console.log('PASS: 320/390/768/1440px layouts, reduced motion');

    const unsupported = await context.newPage();
    await unsupported.addInitScript(() => {
      Object.defineProperty(navigator, 'mediaDevices', { value: undefined });
      Object.defineProperty(navigator, 'geolocation', { value: undefined, configurable: true });
      delete window.DeviceMotionEvent; delete window.DeviceOrientationEvent;
    });
    await unsupported.goto(`${base}/browser-xray`);
    for (const key of ['motion', 'location', 'camera', 'microphone', 'screen']) {
      assert.equal(await unsupported.locator(`[data-enable="${key}"]`).isDisabled(), true);
    }
    await unsupported.close();
    const insecure = await context.newPage();
    await insecure.addInitScript(() => Object.defineProperty(window, 'isSecureContext', { value: false }));
    await insecure.goto(`${base}/browser-xray`);
    assert.equal(await insecure.locator('#xr-insecure').isVisible(), true);
    for (const key of ['motion', 'location', 'camera', 'microphone', 'screen']) assert.equal(await insecure.locator(`[data-enable="${key}"]`).isDisabled(), true);
    assert.deepEqual(await insecure.evaluate(() => probe.calls), []);
    await insecure.close();
    console.log('PASS: unsupported APIs and simulated insecure context');
    await context.close();
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
