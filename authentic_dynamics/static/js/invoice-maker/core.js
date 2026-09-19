export const CURRENCIES = ['USD', 'CAD', 'EUR', 'GBP', 'AUD', 'NZD', 'JPY', 'CHF', 'INR', 'MXN', 'BRL'];
export const STATUSES = ['Draft', 'Unpaid', 'Partially Paid', 'Paid', 'Overdue', 'Canceled'];
export const TEMPLATES = ['Classic', 'Modern', 'Minimal', 'Professional', 'Compact'];
export const UNITS = ['', 'Item', 'Unit', 'Hour', 'Day', 'Week', 'Month', 'Job', 'Project', 'Visit', 'Session', 'Piece', 'Mile', 'Kilometer', 'Square Foot', 'Square Meter'];
export const BUSINESS_FIELDS = ['name', 'contact', 'street', 'address2', 'city', 'region', 'postal', 'country', 'phone', 'email', 'website', 'taxId', 'license'];
export const CUSTOMER_FIELDS = ['name', 'contact', 'street', 'address2', 'city', 'region', 'postal', 'country', 'email', 'phone', 'customerId'];
export const PROJECT_FIELDS = ['name', 'number', 'address', 'provider', 'reference'];
export const LABELS = { name: 'Name', contact: 'Contact name', street: 'Street address', address2: 'Address line 2', city: 'City', region: 'State / province / region', postal: 'ZIP / postal code', country: 'Country', phone: 'Phone', email: 'Email', website: 'Website', taxId: 'Tax ID / EIN / VAT number', license: 'License / registration number', customerId: 'Customer ID', number: 'Project number', address: 'Service address', provider: 'Technician / provider', reference: 'Custom reference' };
export const LIMITS = { items: 100, charges: 20, payments: 30, taxes: 3, saved: 100 };
export const uuid = () => globalThis.crypto?.randomUUID?.() || `local-${Date.now()}-${Math.random().toString(36).slice(2)}`;
export function today() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}
const record = fields => Object.fromEntries(fields.map(key => [key, '']));
export const blankItem = () => ({ description: '', quantity: '1', unit: '', rate: '0', discountType: 'none', discount: '0', taxable: true });
export function blankInvoice(number = 'INV-001') {
  return { schemaVersion: 1, id: uuid(), createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
    invoiceNumber: number, invoiceDate: today(), dueDate: today(), paymentTerms: '0', dueManual: false,
    po: '', reference: '', serviceStart: '', serviceEnd: '', currency: 'USD', status: 'Draft',
    business: record(BUSINESS_FIELDS), customer: record(CUSTOMER_FIELDS), project: record(PROJECT_FIELDS),
    items: [blankItem()], charges: [], payments: [], discount: { type: 'none', value: '0' },
    taxes: [{ name: 'Sales tax', rate: '0' }], notes: '', terms: '', paymentInstructions: '', footer: '',
    template: 'Classic', accentColor: '#274b3a', paperSize: 'letter', logo: null };
}

export function validDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value.slice(0, 4) < '1900') return false;
  const date = new Date(`${value}T12:00:00Z`);
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
}
export function dueDate(date, term) {
  if (!validDate(date) || !['0', '7', '10', '15', '30', '45', '60'].includes(term)) return '';
  const result = new Date(`${date}T12:00:00Z`);
  result.setUTCDate(result.getUTCDate() + Number(term));
  return result.toISOString().slice(0, 10);
}
export function nextNumber(invoices) {
  const greatest = invoices.reduce((max, invoice) => {
    const match = /^INV-(\d{1,9})$/.exec(invoice.invoiceNumber);
    return match ? Math.max(max, Number(match[1])) : max;
  }, 0);
  return `INV-${String(greatest + 1).padStart(3, '0')}`;
}
export function duplicateInvoice(source, number) {
  const invoice = structuredClone(source);
  invoice.id = uuid(); invoice.invoiceNumber = number; invoice.invoiceDate = today();
  invoice.dueDate = dueDate(invoice.invoiceDate, invoice.paymentTerms) || invoice.invoiceDate;
  invoice.dueManual = invoice.paymentTerms === 'custom'; invoice.status = 'Draft'; invoice.payments = [];
  invoice.createdAt = invoice.updatedAt = new Date().toISOString();
  return invoice;
}

