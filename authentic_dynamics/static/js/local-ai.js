const MODEL = 'SmolLM2-360M-Instruct-q4f16_1-MLC';
const MAX_PROMPT_LENGTH = 4000;
const loadButton = document.querySelector('#ai-load');
const askButton = document.querySelector('#ai-ask');
const promptElement = document.querySelector('#ai-prompt');
const statusElement = document.querySelector('#ai-status');
const progressElement = document.querySelector('#ai-progress');
const outputElement = document.querySelector('#ai-output');
const countElement = document.querySelector('#ai-count');
let engine = null;
let busy = false;

function setStatus(message, isError = false) {
  statusElement.textContent = message;
  statusElement.classList.toggle('is-error', isError);
}

function updateProgress(report) {
  setStatus(`Downloading/loading model: ${report.text || 'Loading model…'}`);
  progressElement.hidden = false;
  if (Number.isFinite(report.progress)) {
    progressElement.value = Math.max(0, Math.min(1, report.progress));
  } else {
    progressElement.removeAttribute('value');
  }
}

function updateInput() {
  countElement.textContent = promptElement.value.length.toLocaleString('en-US');
  askButton.disabled = !engine || busy;
}

async function checkWebGPU() {
  if (!window.isSecureContext) return 'Local AI requires a secure HTTPS connection (or localhost for development).';
  if (!navigator.gpu) return 'WebGPU is unavailable in this browser. Try a current WebGPU-compatible browser/device.';
  const adapter = await navigator.gpu.requestAdapter();
  if (!adapter) return 'A compatible GPU could not be found on this device.';
  if (!adapter.features.has('shader-f16')) return 'This test model requires shader-f16, which your GPU/browser configuration does not support.';
  return null;
}

loadButton.addEventListener('click', async () => {
  if (busy || engine) return;
  busy = true;
  loadButton.disabled = true;
  setStatus('Checking browser compatibility…');
  try {
    const unsupported = await checkWebGPU();
    if (unsupported) {
      setStatus(`Unsupported browser/GPU: ${unsupported}`, true);
      return;
    }
    progressElement.hidden = false;
    progressElement.removeAttribute('value');
    setStatus('Downloading/loading model: loading WebLLM…');
    // Import only after explicit consent and compatibility checks; pin the runtime version.
    const webllm = await import('https://esm.run/@mlc-ai/web-llm@0.2.85');
    engine = await webllm.CreateMLCEngine(MODEL, {
      initProgressCallback: updateProgress,
      logLevel: 'SILENT',
    });
    progressElement.value = 1;
    promptElement.disabled = false;
    loadButton.textContent = 'Local AI loaded';
    setStatus('AI ready. Enter a short prompt.');
    promptElement.focus();
  } catch (error) {
    console.error('Local AI model loading failed:', error);
    progressElement.hidden = true;
    setStatus('Error: The local AI model could not be loaded. Please check your connection or try another supported browser.', true);
  } finally {
    busy = false;
    loadButton.disabled = Boolean(engine);
    updateInput();
  }
});

promptElement.addEventListener('input', updateInput);
askButton.addEventListener('click', async () => {
  if (!engine || busy) return;
  const userText = promptElement.value.trim();
  if (!userText || promptElement.value.length > MAX_PROMPT_LENGTH) {
    setStatus('Enter a prompt between 1 and 4,000 characters.', true);
    promptElement.focus();
    return;
  }
  busy = true;
  promptElement.disabled = true;
  updateInput();
  outputElement.textContent = '';
  outputElement.setAttribute('aria-busy', 'true');
  setStatus('Generating locally on your device…');
  try {
    // Messages go directly to the in-browser engine, never to a network endpoint.
    const chunks = await engine.chat.completions.create({
      messages: [
        { role: 'system', content: 'You are a concise helpful assistant. Give clear and accurate responses. If you do not know something, say so rather than inventing information.' },
        { role: 'user', content: userText },
      ],
      temperature: 0.4,
      max_tokens: 300,
      stream: true,
    });
    let response = '';
    for await (const chunk of chunks) {
      response += chunk.choices[0]?.delta?.content || '';
      outputElement.textContent = response;
    }
    if (!response) outputElement.textContent = 'No text returned. Try another short prompt.';
    setStatus('Finished. You can ask another question.');
  } catch (error) {
    // Runtime exceptions can contain input text: log only the error type, never its payload.
    console.error('Local AI generation failed; error type:', error instanceof Error ? error.constructor.name : 'Unknown');
    outputElement.textContent = 'Generation failed. Please try a shorter prompt. If the problem continues, reload this page and load the model again.';
    setStatus('Error: Could not generate a response.', true);
  } finally {
    busy = false;
    promptElement.disabled = false;
    outputElement.setAttribute('aria-busy', 'false');
    updateInput();
  }
});
