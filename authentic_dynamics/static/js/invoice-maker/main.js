import { blankInvoice, blankItem, calculateInvoice, sanitizeInvoice, validateInvoice, warnings, money, dueDate, nextNumber, duplicateInvoice, uuid, safeFilename, UNITS, PRESETS, LIMITS } from './core.js';
import * as storage from './storage.js';
import { optimizeLogo, checkImportedLogo } from './logo.js';
import { element, createRenderer } from './document.js';
import { downloadPDF } from './pdf.js';

const $ = selector => document.querySelector(selector);
let invoice = blankInvoice(), library = [], profile = null;
let revision = 0, dirty = false, libraryDirty = false, autosaveTimer = 0, frame = 0, logoVersion = 0;
let storageReady = false, printing = false, pdfBusy = false, initialized = false;
let writeQueue = Promise.resolve();
const renderDocument = createRenderer($('#im-document'));
const printStyle = document.createElement('style'); document.head.append(printStyle);
const say = text => { $('#im-status').textContent = text; };
const saveStatus = text => { $('#im-save-status').textContent = text; };
const get = path => path.split('.').reduce((value, key) => value[key], invoice);
function set(path, value) {
  const parts = path.split('.'); const key = parts.pop();
  const parent = parts.reduce((value, name) => value[name], invoice); parent[key] = value;
}
function queue(work) { const task = writeQueue.then(work, work); writeQueue = task.catch(() => {}); return task; }
function profileFrom(value) {
  return { business: structuredClone(value.business), logo: value.logo, currency: value.currency, paymentTerms: value.paymentTerms,
    notes: value.notes, paymentInstructions: value.paymentInstructions };
}
function syncField(path) {
  const control = $(`[data-field="${path}"]`);
  if (control) control.value = get(path);
}
function updatePrintSize(value) { printStyle.textContent = `@media print { @page { size: ${value === 'a4' ? 'A4' : 'letter'}; margin: 14mm; } }`; }
function render() {
  frame = 0;
  if (printing) return;
  let valid = true;
  try {
    validateInvoice(invoice);
    const totals = calculateInvoice(invoice);
    renderDocument(invoice, totals);
    $('#im-document').hidden = false; $('#im-errors').hidden = true;
    const alerts = warnings(invoice, totals);
    $('#im-warnings').textContent = alerts.join(' '); $('#im-warnings').hidden = !alerts.length;
    totals.lines.forEach((line, index) => { const amount = $(`[data-amount="${index}"]`); if (amount) amount.textContent = `Item amount: ${money(line.net, invoice.currency)}`; });
  } catch (error) {
    valid = false; $('#im-document').hidden = true;
    $('#im-errors').hidden = false; $('#im-errors').textContent = `${error.message} Preview and document exports pause until corrected. Your draft remains editable.`;
    $('#im-warnings').hidden = true;
    document.querySelectorAll('[data-amount]').forEach(node => { node.textContent = 'Correct the numeric inputs to calculate amounts.'; });
  }
  for (const action of ['pdf', 'print', 'export', 'save']) $(`[data-action="${action}"]`).disabled = !valid || (action === 'pdf' && pdfBusy);
  updatePrintSize(invoice.paperSize);
}
function scheduleRender() { if (!frame) frame = requestAnimationFrame(render); }
function autosave() {
  clearTimeout(autosaveTimer); autosaveTimer = 0;
  const snapshot = structuredClone(invoice), version = revision, remember = $('#im-remember').checked;
  saveStatus('Saving draft locally…');
  return queue(async () => {
    await storage.write('settings', snapshot, 'draft');
    if (remember) { await storage.write('settings', profileFrom(snapshot), 'profile'); }
  }).then(() => {
    storageReady = true;
    if (version === revision) { dirty = false; saveStatus('Draft saved on this device. Use Save Invoice to update your library copy.'); }
  }).catch(() => {
    if (version === revision) saveStatus('Unsaved changes: local storage is unavailable or full. Export JSON to keep a backup.');
  });
}
function changed() {
  revision += 1; dirty = true; libraryDirty = true;
  invoice.updatedAt = new Date().toISOString();
  if ($('#im-remember').checked) profile = profileFrom(invoice);
  saveStatus('Unsaved changes…');
  clearTimeout(autosaveTimer); autosaveTimer = setTimeout(autosave, 750);
  scheduleRender();
}
function discardAllowed() {
  return !(dirty || libraryDirty) || window.confirm('Replace the current invoice? Changes not saved to the invoice library will be replaced, including the working draft. Cancel to save or export a backup first.');
}

