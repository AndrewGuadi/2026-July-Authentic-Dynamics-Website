(() => {
  const form = document.querySelector('[data-converter]');
  if (!form || !window.fetch) return;
  const status = form.querySelector('.tool-status');
  const button = form.querySelector('button[type="submit"]:not([name="action"])');
  const submitButtons = form.querySelectorAll('button[type="submit"]');
  const download = form.querySelector('.tool-download');
  const xlsxOptions = form.querySelector('[data-xlsx-options]');
  const previewPanel = form.querySelector('[data-workbook-preview]');
  const pdfTool = window.JsonPdfTool && form.querySelector('[data-pdf-options]') ? new window.JsonPdfTool(form) : null;
  let revision = 0;
  let downloadUrl;
  function syncOptions() {
    pdfTool?.sync();
    if (!xlsxOptions) return;
    xlsxOptions.hidden = form.elements.format.value !== 'xlsx';
    xlsxOptions.disabled = xlsxOptions.hidden;
    form.elements.max_depth.disabled = form.elements.nesting.value === 'keep';
  }
  function invalidate(event) {
    revision += 1;
    if (previewPanel) previewPanel.hidden = true;
    download.hidden = true;
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    downloadUrl = undefined;
    status.textContent = '';
    pdfTool?.invalidate(event);
    syncOptions();
  }
  form.addEventListener('input', invalidate);
  form.addEventListener('change', invalidate);
  syncOptions();
  function showPreview(result) {
    previewPanel.replaceChildren();
    const title = document.createElement('h3');
    title.textContent = 'Workbook preview';
    previewPanel.append(title);
    for (const sheet of result.sheets) {
      const article = document.createElement('article');
      const heading = document.createElement('h4');
      heading.textContent = `${sheet.name} · ${sheet.row_count} data rows`;
      article.append(heading);
      if (sheet.parent_sheet) {
        const relation = document.createElement('p');
        relation.textContent = `From ${sheet.source_field}. @parent_id links to @record_id in ${sheet.parent_sheet}.`;
        article.append(relation);
      }
      const columns = document.createElement('p');
      columns.textContent = `Columns: ${sheet.columns.join(', ')}`;
      article.append(columns);
      previewPanel.append(article);
    }
    for (const warning of result.warnings) {
      const note = document.createElement('p');
      note.className = 'tool-note';
      note.textContent = warning;
      previewPanel.append(note);
    }
    previewPanel.hidden = false;
  }
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (button.disabled) return;
    const isPdf = Boolean(pdfTool && form.elements.format.value === 'pdf');
    if (isPdf && pdfTool.cache && !event.submitter?.name) {
      pdfTool.download();
      status.textContent = 'Downloading the exact PDF you previewed.';
      return;
    }
    const isPreview = isPdf || event.submitter?.value === 'preview';
    const requestRevision = revision;
    if (previewPanel) previewPanel.hidden = true;
    download.hidden = true;
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    status.classList.remove('is-error');
    const file = form.elements.file.files[0];
    const textInput = form.elements.json_text;
    const text = textInput ? textInput.value.trim() : '';
    if ((file && text) || (!file && !text) ||
        (file && (file.size === 0 || file.size > 10 * 1024 * 1024)) ||
        (text && new Blob([textInput.value]).size > 400000)) {
      status.textContent = file && text ? 'Choose either a file or pasted JSON, then clear the other input.' :
        textInput ? 'Upload a nonempty JSON file (up to 10 MiB) or paste JSON (up to 400 KB).' :
          'Choose a nonempty file no larger than 10 MiB.';
      status.classList.add('is-error');
      status.focus();
      return;
    }
    submitButtons.forEach((submit) => { submit.disabled = true; });
    form.setAttribute('aria-busy', 'true');
    status.textContent = isPdf ? 'Measuring your table and preparing the PDF preview…' : isPreview ? 'Preparing your workbook preview…' :
      'Converting your file… Larger documents may take a moment.';
    try {
      const payload = new FormData(form);
      if (isPreview) payload.set('action', isPdf ? 'pdf_preview' : 'preview');
      const response = await fetch(form.getAttribute('action'), {
        method: 'POST', body: payload, headers: { Accept: 'application/json' }
      });
      if (!response.ok) {
        let message = response.status === 413 ? 'This upload exceeds the server’s size limit. Choose a smaller file.' :
          response.status === 400 ? 'The request could not be processed. Refresh the page and try again.' :
            'The conversion could not finish. Please try a smaller file or try again later.';
        if ((response.headers.get('Content-Type') || '').includes('application/json')) {
          message = (await response.json()).error || message;
        }
        throw new Error(message);
      }
      if (isPreview) {
        const result = await response.json();
        if (revision !== requestRevision) return;
        if (isPdf) {
          pdfTool.accept(result);
          status.textContent = 'PDF ready. Review the pages below, then download this exact file.';
        } else {
          showPreview(result);
          status.textContent = 'Preview ready. Review your sheets, then convert and download.';
        }
        return;
      }
      const blob = await response.blob();
      if (revision !== requestRevision) return;
      const disposition = response.headers.get('Content-Disposition') || '';
      const filename = disposition.match(/filename="?([^";]+)"?/);
      downloadUrl = URL.createObjectURL(blob);
      download.href = downloadUrl;
      download.download = filename ? filename[1] : 'converted-file';
      download.hidden = false;
      download.click();
      status.textContent = 'Your file is ready. If the download didn’t start, use the link below.';
    } catch (error) {
      if (revision !== requestRevision) return;
      status.classList.add('is-error');
      status.textContent = error instanceof TypeError ? 'Connection interrupted. Please check your connection and try again.' : error.message;
    } finally {
      submitButtons.forEach((submit) => { submit.disabled = false; });
      form.removeAttribute('aria-busy');
      if (revision !== requestRevision) {
        status.textContent = 'Your input changed. Preview or convert again to use the latest settings.';
      } else {
        status.focus();
      }
    }
  });
  window.addEventListener('pagehide', () => { if (downloadUrl) URL.revokeObjectURL(downloadUrl); pdfTool?.invalidate(); });
})();
