'use strict';
// Native anchors and details remain usable when JavaScript is unavailable.
document.querySelectorAll('[data-open-panel]').forEach(link => {
  link.addEventListener('click', () => {
    const panel = document.getElementById(link.dataset.openPanel);
    if (panel instanceof HTMLDetailsElement) panel.open = true;
  });
});
const layout = document.getElementById('qr-layout');
if (layout) {
  const updateExport = () => {
    const primary = layout.value === 'plain' ? 'png' : layout.value === 'social' ? 'artwork' : 'pdf';
    document.querySelectorAll('[data-download]').forEach(button => {
      button.classList.toggle('is-primary', button.dataset.download === primary);
    });
    document.getElementById('qr-export-guide').textContent = primary === 'pdf'
      ? 'For this sign, download the print-ready PDF. Print at 100% / Actual size.'
      : primary === 'artwork' ? 'For a social post, download Artwork PNG.' : 'For a code without a sign, download QR PNG. SVG is available for scalable artwork.';
  };
  layout.addEventListener('change', updateExport);
  updateExport();
}
