// Browser X-Ray: no network, storage, recording or identifier APIs are used here.
const $ = selector => document.querySelector(selector);
const keys = ['motion', 'location', 'camera', 'microphone', 'screen'];
const states = Object.fromEntries(['browser', 'display', ...keys].map(key => [key, 'Not enabled']));
const labs = Object.fromEntries(keys.map(key => [key, { version: 0, cleanups: [], busy: false }]));
const AudioContextType = window.AudioContext || window.webkitAudioContext;
const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)');
let scanned = false;
let events = [];
let latestOrientation = null;
let latestMotion = null;
let trace = [];
let scanFrame = 0;

function safe(check) { try { return Boolean(check()); } catch { return false; } }
function support(key) {
  return safe(() => ({
    motion: () => 'DeviceOrientationEvent' in window || 'DeviceMotionEvent' in window,
    location: () => typeof navigator.geolocation?.getCurrentPosition === 'function',
    camera: () => typeof navigator.mediaDevices?.getUserMedia === 'function',
    microphone: () => typeof navigator.mediaDevices?.getUserMedia === 'function' && Boolean(AudioContextType),
    screen: () => typeof navigator.mediaDevices?.getDisplayMedia === 'function',
  })[key]());
}

function status(key, state, explanation = '') {
  states[key] = state;
  $(`#access-${key}`).textContent = state;
  const element = $(`#${key}-status`);
  if (element) {
    element.dataset.state = state;
    element.textContent = `${state}${explanation ? ` — ${explanation}` : ''}`;
  }
  $('#xr-count').textContent = `Experiments active: ${Object.values(states).filter(value => value === 'Active').length} / 7`;
}

function readings(selector, values) {
  const fragment = document.createDocumentFragment();
  for (const [label, value] of values) {
    const row = document.createElement('div');
    const term = document.createElement('dt');
    const detail = document.createElement('dd');
    term.textContent = label;
    detail.textContent = String(value);
    row.append(term, detail);
    fragment.append(row);
  }
  $(selector).replaceChildren(fragment);
}

const number = (value, digits = 1, unit = '') => Number.isFinite(value) ? `${value.toFixed(digits)}${unit}` : 'Not provided';
function renderLog() {
  $('#xr-log').textContent = events.length ? events.map(event => `${event.time} · ${event.kind}\n${JSON.stringify(event.values, null, 2)}`).join('\n\n') : 'No events retained.';
}
function log(key, kind, values) {
  if (!$('#xr-technical').open) return;
  events.push({ key, kind, values, time: new Date().toLocaleTimeString() });
  if (events.length > 100) events.shift();
  renderLog();
}
$('#xr-technical').addEventListener('toggle', () => {
  if (!$('#xr-technical').open) { events = []; renderLog(); }
});