function field(path, label, value, options = {}) {
  const wrapper = element('label', label, 'im-field');
  const input = element(options.area ? 'textarea' : options.choices ? 'select' : 'input');
  if (options.choices) {
    for (const [key, text] of options.choices) { const option = element('option', text); option.value = key; input.append(option); }
  } else if (options.area) { input.rows = 3; input.maxLength = 2000; }
  else { input.type = options.date ? 'date' : 'text'; input.maxLength = options.numeric ? 20 : 300; if (options.numeric) input.inputMode = 'decimal'; if (options.date) { input.min = '1900-01-01'; input.max = '9999-12-31'; } }
  input.dataset.field = path; input.value = value; input.autocomplete = 'off';
  wrapper.append(input); return wrapper;
}
function check(path, label, value) {
  const wrapper = element('label', undefined, 'im-check'); const input = element('input');
  input.type = 'checkbox'; input.dataset.field = path; input.checked = value;
  wrapper.append(input, document.createTextNode(label)); return wrapper;
}
function rowButton(label, action, group, index) {
  const button = element('button', label); button.type = 'button'; button.dataset.rowAction = action; button.dataset.group = group; button.dataset.index = index; return button;
}
function renderRows(group) {
  const fragment = document.createDocumentFragment();
  invoice[group].forEach((entry, index) => {
    const row = element('div', undefined, 'im-row');
    row.append(element('h4', `${({ items: 'Item', charges: 'Charge', payments: 'Payment / credit', taxes: 'Tax' })[group]} ${index + 1}`));
    const fields = element('div', undefined, 'im-fields');
    if (group === 'items') {
      row.append(field(`items.${index}.description`, 'Description', entry.description, { area: true }));
      fields.append(field(`items.${index}.quantity`, 'Quantity', entry.quantity, { numeric: true }));
      const unit = field(`items.${index}.unit`, 'Unit', UNITS.includes(entry.unit) ? entry.unit : '__custom', { choices: [...UNITS.map(value => [value, value || 'No unit']), ['__custom', 'Custom…']] });
      const unitSelect = unit.querySelector('select'); delete unitSelect.dataset.field; unitSelect.dataset.unit = index;
      fields.append(unit);
      const custom = field(`items.${index}.unit`, 'Custom unit', entry.unit); custom.dataset.customUnit = index; custom.hidden = UNITS.includes(entry.unit); custom.querySelector('input').maxLength = 50; fields.append(custom);
      fields.append(field(`items.${index}.rate`, `Rate (${invoice.currency})`, entry.rate, { numeric: true }),
        field(`items.${index}.discountType`, 'Item discount', entry.discountType, { choices: [['none', 'None'], ['percent', 'Percentage'], ['fixed', 'Fixed amount']] }),
        field(`items.${index}.discount`, 'Discount value', entry.discount, { numeric: true }));
      row.append(fields, check(`items.${index}.taxable`, 'Taxable at the invoice’s tax rates', entry.taxable));
      const amount = element('p', '', 'im-row-amount'); amount.dataset.amount = index; row.append(amount);
    } else if (group === 'taxes') {
      fields.append(field(`taxes.${index}.name`, 'Tax name', entry.name), field(`taxes.${index}.rate`, 'Tax rate (%)', entry.rate, { numeric: true })); row.append(fields);
    } else {
      fields.append(field(`${group}.${index}.description`, 'Description', entry.description), field(`${group}.${index}.amount`, `Amount (${invoice.currency})`, entry.amount, { numeric: true }));
      if (group === 'payments') fields.append(field(`${group}.${index}.date`, 'Date (optional)', entry.date, { date: true }));
      row.append(fields);
      if (group === 'charges') row.append(check(`charges.${index}.taxable`, 'Taxable (not discounted)', entry.taxable));
    }
    const buttons = element('div', undefined, 'im-row-actions');
    if (group === 'items') {
      buttons.append(rowButton('Duplicate item', 'duplicate', group, index));
      const up = rowButton('Move up', 'up', group, index); up.disabled = index === 0;
      const down = rowButton('Move down', 'down', group, index); down.disabled = index === invoice.items.length - 1;
      buttons.append(up, down);
    }
    buttons.append(rowButton('Delete', 'delete', group, index)); row.append(buttons); fragment.append(row);
  });
  $(`#im-${group}`).replaceChildren(fragment);
}
function syncEditor() {
  document.querySelectorAll('#im-fields [data-field]').forEach(control => {
    if (/^(items|charges|payments|taxes)\./.test(control.dataset.field)) return;
    control.value = get(control.dataset.field);
  });
  for (const group of ['items', 'charges', 'payments', 'taxes']) renderRows(group);
  $('#im-logo-preview').hidden = !invoice.logo;
  if (invoice.logo) $('#im-logo-preview').src = invoice.logo.data; else $('#im-logo-preview').removeAttribute('src');
  $('#im-logo').value = '';
  $('#im-due-note').textContent = invoice.dueManual ? 'Due date manually overridden. Changing invoice date keeps this due date; selecting a payment term resumes automatic dates.' : 'Due date follows invoice date and payment terms. Edit it to override. Currency changes do not convert amounts.';
  render();
}
function replaceInvoice(value, saved = false) {
  clearTimeout(autosaveTimer); logoVersion += 1; invoice = value;
  syncEditor(); changed(); libraryDirty = !saved;
}
function ensureValid(value = invoice) { return validateInvoice(sanitizeInvoice(value)); }
function fresh() {
  const value = blankInvoice(nextNumber([...library, invoice]));
  if (profile && $('#im-remember').checked) {
    value.business = structuredClone(profile.business); value.logo = profile.logo;
    value.currency = profile.currency; value.paymentTerms = profile.paymentTerms;
    value.notes = profile.notes; value.paymentInstructions = profile.paymentInstructions;
    value.dueDate = dueDate(value.invoiceDate, value.paymentTerms) || value.invoiceDate;
  }
  return value;
}

