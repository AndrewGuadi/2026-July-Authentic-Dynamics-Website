// Run against Flask on port 5055; override with LAB_BASE_URL.
// CHROMIUM_PATH optionally selects an installed Chromium executable.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const {chromium} = require('playwright');
(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {})});
  const base = process.env.LAB_BASE_URL || 'http://127.0.0.1:5055';
  try {
    for (const width of [1440, 390, 360, 320]) {
      const context = await browser.newContext({viewport:{width,height:900},isMobile:width<600,hasTouch:width<600,acceptDownloads:true});
      const page = await context.newPage();
      const errors = [], writes = [];
      page.on('pageerror', e => errors.push(e.message));
      page.on('request', r => {if(r.method() !== 'GET') writes.push(r.url());});
      await page.goto(base+'/tools/ai-lab/ai-website-design-deepseek');
      const root = page.locator('.ai-lab');
      const field = name => root.locator(`[name="${name}"]`);
      const exportHTML = async () => {
        const pending = page.waitForEvent('download');
        await root.getByRole('button',{name:'Download HTML',exact:true}).click();
        const download = await pending;
        assert.equal(download.suggestedFilename(),'homepage-preview.html');
        return fs.readFile(await download.path(),'utf8');
      };
      await field('business').fill('First business');
      await field('offer').fill('First service');
      // Export must work without building a preview first.
      assert.match(await exportHTML(), /First service by First business/);
      await root.getByRole('button',{name:'Build my preview',exact:true}).click();
      await field('business').fill('Maple & Main');
      await field('offer').fill('Bakery');
      await field('location').fill('Harrisburg, PA');
      await field('audience').fill('Our neighbors');
      await field('promise').fill('Fresh bread <daily>');
      await field('phone').fill('717-555-0123');
      await field('action').fill('Call the bakery');
      const updated = await exportHTML();
      for (const text of ['Bakery by Maple &amp; Main','Harrisburg, PA','Fresh bread &lt;daily&gt;','tel:7175550123','Call the bakery']) assert.ok(updated.includes(text), text);
      assert.ok(!updated.includes('First business'));
      assert.equal(await root.locator('iframe').getAttribute('srcdoc'),updated);
      assert.equal(await root.locator('iframe').getAttribute('sandbox'),'');
      let downloads = 0;
      page.on('download',()=>downloads++);
      for (const [name, invalid, message, valid] of [
        ['business','', 'Enter a business name and main service.', 'Maple & Main'],
        ['offer','', 'Enter a business name and main service.', 'Bakery'],
        ['phone','123', 'Enter a valid phone number or leave it empty.', '7175550123'],
      ]) {
        await field(name).fill(invalid);
        await root.getByRole('button',{name:'Download HTML',exact:true}).click();
        assert.equal(await root.locator('[data-status]').textContent(),message);
        await page.waitForTimeout(100);
        assert.equal(downloads,0,'Invalid edits must not download the previous preview');
        await field(name).fill(valid);
      }
      await field('phone').fill('');
      await field('promise').fill('');
      const recovered = await exportHTML();
      assert.ok(recovered.includes('Helping Our neighbors.'));
      assert.ok(recovered.includes('Contact details pending.'));
      assert.ok(!recovered.includes('tel:'));
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
      await page.screenshot({path:`/tmp/homepage-export-${width}.png`,fullPage:true});
      if(width<600) {
        await page.getByRole('button',{name:'Open menu',exact:true}).click();
        assert.equal(await page.locator('.menu').getAttribute('aria-expanded'),'true');
        await page.locator('#nav').getByRole('link',{name:'Websites',exact:true}).click();
        assert.ok(page.url().endsWith('/websites'));
        await page.goBack();
      }
      await page.getByRole('link',{name:'Read the research guide'}).click();
      assert.ok(page.url().endsWith('/blog/ai-website-design-deepseek'));
      await page.goBack();
      await page.getByRole('link',{name:'All AI guides'}).click();
      assert.ok(page.url().endsWith('/blog'));
      assert.deepEqual(errors,[]);
      assert.deepEqual(writes,[]);
      await context.close();
      console.log(`Homepage exports, validation, navigation and overflow passed at ${width}px`);
    }
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