function controls(key, busy) {
  labs[key].busy = busy;
  $(`[data-enable="${key}"]`).disabled = busy || !support(key) || !window.isSecureContext;
  $(`[data-stop="${key}"]`).disabled = !busy;
  if (key === 'camera') $('#xr-facing').disabled = busy;
}
function disposeStream(stream) { stream.getTracks().forEach(track => track.stop()); }
function stop(key, state = 'Stopped', explanation = 'Access stopped; local readings cleared.') {
  const lab = labs[key];
  lab.version += 1; // Invalidate asynchronous permission results, including uncancellable geolocation.
  for (const cleanup of lab.cleanups.splice(0)) { try { cleanup(); } catch { /* Continue releasing other resources. */ } }
  $(`#${key}-boundary`).hidden = true;
  controls(key, false);
  events = events.filter(event => event.key !== key);
  renderLog();
  if (key === 'motion') {
    latestOrientation = null; latestMotion = null; trace = [];
    $('#xr-phone').style.transform = '';
    readings('#xr-orientation', [['Rotation / alpha', '—'], ['Front/back tilt / beta', '—'], ['Left/right tilt / gamma', '—']]);
    $('#xr-orientation-note').textContent = 'No orientation readings held.';
    $('#xr-acceleration').textContent = 'Acceleration: no readings held.';
    $('#xr-gravity').textContent = 'Acceleration including gravity: no readings held.';
    $('#xr-graph-note').textContent = 'Recent acceleration magnitude in m/s²; waiting for readings.';
    for (const [id, text] of [['side', 'Turn your phone sideways'], ['tilt', 'Tilt at least 30° to the left'], ['shake', 'Gently shake your phone']]) $(`#challenge-${id}`).textContent = `○ ${text}`;
    draw($('#xr-seismograph'), [], false);
  } else if (key === 'location') {
    $('#location-has').textContent = 'No';
    readings('#xr-location', [['No coordinates held', '—']]);
    $('#xr-accuracy-label').textContent = 'Accuracy not yet reported.';
  } else if (key === 'camera' || key === 'screen') {
    const video = $(`#xr-${key}`);
    video.pause(); video.srcObject = null; video.hidden = true;
    $(`#${key}-placeholder`).hidden = false;
    if (key === 'camera') readings('#xr-camera-settings', []);
  } else if (key === 'microphone') {
    $('#xr-volume').value = 0;
    $('#xr-volume-label').textContent = 'Microphone is off.';
    draw($('#xr-waveform'), [], true);
  }
  status(key, state, explanation);
}

function errorMessage(error) {
  if (error?.name === 'NotAllowedError' || error?.name === 'SecurityError' || error?.code === 1) return ['Denied', 'Access was denied or blocked by browser/site settings. You can change those settings and try again.'];
  if (error?.name === 'NotFoundError') return ['Error', 'No compatible device or sharing source was found.'];
  if (error?.name === 'NotReadableError') return ['Error', 'The device may be in use, or your operating system may be blocking access.'];
  if (error?.name === 'InvalidStateError') return ['Error', 'Start this experiment with a tap or click while this tab is visible.'];
  if (error?.code === 3 || error?.name === 'TimeoutError') return ['Error', 'The request timed out. Stop or try again when your device is ready.'];
  return ['Error', 'This experiment could not start. Check device/browser settings, then try again.'];
}
function fail(key, version, error) {
  if (labs[key].version !== version) return;
  stop(key, ...errorMessage(error)); // Never expose or log exception payloads or device identifiers.
}
function current(key, version) { return labs[key].version === version && !document.hidden; }
function cleanup(key, callback) { labs[key].cleanups.push(callback); }