$('#im-editor').addEventListener('input', event => {
  const path = event.target.dataset.field;
  if (!path) return;
  const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value;
  set(path, value);
  if (path === 'dueDate') invoice.dueManual = true;
  if (path === 'paymentTerms') invoice.dueManual = value === 'custom';
  if (['invoiceDate', 'paymentTerms'].includes(path) && !invoice.dueManual) {
    invoice.dueDate = dueDate(invoice.invoiceDate, invoice.paymentTerms); syncField('dueDate');
  }
  if (['invoiceDate', 'paymentTerms', 'dueDate'].includes(path)) $('#im-due-note').textContent = invoice.dueManual ? 'Manual due date: changing invoice date will keep your chosen due date.' : 'Due date is calculated from invoice date and payment terms.';
  if (path === 'currency') {
    for (const group of ['items', 'charges', 'payments']) renderRows(group);
    say('Currency changed without converting numbers. Check all prices; JPY accepts whole yen only.');
  }
  changed();
});
$('#im-editor').addEventListener('change', event => {
  if (event.target.dataset.unit === undefined) return;
  const index = Number(event.target.dataset.unit);
  const custom = event.target.value === '__custom';
  invoice.items[index].unit = custom ? '' : event.target.value;
  const control = $(`[data-custom-unit="${index}"]`); control.hidden = !custom;
  control.querySelector('input').value = invoice.items[index].unit;
  if (custom) control.querySelector('input').focus();
  changed();
});
$('#im-editor').addEventListener('click', event => {
  const button = event.target.closest('[data-row-action]'); if (!button) return;
  const { group, rowAction } = button.dataset, index = Number(button.dataset.index);
  const rows = invoice[group];
  if (rowAction === 'delete') rows.splice(index, 1);
  else if (rowAction === 'duplicate') {
    if (rows.length >= LIMITS[group]) { say(`Maximum ${LIMITS[group]} ${group}.`); return; }
    rows.splice(index + 1, 0, structuredClone(rows[index]));
  } else {
    const other = index + (rowAction === 'up' ? -1 : 1);
    if (other >= 0 && other < rows.length) [rows[index], rows[other]] = [rows[other], rows[index]];
  }
  renderRows(group); changed();
  const focus = $(`#im-${group} .im-row:nth-child(${Math.min(index + 1, rows.length)}) input, #im-${group} .im-row:nth-child(${Math.min(index + 1, rows.length)}) textarea`);
  focus?.focus();
});

