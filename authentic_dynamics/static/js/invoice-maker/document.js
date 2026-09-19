import { money, partyLines, metaRows, totalRows } from './core.js';
export function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = String(text);
  if (className) node.className = className;
  return node;
}
export function lineCells(invoice, totals, item, index) {
  const discount = item.discountType === 'none' ? '—' : item.discountType === 'percent' ? `${item.discount || '0'}%` : money(totals.lines[index].discount, invoice.currency);
  return [item.description, item.quantity || '0', item.unit, money(totals.lines[index].rate, invoice.currency), discount, item.taxable ? 'Yes' : 'No', money(totals.lines[index].net, invoice.currency)];
}
export const HEADINGS = ['Description', 'Qty', 'Unit', 'Rate', 'Discount', 'Taxable', 'Amount'];
export function createRenderer(root) {
  const sections = {};
  const hashes = {};
  for (const key of ['head', 'parties', 'meta', 'items', 'totals', 'notes', 'terms', 'paymentInstructions', 'footer']) {
    sections[key] = element('div'); root.append(sections[key]);
  }
  function update(key, data, build) {
    const hash = JSON.stringify(data);
    if (hashes[key] === hash) return;
    hashes[key] = hash;
    sections[key].replaceChildren(build());
  }
  return (invoice, totals) => {
    root.dataset.template = invoice.template;
    root.style.setProperty('--invoice-accent', invoice.accentColor);
    update('head', [invoice.logo, invoice.invoiceNumber, invoice.status], () => {
      const row = element('div', undefined, 'doc-head');
      const left = element('div');
      if (invoice.logo) {
        const image = element('img', undefined, 'doc-logo'); image.src = invoice.logo.data; image.alt = 'Business logo'; left.append(image);
      }
      left.append(element('h2', 'INVOICE'));
      const right = element('div'); right.append(element('p', invoice.invoiceNumber, 'doc-number'), element('p', invoice.status));
      row.append(left, right); return row;
    });
    update('parties', [invoice.business, invoice.customer], () => {
      const row = element('div', undefined, 'doc-parties');
      for (const [label, party] of [['From', invoice.business], ['Bill to', invoice.customer]]) {
        const column = element('div');
        if (Object.values(party).some(Boolean)) {
          column.append(element('h3', label));
          if (party.name) column.append(element('strong', party.name));
          for (const line of partyLines(party)) column.append(element('p', line));
        }
        row.append(column);
      }
      return row;
    });
    update('meta', metaRows(invoice), () => {
      const list = element('dl', undefined, 'doc-meta');
      for (const [label, value] of metaRows(invoice)) { const row = element('div'); row.append(element('dt', label), element('dd', value)); list.append(row); }
      return list;
    });
    update('items', [invoice.items, invoice.currency], () => {
      const table = element('table', undefined, 'invoice-line-table');
      const head = element('thead'); const row = element('tr');
      HEADINGS.forEach(label => { const cell = element('th', label); cell.scope = 'col'; row.append(cell); }); head.append(row); table.append(head);
      const body = element('tbody');
      invoice.items.forEach((item, index) => {
        const line = element('tr');
        lineCells(invoice, totals, item, index).forEach((value, i) => { const cell = element('td', value, [3, 6].includes(i) ? 'doc-money' : ''); cell.dataset.label = HEADINGS[i]; line.append(cell); });
        body.append(line);
      });
      table.append(body); return table;
    });
    const summary = totalRows(invoice, totals).map(([label, amount]) => [label, money(amount, invoice.currency)]);
    update('totals', summary, () => {
      const table = element('table', undefined, 'doc-totals');
      const body = element('tbody');
      for (const [label, value] of summary) { const row = element('tr'); row.append(element('td', label), element('td', value)); body.append(row); }
      table.append(body); return table;
    });
    for (const [key, label] of [['notes', 'Notes'], ['terms', 'Terms & conditions'], ['paymentInstructions', 'Payment instructions']]) {
      update(key, invoice[key], () => {
        const block = element('section', undefined, 'doc-text');
        if (invoice[key]) block.append(element('h3', label), element('p', invoice[key]));
        else block.hidden = true;
        return block;
      });
    }
    update('footer', invoice.footer, () => { const footer = element('p', invoice.footer, 'doc-footer'); footer.hidden = !invoice.footer; return footer; });
  };
}
