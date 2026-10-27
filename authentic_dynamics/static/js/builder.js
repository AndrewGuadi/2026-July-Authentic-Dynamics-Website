const KEY = 'ad-showroom-v1';
const $ = (s, p = document) => p.querySelector(s);
const el = (tag, text, cls) => { const n = document.createElement(tag); if (text) n.textContent = text; if (cls) n.className = cls; return n; };
let storageOK = true;
function readState() {
  try { const v = JSON.parse(localStorage.getItem(KEY) || '{}'); return v && typeof v === 'object' && !Array.isArray(v) ? v : {}; }
  catch { storageOK = false; return {}; }
}
let state = readState();
window.addEventListener('storage', event => { if (event.key === KEY) state = readState(); });
function save(message = 'Saved in this browser.') {
  try { localStorage.setItem(KEY, JSON.stringify(state)); storageOK = true; }
  catch { storageOK = false; }
  const status = $('#storage-status') || $('#preview-status');
  if (status) status.textContent = storageOK ? message : 'Browser storage is unavailable. You can still explore, but changes may not survive a reload.';
}
function favorites() { return Array.isArray(state.favorites) ? state.favorites.filter(v => typeof v === 'string') : []; }
function favorite(id, button) {
  const values = favorites(); state.favorites = values.includes(id) ? values.filter(x => x !== id) : [...values, id];
  save(); button.setAttribute('aria-pressed', String(state.favorites.includes(id))); button.textContent = state.favorites.includes(id) ? '♥ Saved' : '♡ Save';
}
function saveButton(id) { const b = el('button', favorites().includes(id) ? '♥ Saved' : '♡ Save', 'builder-link'); b.type = 'button'; b.setAttribute('aria-pressed', String(favorites().includes(id))); b.addEventListener('click', () => favorite(id, b)); return b; }
function link(text, href, cls) { const a = el('a', text, cls); a.href = href; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a; }
async function json(path) { const r = await fetch(path); if (!r.ok) throw Error('Could not load the catalog. Please refresh.'); return r.json(); }
const cache = new Map();
async function source(path) {
  if (!cache.has(path)) cache.set(path, fetch(path).then(r => { if (!r.ok) throw Error('This design could not load. Please try another.'); return r.text(); }));
  return cache.get(path);
}
// Sources are curated snapshots. Never execute upstream scripts or send preview forms.
function previewHTML(html, basePath) {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  doc.querySelectorAll('script,iframe,object,embed,base,meta[http-equiv],link[rel="import"]').forEach(n => n.remove());
  for (const n of doc.querySelectorAll('*')) for (const a of [...n.attributes]) {
    if (/^on/i.test(a.name) || /^(action|formaction|srcdoc|autofocus)$/i.test(a.name) || /^javascript:/i.test(a.value.trim())) n.removeAttribute(a.name);
  }
  doc.querySelectorAll('a').forEach(a => { if (a.getAttribute('href')?.startsWith('tel:')) a.dataset.contactType = 'phone'; if (a.getAttribute('href')?.startsWith('mailto:')) a.dataset.contactType = 'email'; if (!a.getAttribute('href')?.startsWith('#')) a.setAttribute('href', '#'); a.removeAttribute('target'); });
  const csp = doc.createElement('meta'); csp.httpEquiv = 'Content-Security-Policy';
  csp.content = "default-src 'none'; script-src 'none'; style-src 'self' 'unsafe-inline' https:; img-src 'self' data: https:; font-src 'self' data: https:; form-action 'none'; frame-src 'none'; connect-src 'none'; base-uri 'self'";
  const base = doc.createElement('base'); base.href = new URL(basePath, location.origin).href;
  doc.head.prepend(base); doc.head.prepend(csp);
  const style = doc.createElement('style'); style.textContent = '.reveal,.fade-in,.animate-on-scroll,[data-reveal]{opacity:1!important;transform:none!important;visibility:visible!important}@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}'; doc.head.append(style);
  return '<!doctype html>' + doc.documentElement.outerHTML;
}
function hydrate(doc, template, profile = {}, options = {}) {
  const clean = key => typeof profile[key] === 'string' ? profile[key].slice(0, 160) : '';
  const name = clean('name');
  if (name) {
    const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT); const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    let replaced = false;
    for (const n of nodes) if (!['STYLE','SCRIPT'].includes(n.parentElement.tagName) && n.textContent.includes(template.brand)) { n.textContent = n.textContent.split(template.brand).join(name); replaced = true; }
    // Some templates split their brand over multiple spans.
    if (!replaced) { const brand = doc.querySelector('.navbar-brand,.logo,.brand'); if (brand) brand.textContent = name; }
    doc.title = name + ' — design example';
  }
  if (clean('tagline') && doc.querySelector('h1')) doc.querySelector('h1').textContent = clean('tagline');
  if (clean('location')) { const address = doc.querySelector('address'); if (address) address.textContent = clean('location'); }
  doc.querySelectorAll('a[data-contact-type="phone"]').forEach(n => { if (clean('phone')) n.textContent = clean('phone'); });
  doc.querySelectorAll('a[data-contact-type="email"]').forEach(n => { if (clean('email')) n.textContent = clean('email'); });
  // These links were neutralized already, so match the original labels as well.
  const banner = doc.createElement('div'); banner.className = 'ad-preview-business';
  banner.style.cssText = 'padding:14px 20px;background:#182b25;color:white;font:14px/1.5 sans-serif;position:relative;z-index:10000';
  banner.textContent = [name || template.name, clean('location'), clean('phone'), clean('email')].filter(Boolean).join(' · ') + ' | Design example • sample content • actions disabled'; doc.body.prepend(banner);
  const color = /^#[0-9a-f]{6}$/i.test(options.color || '') ? options.color : '#c65a32';
  const style = doc.createElement('style'); style.id = 'ad-customization';
  style.textContent = `:root{--brand:${color};--bs-primary:${color};--color-primary:${color};--accent:${color}} .btn-primary,.btn-solid,.btn--primary,.button--primary{background:${color}!important;border-color:${color}!important}`;
  if (['sans-serif','Georgia, serif'].includes(options.font)) style.textContent += `body,button,input,h1,h2,h3{font-family:${options.font}!important}`;
  doc.head.append(style);
  doc.addEventListener('click', e => { if (e.target.closest('a,button[type="submit"]')) e.preventDefault(); });
  doc.addEventListener('submit', e => e.preventDefault());
}
function fillFrame(frame, html, path, onload) { frame.onload = () => onload?.(frame.contentDocument); frame.srcdoc = previewHTML(html, path); }
async function catalog(data, components) {
  const industry = $('#industry'); industry.replaceChildren();
  for (const i of data.industries) { const o = el('option', i.name); o.value = i.id; industry.append(o); }
  industry.value = data.industries.some(i => i.id === state.industry) ? state.industry : data.industries[0].id;
  const form = $('#profile-form');
  for (const input of form.elements) if (input.name && typeof state.profile?.[input.name] === 'string') input.value = state.profile[input.name];
  function capture() { state.profile = Object.fromEntries(new FormData(form)); state.industry = industry.value; save(); }
  form.addEventListener('submit', e => { e.preventDefault(); capture(); });
  form.addEventListener('input', capture);
  function renderTemplates() {
    state.industry = industry.value; save('Your choices stay in this browser.');
    $('#industry-heading').textContent = data.industries.find(i => i.id === industry.value).name;
    const templates = data.templates.filter(t => t.industry === industry.value && (!$('#saved-only').checked || favorites().includes(t.id)));
    $('#template-status').textContent = `${templates.length} designs${$('#saved-only').checked ? ' saved' : ' to explore'}.`;
    const grid = $('#template-grid'); grid.replaceChildren();
    for (const t of templates) {
      const card = el('article', '', 'builder-card');
      const art = el('div', '', 'mini-site'); const frame = el('iframe'); frame.title = t.name + ' thumbnail'; frame.tabIndex = -1; frame.loading = 'lazy'; frame.setAttribute('sandbox', 'allow-same-origin'); art.append(frame);
      const body = el('div', '', 'builder-card-content'); body.append(el('small', t.provider + ' / ' + (t.adapted ? 'Adaptable foundation' : 'Industry foundation')), el('h3', t.name));
      body.append(el('p', t.adapted ? 'An adjacent design to explore with your business details. Industry content still needs tailoring.' : 'Try this design with your business name, contact details and headline.'));
      const actions = el('div', '', 'builder-card-actions'); const open = link('Try it on ↗', '/try-builder/preview#' + encodeURIComponent(t.id), 'builder-button'); open.addEventListener('click', capture);
      const saved = saveButton(t.id); saved.addEventListener('click', () => { if ($('#saved-only').checked) renderTemplates(); });
      actions.append(open, saved, link('Source ↗', t.source)); body.append(actions); card.append(art, body); grid.append(card);
      source(t.path).then(html => { if (card.isConnected) fillFrame(frame, html, t.path, doc => hydrate(doc, t, {}, {color: '#c65a32'})); }).catch(() => { art.textContent = 'Open to explore this design'; });
    }
  }
  industry.addEventListener('change', renderTemplates); $('#saved-only').addEventListener('change', renderTemplates); renderTemplates();
  const category = $('#component-category');
  for (const c of [...new Set(components.map(c => c.category))]) { const o = el('option', c); o.value = c; category.append(o); }
  function renderComponents() {
    const grid = $('#component-grid'); grid.replaceChildren();
    const filtered = components.filter(c => category.value === 'all' || c.category === category.value);
    for (const c of filtered) {
      const card = el('article', '', 'builder-card'); const frame = el('iframe', '', 'component-demo'); frame.title = `${c.category} by ${c.author}`; frame.loading = 'lazy'; frame.setAttribute('sandbox', 'allow-same-origin');
      const body = el('div', '', 'builder-card-content'); body.append(el('small', c.category), el('h3', c.name), el('p', 'By ' + c.author)); const actions = el('div', '', 'builder-card-actions'); actions.append(saveButton(c.id), link('Uiverse source ↗', c.source)); body.append(actions); card.append(frame, body); grid.append(card);
      source(c.path).then(html => { if (card.isConnected) fillFrame(frame, `<html><head><style>body{margin:0;min-height:185px;display:grid;place-items:center;background:#eef0eb;color:#172e25;padding:12px;box-sizing:border-box}</style></head><body>${html}</body></html>`, c.path); }).catch(() => { body.append(el('p','Component preview unavailable.')); });
    }
    $('#component-status').textContent = `${filtered.length} components. Save buttons to try them in a website preview.`;
  }
  category.addEventListener('change', renderComponents); renderComponents();
  $('#clear-data').addEventListener('click', () => { state = {}; try { localStorage.removeItem(KEY); } catch { storageOK = false; } form.reset(); industry.selectedIndex = 0; $('#saved-only').checked = false; renderTemplates(); renderComponents(); save('Saved details and favorites cleared.'); });
}
async function preview(data, components) {
  let id; try { id = decodeURIComponent(location.hash.slice(1)); } catch { id = ''; }
  const t = data.templates.find(t => t.id === id);
  if (!t) { $('#preview-name').textContent = 'Choose a design first'; $('#preview-status').textContent = 'Return to the showroom and select Try it on.'; return; }
  $('#preview-name').textContent = t.name; $('#preview-source').href = t.source;
  const options = state.combinations?.[id] || {}; const color = $('#preview-color'), font = $('#preview-font'), button = $('#preview-button'), width = $('#preview-width');
  color.value = /^#[0-9a-f]{6}$/i.test(options.color || '') ? options.color : state.profile?.color || '#c65a32';
  if (['original','sans-serif','Georgia, serif'].includes(options.font)) font.value = options.font;
  const buttons = components.filter(c => c.category === 'Buttons' && favorites().includes(c.id));
  for (const c of buttons) { const o = el('option', `${c.name} / ${c.author}`); o.value = c.id; button.append(o); }
  if (buttons.some(c => c.id === options.button)) button.value = options.button;
  const html = await source(t.path); const frame = $('#website-preview'); let generation = 0;
  async function render() {
    const token = ++generation;
    const component = buttons.find(c => c.id === button.value); const componentHTML = component ? await source(component.path) : null;
    if (token !== generation) return;
    fillFrame(frame, html, t.path, doc => {
      hydrate(doc, t, state.profile, {color:color.value,font:font.value});
      if (componentHTML) {
        const parsed = new DOMParser().parseFromString(previewHTML(componentHTML, component.path), 'text/html');
        const target = doc.querySelector('a.btn,button.btn,.btn-primary,.btn-solid,main a[class*="btn"],.hero a');
        if (target) { const host = doc.createElement('span'); const shadow = host.attachShadow({mode:'open'}); shadow.append(...[...parsed.head.querySelectorAll('style'), ...parsed.body.childNodes].map(n => doc.importNode(n,true))); const label = shadow.querySelector('.text') || shadow.querySelector('button'); if (label) label.textContent = target.textContent.trim() || 'Learn more'; target.replaceWith(host); }
        else $('#preview-status').textContent = 'Saved button selected; this layout needs a manual placement to apply it.';
      }
    });
  }
  for (const input of [color,font,button]) input.addEventListener('change', () => render().catch(error => { $('#preview-status').textContent = error.message; }));
  width.addEventListener('change', () => { frame.style.width = width.value; frame.style.maxWidth = '100%'; });
  $('#save-preview').addEventListener('click', () => { state = readState(); state.combinations = state.combinations && typeof state.combinations === 'object' ? state.combinations : {}; state.combinations[id] = {color:color.value,font:font.value,button:button.value}; if (!favorites().includes(id)) state.favorites = [...favorites(),id]; save('This design and customization are saved in this browser.'); });
  $('#reset-preview').addEventListener('click', () => { color.value = state.profile?.color || '#c65a32'; font.value = 'original'; button.value = ''; render(); });
  await render();
}
try {
  const [data, components] = await Promise.all([json('/static/builder/catalog.json'),json('/static/builder/components.json')]);
  if ($('#template-grid')) await catalog(data,components); else await preview(data,components);
} catch (error) { const status = $('#template-status') || $('#preview-status'); if (status) status.textContent = error.message; }
