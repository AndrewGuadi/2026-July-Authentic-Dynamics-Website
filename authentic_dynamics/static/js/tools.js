(() => {
  const form = document.querySelector('[data-converter]');
  if (!form || !window.fetch) return;
  const status = form.querySelector('.tool-status');
  const button = form.querySelector('button[type="submit"]');
  const download = form.querySelector('.tool-download');
  let downloadUrl;
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (button.disabled) return;
    download.hidden = true;
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    status.classList.remove('is-error');
    const file = form.elements.file.files[0];
    if (!file || file.size === 0 || file.size > 10 * 1024 * 1024) {
      status.textContent = 'Choose a nonempty file no larger than 10 MiB.';
      status.classList.add('is-error');
      status.focus();
      return;
    }
    button.disabled = true;
    form.setAttribute('aria-busy', 'true');
    status.textContent = 'Converting your file… Larger documents may take a moment.';
    try {
      const response = await fetch(form.action, {
        method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' }
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
      const blob = await response.blob();
      const disposition = response.headers.get('Content-Disposition') || '';
      const filename = disposition.match(/filename="?([^";]+)"?/);
      downloadUrl = URL.createObjectURL(blob);
      download.href = downloadUrl;
      download.download = filename ? filename[1] : 'converted-file';
      download.hidden = false;
      download.click();
      status.textContent = 'Your file is ready. If the download didn’t start, use the link below.';
    } catch (error) {
      status.classList.add('is-error');
      status.textContent = error instanceof TypeError ? 'Connection interrupted. Please check your connection and try again.' : error.message;
    } finally {
      button.disabled = false;
      form.removeAttribute('aria-busy');
      status.focus();
    }
  });
  window.addEventListener('pagehide', () => { if (downloadUrl) URL.revokeObjectURL(downloadUrl); });
})();