$('#im-logo').addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  const token = ++logoVersion; const id = invoice.id;
  say('Checking and optimizing your logo locally…');
  try {
    const logo = await optimizeLogo(file);
    if (token !== logoVersion || id !== invoice.id) return;
    invoice.logo = logo; $('#im-logo-preview').src = logo.data; $('#im-logo-preview').hidden = false;
    changed(); say('Logo added and optimized locally.');
  } catch (error) { if (token === logoVersion) say(error.message); }
  finally { event.target.value = ''; }
});
$('#im-remember').addEventListener('change', async event => {
  if (event.target.checked) { profile = profileFrom(invoice); changed(); say('Business profile will be remembered on this device.'); }
  else {
    profile = null;
    try { await queue(() => storage.remove('settings', 'profile')); say('Remembered business profile removed. Invoice copies still contain their original details.'); }
    catch { say('The profile could not be removed. Try Clear saved invoice data or clear this site’s browser storage.'); }
  }
});

async function refreshLibrary() {
  const records = await storage.read('invoices');
  library = []; let corrupt = 0;
  for (const record of records) { try { library.push(sanitizeInvoice(record)); } catch { corrupt += 1; } }
  library.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  renderLibrary();
  if (corrupt) say(`${corrupt} unreadable saved record(s) were left untouched. Valid invoices remain available; export them before clearing local data.`);
}
function renderLibrary() {
  const query = $('#im-search').value.toLowerCase();
  const fragment = document.createDocumentFragment();
  for (const record of library.filter(value => [value.invoiceNumber, value.customer.name, value.status].join(' ').toLowerCase().includes(query))) {
    const entry = element('article', undefined, 'im-library-entry');
    entry.append(element('h3', `${record.invoiceNumber || 'Untitled invoice'} · ${record.customer.name || 'No customer name'}`));
    let total = 'Invalid amounts — open to correct';
    try { total = money(calculateInvoice(record).total, record.currency); } catch { /* A recoverable old draft. */ }
    entry.append(element('p', `${total} · ${record.invoiceDate || 'No date'} · ${record.status}`));
    const buttons = element('div', undefined, 'im-toolbar');
    for (const [action, label] of [['open', 'Open'], ['duplicate', 'Duplicate'], ['pdf', 'Download PDF'], ['print', 'Print'], ['delete', 'Delete']]) {
      const button = element('button', label); button.type = 'button'; button.dataset.library = action; button.dataset.id = record.id; buttons.append(button);
    }
    entry.append(buttons); fragment.append(entry);
  }
  if (!fragment.childNodes.length) fragment.append(element('p', library.length ? 'No matching invoices.' : 'No saved invoices yet. Your working draft is separate from this library.'));
  $('#im-library-list').replaceChildren(fragment);
}
$('#im-search').addEventListener('input', renderLibrary);

