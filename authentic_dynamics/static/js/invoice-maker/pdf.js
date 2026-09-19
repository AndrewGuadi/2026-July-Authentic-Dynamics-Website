import { calculateInvoice, validateInvoice, partyLines, metaRows, totalRows, money, safeFilename } from './core.js';
import { HEADINGS, lineCells } from './document.js';
let assets;
function loadScript(url) {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script'); script.src = url;
    script.onload = resolve;
    script.onerror = () => { script.remove(); reject(new Error('PDF library could not load. Try again or use Print → Save as PDF.')); };
    document.head.append(script);
  });
}
function base64(buffer) {
  const bytes = new Uint8Array(buffer); let result = '';
  for (let index = 0; index < bytes.length; index += 8192) result += String.fromCharCode(...bytes.subarray(index, index + 8192));
  return btoa(result);
}
async function loadAssets() {
  if (!assets) assets = (async () => {
    const root = new URL('../../vendor/invoice/', import.meta.url);
    const [regular, bold, table] = await Promise.all([
      fetch(new URL('DejaVuSans.ttf', root)).then(response => { if (!response.ok) throw new Error('PDF font unavailable.'); return response.arrayBuffer(); }),
      fetch(new URL('DejaVuSans-Bold.ttf', root)).then(response => { if (!response.ok) throw new Error('PDF font unavailable.'); return response.arrayBuffer(); }),
      import(new URL('autotable-5.0.8.mjs', root).href),
      loadScript(new URL('jspdf-4.2.1.umd.min.js', root).href),
    ]);
    return { regular: base64(regular), bold: base64(bold), autoTable: table.autoTable };
  })().catch(error => { assets = null; throw error; });
  return assets;
}

