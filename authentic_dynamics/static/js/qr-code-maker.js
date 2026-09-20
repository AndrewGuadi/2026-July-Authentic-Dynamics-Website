import qrcode from '../vendor/qr/qrcode-2.0.4.mjs';

const $ = id => document.getElementById(`qr-${id}`);
const value = id => $(id).value;
const presets = {
  review: ['How did we do?', 'Scan to leave us a Google review.'],
  website: ['Come on in.', 'Scan to visit our website.'],
  menu: ['Find your next favorite.', 'Scan for our menu or services.'],
  social: ['Stay in the loop.', 'Scan to follow us.'],
  custom: ['Take a closer look.', 'Scan to find out more.'],
};
let code, destination, logo, logoRequest = 0, busy = false, pdfLoader;
const buttons = [...document.querySelectorAll('[data-download]')];
qrcode.stringToBytes = text => Array.from(new TextEncoder().encode(text));

function luminance(hex) {
  const parts = hex.slice(1).match(/../g).map(part => {
    const c = parseInt(part, 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return parts[0] * .2126 + parts[1] * .7152 + parts[2] * .0722;
}

function readDestination() {
  const raw = value('url').trim();
  if (!raw) throw new Error('Paste a destination link to create your code.');
  if (/[\u0000-\u0020\u007f]/u.test(raw) || !/^https?:\/\//i.test(raw)) throw new Error('Use a complete http:// or https:// link without spaces.');
  let url;
  try { url = new URL(raw); } catch { throw new Error('Enter a valid website address.'); }
  if (!url.hostname || url.username || url.password) throw new Error('Use a website link without embedded usernames or passwords.');
  if (new TextEncoder().encode(url.href).length > 1800) throw new Error('This link is too long. Use a shorter destination URL (up to 1,800 bytes).');
  return url;
}

function drawCode(canvas, pixels) {
  canvas.width = canvas.height = pixels;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = value('background'); ctx.fillRect(0, 0, pixels, pixels);
  const count = code.getModuleCount(), step = Math.floor(pixels / (count + 8));
  const offset = Math.floor((pixels - count * step) / 2);
  ctx.fillStyle = value('foreground');
  for (let y = 0; y < count; y++) for (let x = 0; x < count; x++) {
    if (code.isDark(y, x)) ctx.fillRect(offset + x * step, offset + y * step, step, step);
  }
  return canvas;
}

function qrCanvas(pixels) { return drawCode(document.createElement('canvas'), pixels); }

function svg() {
  const count = code.getModuleCount(), side = count + 8;
  let path = '';
  for (let y = 0; y < count; y++) for (let x = 0; x < count; x++) {
    if (code.isDark(y, x)) path += `M${x + 4},${y + 4}h1v1h-1z`;
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${side} ${side}" width="${value('size')}" height="${value('size')}" shape-rendering="crispEdges"><rect width="100%" height="100%" fill="${value('background')}"/><path d="${path}" fill="${value('foreground')}"/></svg>`;
}

const layouts = {counter: [1500, 2100, 5, 7], window: [2550, 3300, 8.5, 11], insert: [1200, 1800, 4, 6], social: [1800, 1800, 6, 6], plain: [1800, 1800, 6, 6]};

// Fit full text into a bounded area, including long unbroken words and Unicode.
function fitText(ctx, text, center, top, width, height, initialSize, bold = false) {
  if (!text) return;
  let lines, size = initialSize;
  do {
    ctx.font = `${bold ? '700' : '400'} ${size}px Arial, sans-serif`;
    lines = [''];
    for (const char of text) {
      const last = lines.length - 1;
      if (ctx.measureText(lines[last] + char).width > width) lines.push(char);
      else lines[last] += char;
    }
    if (lines.length * size * 1.25 <= height) break;
    size -= 2;
  } while (size > 8);
  ctx.textAlign = 'center'; ctx.textBaseline = 'top'; ctx.fillStyle = '#172c28';
  lines.forEach((line, i) => ctx.fillText(line, center, top + i * size * 1.25));
}

function renderArtwork() {
  const canvas = $('artwork'), layout = value('layout');
  if (layout === 'plain') { drawCode(canvas, 1800); return; }
  const [w, h] = layouts[layout]; canvas.width = w; canvas.height = h;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, w, h);
  ctx.fillStyle = value('accent'); ctx.fillRect(0, 0, w, h * .025);
  if (logo) {
    const scale = Math.min(w * .45 / logo.width, h * .09 / logo.height);
    const lw = logo.width * scale, lh = logo.height * scale;
    ctx.drawImage(logo, (w - lw) / 2, h * .05 + (h * .09 - lh) / 2, lw, lh);
  }
  fitText(ctx, value('business'), w / 2, h * .16, w * .83, h * .055, w * .034, true);
  fitText(ctx, value('headline'), w / 2, h * .235, w * .84, h * .10, w * .062, true);
  fitText(ctx, value('message'), w / 2, h * .345, w * .82, h * .065, w * .03);
  const qrSize = Math.floor(Math.min(w * .68, h * .40));
  ctx.drawImage(qrCanvas(qrSize), Math.floor((w - qrSize) / 2), Math.floor(h * .43));
  fitText(ctx, value('instruction'), w / 2, h * .85, w * .84, h * .05, w * .032, true);
  fitText(ctx, destination.hostname, w / 2, h * .92, w * .80, h * .045, w * .022);
}

function update() {
  code = null; destination = null;
  buttons.forEach(button => { button.disabled = true; });
  $('test').hidden = true; $('test').removeAttribute('href');
  $('artwork').hidden = true; $('empty').hidden = false;
  $('destination').textContent = ''; $('error').textContent = '';
  $('status').textContent = 'Ready for your link.';
  $('print').replaceChildren();
  if (!value('url').trim()) return;
  try {
    destination = readDestination();
    const fg = luminance(value('foreground')), bg = luminance(value('background'));
    if (bg <= fg || (bg + .05) / (fg + .05) < 4.5) throw new Error('Choose a darker code and lighter background with stronger contrast.');
    const next = qrcode(0, value('level'));
    next.addData(destination.href, 'Byte');
    try { next.make(); } catch { throw new Error('This link is too long for this QR setting. Shorten the link or use Standard correction.'); }
    code = next;
    renderArtwork();
    $('artwork').hidden = false; $('empty').hidden = true;
    $('destination').textContent = `Destination: ${destination.href}`;
    $('test').href = destination.href; $('test').hidden = false;
    buttons.forEach(button => { button.disabled = busy; });
    $('status').textContent = 'Ready to download. Your link is encoded directly in the code.';
  } catch (error) {
    code = null;
    $('error').textContent = error.message;
    $('status').textContent = 'Update the fields above to continue.';
  }
}

function download(blob, extension, suffix = '') {
  if (!blob) throw new Error('The image could not be exported. Try a smaller size.');
  const url = URL.createObjectURL(blob), anchor = document.createElement('a');
  anchor.href = url;
  const name = (value('business') || 'qr-code').replace(/[^a-z0-9_-]+/gi, '-').slice(0, 70) || 'qr-code';
  anchor.download = `${name}${suffix}.${extension}`;
  anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 30000);
}
function png(canvas) { return new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('Image export failed.')), 'image/png')); }

