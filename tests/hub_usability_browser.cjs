/* Run only against an isolated app with synthetic Hub records. */
const assert = require('node:assert/strict');
const {chromium} = require('playwright');
const base = process.env.HUB_BASE_URL || 'http://127.0.0.1:5058';
(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {}), args:['--no-sandbox']});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000}});
    page.setDefaultTimeout(10000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`${base}/hub`);
    await page.getByLabel('Email address').fill(process.env.HUB_TEST_EMAIL || 'preview@example.test');
    await page.getByLabel('Password', {exact:true}).fill(process.env.HUB_TEST_PASSWORD || 'preview-password-only');
    await page.getByRole('button',{name:/Sign in/}).click();
    await page.waitForURL('**/hub');
    await page.goto(`${base}/hub/businesses/new`);
    await page.getByLabel('Name', {exact:false}).first().fill('Hub usability sample business');
    await page.getByRole('button',{name:'Save record'}).click();
    await page.waitForURL(/\/hub\/businesses\/[a-z0-9-]+$/);
    await page.goto(`${base}/hub/projects/new`);
    await page.locator('[name="business_id"]').selectOption({label:'Hub usability sample business'});
    await page.getByLabel('Title', {exact:false}).fill('Hub usability sample project');
    await page.getByRole('button',{name:'Save record'}).click();
    await page.getByRole('button',{name:'Apply website project template'}).click();
    await page.goto(`${base}/hub/payments/new`);
    await page.locator('[name="business_id"]').selectOption({label:'Hub usability sample business'});
    await page.getByLabel('Amount', {exact:false}).fill('1.234');
    await page.getByLabel('Received On', {exact:false}).fill('2026-10-20');
    await page.getByLabel('Method', {exact:false}).fill('check');
    await page.locator('.hub-form').evaluate(form => { form.noValidate=true; });
    await page.getByRole('button',{name:'Save record'}).click();
    await page.getByRole('heading',{name:'Your changes have not been saved.'}).waitFor();
    assert.equal(await page.getByLabel('Amount', {exact:false}).inputValue(),'1.234');
    await page.getByRole('link',{name:/Amount: Enter an amount/}).click();
    assert.equal(await page.evaluate(()=>document.activeElement.id),'field-amount_minor');
    await page.getByLabel('Amount', {exact:false}).fill('123.45');
    assert.equal(await page.getByLabel('Amount', {exact:false}).evaluate(el=>el.checkValidity()),true);
    await page.getByRole('button',{name:'Save record'}).click();
    await page.waitForURL(url => /\/hub\/payments\/[a-f0-9-]{36}$/.test(url.pathname));
    assert.match(await page.locator('.hub-details').innerText(),/123\.45/);
    await page.goto(`${base}/hub/tasks/new`);
    await page.getByLabel('Project', {exact:false}).selectOption({label:'Hub usability sample project'});
    await page.getByLabel('Title', {exact:false}).fill('Clock change example');
    await page.getByLabel('Due At', {exact:false}).fill('2026-11-01T01:30');
    await page.getByRole('button',{name:'Save record'}).click();
    await page.getByRole('heading',{name:'Your changes have not been saved.'}).waitFor();
    assert.match(await page.getByRole('alert').innerText(),/occurs twice/);
    for (const width of [360,390,412,1440]) {
      await page.setViewportSize({width,height:900});
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth), `form overflow ${width}`);
      await page.screenshot({path:`/tmp/ad-browser/hub-form-${width}.png`,fullPage:true});
    }
    await page.goto(`${base}/hub/projects`);
    await page.getByRole('link').filter({hasText:'Hub usability sample project'}).click();
    await page.getByRole('link',{name:/Open project board/}).click();
    const card=page.locator('.hub-card').filter({hasText:'Discovery call'});
    const lanes=await page.locator('.hub-lane').evaluateAll(els=>els.map(el=>({id:el.dataset.lane,title:el.querySelector('h2').textContent})));
    const target=lanes.find(l=>l.title==='Build');
    await card.locator('select').selectOption(target.id);
    await card.getByRole('button',{name:'Move',exact:true}).click();
    await page.getByRole('status').filter({hasText:'Move saved.'}).waitFor();
    assert.equal(await card.evaluate(el=>el.closest('.hub-lane').dataset.lane),target.id);
    assert.equal(await page.evaluate(()=>document.activeElement.textContent.trim()),'Move');
    const failTarget=lanes.find(l=>l.id!==target.id);
    await page.route('**/hub/tasks/*/move', route=>route.fulfill({status:500,contentType:'application/json',body:'{"error":"test failure"}'}));
    await card.locator('select').selectOption(failTarget.id);
    await card.getByRole('button',{name:'Move',exact:true}).click();
    await page.getByRole('status').filter({hasText:'The move was not confirmed.'}).waitFor();
    assert.equal(await card.evaluate(el=>el.closest('.hub-lane').dataset.lane),target.id);
    assert.equal(await card.locator('select').inputValue(),target.id);
    assert.equal(await card.locator('select').isEnabled(),true);
    await page.emulateMedia({reducedMotion:'reduce'});
    assert.equal(await card.evaluate(el=>getComputedStyle(el).animationName),'none');
    for(const width of [360,390,412]){
      await page.setViewportSize({width,height:900});
      const layout=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,boxes:[...document.querySelectorAll('.hub-board,.hub-workspace,.hub-main,.hub-topbar,.hub-heading,.hub-sidebar')].map(el=>({name:el.className,right:el.getBoundingClientRect().right,width:el.getBoundingClientRect().width}))}));
      await page.screenshot({path:`/tmp/ad-browser/hub-board-${width}.png`,fullPage:true});
      assert(layout.scroll<=layout.width,`board overflow ${width}: ${JSON.stringify(layout)}`);
    }
    assert.deepEqual(errors,[]);
    console.log('Hub usability: money validation/retention, precise save, workspace-time DST error, field focus, mobile form/board overflow, confirmed keyboard move/failure recovery, reduced motion and runtime errors passed (Chromium viewport emulation).');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
