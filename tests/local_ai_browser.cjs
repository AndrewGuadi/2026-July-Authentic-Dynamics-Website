// Optional browser regression check. Install Playwright outside the Python environment.
// Run with LOCAL_AI_BASE_URL pointing to a running Flask development server.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = process.env.LOCAL_AI_BASE_URL || 'http://127.0.0.1:5055';
const runtimeURL = 'https://esm.run/@mlc-ai/web-llm@0.2.85';
const phrase = 'This is a private test phrase 938472';

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    // Probe actual host support separately from simulated adapters and engine.
    const probe = await browser.newPage();
    await probe.goto(`${base}/tools/local-ai`);
    console.log('Actual WebGPU:', await probe.evaluate(async () => {
      const adapter = await navigator.gpu?.requestAdapter();
      return { available: Boolean(navigator.gpu), adapter: Boolean(adapter),
        shaderF16: adapter?.features.has('shader-f16') || false };
    }));
    await probe.close();

    for (const mode of ['unavailable', 'no-adapter', 'no-f16', 'adapter-error', 'load-error', 'ready']) {
      const page = await browser.newPage({ viewport: { width: 375, height: 812 } });
      const requests = [];
      const errors = [];
      page.on('request', request => requests.push({ url: request.url(), method: request.method(), body: request.postData() }));
      page.on('pageerror', error => errors.push(error.message));
      await page.addInitScript(mode => {
        Object.defineProperty(navigator, 'gpu', { value: mode === 'unavailable' ? undefined : {
          requestAdapter: async () => {
            if (mode === 'adapter-error') throw new Error('Adapter unavailable');
            return mode === 'no-adapter' ? null : { features: new Set(mode === 'no-f16' ? [] : ['shader-f16']) };
          },
        } });
      }, mode);
      await page.route(runtimeURL, route => route.fulfill({ contentType: 'text/javascript', body: `
        export async function CreateMLCEngine(model, options) {
          window.testModel = model;
          options.initProgressCallback({ progress: 0.5, text: 'Test download' });
          await new Promise(resolve => setTimeout(resolve, 100));
          if (${JSON.stringify(mode)} === 'load-error') throw new Error('Test loading failure');
          return { chat: { completions: { create: async function* (request) {
            window.testRequest = request;
            if (window.failGeneration) throw new Error('Private error: ' + request.messages[1].content);
            yield { choices: [{ delta: { content: '<img src=x onerror=alert(1)>' } }] };
            await new Promise(resolve => setTimeout(resolve, 300));
            yield { choices: [{ delta: { content: ' Safe text.' } }] };
          } } } };
        }
      ` }));
      await page.goto(`${base}/tools/local-ai`);
      assert.equal(await page.locator('#ai-prompt').isDisabled(), true);
      assert.equal(await page.locator('#ai-ask').isDisabled(), true);
      assert.equal(requests.some(request => request.url === runtimeURL), false);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      await page.locator('#ai-load').click();
      if (['unavailable', 'no-adapter', 'no-f16'].includes(mode)) {
        await page.waitForFunction(() => document.querySelector('#ai-status').textContent.startsWith('Unsupported'));
        assert.equal(requests.some(request => request.url === runtimeURL), false);
      } else if (mode === 'load-error' || mode === 'adapter-error') {
        await page.waitForFunction(() => document.querySelector('#ai-status').textContent.startsWith('Error:'));
        assert.equal(await page.locator('#ai-load').isEnabled(), true);
        assert.equal(await page.locator('#ai-prompt').isDisabled(), true);
      } else {
        await page.waitForFunction(() => document.querySelector('#ai-status').textContent.startsWith('AI ready'));
        assert.equal(await page.evaluate(() => window.testModel), 'SmolLM2-360M-Instruct-q4f16_1-MLC');
        assert.equal(await page.locator('#ai-progress').evaluate(element => element.value), 1);
        await page.locator('#ai-ask').click();
        assert.match(await page.locator('#ai-status').textContent(), /between 1 and 4,000/);
        await page.locator('#ai-prompt').evaluate(element => { element.value = 'x'.repeat(4001); });
        await page.locator('#ai-ask').click();
        assert.equal(await page.evaluate(() => window.testRequest), undefined);
        await page.locator('#ai-prompt').fill(phrase);
        const networkStart = requests.length;
        await page.locator('#ai-ask').click();
        await page.waitForFunction(() => document.querySelector('#ai-output').textContent.startsWith('<img'));
        assert.equal(await page.locator('#ai-ask').isDisabled(), true);
        await page.waitForFunction(() => document.querySelector('#ai-status').textContent.startsWith('Finished'));
        assert.equal(await page.locator('#ai-output img').count(), 0);
        assert.equal(await page.evaluate(() => window.testRequest.messages[1].content), phrase);
        assert.equal(await page.evaluate(() => window.testRequest.stream), true);
        assert.deepEqual(requests.slice(networkStart), []);
        assert.equal(requests.some(request => JSON.stringify(request).includes(phrase)), false);
        await page.evaluate(() => { window.failGeneration = true; });
        await page.locator('#ai-ask').click();
        await page.waitForFunction(() => document.querySelector('#ai-status').textContent.startsWith('Error:'));
        assert.equal(await page.locator('#ai-ask').isEnabled(), true);
        assert.equal(await page.locator('#ai-output').textContent().then(text => text.includes(phrase)), false);
        await page.screenshot({ path: '/tmp/local-ai-mobile.png', fullPage: true });
        await page.setViewportSize({ width: 1440, height: 1000 });
        await page.screenshot({ path: '/tmp/local-ai-desktop.png', fullPage: true });
      }
      assert.deepEqual(errors, []);
      console.log(`PASS ${mode}`);
      await page.close();
    }
    console.log('Simulated engine: streamed text, XSS, limits, error recovery and zero generation requests passed. Real model inference still requires a compatible GPU.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
