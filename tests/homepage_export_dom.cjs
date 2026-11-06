// Optional DOM regression: NODE_PATH=/path/to/jsdom/node_modules node tests/homepage_export_dom.cjs
// This verifies behavior, not browser rendering or responsive layout.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('jsdom');
(async () => {
  const dom = new JSDOM('<div class="ai-lab" data-tool="ai-website-design-deepseek"></div>', {runScripts:'outside-only',url:'https://example.test'});
  try {
    const w = dom.window;
    const exports = [];
    let pending;
    w.Blob = Blob;
    w.URL.createObjectURL = blob => {pending=blob;return 'blob:local-export';};
    w.URL.revokeObjectURL = () => {};
    w.HTMLAnchorElement.prototype.click = function () {exports.push({name:this.download,blob:pending});};
    const source = process.env.LAB_SCRIPT || path.join(__dirname,'../authentic_dynamics/static/js/ai-lab.js');
    w.eval(fs.readFileSync(source,'utf8'));
    const root = w.document.querySelector('.ai-lab');
    const set = (name,value) => {root.querySelector(`[name="${name}"]`).value=value;};
    const click = action => root.querySelector(`[data-action="${action}"]`).click();
    const latest = () => exports.at(-1).blob.text();
    set('business','First business');set('offer','First service');
    click('download');
    assert.match(await latest(),/First service by First business/);
    click('go');
    set('business','Maple & Main');set('offer','Bakery');set('location','Harrisburg, PA');
    set('audience','Our neighbors');set('promise','Fresh bread <daily>');
    set('phone','717-555-0123');set('action','Call the bakery');
    click('download');
    const updated = await latest();
    for (const text of ['Bakery by Maple &amp; Main','Harrisburg, PA','Fresh bread &lt;daily&gt;','tel:7175550123','Call the bakery']) assert.ok(updated.includes(text),text);
    assert.ok(!updated.includes('First business'));
    assert.equal(root.querySelector('iframe').getAttribute('srcdoc'),updated);
    assert.equal(exports.at(-1).name,'homepage-preview.html');
    const count=exports.length;
    for (const [name,value,message,valid] of [
      ['business','','Enter a business name and main service.','Maple & Main'],
      ['offer','','Enter a business name and main service.','Bakery'],
      ['phone','123','Enter a valid phone number or leave it empty.','7175550123'],
    ]) {
      set(name,value);click('download');
      assert.equal(exports.length,count,'Invalid edits must not export a stale preview');
      assert.equal(root.querySelector('[data-status]').textContent,message);
      set(name,valid);
    }
    set('phone','');set('promise','');click('download');
    const recovered=await latest();
    assert.ok(recovered.includes('Helping Our neighbors.'));
    assert.ok(recovered.includes('Contact details pending.'));
    assert.ok(!recovered.includes('tel:'));
    console.log('PASS: first export, edited export, escaping, preview parity, invalid edits blocked, recovery');
  } finally {dom.window.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
