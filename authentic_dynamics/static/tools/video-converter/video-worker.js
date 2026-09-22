import createFFmpegCore from './ffmpeg/ffmpeg-core.js';
import {buildArguments} from './conversion-options.js';

self.onmessage = async ({data}) => {
  if (data.type !== 'convert') return;
  let core;
  let reason;
  const output = '/output.' + data.options.format;
  try {
    const args = buildArguments(data.options);
    core = await createFFmpegCore({locateFile: () => new URL('./ffmpeg/ffmpeg-core.wasm', import.meta.url).href});
    core.setLogger(() => {}); // Never forward media details to logging or telemetry.
    core.setProgress(({progress}) => self.postMessage({type: 'progress', progress}));
    self.postMessage({type: 'ready'});
    // Read in the worker: no main-thread ArrayBuffer copy or base64 representation.
    core.FS.writeFile('/input', new Uint8Array(await data.file.arrayBuffer()), {canOwn: true});
    const readings = [];
    core.setLogger(({type, message}) => { if (type === 'stdout') readings.push(message); });
    core.ffprobe('-v', 'error', '-show_entries', 'format=duration',
      '-of', 'default=noprint_wrappers=1:nokey=1', '/input');
    const duration = Number(readings.join('').trim());
    core.reset();
    core.setLogger(() => {});
    if (!Number.isFinite(duration) || duration <= 0 || duration > data.maxSeconds) {
      reason = 'duration';
      throw new Error('Unsupported local duration');
    }
    core.exec(...args);
    if (core.ret !== 0) throw new Error('Conversion failed');
    const bytes = core.FS.readFile(output);
    if (!bytes.length) throw new Error('Empty output');
    self.postMessage({type: 'complete', bytes}, [bytes.buffer]);
  } catch {
    self.postMessage({type: 'error', reason});
  } finally {
    if (core) {
      for (const path of ['/input', output]) { try { core.FS.unlink(path); } catch { /* absent on failure */ } }
    }
    self.close();
  }
};
