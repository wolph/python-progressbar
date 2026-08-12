// Runs example code in Pyodide, off the main thread.
//
// Being in a Worker is what makes the animation real: `time.sleep` blocks
// here without freezing the page, and each write is posted to the main
// thread as it happens, so frames arrive live rather than all at once.
// Verified in an actual browser Worker, served with no COOP/COEP headers
// (matching Read the Docs) -- see task-19-report.md for the evidence.
//
// THIS MUST BE CONSTRUCTED AS A MODULE WORKER:
//   new Worker(url, {type: 'module'})
// Empirically, `new Worker(url)` (classic) plus `importScripts(pyodide.js)`
// -- the brief's literal shape -- failed every time in real testing: the
// cross-origin importScripts() call threw "failed to load" while a plain
// fetch() of the *identical* URL from inside the same worker succeeded.
// Loading the ESM build (`pyodide.mjs`) via dynamic `import()` from a
// module worker works reliably and is Pyodide's own forward-recommended
// loading path. See task-19-report.md for the evidence and the classic-vs-
// module comparison.
const PYODIDE_VERSION = '314.0.3';
const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

let pyodide = null;

// A demo written with `with progressbar.MultiBar(...):` spawns a real OS
// thread (MultiBar.start() -> threading.Thread.start()), which Pyodide
// cannot provide in the browser -- confirmed by the Task 17 spike, which
// caught `RuntimeError: can't start new thread` before anything rendered.
// Task 20 suppresses the Run button for the two demos that use that form
// (readme/multibar, howto/multibar) so this should never fire in normal
// use; it exists as a defense-in-depth translation from a raw Python
// traceback to an honest, specific explanation, in case it is ever
// reached some other way.
const THREAD_ERROR_MARKER = "can't start new thread";
const THREAD_ERROR_MESSAGE =
  'This demo uses MultiBar’s `with` form, which starts a real OS ' +
  'thread. Browsers cannot provide that, so it cannot run here -- the ' +
  'animation above is the real output. See the source for the pattern.';

const BRIDGE = `
import os, sys, js, traceback
from pyodide.ffi import to_js


# A bare Python dict handed to a JS function crosses the ffi boundary as a
# PyProxy, not a plain JS object -- and postMessage's structured clone
# cannot clone a PyProxy. Empirically confirmed: 'js.postMessage({...})',
# the brief's literal code, raised
# "DataCloneError: ... could not be cloned" on the very first write and
# never delivered a single byte. to_js(..., dict_converter=js.Object.fromEntries)
# produces a real JS object (not a Map, which /would/ clone but would then
# read back on the JS side as .get('type') instead of .type, breaking the
# protocol every consumer of these messages relies on).
def _post(payload):
    js.postMessage(to_js(payload, dict_converter=js.Object.fromEntries))


class _TerminalBridge:
    encoding = 'utf-8'
    errors = 'replace'
    # Required for demos using redirect_stdout=True / redirect_stderr=True.
    # progressbar.utils.WrappingIO wraps whatever sys.stdout/sys.stderr was
    # at capture-start as its \`target\` and checks \`target.closed\`
    # unconditionally on every write and flush (utils.py:207, 214), with no
    # getattr/hasattr guard -- unlike every other target method, which it
    # only touches if something calls it. Confirmed empirically: without
    # this, readme/hero.py (a plain redirect_stdout demo, no threading, no
    # MultiBar) failed every run with
    # "AttributeError: '_TerminalBridge' object has no attribute 'closed'"
    # the moment its first bar.update() flushed. The bridge never closes
    # for the worker's lifetime, so this is always False.
    closed = False

    def write(self, text):
        _post({'type': 'output', 'text': text})
        return len(text)

    def flush(self):
        pass

    def isatty(self):
        return True

    def fileno(self):
        raise OSError('no file descriptor in the browser')


# ONE bridge instance for the worker's lifetime. Task 17 verified that
# ProgressBar's \`fd\` default and utils.streams' original_stdout/stderr are
# bound at IMPORT time, not looked up per call -- so a fresh bridge per run
# would leave progressbar writing into the previous run's dead object.
_BRIDGE = _TerminalBridge()

# In this Pyodide build (314.0.3), the JsException a failed run() throws on
# the JS side carries an EMPTY .message and a .stack full of wasm frames --
# confirmed empirically, including for a plain \`raise ValueError('x')\`. The
# only usable field left on the JS side is .type (the exception class
# name, e.g. 'ValueError'), with no text. The real 'type: message' pair
# still exists, just Python-side -- captured here via sys.excepthook
# (which was already firing, unpatched, printing the traceback through
# this same bridge every time a run raised) so run() can read it back
# after catching. Reset before every run so a stale value never survives
# past the run that set it.
_LAST_ERROR = None


def _excepthook(exc_type, exc_value, exc_tb):
    global _LAST_ERROR
    _LAST_ERROR = f'{exc_type.__name__}: {exc_value}'
    traceback.print_exception(exc_type, exc_value, exc_tb, file=sys.stderr)


def _install_bridge(columns):
    global _LAST_ERROR
    _LAST_ERROR = None
    os.environ['TERM'] = 'xterm-256color'
    os.environ['COLORTERM'] = 'truecolor'
    os.environ['COLUMNS'] = str(columns)
    os.environ['LINES'] = '24'
    sys.stdout = _BRIDGE
    sys.stderr = _BRIDGE
    sys.excepthook = _excepthook
`;

