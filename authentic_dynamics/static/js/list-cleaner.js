const input = document.querySelector('#list-input');
const output = document.querySelector('#list-output');
const ignoreCase = document.querySelector('#list-case');
const sort = document.querySelector('#list-sort');
const status = document.querySelector('#list-status');
const copy = document.querySelector('#list-copy');
const download = document.querySelector('#list-download');
let revision = 0;
let downloadURL = null;
let clearedDraft = null;
const undo = document.querySelector('#list-undo');
const sample = document.querySelector('#list-sample');
function discardUndo() { clearedDraft = null; undo.hidden = true; }

function releaseDownload() {
  if (downloadURL) URL.revokeObjectURL(downloadURL);
  downloadURL = null;
}

function invalidate() {
  revision += 1;
  output.value = '';
  copy.disabled = true;
  download.disabled = true;
  releaseDownload();
  status.textContent = 'Ready to clean. Changes are not applied until you click Clean my list.';
}

document.querySelector('#list-clean').addEventListener('click', () => {
  invalidate();
  if (input.value.length > 100000) {
    status.textContent = 'Please keep your list under 100,000 characters.';
    return;
  }
  const lines = input.value.split(/\r\n|\n|\r/).map(line => line.trim());
  const seen = new Set();
  const cleaned = [];
  let duplicates = 0;
  const blanks = lines.filter(line => !line).length;
  for (const line of lines) {
    if (!line) continue;
    const key = ignoreCase.checked ? line.toLowerCase() : line;
    if (seen.has(key)) { duplicates += 1; continue; }
    seen.add(key);
    cleaned.push(line);
  }
  if (sort.checked) cleaned.sort(new Intl.Collator('en', { numeric: true }).compare);
  output.value = cleaned.join('\n');
  copy.disabled = download.disabled = cleaned.length === 0;
  status.textContent = cleaned.length
    ? `${cleaned.length.toLocaleString('en-US')} items kept · ${duplicates.toLocaleString('en-US')} duplicates removed · ${blanks.toLocaleString('en-US')} blank ${blanks === 1 ? 'line' : 'lines'} removed. Edge whitespace trimmed.`
    : 'No items found. Paste at least one nonblank line.';
});

for (const element of [input, ignoreCase, sort]) element.addEventListener('input', () => { discardUndo(); invalidate(); });

copy.addEventListener('click', async () => {
  const currentRevision = revision;
  try {
    if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
    await navigator.clipboard.writeText(output.value);
    if (revision === currentRevision) status.textContent = 'Copied to your clipboard.';
  } catch {
    if (revision !== currentRevision) return;
    output.focus(); output.select();
    status.textContent = 'Automatic copying is unavailable. The result is selected; use your device’s Copy command.';
  }
});

download.addEventListener('click', () => {
  releaseDownload();
  downloadURL = URL.createObjectURL(new Blob([output.value], { type: 'text/plain;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = downloadURL;
  link.download = 'cleaned-list.txt';
  document.body.append(link); link.click(); link.remove();
  status.textContent = 'Plain-text download requested. Check your browser’s downloads.';
});

function reset() {
  input.value = '';
  ignoreCase.checked = false; sort.checked = false;
  invalidate();
  status.textContent = 'Cleared. Paste a list to get started.';
}
document.querySelector('#list-reset').addEventListener('click', () => {
  if (input.value) clearedDraft = {value: input.value, ignoreCase: ignoreCase.checked, sort: sort.checked};
  reset();
  undo.hidden = !clearedDraft;
  if (clearedDraft) status.textContent = 'Cleared. Undo clear restores the previous input until you edit again or leave this page.';
  input.focus();
});
undo.addEventListener('click', () => {
  if (!clearedDraft) return;
  input.value = clearedDraft.value;
  ignoreCase.checked = clearedDraft.ignoreCase; sort.checked = clearedDraft.sort;
  discardUndo(); invalidate(); input.focus();
  status.textContent = 'Input restored. Choose Clean my list to create a fresh result.';
});
sample.addEventListener('click', () => {
  if (input.value.trim()) { status.textContent = 'Clear your current list before loading the example.'; return; }
  discardUndo();
  input.value = '  Counter signs  \nMenu cards\nCounter signs\n\nmenu cards\nWindow decals';
  ignoreCase.checked = true; sort.checked = false;
  invalidate(); input.focus();
  status.textContent = 'Example loaded. Clean the list to see duplicates and blank lines removed.';
});
sample.disabled = false;
window.addEventListener('pagehide', () => { discardUndo(); reset(); });
document.querySelector('#list-clean').disabled = false;
document.querySelector('#list-reset').disabled = false;