async function pdf(value) {
  if (pdfBusy) return;
  const snapshot = ensureValid(value); pdfBusy = true; render(); say('Creating your PDF locally…');
  try { await downloadPDF(snapshot); say('PDF created. Check your browser’s downloads.'); }
  catch (error) { say(`PDF could not be created. ${error.message} Your invoice is unchanged.`); }
  finally { pdfBusy = false; render(); }
}
function print(value) {
  const snapshot = ensureValid(value);
  if (typeof window.print !== 'function') { say('Printing is unavailable in this browser. Try Download PDF.'); return; }
  printing = true; renderDocument(snapshot, calculateInvoice(snapshot)); $('#im-document').hidden = false;
  updatePrintSize(snapshot.paperSize);
  const restore = () => { printing = false; window.removeEventListener('afterprint', restore); render(); say('Print dialog closed. Your invoice is unchanged; a canceled print is not a payment or save.'); };
  window.addEventListener('afterprint', restore);
  try { window.print(); } catch { restore(); say('The print dialog could not open. Try Download PDF instead.'); }
}
function downloadData(blob, filename) {
  const url = URL.createObjectURL(blob); const link = element('a'); link.href = url; link.download = filename;
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
$('#im-library-list').addEventListener('click', async event => {
  const button = event.target.closest('[data-library]'); if (!button) return;
  const source = library.find(value => value.id === button.dataset.id); if (!source) return;
  const action = button.dataset.library;
  try {
    if (action === 'pdf') await pdf(source);
    else if (action === 'print') print(source);
    else if (action === 'delete') {
      if (!window.confirm(`Delete invoice ${source.invoiceNumber || '(untitled)'}? This removes the saved library copy from this browser. The current editor and its working draft, if open, remain.`)) return;
      await queue(() => storage.remove('invoices', source.id)); await refreshLibrary(); say('Saved invoice deleted.');
    } else if (discardAllowed()) {
      replaceInvoice(action === 'open' ? structuredClone(source) : duplicateInvoice(source, nextNumber([...library, invoice])), action === 'open');
      say(action === 'open' ? 'Saved invoice opened.' : 'Invoice duplicated with today’s date, a new number, Draft status and no prior payments.');
      $('#im-builder').scrollIntoView({ block: 'start' });
    }
  } catch (error) { say(`Could not complete that action. ${error.message}`); }
});

const actions = {
  new() { if (discardAllowed()) { replaceInvoice(fresh()); say('New blank invoice started.'); } },
  duplicate() { if (discardAllowed()) { replaceInvoice(duplicateInvoice(invoice, nextNumber([...library, invoice]))); say('Invoice duplicated. Prior payments cleared; status is Draft.'); } },
  async save() {
    const snapshot = ensureValid(), version = revision;
    await queue(() => storage.saveInvoice(snapshot));
    if (version === revision) libraryDirty = false;
    await refreshLibrary(); await autosave(); say('Invoice saved locally in your library. Export JSON for a portable backup.');
  },
  pdf() { return pdf(invoice); }, print() { print(invoice); },
  preview() {
    $('#im-builder').classList.add('is-preview'); $('[data-action="preview"]').hidden = true; $('[data-action="edit"]').hidden = false;
    $('#im-preview-panel').scrollIntoView({ block: 'start' }); $('[data-action="edit"]').focus();
  },
  edit() { $('#im-builder').classList.remove('is-preview'); $('[data-action="preview"]').hidden = false; $('[data-action="edit"]').hidden = true; $('[data-action="preview"]').focus(); },
  'remove-logo'() { logoVersion += 1; invoice.logo = null; $('#im-logo-preview').removeAttribute('src'); $('#im-logo-preview').hidden = true; changed(); say('Logo removed.'); },
  preset() {
    const selected = $('#im-preset').value;
    if (!window.confirm('Replace all current line items with editable sample items? Your other invoice details will stay.')) return;
    invoice.items = selected ? PRESETS[selected].map(([description, quantity, unit, rate]) => ({ ...blankItem(), description, quantity, unit, rate })) : [blankItem()];
    renderRows('items'); changed(); say('Sample items applied. Review all descriptions, rates and taxability.');
  },
  export() {
    const value = ensureValid();
    downloadData(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }), safeFilename(value, 'json'));
    say('Invoice data exported as JSON. Keep this file private; it contains your invoice details.');
  },
  async clear() {
    if (!window.confirm('Clear ALL saved invoice data in this browser? This deletes the invoice library, working draft and remembered business profile. Export backups first. Your current editor remains, but is not saved until you edit or save again.')) return;
    clearTimeout(autosaveTimer); revision += 1; dirty = true; libraryDirty = true;
    $('#im-remember').checked = false; profile = null;
    await queue(storage.clearStorage); library = []; renderLibrary();
    saveStatus('Saved data cleared. Current editor is unsaved; autosave resumes when you edit.'); say('This tool’s saved invoice data was cleared. Other tools and downloaded files were not changed.');
  },
};
for (const [action, group, value] of [['add-item', 'items', blankItem], ['add-charge', 'charges', () => ({ description: '', amount: '0', taxable: false })], ['add-payment', 'payments', () => ({ description: '', amount: '0', date: '' })], ['add-tax', 'taxes', () => ({ name: '', rate: '0' })]]) {
  actions[action] = () => {
    if (invoice[group].length >= LIMITS[group]) { say(`Maximum ${LIMITS[group]} ${group}.`); return; }
    invoice[group].push(value()); renderRows(group); changed();
    $(`#im-${group} .im-row:last-child input, #im-${group} .im-row:last-child textarea`)?.focus();
  };
}
document.querySelector('.invoice-maker').addEventListener('click', async event => {
  const button = event.target.closest('[data-action]'); if (!button || !initialized) return;
  try { await actions[button.dataset.action](); }
  catch (error) { say(`Action could not be completed. ${error.message} Your editor is unchanged unless you already made edits.`); }
});