async function fetchJSON(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`failed to fetch ${url}: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function boot(wheelsUrl) {
  postMessage({type: 'status', stage: 'loading'});
  // Dynamic import (not a static top-level `import`) so the module
  // specifier can be built from PYODIDE_VERSION -- a static import
  // requires a string literal, which would force the version to be
  // duplicated and could silently drift out of sync with the constant
  // above. Dynamic import also lets a load failure surface as a normal
  // caught error -> {type: 'error'} message instead of an uncatchable
  // top-level worker failure.
  const {loadPyodide} = await import(`${PYODIDE_URL}pyodide.mjs`);
  pyodide = await loadPyodide({indexURL: PYODIDE_URL});

  postMessage({type: 'status', stage: 'installing'});
  // `wheelsUrl` is resolved against THIS SCRIPT's own location
  // (self.location, i.e. .../_static/livecode/worker.js), not the page
  // that sent the message -- that is how fetch() and every other URL
  // inside a Worker resolves relative strings, by spec, regardless of
  // which page created the worker. Verified empirically: passing the
  // page-relative string a caller would naturally compute (mirroring the
  // `.. demo::` directive's page-relative asset URLs, Task 10) resolved
  // to the wrong path from inside the worker and 404'd every time, even
  // though the same string is correct when used on the page itself.
  // Made explicit here, with the resolved absolute URL, so a wrong value
  // fails loudly with the URL it actually tried, not a bare 404.
  // Callers should pass either an absolute URL, or a path relative to
  // worker.js's own fixed location -- `../wheels/` from here, always,
  // since docs/_static/livecode/ and docs/_static/wheels/ are siblings.
  const resolvedWheelsUrl = new URL(wheelsUrl, self.location.href);
  const manifest = await fetchJSON(new URL('wheels.json', resolvedWheelsUrl));
  await pyodide.loadPackage('micropip');
  const micropip = pyodide.pyimport('micropip');
  await micropip.install(
    manifest.wheels.map((name) => new URL(name, resolvedWheelsUrl).href),
  );

  pyodide.runPython(BRIDGE);
  postMessage({type: 'status', stage: 'ready'});
}

async function run(code, columns) {
  if (pyodide === null) {
    postMessage({type: 'error', message: 'worker is not booted yet'});
    return;
  }
  pyodide.globals.get('_install_bridge')(columns);
  try {
    await pyodide.runPythonAsync(code);
    postMessage({type: 'done'});
  } catch (error) {
    // pyodide.globals.get('_LAST_ERROR') is `type: message`, set by the
    // BRIDGE's sys.excepthook -- see the comment there for why the JS
    // `error` object itself has nothing usable. Falls back to the JS
    // exception's own (bare) type name if the hook never ran, e.g. a
    // failure before Python code started executing at all.
    const lastError = pyodide.globals.get('_LAST_ERROR');
    const detail =
      typeof lastError === 'string' && lastError
        ? lastError
        : String((error && error.type) || error);
    const message = detail.includes(THREAD_ERROR_MARKER) ? THREAD_ERROR_MESSAGE : detail;
    postMessage({type: 'error', message});
  }
}

onmessage = async (event) => {
  const message = event.data;
  try {
    if (message.type === 'boot') {
      await boot(message.wheelsUrl);
    } else if (message.type === 'run') {
      await run(message.code, message.columns);
    }
  } catch (error) {
    postMessage({type: 'error', message: String(error.message || error)});
  }
};
