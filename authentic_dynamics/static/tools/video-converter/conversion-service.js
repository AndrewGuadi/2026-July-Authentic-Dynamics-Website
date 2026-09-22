export function capabilities() {
  return {supported: typeof Worker !== 'undefined' && typeof WebAssembly !== 'undefined' && typeof File !== 'undefined' && typeof File.prototype.arrayBuffer === 'function',
    webCodecs: typeof VideoDecoder !== 'undefined' && typeof VideoEncoder !== 'undefined'};
}

// Engine boundary: UI never constructs FFmpeg commands. One worker per job releases WASM memory.
export function convertVideo({file, options, onUpdate, mode = 'browser', consent = false, maxSeconds = 60}) {
  if (mode === 'server') return convertOnServer({file, options, onUpdate, consent});
  let worker, rejectJob, loadingTimer, engineReady = false, settled = false;
  const stop = () => { clearTimeout(loadingTimer); worker?.terminate(); };
  const promise = new Promise((resolve, reject) => {
    rejectJob = reject;
    const fail = (reason = 'conversion') => {
      if (settled) return;
      settled = true; stop(); reject(new Error(reason));
    };
    try {
      worker = new Worker(new URL('./video-worker.js', import.meta.url), {type: 'module'});
      loadingTimer = setTimeout(() => fail('engine'), 120000);
      worker.onerror = () => fail(engineReady ? 'conversion' : 'engine');
      worker.onmessageerror = () => fail(engineReady ? 'conversion' : 'engine');
      worker.onmessage = ({data}) => {
        try {
          if (data.type === 'complete') {
            const mime = {mp4: 'video/mp4', webm: 'video/webm', mp3: 'audio/mpeg', wav: 'audio/wav'}[options.format];
            const blob = new Blob([data.bytes], {type: mime});
            settled = true; stop(); resolve(blob);
          } else if (data.type === 'error') fail(data.reason === 'duration' ? 'duration' : 'conversion');
          else {
            if (data.type === 'ready') {
              engineReady = true;
              clearTimeout(loadingTimer);
              loadingTimer = setTimeout(() => fail('limit'), maxSeconds * 1000);
            }
            onUpdate(data);
          }
        } catch { fail('conversion'); }
      };
      worker.postMessage({type: 'convert', file, options, maxSeconds});
    } catch { fail('engine'); }
  });
  return {promise, cancel() {
    stop();
    if (!settled) { settled = true; rejectJob(new Error('cancelled')); }
  }};
}

function convertOnServer({file, options, onUpdate, consent}) {
  let xhr;
  const promise = new Promise((resolve, reject) => {
    if (!consent) { reject(new Error('Upload consent is required.')); return; }
    xhr = new XMLHttpRequest();
    xhr.open('POST', document.getElementById('processing-mode').dataset.endpoint);
    xhr.responseType = 'blob';
    xhr.timeout = (Number(document.getElementById('processing-mode').dataset.timeout) + 300) * 1000;
    xhr.setRequestHeader('X-CSRFToken', document.querySelector('meta[name="csrf-token"]').content);
    xhr.setRequestHeader('X-Video-Upload-Consent', 'yes');
    xhr.upload.onprogress = event => onUpdate({type: 'upload', progress: event.lengthComputable ? event.loaded / event.total : 0});
    xhr.upload.onload = () => onUpdate({type: 'server-processing'});
    xhr.onload = async () => {
      if (xhr.status === 200 && xhr.response?.size) resolve(xhr.response);
      else {
        let message = xhr.status === 413 ? 'This video exceeds the server upload limit. Choose browser conversion.' : 'Server conversion failed. Try again or choose browser conversion.';
        try { message = JSON.parse(await xhr.response.text()).error || message; } catch { /* proxy/CSRF HTML response */ }
        reject(new Error(message));
      }
    };
    xhr.onerror = () => reject(new Error('The server connection failed. Try again or choose browser conversion.'));
    xhr.ontimeout = () => reject(new Error('The server request timed out. Try a smaller video or browser conversion.'));
    xhr.onabort = () => reject(new Error('cancelled'));
    const data = new FormData();
    // Send a generic name; the original filename is not needed by the server.
    data.append('file', file, 'input.video');
    for (const [key, value] of Object.entries(options)) data.append(key, value);
    xhr.send(data);
  });
  return {promise, cancel() { xhr?.abort(); }};
}
