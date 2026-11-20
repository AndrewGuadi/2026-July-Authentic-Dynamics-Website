const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const {chromium} = require('playwright');
(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {})});
  const base = process.env.EVENT_BASE_URL || 'http://127.0.0.1:5055';
  try {
    for (const width of [1440, 390, 360, 320]) {
      const context = await browser.newContext({viewport:{width,height:900},isMobile:width<600,hasTouch:width<600,acceptDownloads:true});
      const page = await context.newPage();
      // Exercise success, permission denial and delayed writes deterministically.
      await page.addInitScript(() => {
        window.copyMode = 'success';
        Object.defineProperty(navigator, 'clipboard', {configurable:true,value:{
          writeText: async text => {
            if (window.copyMode === 'deny') throw new Error('Permission denied');
            if (window.copyMode === 'delay') await new Promise(resolve => {window.finishCopy = resolve;});
            window.copiedEstimate = text;
          }
        }});
      });
      const errors = [], requests = [];
      page.on('pageerror', e => errors.push(e.message));
      page.on('request', r => requests.push({url:r.url(),method:r.method()}));
      await page.goto(base+'/tools/');
      await page.getByRole('link',{name:'Plan an event'}).click();
      assert.equal(await page.locator('#event-result').isHidden(),true);
      await page.locator('#calculate').click();
      assert.equal(await page.locator('#booth').evaluate(el=>el.validity.valueMissing),true);
      await page.locator('#example').click();
      await page.locator('#calculate').click();
      assert.equal(await page.locator('#break-even-result').textContent(),'42');
      assert.equal(await page.locator('#target-result').textContent(),'74');
      assert.equal(await page.locator('#profit-result').textContent(),'$555.00');
      const downloading = page.waitForEvent('download');
      await page.locator('#download').click();
      const download = await downloading;
      const report = await fs.readFile(await download.path(),'utf8');
      assert.match(report,/Estimated event profit \/ loss: \$555.00/);
      await page.locator('#copy-estimate').click();
      assert.equal(await page.evaluate(()=>window.copiedEstimate),report);
      assert.match(await page.locator('#event-status').textContent(),/Estimate copied/);
      assert.equal(await page.locator('#copy-fallback').isHidden(),true);
      await page.evaluate(()=>{window.copyMode='deny';});
      await page.locator('#copy-estimate').click();
      await page.locator('#copy-text').waitFor({state:'visible'});
      assert.equal(await page.locator('#copy-text').inputValue(),report);
      assert.equal(await page.locator('#copy-text').evaluate(el=>document.activeElement===el && el.selectionStart===0 && el.selectionEnd===el.value.length),true);
      assert.match(await page.locator('#event-status').textContent(),/Automatic copying is unavailable/);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
      await page.screenshot({path:`/tmp/event-${width}.png`,fullPage:true});
      await page.locator('#transactions').fill('10');
      assert.equal(await page.locator('#copy-text').inputValue(),'');
      assert.equal(await page.locator('#copy-fallback').isHidden(),true);
      assert.equal(await page.locator('#event-result').isHidden(),true);
      await page.locator('#calculate').click();
      assert.equal(await page.locator('#profit-result').textContent(),'-$304.50');
      // No clipboard API: still provide the complete current report.
      await page.evaluate(()=>{window.savedClipboard=navigator.clipboard;Object.defineProperty(navigator,'clipboard',{configurable:true,value:undefined});});
      await page.locator('#copy-estimate').click();
      assert.match(await page.locator('#copy-text').inputValue(),/Estimated event profit \/ loss: -\$304.50/);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
      await page.locator('#calculate').click();
      assert.equal(await page.locator('#copy-fallback').isHidden(),true);
      // A late clipboard promise cannot announce success over changed inputs.
      await page.evaluate(()=>{Object.defineProperty(navigator,'clipboard',{configurable:true,value:window.savedClipboard});window.copyMode='delay';});
      await page.locator('#copy-estimate').click();
      await page.locator('#fee').fill('101');
      await page.evaluate(async()=>{window.finishCopy();await Promise.resolve();});
      assert.match(await page.locator('#event-status').textContent(),/Numbers changed/);
      await page.locator('#calculate').click();
      assert.equal(await page.locator('#fee').evaluate(el=>el.validity.rangeOverflow),true);
      assert.equal(await page.locator('#event-result').isHidden(),true);
      await page.locator('#fee').fill('0');
      await page.locator('#cost').fill('15');
      await page.locator('#calculate').click();
      assert.equal(await page.locator('#break-even-result').textContent(),'Not reachable');
      await page.getByRole('button',{name:'Clear',exact:true}).click();
      assert.equal(await page.locator('#sale').inputValue(),'');
      assert.equal(await page.locator('#event-result').isHidden(),true);
      assert.deepEqual(errors,[]);
      assert.ok(requests.every(r=>r.url.startsWith(base)&&r.method==='GET'));
      assert.equal(await page.evaluate(()=>localStorage.length),0);
      if(width<600) {
        await page.getByRole('button',{name:'Open menu',exact:true}).click();
        assert.equal(await page.locator('.menu').getAttribute('aria-expanded'),'true');
        await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Websites',exact:true}).click();
        assert.ok(page.url().endsWith('/websites'));
        await page.goBack();
      }
      await page.getByRole('link',{name:'Make a QR code for your menu or website'}).click();
      assert.ok(page.url().endsWith('/tools/qr-code-maker'));
      await page.goBack();
      await page.getByRole('link',{name:'← All tools'}).click();
      assert.ok(page.url().endsWith('/tools/'));
      await context.close();
      console.log(`${width}px: calculations, validation, downloads, copy success/fallback/stale state, privacy, links and layout passed`);
    }
    const clipboardContext = await browser.newContext({permissions:['clipboard-read','clipboard-write']});
    const clipboardPage = await clipboardContext.newPage();
    await clipboardPage.goto(base+'/tools/event-break-even');
    await clipboardPage.locator('#example').click();
    await clipboardPage.locator('#calculate').click();
    await clipboardPage.locator('#copy-estimate').click();
    await clipboardPage.waitForFunction(()=>document.getElementById('event-status').textContent.startsWith('Estimate copied'));
    assert.match(await clipboardPage.evaluate(()=>navigator.clipboard.readText()),/Estimated event profit \/ loss: \$555.00/);
    await clipboardContext.close();
    console.log('Native Chromium clipboard write/read passed (permission granted).');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