$('#im-import').addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  const version = revision;
  try {
    if (file.size > 5000000) throw new Error('Invoice backup must be 5 MB or smaller.');
    const imported = validateInvoice(sanitizeInvoice(JSON.parse(await file.text())));
    imported.logo = await checkImportedLogo(imported.logo);
    if (revision !== version) throw new Error('Your editor changed during import. Try again when you are ready.');
    if (!discardAllowed()) return;
    imported.id = uuid(); imported.createdAt = imported.updatedAt = new Date().toISOString();
    replaceInvoice(imported); say('Invoice imported successfully as a new local copy. Save it to add it to your library.');
  } catch (error) { say(`Import failed. ${error instanceof SyntaxError ? "This file isn't valid JSON." : error.message} Your current invoice was kept.`); }
  finally { event.target.value = ''; }
});

window.addEventListener('beforeunload', event => {
  if (dirty) { event.preventDefault(); event.returnValue = ''; }
});
document.addEventListener('visibilitychange', () => { if (document.hidden && dirty && autosaveTimer) void autosave(); });
window.addEventListener('pagehide', () => { clearTimeout(autosaveTimer); if (dirty && storageReady) void autosave(); });

async function initialize() {
  for (const name of Object.keys(PRESETS)) { const option = element('option', name); option.value = name; $('#im-preset').append(option); }
  try {
    await storage.openStorage(); storageReady = true;
    const [draft, remembered] = await Promise.all([storage.read('settings', 'draft'), storage.read('settings', 'profile')]);
    await refreshLibrary();
    if (remembered) {
      try {
        const probe = blankInvoice(); Object.assign(probe, { business: remembered.business, logo: remembered.logo, currency: remembered.currency, paymentTerms: remembered.paymentTerms, notes: remembered.notes, paymentInstructions: remembered.paymentInstructions });
        profile = profileFrom(sanitizeInvoice(probe)); $('#im-remember').checked = true;
      } catch { say('The remembered profile could not be read. Existing saved data was left untouched.'); }
    }
    if (draft) {
      try { invoice = sanitizeInvoice(draft); saveStatus('Working draft restored from this device.'); libraryDirty = true; }
      catch { saveStatus('The old draft could not be read. It will remain untouched until you edit or save a new draft.'); }
    } else { invoice = fresh(); saveStatus('Ready. Your working draft will autosave after edits.'); }
  } catch {
    saveStatus('Browser storage is unavailable. You can still create, print and download invoices. Export JSON before leaving.');
    renderLibrary();
  }
  $('#im-fields').disabled = false; $('#im-import').disabled = false;
  document.querySelectorAll('[data-action]').forEach(button => { button.disabled = false; });
  initialized = true; syncEditor(); say('Ready to create your invoice. All fields are optional; review the document before sending.');
}
void initialize();