export async function createPDF(invoice) {
  validateInvoice(invoice);
  const totals = calculateInvoice(invoice);
  const { regular, bold, autoTable } = await loadAssets();
  const doc = new window.jspdf.jsPDF({ orientation: 'portrait', unit: 'pt', format: invoice.paperSize, compress: true, putOnlyUsedFonts: true });
  doc.addFileToVFS('ADInvoice.ttf', regular); doc.addFont('ADInvoice.ttf', 'ADInvoice', 'normal');
  doc.addFileToVFS('ADInvoice-Bold.ttf', bold); doc.addFont('ADInvoice-Bold.ttf', 'ADInvoice', 'bold');
  doc.setFont('ADInvoice', 'normal');
  // Avoid silently producing missing glyphs. Browser print can use installed fallback fonts.
  const cmap = doc.getFont().metadata?.cmap?.unicode?.codeMap;
  const strings = [invoice.invoiceNumber, ...Object.values(invoice.business), ...Object.values(invoice.customer), ...metaRows(invoice).flat(), ...invoice.items.flatMap(item => [item.description, item.unit]), ...invoice.charges.map(c => c.description), ...invoice.payments.map(p => p.description), ...invoice.taxes.map(t => t.name), invoice.notes, invoice.terms, invoice.paymentInstructions, invoice.footer];
  if (cmap && strings.some(text => Array.from(text).some(char => char.codePointAt(0) > 31 && !cmap[char.codePointAt(0)]))) throw new Error('Some characters are not available in the PDF font. Use Print → Save as PDF for this writing system.');
  const width = doc.internal.pageSize.getWidth(), height = doc.internal.pageSize.getHeight();
  const margin = 42, bottom = height - 45, usable = width - margin * 2;
  const color = invoice.accentColor.match(/[a-f\d]{2}/gi).map(part => parseInt(part, 16));
  let y = margin;
  doc.setProperties({ title: `Invoice ${invoice.invoiceNumber}`, creator: 'Local invoice editor' });
  function room(amount) { if (y + amount > bottom) { doc.addPage(); y = margin; } }
  function text(value, options = {}) {
    if (!value) return;
    const size = options.size || 10;
    doc.setFont('ADInvoice', options.bold ? 'bold' : 'normal'); doc.setFontSize(size); doc.setTextColor(24, 24, 24);
    const lines = doc.splitTextToSize(String(value), options.width || usable);
    for (const line of lines) { room(size * 1.5); doc.text(line, options.x || margin, y + size); y += size * 1.4; }
    y += options.gap ?? 6;
  }
  if (invoice.template !== 'Minimal') {
    doc.setDrawColor(...color); doc.setLineWidth(invoice.template === 'Modern' ? 7 : 2);
    doc.line(margin, y, width - margin, y); y += 17;
  }
  if (invoice.logo) {
    const ratio = Math.min(145 / invoice.logo.width, 65 / invoice.logo.height);
    doc.addImage(invoice.logo.data, 'PNG', margin, y, invoice.logo.width * ratio, invoice.logo.height * ratio);
    y += invoice.logo.height * ratio + 16;
  }
  text('INVOICE', { size: invoice.template === 'Compact' ? 21 : 28, bold: true });
  text([invoice.invoiceNumber, invoice.status].filter(Boolean).join(' · '), { size: 11 });
  const tableBase = { margin: { left: margin, right: margin, top: margin, bottom: 45 },
    styles: { font: 'ADInvoice', fontSize: invoice.template === 'Compact' ? 8 : 9, cellPadding: 5, overflow: 'linebreak', textColor: [24, 24, 24] },
    headStyles: { fillColor: [237, 240, 232], textColor: [24, 24, 24], fontStyle: 'bold' },
    rowPageBreak: 'avoid', showHead: 'everyPage', theme: invoice.template === 'Minimal' ? 'plain' : 'striped' };
  const from = [invoice.business.name, ...partyLines(invoice.business)].filter(Boolean).join('\n');
  const to = [invoice.customer.name, ...partyLines(invoice.customer)].filter(Boolean).join('\n');
  if (from || to) {
    autoTable(doc, { ...tableBase, startY: y, head: [['From', 'Bill to']], body: [[from, to]], theme: 'plain', columnStyles: { 0: { cellWidth: usable / 2 }, 1: { cellWidth: usable / 2 } } });
    y = doc.lastAutoTable.finalY + 12;
  }
  autoTable(doc, { ...tableBase, startY: y, body: metaRows(invoice), theme: 'plain', columnStyles: { 0: { cellWidth: 125, fontStyle: 'bold' } } });
  y = doc.lastAutoTable.finalY + 14;
  autoTable(doc, { ...tableBase, startY: y, head: [HEADINGS], body: invoice.items.map((item, index) => lineCells(invoice, totals, item, index)),
    columnStyles: { 0: { cellWidth: usable * 0.32 }, 1: { cellWidth: usable * 0.07 }, 2: { cellWidth: usable * 0.10 }, 3: { cellWidth: usable * 0.15, halign: 'right' }, 4: { cellWidth: usable * 0.10 }, 5: { cellWidth: usable * 0.08 }, 6: { cellWidth: usable * 0.18, halign: 'right' } } });
  y = doc.lastAutoTable.finalY + 14;
  const rows = totalRows(invoice, totals).map(([label, amount]) => [label, money(amount, invoice.currency)]);
  autoTable(doc, { ...tableBase, startY: y, body: rows, theme: 'plain', pageBreak: 'avoid',
    margin: { ...tableBase.margin, left: margin + usable * 0.25 }, tableWidth: usable * 0.75,
    columnStyles: { 1: { halign: 'right', cellWidth: usable * 0.3 } },
    didParseCell(data) { if (data.row.index === rows.length - 1) { data.cell.styles.fontStyle = 'bold'; data.cell.styles.fontSize = 11; } } });
  y = doc.lastAutoTable.finalY + 20;
  for (const [label, value] of [['Notes', invoice.notes], ['Terms & conditions', invoice.terms], ['Payment instructions', invoice.paymentInstructions]]) {
    if (!value) continue;
    room(45); text(label, { bold: true, size: 11 }); text(value); y += 8;
  }
  text(invoice.footer, { size: 9 });
  const pages = doc.getNumberOfPages();
  for (let page = 1; page <= pages; page += 1) {
    doc.setPage(page); doc.setFont('ADInvoice', 'normal'); doc.setFontSize(8); doc.setTextColor(85, 85, 85);
    doc.text(`${page} / ${pages}`, width - margin, height - 24, { align: 'right' });
  }
  return doc;
}
export async function downloadPDF(invoice) { const doc = await createPDF(invoice); doc.save(safeFilename(invoice, 'pdf')); }
