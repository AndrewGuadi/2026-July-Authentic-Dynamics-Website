import {PRESETS} from './conversion-options.js';
import {capabilities, convertVideo} from './conversion-service.js';

const $ = id => document.getElementById(id);
let file = null, sourceURL = null, outputURL = null, job = null, generation = 0;
const supported = capabilities().supported;
const serverMode = () => $('processing-mode').value === 'server';
const size = bytes => `${(bytes / 1048576).toFixed(2)} MB`;
function status(message, error = false) { $('status').textContent = message; $('status').classList.toggle('is-error', error); }
function clearOutput() {
  if (outputURL) URL.revokeObjectURL(outputURL);
  outputURL = null; $('download').removeAttribute('href'); $('result').hidden = true;
}
function ready() {
  const server = serverMode();
  $('convert').disabled = (!server && !supported) || !file || !!job ||
    (server ? !$('upload-consent').checked || file.size > Number($('processing-mode').dataset.maxBytes)
      : !$('large-warning').hidden && !$('large-confirm').checked);
  $('settings').disabled = !file || !!job;
  $('video-file').disabled = (!server && !supported) || !!job;
  $('processing-mode').disabled = !!job;
  $('upload-consent').disabled = !!job;
  $('convert').textContent = server ? 'Upload & convert on server' : 'Convert locally';
  $('cancel').hidden = !job;
}
function warnLarge() {
  $('large-warning').hidden = serverMode() || !(file && (file.size >= 200 * 1048576 || $('preview').videoWidth * $('preview').videoHeight > 1920 * 1080 || $('preview').duration > 600));
  $('server-size-warning').hidden = !(serverMode() && file && file.size > Number($('processing-mode').dataset.maxBytes));
  ready();
}
function applyPreset() {
  const preset = PRESETS[$('intent').value];
  for (const key of ['quality', 'resolution', 'audio']) $(key).value = preset[key];
  $('fps').value = 'original';
  const extract = $('intent').value === 'extract';
  $('format').value = extract ? 'mp4' : preset.format;
  for (const key of ['format', 'resolution', 'fps', 'audio']) $(key).closest('label').hidden = extract;
  $('audio-format-label').hidden = !extract;
  $('preset-note').textContent = extract ? 'Extract the first audio track. Choose MP3 or WAV in output settings.' : `${preset.format.toUpperCase()} · ${preset.quality} quality · ${preset.resolution === 'original' ? 'original size' : preset.resolution + 'p maximum'} · ${preset.audio === 'remove' ? 'no audio' : 'audio kept if present'}`;
  clearOutput();
}
function reset(clearPicker = true) {
  generation++; job?.cancel(); job = null;
  $('preview').removeAttribute('src'); $('preview').load();
  if (sourceURL) URL.revokeObjectURL(sourceURL);
  sourceURL = null; file = null; clearOutput();
  if (clearPicker) $('video-file').value = '';
  $('source').hidden = true; $('clear').hidden = true;
  $('large-warning').hidden = true; $('large-confirm').checked = false; $('progress').hidden = true;
  ready();
}
function selectFile(selected) {
  if (job || (!supported && !serverMode())) return;
  reset(false);
  $('upload-consent').checked = false;
  if (!selected) return;
  if (!selected.size || !(selected.type.startsWith('video/') || /\.(mp4|m4v|mov|webm|mkv|avi|mpeg|mpg)$/i.test(selected.name))) {
    status('Choose a nonempty video file, such as MP4, WebM or MOV.', true); return;
  }
  file = selected;
  $('file-info').textContent = `${file.name}\n${size(file.size)}`;
  $('source').hidden = false; $('clear').hidden = false;
  sourceURL = URL.createObjectURL(file); $('preview').src = sourceURL;
  warnLarge(); status('Video selected locally. Choose your settings, then convert.');
}
$('preview').addEventListener('loadedmetadata', () => {
  if (!file) return;
  const video = $('preview');
  $('file-info').textContent = `${file.name}\n${size(file.size)} · ${video.videoWidth} × ${video.videoHeight}${Number.isFinite(video.duration) ? ' · ' + Math.floor(video.duration / 60) + ':' + String(Math.floor(video.duration % 60)).padStart(2, '0') : ''}`;
  warnLarge();
});
$('preview').addEventListener('error', () => { if (file && !job) status('Preview unavailable. You can still try converting this file locally.'); });
$('video-file').addEventListener('change', event => selectFile(event.target.files[0]));
for (const name of ['dragover', 'drop']) document.addEventListener(name, event => { event.preventDefault(); });
$('drop-zone').addEventListener('dragover', () => $('drop-zone').classList.add('dragging'));
$('drop-zone').addEventListener('dragleave', () => $('drop-zone').classList.remove('dragging'));
$('drop-zone').addEventListener('drop', event => {
  $('drop-zone').classList.remove('dragging');
  if (!job) $('video-file').value = '';
  selectFile(event.dataTransfer.files[0]);
});
$('intent').addEventListener('change', applyPreset);
$('settings').addEventListener('change', event => {
  clearOutput();
  if (event.target.id !== 'intent') $('preset-note').textContent = 'Using your adjusted output settings.';
});
$('large-confirm').addEventListener('change', ready);
$('upload-consent').addEventListener('change', ready);
$('processing-mode').addEventListener('change', () => {
  clearOutput(); $('upload-consent').checked = false;
  $('server-notice').hidden = !serverMode();
  $('selection-note').textContent = serverMode() ? 'Selection is local. Upload starts only when you agree and click Upload & convert.' : 'Read locally. Never uploaded in browser mode.';
  warnLarge();
  status(serverMode() ? 'Server mode selected. Review the upload notice before converting.' : 'Browser mode selected. Your video stays on this device.');
});
$('clear').addEventListener('click', () => { reset(); status('Video and result cleared from this page.'); });
$('cancel').addEventListener('click', () => job?.cancel());
$('convert').addEventListener('click', async () => {
  if ($('convert').disabled) return;
  clearOutput();
  const run = ++generation;
  const mode = serverMode() ? 'server' : 'browser';
  const options = Object.fromEntries(['format', 'quality', 'resolution', 'fps', 'audio'].map(key => [key, $(key).value]));
  if ($('intent').value === 'extract') options.format = $('audio-format').value;
  const originalSize = file.size, filename = file.name.replace(/\.[^.]+$/, '') + '-converted.' + options.format;
  $('preview').pause(); $('progress').hidden = false; $('progress').removeAttribute('value');
  status(mode === 'server' ? 'Uploading to Authentic Dynamics…' : 'Preparing local converter… Downloading the engine if needed. Your video is staying on this device.');
  job = convertVideo({file, options, mode, consent: $('upload-consent').checked, onUpdate(data) {
    if (run !== generation) return;
    if (data.type === 'upload') {
      $('progress').value = Math.floor(data.progress * 100);
      status(`Uploading to Authentic Dynamics… ${Math.floor(data.progress * 100)}%`);
    }
    if (data.type === 'server-processing') {
      $('progress').removeAttribute('value');
      status('Converting on the server… The result will download to this page when ready.');
    }
    if (data.type === 'ready') status('Converting locally… Your video is staying on this device.');
    if (data.type === 'progress' && Number.isFinite(data.progress) && data.progress > 0) {
      const percent = Math.min(99, Math.floor(data.progress * 100));
      $('progress').value = percent;
      status(`Converting locally… ${percent}% (estimated). Your video is staying on this device.`);
    }
  }});
  ready();
  try {
    const blob = await job.promise;
    if (run !== generation) return;
    outputURL = URL.createObjectURL(blob);
    $('download').href = outputURL; $('download').download = filename;
    const saved = originalSize - blob.size;
    $('result-info').textContent = `${filename}\n${options.format.toUpperCase()} · ${size(blob.size)}\nOriginal: ${size(originalSize)}\n${saved > 0 ? size(saved) + ' smaller · ' + Math.round(saved / originalSize * 100) + '% reduction' : size(-saved) + ' larger than original'}`;
    if (options.format === 'mp4' || options.format === 'webm') {
      const probe = document.createElement('video'); probe.preload = 'metadata';
      const cleanup = () => { probe.removeAttribute('src'); probe.load(); };
      const timeout = setTimeout(cleanup, 10000);
      probe.onloadedmetadata = () => {
        if (run === generation && outputURL === probe.src) $('result-info').textContent += `\n${probe.videoWidth} × ${probe.videoHeight}`;
        clearTimeout(timeout); cleanup();
      };
      probe.onerror = () => { clearTimeout(timeout); cleanup(); };
      probe.src = outputURL;
    }
    $('result').hidden = false; $('progress').value = 100;
    status(mode === 'server' ? 'Server conversion complete. The temporary upload has been removed; save your result below.' : 'Conversion complete. Your video was never uploaded.');
  } catch (error) {
    if (run !== generation) return;
    const message = error.message === 'cancelled' ? (mode === 'server' ? 'Request cancelled. If processing already started, the server may finish before its time limit and then remove temporary files.' : 'Conversion cancelled. You can try again.')
      : mode === 'server' ? error.message
      : error.message === 'engine' ? 'We couldn’t prepare the local converter. Check your connection for the engine download, then try again in a current browser. Your video was not uploaded.'
      : "We couldn’t convert this video in your browser. The codec may be unsupported, the file damaged, or device memory insufficient. Try another format, a smaller video, or another browser. Audio extraction requires an audio track.";
    status(message, error.message !== 'cancelled');
    $('progress').hidden = true;
  } finally { if (run === generation) { job = null; ready(); } }
});
window.addEventListener('pagehide', reset);
applyPreset();
if (!supported) { $('video-file').disabled = true; status('This browser needs WebAssembly and Web Workers. Try a current browser on another device. No video has been uploaded.', true); }