function display() {
  if (!scanned) return;
  const orientation = screen.orientation?.type || (innerWidth > innerHeight ? 'Landscape viewport (screen orientation not provided)' : 'Portrait viewport (screen orientation not provided)');
  readings('#xr-display', [['Viewport / CSS px', `${innerWidth} × ${innerHeight}`], ['Screen / CSS px', `${screen.width} × ${screen.height}`], ['Device pixel ratio', window.devicePixelRatio || 'Not provided'], ['Orientation', orientation], ['Touch points', navigator.maxTouchPoints ?? 'Not provided']]);
}
function glSupported(type) {
  const canvas = document.createElement('canvas');
  const context = canvas.getContext(type);
  if (!context) return false;
  context.getExtension('WEBGL_lose_context')?.loseContext();
  return true;
}
const capabilities = [
  ['Camera', () => support('camera'), 'Permission required', 'A camera preview uses getUserMedia. API presence does not prove that a camera is connected.'],
  ['Microphone', () => support('microphone'), 'Permission required', 'Audio input can feed a local Web Audio analyser. This demo never records or plays it back.'],
  ['Geolocation', () => support('location'), 'Permission required', 'The browser and operating system provide an estimated position and accuracy.'],
  ['Motion / accelerometer', () => 'DeviceMotionEvent' in window, 'Browser-dependent permission', 'Motion events may include acceleration. A present API may deliver no readings.'],
  ['Orientation', () => 'DeviceOrientationEvent' in window, 'Browser-dependent permission', 'Device rotation angles can drive a local illustration. These are not always compass bearings.'],
  ['Gyroscope API', () => 'Gyroscope' in window, 'Browser-dependent permission', 'The generic sensor API can expose angular velocity; some browsers instead provide rotationRate in motion events. Presence does not prove hardware.'],
  ['WebGL', () => glSupported('webgl'), 'No sensitive permission requested', 'Graphics rendering through a local GPU context. We do not inspect renderer identifiers or fingerprint your graphics output.'],
  ['WebGL2', () => glSupported('webgl2'), 'No sensitive permission requested', 'A newer graphics API; a temporary context is released after this check.'],
  ['WebGPU', () => 'gpu' in navigator, 'API presence only', 'High-performance graphics and computation, including some local AI models. We do not request an adapter or run a benchmark.'],
  ['WebAssembly', () => 'WebAssembly' in window, 'No sensitive permission requested', 'Runs compiled code inside the browser sandbox, useful for image processing and local computation.'],
  ['IndexedDB', () => 'indexedDB' in window, 'Presence only; no database opened', 'Structured browser storage. This page does not store readings in it.'],
  ['Cache Storage', () => 'caches' in window, 'Presence only; no cache opened', 'Can cache app resources or model files. This lab writes nothing to it.'],
  ['Service Workers', () => 'serviceWorker' in navigator, 'Presence only; none registered', 'Can support offline sites and intercept requests within their scope. This page registers none.'],
  ['Web Workers', () => 'Worker' in window, 'Presence only; none started', 'Run JavaScript work away from the interface thread. Workers are not inherently network services.'],
  ['File APIs', () => 'File' in window && 'FileReader' in window, 'User selection normally required', 'A file picker lets you choose specific files; it does not grant automatic access to all your files.'],
  ['Screen sharing', () => support('screen'), 'Explicit chooser required', 'The browser asks you to select a screen, window or tab on each sharing attempt.'],
  ['Bluetooth', () => 'bluetooth' in navigator, 'Device permission required; not requested', 'Some browsers can connect to selected nearby Bluetooth devices. No device scan is performed here.'],
  ['USB', () => 'usb' in navigator, 'Device permission required; not requested', 'WebUSB supports selected devices through a browser chooser.'],
  ['Serial', () => 'serial' in navigator, 'Device permission required; not requested', 'Can connect to serial hardware such as development boards after authorization.'],
  ['HID', () => 'hid' in navigator, 'Device permission required; not requested', 'Can communicate with selected human-interface devices; support and restrictions vary.'],
  ['MIDI', () => 'requestMIDIAccess' in navigator, 'Browser-dependent permission; not requested', 'Allows communication with supported musical instruments. We request no MIDI access.'],
  ['NFC', () => 'NDEFReader' in window, 'Permission required; not requested', 'Some mobile browsers can read certain nearby NFC tags after a user action.'],
  ['Web Share', () => 'share' in navigator, 'User action required; not invoked', 'Opens the operating system sharing interface. Availability depends on data and platform.'],
  ['Clipboard', () => 'clipboard' in navigator, 'Permission/user action may be required', 'Reading clipboard content is restricted. This page neither reads nor writes your clipboard.'],
];
function scan() {
  scanned = true;
  let timezone = 'Not provided';
  try { timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || timezone; } catch { /* Privacy-limited browser. */ }
  readings('#xr-browser', [['Browser', 'Browser identification limited'], ['Reported platform', navigator.platform || 'Not provided'], ['Language', navigator.language || 'Not provided'], ['Languages', navigator.languages?.join(', ') || 'Not provided'], ['Time zone', timezone], ['Online flag', navigator.onLine ? 'Online (reported)' : 'Offline (reported)'], ['Cookies enabled flag', navigator.cookieEnabled ? 'Yes (reported)' : 'No (reported)'], ['Touch input indicated', navigator.maxTouchPoints > 0 ? 'Yes' : 'Not reported']]);
  display();
  const fragment = document.createDocumentFragment();
  for (const [name, check, permission, explanation] of capabilities) {
    const card = document.createElement('details');
    const summary = document.createElement('summary');
    const label = document.createElement('span');
    const body = document.createElement('p');
    summary.textContent = name;
    label.textContent = safe(check) ? `SUPPORTED · ${permission}` : 'NOT SUPPORTED / unavailable in this context';
    body.textContent = explanation;
    summary.append(label); card.append(summary, body); fragment.append(card);
  }
  $('#xr-capabilities').replaceChildren(fragment);
  status('browser', 'Active'); status('display', 'Active');
  $('#xr-scan-status').textContent = 'Scan complete. No sensitive permissions were requested. Expand any capability below to learn more.';
}
$('#xr-scan').addEventListener('click', scan);
window.addEventListener('resize', () => {
  if (!scanned || scanFrame) return;
  scanFrame = requestAnimationFrame(() => { scanFrame = 0; display(); });
});

