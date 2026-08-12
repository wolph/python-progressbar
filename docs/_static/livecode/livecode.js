// Upgrades every `.demo-run` placeholder into a Run button.
//
// One worker is shared by the whole page and booted lazily on the first
// click, so a reader who never runs anything never downloads Pyodide.

const COLUMNS = 80;
const RUN_TIMEOUT_MS = 30000;

// Read the Docs serves the site under `/en/<version>/`, so root-absolute
// asset paths 404 there. Derive the static root from this script's own
// URL instead: it is the one path the browser always knows.
const SCRIPT_ELEMENT =
  document.currentScript ||
  document.querySelector('script[src$="livecode/livecode.js"]');
const STATIC_ROOT = new URL('../', SCRIPT_ELEMENT.src).href;
const WORKER_URL = `${STATIC_ROOT}livecode/worker.js`;
const WHEELS_URL = `${STATIC_ROOT}wheels/`;

let worker = null;
let booting = null;
let activePanel = null;
let timeoutHandle = null;

function bootWorker() {
  if (booting) return booting;
  booting = new Promise((resolve, reject) => {
    // The worker uses one `error` shape for boot-phase and run-phase
    // failures alike, so track whether this instance ever reached `ready`.
    // Without it a boot failure (missing wheels, a 404 on wheels.json, a
    // micropip error) settles neither branch: the awaiting click hangs, and
    // the cached `booting` promise makes every later click hang too, stuck
    // on "Downloading Python...".
    let ready = false;

    // MUST be a module worker. Task 19 found that a classic worker's
    // importScripts() of the cross-origin pyodide.js fails in a real
    // browser; ESM dynamic import works. This was invisible to the Node
    // spike.
    worker = new Worker(WORKER_URL, {type: 'module'});
    worker.onmessage = (event) => {
      const message = event.data;
      if (message.type === 'status') {
        if (activePanel) activePanel.setStatus(message.stage);
        if (message.stage === 'ready') {
          ready = true;
          resolve();
        }
      } else if (message.type === 'output') {
        if (activePanel) activePanel.terminal.write(message.text);
      } else if (message.type === 'done') {
        finishRun();
      } else if (message.type === 'error') {
        if (!ready) {
          // Boot will never complete (bad wheels URL, a 404 on
          // wheels.json, a micropip failure, ...). Discard this worker
          // so the next click builds a fresh one and genuinely retries,
          // and reject so the awaiting click's `await bootWorker()`
          // doesn't hang forever -- the catch block below is the single
          // place that reports this to the reader, so it isn't printed
          // twice.
          resetWorker();
          reject(new Error(message.message));
          return;
        }
        if (activePanel) {
          activePanel.terminal.write(`\r\n\x1b[31m${message.message}\x1b[0m\r\n`);
        }
        finishRun();
      }
    };
    // Do not try to read `.message` here. For a *module* worker Chromium
    // delivers a plain `Event` (not an `ErrorEvent`) with no `.message`
    // property at all, so any stringification yields "[object Event]".
    // This fires when the worker script itself never runs -- a 404 on
    // worker.js, or a syntax error in it -- so say that instead.
    worker.onerror = () =>
      reject(new Error('the Python worker script failed to load'));
    worker.postMessage({type: 'boot', wheelsUrl: WHEELS_URL});
  });
  return booting;
}

function resetWorker() {
  if (worker) worker.terminate();
  worker = null;
  booting = null;
}

function finishRun() {
  clearTimeout(timeoutHandle);
  if (activePanel) activePanel.setStatus('idle');
}

function createPanel(container, source) {
  const editor = document.createElement('textarea');
  editor.className = 'demo-editor';
  editor.value = source;
  editor.rows = source.split('\n').length;
  editor.spellcheck = false;

  const button = document.createElement('button');
  button.className = 'demo-button';
  button.type = 'button';
  button.textContent = 'Run';

  const status = document.createElement('span');
  status.className = 'demo-status';

  const screen = document.createElement('div');
  screen.className = 'demo-terminal';

  const controls = document.createElement('div');
  controls.className = 'demo-controls';
  controls.append(button, status);
  container.append(controls, editor, screen);

  const terminal = new Terminal({
    cols: COLUMNS,
    rows: 12,
    convertEol: true,
    fontSize: 13,
    theme: {background: '#101418', foreground: '#d6e2ef'},
  });
  terminal.open(screen);

  const panel = {
    terminal,
    setStatus(stage) {
      const labels = {
        loading: 'Downloading Python...',
        installing: 'Installing progressbar2...',
        ready: 'Running...',
        idle: '',
      };
      status.textContent = labels[stage] ?? '';
      button.disabled = stage !== 'idle';
    },
  };

  button.addEventListener('click', async () => {
    activePanel = panel;
    panel.setStatus('loading');
    terminal.reset();
    try {
      await bootWorker();
    } catch (error) {
      // error.message (not `${error}`) so a rejection built from the
      // worker's own {type: 'error'} text reads as one clean sentence
      // instead of "Error: <message>"; also correct for the native
      // Worker onerror path, where `${error}` on an ErrorEvent would
      // print "[object ErrorEvent]" instead of the real reason.
      terminal.write(
        `\r\n\x1b[31mFailed to start Python: ${error.message || error}\x1b[0m\r\n`
        + '\x1b[33mClick Run again to retry.\x1b[0m\r\n',
      );
      resetWorker();
      panel.setStatus('idle');
      return;
    }
    panel.setStatus('ready');
    timeoutHandle = setTimeout(() => {
      terminal.write('\r\n\x1b[33mStopped after 30 seconds.\x1b[0m\r\n');
      resetWorker();
      panel.setStatus('idle');
    }, RUN_TIMEOUT_MS);
    worker.postMessage({
      type: 'run',
      code: editor.value,
      columns: COLUMNS,
    });
  });

  panel.setStatus('idle');
  return panel;
}

// Two demos cannot run under Pyodide at all: MultiBar starts a background
// thread and `Thread.start()` raises `RuntimeError: can't start new thread`
// there, rendering nothing first. The worker returns a friendly message
// rather than a traceback, but the Run button should not be offered in the
// first place -- the message is defence in depth, not the control.
const NON_RUNNABLE_DEMOS = new Set(['readme/multibar', 'howto/multibar']);

document.addEventListener('DOMContentLoaded', () => {
  if (typeof Terminal === 'undefined') return;
  for (const container of document.querySelectorAll('.demo-run')) {
    if (NON_RUNNABLE_DEMOS.has(container.dataset.demo)) {
      container.textContent =
        'This example uses MultiBar, which needs a background thread. '
        + 'Python in the browser cannot start one, so run it locally.';
      container.classList.add('demo-run-unavailable');
      continue;
    }
    fetch(container.dataset.source)
      .then((response) => response.text())
      .then((source) => createPanel(container, source))
      .catch(() => {
        container.textContent = 'Live console unavailable.';
      });
  }
});
