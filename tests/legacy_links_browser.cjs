const assert = require('node:assert/strict');
const {chromium} = require('playwright');
(async () => {
 const browser = await chromium.launch({headless:true, ...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH}: {})});
 try {
  for (const width of [390,412,1440]) {
   const page=await browser.newPage({viewport:{width,height:900},hasTouch:width<500});
   const errors=[];page.on('pageerror',e=>errors.push(e.message));
   for (const [from,to] of [['/contact?intent=consult','/about-community#contact'],['/about','/about-community'],['/portfolio','/work']]) {
    const response=await page.goto((process.env.BASE_URL||'http://127.0.0.1:5068')+from);
    assert.equal(response.status(),200);assert.ok(page.url().endsWith(to));
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   }
   await page.goto((process.env.BASE_URL||'http://127.0.0.1:5068')+'/contact');
   await page.locator('#contact-form').waitFor({state:'visible'});
   assert.equal(await page.locator('#contact-form').evaluate(f=>f.checkValidity()),false);
   assert.equal(await page.locator('#contact-form').getAttribute('method'),'post');
   if(width<500){
    await page.locator('button.menu').click();
    assert.equal(await page.locator('button.menu').getAttribute('aria-expanded'),'true');
    await page.locator('#nav a[href="/websites"]').click();
    await page.waitForURL('**/websites');
   }
   assert.deepEqual(errors,[]);console.log(`PASS ${width}px redirects, overflow, contact validation, navigation`);
   await page.close();
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