function draw(canvas, samples, waveform) {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  const width = canvas.width, height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = '#d2ddc7'; ctx.lineWidth = 1;
  for (let y = 30; y < height; y += 30) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke(); }
  if (!samples.length) return;
  ctx.strokeStyle = '#35572b'; ctx.lineWidth = 2; ctx.beginPath();
  samples.forEach((value, index) => {
    const y = waveform ? (value / 255) * height : height - 10 - Math.min(value / 25, 1) * (height - 20);
    const x = index / Math.max(1, samples.length - 1) * width;
    if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();
}
const xyz = value => value ? { x: value.x, y: value.y, z: value.z } : null;
const hasVector = value => value && [value.x, value.y, value.z].some(Number.isFinite);
const vectorText = value => `X ${number(value?.x)} · Y ${number(value?.y)} · Z ${number(value?.z)} m/s²`;

async function motion(version) {
  // Invoke both iOS permission methods in the click turn, before the first await.
  const types = [['deviceorientation', window.DeviceOrientationEvent], ['devicemotion', window.DeviceMotionEvent]];
  const permissions = await Promise.allSettled(types.map(([, Type]) => {
    if (!Type) return 'unsupported';
    return typeof Type.requestPermission === 'function' ? Type.requestPermission() : 'available';
  }));
  if (!current('motion', version)) return;
  const enabled = permissions.map(result => result.status === 'fulfilled' && ['granted', 'available'].includes(result.value));
  if (!enabled.some(Boolean)) {
    stop('motion', 'Denied', 'Motion/orientation access was denied or could not be requested. Check browser settings.');
    return;
  }
  let lastOrientation = 0, lastMotion = 0, lastRender = 0, lastLog = 0, frame = 0;
  let dirtyOrientation = false, dirtyMotion = false;
  const since = performance.now();
  const orientationListener = event => {
    if (![event.alpha, event.beta, event.gamma].some(Number.isFinite)) return;
    latestOrientation = { alpha: event.alpha, beta: event.beta, gamma: event.gamma };
    lastOrientation = performance.now(); dirtyOrientation = true;
  };
  const motionListener = event => {
    if (!hasVector(event.acceleration) && !hasVector(event.accelerationIncludingGravity)) return;
    latestMotion = { acceleration: xyz(event.acceleration), includingGravity: xyz(event.accelerationIncludingGravity) };
    lastMotion = performance.now(); dirtyMotion = true;
  };
  for (const [index, [name]] of types.entries()) {
    if (!enabled[index]) continue;
    const listener = index === 0 ? orientationListener : motionListener;
    window.addEventListener(name, listener);
    cleanup('motion', () => window.removeEventListener(name, listener));
  }
  status('motion', 'Granted', 'Listening for actual readings. Some browsers expose APIs but no sensor data.');
  if (!enabled[0]) $('#xr-orientation-note').textContent = 'Orientation unavailable or denied; motion may still work.';
  if (!enabled[1]) $('#xr-acceleration').textContent = 'Acceleration unavailable or denied; orientation may still work.';
  function render(now) {
    if (!current('motion', version)) return;
    if (now - lastRender >= (reducedMotion?.matches ? 200 : 50)) {
      lastRender = now;
      if (dirtyOrientation) {
        const { alpha, beta, gamma } = latestOrientation;
        readings('#xr-orientation', [['Rotation / alpha', number(alpha, 1, '°')], ['Front/back tilt / beta', number(beta, 1, '°')], ['Left/right tilt / gamma', number(gamma, 1, '°')]]);
        $('#xr-orientation-note').textContent = 'Live device-axis angles. The phone is a tilt illustration, not a compass.';
        const angle = screen.orientation?.angle || 0;
        $('#xr-phone').style.transform = reducedMotion?.matches ? '' : `rotateZ(${angle}deg) rotateX(${Number.isFinite(beta) ? beta : 0}deg) rotateY(${Number.isFinite(gamma) ? gamma : 0}deg) rotateZ(${Number.isFinite(alpha) ? -alpha : 0}deg)`;
        if (Math.abs(gamma) > 60 || Math.abs(angle) === 90) $('#challenge-side').textContent = '✓ Completed — turned sideways';
        if (gamma <= -30) $('#challenge-tilt').textContent = '✓ Completed — tilted left';
        dirtyOrientation = false;
      }
      if (dirtyMotion) {
        const { acceleration, includingGravity } = latestMotion;
        $('#xr-acceleration').textContent = `Excluding gravity: ${vectorText(acceleration)}`;
        $('#xr-gravity').textContent = `Including gravity: ${vectorText(includingGravity)}`;
        const vector = hasVector(acceleration) ? acceleration : includingGravity;
        const allAxes = [vector.x, vector.y, vector.z].every(Number.isFinite);
        if (allAxes) {
          const magnitude = Math.hypot(vector.x, vector.y, vector.z);
          trace.push(magnitude); if (trace.length > 160) trace.shift();
          draw($('#xr-seismograph'), trace, false);
          $('#xr-graph-note').textContent = `Trace: ${hasVector(acceleration) ? 'excluding' : 'including'} gravity. Display range 0–25 m/s² (larger values clipped); last 160 samples, not a calibrated time axis.`;
          if (hasVector(acceleration) && magnitude > 12) $('#challenge-shake').textContent = '✓ Completed — movement spike detected';
        }
        dirtyMotion = false;
      }
      if (now - Math.max(lastOrientation, lastMotion, since) > 7000) {
        stop('motion', 'Unavailable', 'No recent sensor data. Try this page on a phone; API presence does not guarantee readings.');
        return;
      }
      if ((lastOrientation || lastMotion) && states.motion !== 'Active') status('motion', 'Active', 'Receiving readings locally. Use Stop motion to clear them.');
      if (now - lastLog > 1000) {
        if (latestOrientation && now - lastOrientation < 1500) log('motion', 'deviceorientation', latestOrientation);
        if (latestMotion && now - lastMotion < 1500) log('motion', 'devicemotion', latestMotion);
        lastLog = now;
      }
    }
    frame = requestAnimationFrame(render);
  }
  frame = requestAnimationFrame(render);
  cleanup('motion', () => cancelAnimationFrame(frame));
}

function location(version) {
  // getCurrentPosition has no cancellation API; version guards discard late results.
  const timer = setTimeout(() => fail('location', version, { code: 3 }), 25000);
  cleanup('location', () => clearTimeout(timer));
  navigator.geolocation.getCurrentPosition(position => {
    if (!current('location', version)) return;
    clearTimeout(timer);
    const c = position.coords;
    const values = { latitude: c.latitude, longitude: c.longitude, accuracy: c.accuracy, altitude: c.altitude, heading: c.heading, speed: c.speed, timestamp: position.timestamp };
    readings('#xr-location', [['Latitude', number(c.latitude, 6)], ['Longitude', number(c.longitude, 6)], ['Accuracy', number(c.accuracy, 1, ' m')], ['Altitude', number(c.altitude, 1, ' m')], ['Heading', number(c.heading, 1, '°')], ['Speed', number(c.speed, 1, ' m/s')], ['Timestamp', new Date(position.timestamp).toLocaleString()]]);
    $('#xr-accuracy-label').textContent = `Reported accuracy: ± ${number(c.accuracy, 1)} meters.`;
    $('#location-has').textContent = 'Yes — one reading held locally';
    status('location', 'Granted', 'One reading received. No live tracking. Stop location clears it.');
    log('location', 'geolocation', values);
  }, error => fail('location', version, error), { enableHighAccuracy: false, timeout: 20000, maximumAge: 0 });
}

async function media(key, version) {
  // Unlock Web Audio in the gesture itself, including Safari. It starts with no input.
  let context = null, audioReady = null;
  if (key === 'microphone') {
    context = new AudioContextType();
    cleanup(key, () => { void context.close().catch(() => {}); });
    audioReady = context.resume().then(() => null, error => error);
  }
  // Call capture directly from Continue to preserve transient activation for screen sharing.
  const pending = key === 'screen'
    ? navigator.mediaDevices.getDisplayMedia({ video: true, audio: false })
    : navigator.mediaDevices.getUserMedia(key === 'camera'
      ? { video: { facingMode: { ideal: $('#xr-facing').value } }, audio: false }
      : { audio: true, video: false });
  const stream = await pending;
  if (!current(key, version)) { disposeStream(stream); return; }
  cleanup(key, () => disposeStream(stream));
  for (const track of stream.getTracks()) {
    const ended = () => { if (current(key, version)) stop(key, 'Stopped', 'The browser or device ended access. Local readings cleared.'); };
    track.addEventListener('ended', ended);
    cleanup(key, () => track.removeEventListener('ended', ended));
  }
  status(key, 'Granted', 'Access authorized. Starting local preview.');
  if (key === 'microphone') {
    const audioError = await audioReady;
    if (!current(key, version)) return;
    if (audioError) throw audioError;
    const source = context.createMediaStreamSource(stream);
    const analyser = context.createAnalyser();
    analyser.fftSize = 512;
    source.connect(analyser);
    cleanup(key, () => { source.disconnect(); analyser.disconnect(); });
    const samples = new Uint8Array(analyser.fftSize);
    let frame = 0, lastRender = 0;
    function render(now) {
      if (!current(key, version)) return;
      if (now - lastRender >= (reducedMotion?.matches ? 200 : 50)) {
        lastRender = now;
        analyser.getByteTimeDomainData(samples);
        const rms = Math.sqrt(samples.reduce((sum, value) => sum + ((value - 128) / 128) ** 2, 0) / samples.length);
        $('#xr-volume').value = rms;
        $('#xr-volume-label').textContent = `Relative amplitude: ${(rms * 100).toFixed(1)}%`;
        draw($('#xr-waveform'), Array.from(samples), true);
      }
      frame = requestAnimationFrame(render);
    }
    frame = requestAnimationFrame(render);
    cleanup(key, () => { cancelAnimationFrame(frame); samples.fill(0); });
  } else {
    const video = $(`#xr-${key}`);
    video.srcObject = stream; video.hidden = false;
    $(`#${key}-placeholder`).hidden = true;
    await video.play();
    if (!current(key, version)) return;
    if (key === 'camera') {
      // Whitelist educational settings; never retain deviceId, groupId, track ID or labels.
      const settings = stream.getVideoTracks()[0]?.getSettings?.() || {};
      const values = { width: settings.width, height: settings.height, frameRate: settings.frameRate, facingMode: settings.facingMode, aspectRatio: settings.aspectRatio };
      readings('#xr-camera-settings', [['Resolution', settings.width && settings.height ? `${settings.width} × ${settings.height}` : 'Not provided'], ['Frame rate', number(settings.frameRate, 1, ' fps')], ['Facing mode', settings.facingMode || 'Not provided'], ['Aspect ratio', number(settings.aspectRatio, 2)]]);
      log('camera', 'MediaStreamTrack settings (selected fields)', values);
    }
  }
  status(key, 'Active', 'Live, local only. Nothing is recorded or uploaded.');
}

function begin(key) {
  if (!support(key) || !window.isSecureContext || document.hidden || labs[key].busy) return;
  stop(key, 'Ready', 'Starting a fresh experiment.');
  const version = labs[key].version;
  controls(key, true);
  status(key, 'Requesting', 'Waiting for browser access. You can stop this request here; a browser prompt may remain open.');
  try {
    const task = key === 'motion' ? motion(version) : key === 'location' ? location(version) : media(key, version);
    Promise.resolve(task).catch(error => fail(key, version, error));
  } catch (error) { fail(key, version, error); }
}
for (const key of keys) {
  $(`[data-enable="${key}"]`).addEventListener('click', () => {
    $(`#${key}-boundary`).hidden = false;
    $(`[data-confirm="${key}"]`).focus();
  });
  $(`[data-confirm="${key}"]`).addEventListener('click', () => begin(key));
  $(`[data-cancel="${key}"]`).addEventListener('click', () => {
    $(`#${key}-boundary`).hidden = true;
    $(`[data-enable="${key}"]`).focus();
  });
  $(`[data-stop="${key}"]`).addEventListener('click', () => stop(key));
  controls(key, false);
  status(key, !window.isSecureContext ? 'Unavailable' : support(key) ? 'Ready' : 'Unsupported', !window.isSecureContext ? 'HTTPS is required.' : support(key) ? 'API available; no access requested by this page.' : 'This browser does not expose the required API.');
}
$('#location-support').textContent = support('location') ? 'Yes — permission required' : 'No';
$('#xr-insecure').hidden = window.isSecureContext;

function dataPath(server) {
  $('#xr-local-path').setAttribute('aria-pressed', String(!server));
  $('#xr-server-path').setAttribute('aria-pressed', String(server));
  $('#xr-path-label').textContent = server ? 'SIMULATION ONLY — no network request is made.' : 'LOCAL DEMONSTRATION — this page’s actual sensor data path.';
  $('#xr-path-note').textContent = server ? 'A different website could send authorized readings in an HTTPS request and store them. This diagram only explains that possibility; it sends nothing.' : 'Readings stay in temporary memory and the page’s display. Stop or reset clears them. No sensor data is uploaded.';
  const stages = server ? ['Device sensor', 'Browser', 'HTTPS request', 'Web server', 'Application / database'] : ['Device sensor', 'Operating system', 'Browser', 'JavaScript', 'Local memory'];
  $('#xr-data-path').replaceChildren(...stages.map(stage => { const item = document.createElement('li'); item.textContent = stage; return item; }));
}
$('#xr-local-path').addEventListener('click', () => dataPath(false));
$('#xr-server-path').addEventListener('click', () => dataPath(true));
function reset() {
  for (const key of keys) stop(key, support(key) && window.isSecureContext ? 'Stopped' : 'Unavailable', 'No active experiment or readings held.');
  scanned = false;
  cancelAnimationFrame(scanFrame); scanFrame = 0;
  status('browser', 'Not enabled'); status('display', 'Not enabled');
  readings('#xr-browser', [['Waiting for your scan', '—']]); readings('#xr-display', [['Waiting for your scan', '—']]);
  $('#xr-capabilities').textContent = 'Scan your browser to reveal its capabilities.';
  $('#xr-scan-status').textContent = 'Lab reset. No readings held. Browser permission decisions may remain saved.';
  events = []; renderLog(); dataPath(false);
}
$('#xr-reset').addEventListener('click', reset);
$('#xr-reset-bottom').addEventListener('click', reset);
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    for (const key of keys) stop(key, support(key) && window.isSecureContext ? 'Stopped' : 'Unavailable', 'Stopped because the page was hidden. Enable again to continue.');
    events = []; renderLog();
  }
});
window.addEventListener('pagehide', reset);
for (const id of ['#xr-scan', '#xr-reset', '#xr-reset-bottom']) $(id).disabled = false;