async function loadPDF() {
  if (!pdfLoader) pdfLoader = new Promise((resolve, reject) => {
    if (window.jspdf) { resolve(); return; }
    const script = document.createElement('script');
    script.src = new URL('../vendor/invoice/jspdf-4.2.1.umd.min.js', import.meta.url).href;
    script.onload = resolve;
    script.onerror = () => { script.remove(); pdfLoader = null; reject(new Error('PDF download is unavailable. Try Print artwork instead.')); };
    document.head.append(script);
  });
  return pdfLoader;
}

buttons.forEach(button => button.addEventListener('click', async () => {
  if (!code || busy) return;
  busy = true; buttons.forEach(item => { item.disabled = true; });
  $('editor').inert = true;
  $('status').textContent = 'Preparing your download…';
  try {
    const kind = button.dataset.download;
    if (kind === 'svg') download(new Blob([svg()], { type: 'image/svg+xml' }), 'svg');
    else if (kind === 'png') download(await png(qrCanvas(Number(value('size')))), 'png');
    else if (kind === 'artwork') download(await png($('artwork')), 'png', '-artwork');
    else {
      const [, , width, height] = layouts[value('layout')];
      const data = $('artwork').toDataURL('image/png');
      if (kind === 'pdf') {
        await loadPDF();
        const pdf = new window.jspdf.jsPDF({ unit: 'in', format: 'letter', compress: true });
        pdf.addImage(data, 'PNG', (8.5 - width) / 2, (11 - height) / 2, width, height);
        download(pdf.output('blob'), 'pdf', '-sign');
      } else {
        const image = new Image(); image.src = data; image.alt = 'Your QR artwork';
        image.style.width = `${width}in`; image.style.height = `${height}in`;
        await image.decode(); $('print').replaceChildren(image); window.print();
      }
    }
    $('status').textContent = 'Your artwork is ready. Test the downloaded code before printing.';
  } catch (error) { $('error').textContent = error.message; $('status').textContent = 'Please try again.'; }
  finally { busy = false; $('editor').inert = false; buttons.forEach(item => { item.disabled = !code; }); }
}));

$('editor').addEventListener('input', event => { if (event.target.id !== 'qr-logo') update(); });
$('purpose').addEventListener('change', () => {
  [ $('headline').value, $('message').value ] = presets[value('purpose')];
  $('review-help').hidden = value('purpose') !== 'review'; update();
});
$('logo').addEventListener('change', async () => {
  const request = ++logoRequest, file = $('logo').files[0];
  if (!file) return;
  $('logo-status').textContent = 'Loading your logo…';
  let url;
  try {
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) throw new Error('Choose a PNG, JPG, or WebP logo up to 5 MB.');
    url = URL.createObjectURL(file);
    const image = new Image(); image.src = url; await image.decode();
    if (request !== logoRequest) return;
    if (image.naturalWidth * image.naturalHeight > 20000000) throw new Error('Choose a logo smaller than 20 megapixels.');
    const canvas = document.createElement('canvas'), scale = Math.min(1, 1000 / Math.max(image.naturalWidth, image.naturalHeight));
    canvas.width = Math.max(1, Math.round(image.naturalWidth * scale)); canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
    canvas.getContext('2d').drawImage(image, 0, 0, canvas.width, canvas.height);
    logo = canvas; $('remove-logo').hidden = false;
    $('logo-status').textContent = 'Logo added locally.'; update();
  } catch (error) { if (request === logoRequest) $('logo-status').textContent = error.message || 'This logo could not be opened.'; }
  finally { if (url) URL.revokeObjectURL(url); $('logo').value = ''; }
});
$('remove-logo').addEventListener('click', () => {
  ++logoRequest; logo = null; $('remove-logo').hidden = true; $('logo-status').textContent = 'Logo removed.'; update();
});
if (navigator.clipboard?.readText) {
  $('paste').hidden = false;
  $('paste').addEventListener('click', async () => {
    try { $('url').value = (await navigator.clipboard.readText()).slice(0, 1800); update(); }
    catch { $('error').textContent = 'Clipboard access is unavailable. Paste directly into the URL field.'; }
  });
}
update();