export function digits(currency) { return currency === 'JPY' ? 0 : 2; }
// Decimal strings -> scaled integers. No binary floating-point arithmetic in totals.
export function decimal(value, places, label = 'Number', maxWhole = 999999999) {
  if (typeof value !== 'string' || !/^\d{1,9}(?:\.\d{0,4})?$/.test(value || '0')) throw new Error(`${label}: enter a nonnegative number without commas.`);
  const [whole, fraction = ''] = (value || '0').split('.');
  if (fraction.length > places) throw new Error(`${label}: use at most ${places} decimal places.`);
  if (Number(whole) > maxWhole) throw new Error(`${label}: maximum ${maxWhole.toLocaleString('en-US')}.`);
  return BigInt(whole) * 10n ** BigInt(places) + BigInt(fraction.padEnd(places, '0') || '0');
}
const round = (numerator, denominator) => (numerator + denominator / 2n) / denominator;
function discountFor(base, type, value, precision, label) {
  if (type === 'none') return 0n;
  const amount = type === 'percent' ? round(base * decimal(value, 2, label, 100), 10000n) : decimal(value, precision, label);
  if (amount > base) throw new Error(`${label} exceeds the amount being discounted.`);
  return amount;
}
function allocate(total, bases) {
  const sum = bases.reduce((a, b) => a + b, 0n);
  if (!sum) return bases.map(() => 0n);
  const parts = bases.map(base => total * base / sum);
  let remaining = total - parts.reduce((a, b) => a + b, 0n);
  const order = bases.map((base, index) => ({ index, rest: total * base % sum })).sort((a, b) => a.rest === b.rest ? a.index - b.index : a.rest > b.rest ? -1 : 1);
  for (const part of order) { if (!remaining) break; parts[part.index] += 1n; remaining -= 1n; }
  return parts;
}
export function calculateInvoice(invoice) {
  const precision = digits(invoice.currency);
  const lines = invoice.items.map((item, index) => {
    const quantity = decimal(item.quantity, 4, `Item ${index + 1} quantity`, 1000000);
    const rate = decimal(item.rate, precision, `Item ${index + 1} rate`);
    const gross = round(quantity * rate, 10000n);
    const discount = discountFor(gross, item.discountType, item.discount, precision, `Item ${index + 1} discount`);
    return { gross, discount, net: gross - discount, rate };
  });
  const subtotal = lines.reduce((sum, line) => sum + line.net, 0n);
  const discount = discountFor(subtotal, invoice.discount.type, invoice.discount.value, precision, 'Invoice discount');
  const allocation = allocate(discount, lines.map(line => line.net));
  const charges = invoice.charges.map((charge, index) => decimal(charge.amount, precision, `Charge ${index + 1}`));
  const chargeTotal = charges.reduce((a, b) => a + b, 0n);
  const taxable = lines.reduce((sum, line, index) => sum + (invoice.items[index].taxable ? line.net - allocation[index] : 0n), 0n)
    + charges.reduce((sum, amount, index) => sum + (invoice.charges[index].taxable ? amount : 0n), 0n);
  const taxes = invoice.taxes.map((tax, index) => round(taxable * decimal(tax.rate, 2, `Tax ${index + 1} rate`, 100), 10000n));
  const taxTotal = taxes.reduce((a, b) => a + b, 0n);
  const total = subtotal - discount + chargeTotal + taxTotal;
  const payments = invoice.payments.map((payment, index) => decimal(payment.amount, precision, `Payment ${index + 1}`));
  const paid = payments.reduce((a, b) => a + b, 0n);
  if (total > 100000000000000n || subtotal > 100000000000000n || paid > 100000000000000n) throw new Error('Invoice exceeds the supported amount limit (100 trillion minor currency units).');
  return { lines, subtotal, discount, allocation, taxable, charges, chargeTotal, taxes, taxTotal, total, payments, paid, balance: total - paid };
}
export function money(amount, currency) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, currencyDisplay: 'code' }).format(Number(amount) / 10 ** digits(currency));
}

