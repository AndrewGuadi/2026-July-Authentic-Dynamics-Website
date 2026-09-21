/* The preview and download share one generated PDF blob until inputs change. */
window.JsonPdfTool = class {
  constructor(form) {
    this.form = form;
    this.options = form.querySelector('[data-pdf-options]');
    this.panel = document.getElementById('json-pdf-preview');
    this.status = form.querySelector('.tool-status');
    this.button = form.querySelector('button[type="submit"]:not([name="action"])');
    this.originalButton = this.button.innerHTML;
    this.columns = form.querySelector('[data-pdf-columns]');
    this.columnsNote = form.querySelector('[data-pdf-columns-note]');
    this.image = this.panel.querySelector('[data-pdf-image]');
    this.pageSelect = this.panel.querySelector('[data-pdf-page]');
    this.prev = this.panel.querySelector('[data-pdf-prev]');
    this.next = this.panel.querySelector('[data-pdf-next]');
    this.pageStatus = this.panel.querySelector('[data-pdf-page-status]');
    this.readRevision = 0;
    this.pageRevision = 0;
    form.querySelector('[data-pdf-js]').hidden = false;
    form.querySelector('[data-pdf-columns-load]').addEventListener('click', () => this.loadColumns());
    form.querySelector('[data-pdf-sample]').addEventListener('click', () => {
      form.elements.file.value = '';
      form.elements.json_text.value = JSON.stringify([
        { order: '001', customer: 'Maya', details: { city: 'Montréal', priority: true },
          notes: 'Please keep every word of these delivery notes. '.repeat(35) },
        { order: '002', customer: 'Alex', details: { city: 'Athens', priority: false },
          notes: 'A short row. Try landscape, 12 pt, or moving the longer note to an appendix.' }
      ], null, 2);
      form.elements.json_text.dispatchEvent(new Event('input', { bubbles: true }));
    });
    this.columns.addEventListener('change', () => this.saveColumns());
    this.prev.addEventListener('click', () => this.showPage(this.cache.page - 1));
    this.next.addEventListener('click', () => this.showPage(this.cache.page + 1));
    this.pageSelect.addEventListener('change', () => this.showPage(Number(this.pageSelect.value)));
  }

  sync() {
    this.options.hidden = this.form.elements.format.value !== 'pdf';
    this.options.disabled = this.options.hidden;
    if (this.options.hidden) this.button.innerHTML = this.originalButton;
    else this.button.textContent = this.cache ? 'Download reviewed PDF ↓' : 'Preview PDF ↗';
  }

  invalidate(event) {
    this.readRevision += 1;
    this.pageRevision += 1;
    this.controller?.abort();
    if (this.cache) URL.revokeObjectURL(this.cache.url);
    if (this.imageUrl) URL.revokeObjectURL(this.imageUrl);
    this.imageUrl = null;
    this.cache = null;
    this.panel.hidden = true;
    this.image.removeAttribute('src');
    if (event && [this.form.elements.file, this.form.elements.json_text].includes(event.target)) {
      this.form.elements.pdf_columns.value = '';
      this.columns.replaceChildren();
      this.columnsNote.textContent = 'All columns are included. Choose columns to select fields and change their order.';
    }
    this.sync();
  }

  async loadColumns() {
    const revision = this.readRevision;
    try {
      const file = this.form.elements.file.files[0];
      const pasted = this.form.elements.json_text.value;
      if ((file && pasted.trim()) || (!file && !pasted.trim())) {
        throw new Error('Choose either a JSON file or pasted text first.');
      }
      if ((file && file.size > 10 * 1024 * 1024) || (!file && new Blob([pasted]).size > 400000)) {
        throw new Error('Use a file up to 10 MiB or pasted text up to 400 KB.');
      }
      const text = file ? new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer()) : pasted;
      if (revision !== this.readRevision) return;
      const value = JSON.parse(text.replace(/^\uFEFF/, ''));
      const rows = Array.isArray(value) ? value : [value];
      if (!rows.length || rows.some(row => !row || typeof row !== 'object' || Array.isArray(row))) {
        throw new Error('Use a JSON object or an array of objects for a PDF table.');
      }
      const keys = [...new Set(rows.flatMap(row => Object.keys(row)))];
      if (!keys.length || keys.length > 100) throw new Error('The column picker supports 1–100 source fields.');
      const saved = this.form.elements.pdf_columns.value ? JSON.parse(this.form.elements.pdf_columns.value) : keys;
      const ordered = [...saved.filter(key => keys.includes(key)), ...keys.filter(key => !saved.includes(key))];
      this.columns.replaceChildren();
      for (const key of ordered) {
        const row = document.createElement('div');
        const label = document.createElement('label');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox'; checkbox.checked = saved.includes(key); checkbox.dataset.key = key;
        label.append(checkbox, document.createTextNode(key || '(empty field name)'));
        row.append(label);
        for (const [symbol, direction] of [['↑', -1], ['↓', 1]]) {
          const button = document.createElement('button');
          button.type = 'button'; button.textContent = symbol;
          button.setAttribute('aria-label', `Move ${key || 'empty field'} ${direction < 0 ? 'up' : 'down'}`);
          button.addEventListener('click', () => {
            const sibling = direction < 0 ? row.previousElementSibling : row.nextElementSibling;
            if (!sibling) return;
            if (direction < 0) sibling.before(row); else sibling.after(row);
            this.saveColumns();
            this.form.dispatchEvent(new Event('input', { bubbles: true }));
            button.focus();
          });
          row.append(button);
        }
        this.columns.append(row);
      }
      this.saveColumns();
      this.form.dispatchEvent(new Event('input', { bubbles: true }));
    } catch (error) {
      if (revision !== this.readRevision) return;
      this.status.textContent = error instanceof SyntaxError ? 'Enter valid JSON before choosing columns.' : error.message;
      this.status.classList.add('is-error');
      this.status.focus();
    }
  }

  saveColumns() {
    const selected = [...this.columns.querySelectorAll('input:checked')].map(input => input.dataset.key);
    this.form.elements.pdf_columns.value = JSON.stringify(selected);
    this.columnsNote.textContent = `${selected.length} columns selected. PDF supports up to 12; arrows set their order.`;
  }

  accept(result) {
    this.invalidate();
    const bytes = Uint8Array.from(atob(result.pdf), char => char.charCodeAt(0));
    const blob = new Blob([bytes], { type: 'application/pdf' });
    const summary = result.summary;
    this.cache = { blob, url: URL.createObjectURL(blob), filename: result.filename, page: 0,
      pages: summary.page_count };
    this.panel.querySelector('[data-pdf-summary]').textContent =
      `${summary.page_count} pages · ${summary.orientation} · ${summary.font_size} pt · ${summary.row_count} rows · ${summary.column_count} columns`;
    this.panel.querySelector('[data-pdf-checks]').textContent = summary.checks.join(' · ');
    const warnings = this.panel.querySelector('[data-pdf-warnings]');
    warnings.replaceChildren();
    for (const message of summary.warnings) {
      const item = document.createElement('li'); item.textContent = message; warnings.append(item);
    }
    this.panel.querySelector('[data-pdf-open]').href = this.cache.url;
    for (const link of [this.panel.querySelector('[data-pdf-download]'), this.form.querySelector('.tool-download')]) {
      link.href = this.cache.url; link.download = result.filename; link.hidden = false;
    }
    this.pageSelect.replaceChildren();
    for (let index = 0; index < summary.page_count; index += 1) {
      const option = document.createElement('option'); option.value = index; option.textContent = index + 1;
      this.pageSelect.append(option);
    }
    this.image.src = `data:image/png;base64,${result.image}`;
    this.image.alt = `Page 1 of ${summary.page_count} of your generated PDF`;
    this.panel.hidden = false;
    this.pageStatus.textContent = `Page 1 of ${summary.page_count}. This image is rendered from the downloadable PDF.`;
    this.updatePager();
    this.sync();
  }

  updatePager(busy = false) {
    this.prev.disabled = busy || this.cache.page <= 0;
    this.next.disabled = busy || this.cache.page >= this.cache.pages - 1;
    this.pageSelect.disabled = busy;
    this.pageSelect.value = this.cache.page;
  }

  async showPage(page) {
    if (!this.cache || page < 0 || page >= this.cache.pages) return;
    this.controller?.abort();
    this.controller = new AbortController();
    const revision = ++this.pageRevision;
    this.updatePager(true);
    this.pageStatus.textContent = `Loading page ${page + 1}…`;
    try {
      const body = new FormData();
      body.set('csrf_token', this.form.elements.csrf_token.value);
      body.set('file', this.cache.blob, 'preview.pdf');
      body.set('page', String(page));
      const response = await fetch(this.form.dataset.pdfPageUrl,
        { method: 'POST', body, signal: this.controller.signal });
      if (!response.ok) throw new Error('Could not load that page. Try again or open the full PDF.');
      const image = await response.blob();
      if (revision !== this.pageRevision || !this.cache) return;
      if (this.imageUrl) URL.revokeObjectURL(this.imageUrl);
      this.imageUrl = URL.createObjectURL(image);
      this.image.src = this.imageUrl;
      this.image.alt = `Page ${page + 1} of ${this.cache.pages} of your generated PDF`;
      this.cache.page = page;
      this.pageStatus.textContent = `Page ${page + 1} of ${this.cache.pages}. This image is rendered from the downloadable PDF.`;
    } catch (error) {
      if (revision === this.pageRevision && error.name !== 'AbortError') this.pageStatus.textContent = error.message;
    } finally {
      if (revision === this.pageRevision && this.cache) this.updatePager();
    }
  }

  download() {
    this.panel.querySelector('[data-pdf-download]').click();
  }
};
