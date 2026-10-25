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
      assert.match(await fs.readFile(await download.path(),'utf8'),/Estimated event profit \/ loss: \$555.00/);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
      await page.screenshot({path:`/tmp/event-${width}.png`,fullPage:true});
      await page.locator('#transactions').fill('10');
      assert.equal(await page.locator('#event-result').isHidden(),true);
      await page.locator('#calculate').click();
      assert.equal(await page.locator('#profit-result').textContent(),'-$304.50');
      await page.locator('#fee').fill('101');
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
      console.log(`${width}px: calculations, validation, downloads, privacy, links and layout passed`);
    }
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