// Reconstruct only known fields. Never merge imported objects into application state.
export function sanitizeInvoice(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw) || raw.schemaVersion !== 1) throw new Error('This file is not a supported invoice backup (version 1).');
  const base = blankInvoice();
  function text(value, max = 300) {
    if (typeof value !== 'string' || value.length > max || /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(value)) throw new Error('Invoice contains invalid or overly long text.');
    return value;
  }
  function object(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invoice structure is invalid.');
    return value;
  }
  function choice(value, options) { if (!options.includes(value)) throw new Error('Invoice contains an unsupported option.'); return value; }
  function bool(value) { if (typeof value !== 'boolean') throw new Error('Invoice contains an invalid checkbox value.'); return value; }
  const result = {};
  for (const key of ['id', 'createdAt', 'updatedAt', 'invoiceNumber', 'invoiceDate', 'dueDate', 'po', 'reference', 'serviceStart', 'serviceEnd']) result[key] = text(raw[key]);
  if (!/^[a-zA-Z0-9-]{1,80}$/.test(result.id)) throw new Error('Invalid invoice identifier.');
  for (const key of ['notes', 'terms', 'paymentInstructions', 'footer']) result[key] = text(raw[key], 10000);
  for (const [key, fields] of [['business', BUSINESS_FIELDS], ['customer', CUSTOMER_FIELDS], ['project', PROJECT_FIELDS]]) {
    object(raw[key]); result[key] = {};
    for (const field of fields) result[key][field] = text(raw[key][field], field === 'address' ? 1000 : 300);
  }
  result.schemaVersion = 1;
  result.currency = choice(raw.currency, CURRENCIES); result.status = choice(raw.status, STATUSES);
  result.template = choice(raw.template, TEMPLATES); result.paperSize = choice(raw.paperSize, ['letter', 'a4']);
  result.paymentTerms = choice(raw.paymentTerms, ['0', '7', '10', '15', '30', '45', '60', 'custom']);
  result.dueManual = bool(raw.dueManual);
  result.accentColor = text(raw.accentColor, 7);
  if (!/^#[0-9a-f]{6}$/i.test(result.accentColor)) throw new Error('Invalid accent color.');
  object(raw.discount);
  result.discount = { type: choice(raw.discount.type, ['none', 'percent', 'fixed']), value: text(raw.discount.value, 20) };
  for (const key of ['items', 'charges', 'payments', 'taxes']) {
    if (!Array.isArray(raw[key]) || raw[key].length > LIMITS[key]) throw new Error(`Invoice has too many ${key} or invalid structure.`);
    result[key] = raw[key].map(entry => {
      object(entry);
      if (key === 'items') return { description: text(entry.description, 2000), quantity: text(entry.quantity, 20), unit: text(entry.unit, 50), rate: text(entry.rate, 20), discountType: choice(entry.discountType, ['none', 'percent', 'fixed']), discount: text(entry.discount, 20), taxable: bool(entry.taxable) };
      if (key === 'taxes') return { name: text(entry.name), rate: text(entry.rate, 20) };
      const row = { description: text(entry.description), amount: text(entry.amount, 20) };
      if (key === 'charges') row.taxable = bool(entry.taxable); else row.date = text(entry.date, 10);
      return row;
    });
  }
  result.logo = null;
  if (raw.logo !== null) {
    object(raw.logo);
    const data = text(raw.logo.data, 1500000);
    if (!/^data:image\/png;base64,[A-Za-z0-9+/]+=*$/.test(data)) throw new Error('Invoice logo must be an embedded PNG.');
    if (![raw.logo.width, raw.logo.height].every(value => Number.isInteger(value) && value > 0 && value <= 1200)) throw new Error('Invalid logo dimensions.');
    result.logo = { data, width: raw.logo.width, height: raw.logo.height };
  }
  // Keep the schema exhaustive so newly added fields cannot silently disappear.
  if (Object.keys(result).length !== Object.keys(base).length) throw new Error('Invoice schema mismatch.');
  return result;
}
export function validateInvoice(invoice) {
  calculateInvoice(invoice);
  for (const [name, value] of [['Invoice date', invoice.invoiceDate], ['Due date', invoice.dueDate], ['Service start', invoice.serviceStart], ['Service end', invoice.serviceEnd], ...invoice.payments.map(p => ['Payment date', p.date])]) {
    if (value && !validDate(value)) throw new Error(`${name} must be a valid date from 1900 onward.`);
  }
  return invoice;
}
export function warnings(invoice, totals) {
  const result = [];
  if (invoice.dueDate && invoice.invoiceDate && invoice.dueDate < invoice.invoiceDate) result.push('Due date is earlier than invoice date. Confirm that this is intentional.');
  if (invoice.serviceStart && invoice.serviceEnd && invoice.serviceEnd < invoice.serviceStart) result.push('Service end is earlier than service start.');
  if (invoice.status === 'Paid' && totals.balance > 0n) result.push('Status is Paid, but a balance remains. Status is set manually.');
  if (totals.balance === 0n && totals.total > 0n && invoice.status !== 'Paid') result.push('Balance is zero. You can mark this invoice Paid.');
  if (totals.balance < 0n) result.push('Payments exceed the total. The difference is shown as credit due.');
  return result;
}
export function partyLines(party) {
  return [party.contact, party.street, party.address2, [party.city, party.region, party.postal].filter(Boolean).join(', '), party.country,
    party.email, party.phone, party.website, party.taxId && `Tax ID: ${party.taxId}`, party.license && `Registration: ${party.license}`, party.customerId && `Customer ID: ${party.customerId}`].filter(Boolean);
}
export function metaRows(invoice) {
  return [['Invoice date', invoice.invoiceDate], ['Due date', invoice.dueDate], ['Payment terms', invoice.paymentTerms === 'custom' ? 'Custom' : invoice.paymentTerms === '0' ? 'Due on receipt' : `Net ${invoice.paymentTerms}`], ['Purchase order', invoice.po], ['Reference', invoice.reference], ['Service period', [invoice.serviceStart, invoice.serviceEnd].filter(Boolean).join(' – ')], ['Project', invoice.project.name], ['Project number', invoice.project.number], ['Service address', invoice.project.address], ['Provider', invoice.project.provider], ['Custom reference', invoice.project.reference]].filter(([, value]) => value);
}
export function totalRows(invoice, totals) {
  const rows = [['Subtotal (after item discounts)', totals.subtotal]];
  if (totals.discount) rows.push(['Invoice discount', -totals.discount]);
  invoice.charges.forEach((charge, i) => rows.push([charge.description || 'Additional charge', totals.charges[i]]));
  invoice.taxes.forEach((tax, i) => { if (Number(tax.rate)) rows.push([`${tax.name || 'Tax'} (${tax.rate}%)`, totals.taxes[i]]); });
  rows.push(['Total', totals.total]);
  invoice.payments.forEach((payment, i) => rows.push([[payment.description || 'Payment / credit', payment.date].filter(Boolean).join(' · '), -totals.payments[i]]));
  rows.push([totals.balance < 0n ? 'Credit due' : 'Balance due', totals.balance < 0n ? -totals.balance : totals.balance]);
  return rows;
}
export function safeFilename(invoice, extension) { return `invoice-${(invoice.invoiceNumber || 'draft').replace(/[^a-zA-Z0-9_-]/g, '-').slice(0, 70)}.${extension}`; }

export const PRESETS = {
  'Web Developer': [['Website design', '8', 'Hour', '75'], ['Development', '15', 'Hour', '100'], ['Hosting', '12', 'Month', '20']],
  'Plumber': [['Service call', '1', 'Job', '85'], ['Drain cleaning', '1', 'Job', '225'], ['Replacement parts', '1', 'Unit', '45']],
  'Contractor': [['Labor', '1', 'Hour', '0'], ['Materials', '1', 'Unit', '0'], ['Equipment rental', '1', 'Day', '0'], ['Travel', '1', 'Job', '0']],
  'Recurring Lawn Care': [['Lawn service', '4', 'Visit', '65'], ['Hedge trimming', '1', 'Job', '120']],
  'Consultant': [['Consulting services', '1', 'Hour', '0']],
  'Photographer': [['Photography session', '1', 'Session', '0'], ['Editing', '1', 'Hour', '0']],
  'Auto Repair': [['Diagnostic inspection', '1', 'Job', '0'], ['Labor', '1', 'Hour', '0'], ['Parts', '1', 'Piece', '0']],
  'Tutor': [['Tutoring', '1', 'Session', '0']],
  'Products / Catering': [['Products or meals', '1', 'Unit', '0']],
};
