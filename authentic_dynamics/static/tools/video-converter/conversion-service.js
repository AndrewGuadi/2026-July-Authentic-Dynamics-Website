export function capabilities() {
  return {supported: typeof Worker !== 'undefined' && typeof WebAssembly !== 'undefined' && typeof File !== 'undefined' && typeof File.prototype.arrayBuffer === 'function',
    webCodecs: typeof VideoDecoder !== 'undefined' && typeof VideoEncoder !== 'undefined'};
}

// Engine boundary: UI never constructs FFmpeg commands. One worker per job releases WASM memory.
export function convertVideo({file, options, onUpdate}) {
  let worker, rejectJob, loadingTimer, engineReady = false, settled = false;
  const stop = () => { clearTimeout(loadingTimer); worker?.terminate(); };
  const promise = new Promise((resolve, reject) => {
    rejectJob = reject;
    const fail = () => {
      if (settled) return;
      settled = true; stop(); reject(new Error(engineReady ? 'conversion' : 'engine'));
    };
    try {
      worker = new Worker(new URL('./video-worker.js', import.meta.url), {type: 'module'});
      loadingTimer = setTimeout(fail, 120000);
      worker.onerror = fail;
      worker.onmessageerror = fail;
      worker.onmessage = ({data}) => {
        try {
          if (data.type === 'complete') {
            const mime = {mp4: 'video/mp4', webm: 'video/webm', mp3: 'audio/mpeg', wav: 'audio/wav'}[options.format];
            const blob = new Blob([data.bytes], {type: mime});
            settled = true; stop(); resolve(blob);
          } else if (data.type === 'error') fail();
          else {
            if (data.type === 'ready') { engineReady = true; clearTimeout(loadingTimer); }
            onUpdate(data);
          }
        } catch { fail(); }
      };
      worker.postMessage({type: 'convert', file, options});
    } catch { fail(); }
  });
  return {promise, cancel() {
    stop();
    if (!settled) { settled = true; rejectJob(new Error('cancelled')); }
  }};
}
