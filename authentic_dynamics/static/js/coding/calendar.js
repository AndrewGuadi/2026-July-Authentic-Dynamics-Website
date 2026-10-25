import { createEditor } from './editor.bundle.js';

const lesson = JSON.parse(document.getElementById('coding-lesson').textContent);
const textarea = document.getElementById('coding-source');
const status = document.getElementById('coding-status');
const results = document.getElementById('coding-results');
const output = document.getElementById('coding-output');
const runButton = document.getElementById('coding-run');
const stopButton = document.getElementById('coding-stop');
const key = `ad-coding-v1:${lesson.language}:${lesson.date}`;
let storage = true, editor, active;
try { if (localStorage.getItem(key + ':completed')) status.textContent = 'Previously completed on this device. Try another approach or revisit your solution.'; } catch { storage = false; }
try { textarea.value = localStorage.getItem(key + ':draft') ?? lesson.starter; } catch { storage = false; }
function save(value) {
  try { localStorage.setItem(key + ':draft', value); } catch { storage = false; }
}
editor = createEditor(document.getElementById('coding-editor'), textarea, lesson.language, save, () => runButton.click());
const cache = new Map();
function busy(value) { runButton.disabled = value; stopButton.disabled = !value; }
function cleanup(run) {
  clearTimeout(run.timer);
  run.abort.abort();
  run.port?.postMessage('stop');
  run.port?.close();
  run.frame?.remove();
  window.removeEventListener('message', run.listener);
  if (active === run) { active = null; busy(false); }
}
function finish(run, message) {
  if (active !== run) return;
  status.textContent = message;
  cleanup(run);
}
function equal(a, b) {
  if (a === b) return true;
  if (!a || !b || typeof a !== 'object' || typeof b !== 'object') return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  const keys = Object.keys(a).sort(), other = Object.keys(b).sort();
  return keys.length === other.length && keys.every((key, i) => key === other[i] && equal(a[key], b[key]));
}
async function loadAssets(run) {
  if (lesson.language === 'javascript') return { sources: '', binaries: {} };
  const response = await fetch(new URL('./runtime-manifest.json', import.meta.url), { signal: run.abort.signal });
  if (!response.ok) throw new Error('Could not load the runtime manifest.');
  const manifest = (await response.json())[lesson.language];
  const files = await Promise.all(Object.entries(manifest.files).map(async ([name, meta]) => {
    const url = manifest.base + name;
    if (!cache.has(url)) {
      const response = await fetch(url, { credentials: 'omit', referrerPolicy: 'no-referrer', signal: run.abort.signal });
      if (!response.ok) throw new Error('Runtime download failed. Check your connection and try again.');
      const bytes = await response.arrayBuffer();
      const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(b => b.toString(16).padStart(2, '0')).join('');
      if (bytes.byteLength !== meta.size || digest !== meta.sha256) throw new Error('Runtime integrity check failed. Nothing was executed.');
      cache.set(url, bytes);
    }
    return [name, cache.get(url)];
  }));
  const binaries = Object.fromEntries(files.filter(([name]) => !name.endsWith('.js')));
  const decoder = new TextDecoder();
  const ordered = lesson.language === 'python' ? ['pyodide.asm.js', 'pyodide.js'] : ['sql-wasm.js'];
  const sources = ordered.map(name => decoder.decode(files.find(([file]) => file === name)[1])).join('\n;\n');
  return { sources, binaries };
}
function render(run, data) {
  if (active !== run) return;
  if (data.type === 'ready') {
    status.textContent = 'Running your solution…';
    clearTimeout(run.timer);
    run.timer = setTimeout(() => finish(run, 'Execution stopped after 5 seconds. Check for an endless loop, then try again.'), 5000);
  } else if (data.type === 'error') {
    output.textContent = String(data.output || '');
    finish(run, 'Could not complete this run: ' + String(data.message || 'Unknown error.').slice(0, 1000));
  } else if (data.type === 'result') {
    if (!Array.isArray(data.results) || data.results.length !== lesson.tests.length) return finish(run, 'The runner returned an invalid result.');
    let passed = 0;
    results.replaceChildren();
    data.results.forEach((result, i) => {
      const test = lesson.tests[i];
      const pass = !result.error && equal(result.actual, test.expected);
      if (pass) passed += 1;
      const row = document.createElement('li');
      row.dataset.pass = String(pass);
      row.textContent = `${pass ? '✓ PASS' : '× FAIL'} · ${test.name}`;
      if (!pass) {
        const detail = document.createElement('pre');
        detail.textContent = result.error ? String(result.error).slice(0, 1000) : `Expected: ${JSON.stringify(test.expected)}\nReceived: ${JSON.stringify(result.actual)}`;
        row.append(detail);
      }
      results.append(row);
    });
    output.textContent = String(data.output || 'No console output.').slice(0, 12000);
    if (passed === lesson.tests.length) {
      try { localStorage.setItem(key + ':completed', new Date().toISOString()); } catch { storage = false; }
    }
    finish(run, `${passed} of ${lesson.tests.length} tests passed.${passed === lesson.tests.length ? ' Challenge complete.' : ' Adjust your solution and try again.'}${storage ? '' : ' Browser storage is unavailable; download your code to keep it.'}`);
  }
}
async function start() {
  if (active) return;
  const code = editor.getValue();
  if (code.length > 20000) { status.textContent = 'Keep your solution under 20,000 characters.'; return; }
  save(code);
  const run = { abort: new AbortController() };
  active = run;
  busy(true);
  results.replaceChildren();
  output.textContent = 'Preparing the isolated workspace…';
  status.textContent = lesson.language === 'javascript' ? 'Preparing JavaScript…' : 'Downloading and verifying the language runtime…';
  run.timer = setTimeout(() => finish(run, 'Runtime setup timed out after 90 seconds. Check your connection and try again.'), 90000);
  try {
    const [assets, workerResponse] = await Promise.all([
      loadAssets(run), fetch(new URL('./worker.js', import.meta.url), { signal: run.abort.signal }),
    ]);
    if (!workerResponse.ok) throw new Error('Could not load the code runner.');
    const workerSource = await workerResponse.text();
    if (active !== run) return;
    const frame = document.createElement('iframe');
    run.frame = frame;
    frame.className = 'coding-frame';
    frame.title = 'Isolated coding workspace';
    frame.setAttribute('sandbox', 'allow-scripts');
    frame.src = '/coding-calendar/sandbox';
    run.listener = event => {
      if (active !== run || event.source !== frame.contentWindow || event.data?.type !== 'coding-sandbox-ready' || run.port) return;
      const channel = new MessageChannel();
      run.port = channel.port1;
      run.port.onmessage = event => render(run, event.data);
      frame.contentWindow.postMessage({ type: 'start', source: assets.sources + '\n;\n' + workerSource, payload: { language: lesson.language, code, tests: lesson.tests, assets: assets.binaries } }, '*', [channel.port2]);
      status.textContent = 'Starting the language runtime…';
    };
    window.addEventListener('message', run.listener);
    document.body.append(frame);
  } catch (error) { if (active === run) finish(run, String(error.message).slice(0, 1000)); }
}
runButton.addEventListener('click', start);
stopButton.addEventListener('click', () => { if (active) finish(active, 'Stopped. Your code is still here.'); });
document.getElementById('coding-reset').addEventListener('click', () => {
  if (active) finish(active, 'Stopped.');
  editor.setValue(lesson.starter);
  results.replaceChildren();
  output.textContent = 'Your output will appear here.';
  status.textContent = 'Starter code restored.';
});
document.getElementById('coding-download').addEventListener('click', () => {
  const url = URL.createObjectURL(new Blob([editor.getValue()], { type: 'text/plain' }));
  const link = document.createElement('a');
  link.href = url; link.download = `coding-${lesson.date}.${{ javascript: 'js', python: 'py', sql: 'sql' }[lesson.language]}`;
  link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
window.addEventListener('pagehide', () => { if (active) cleanup(active); });
