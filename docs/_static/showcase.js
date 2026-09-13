/* Recorded examples use the SVG animation clock, independent of Python. */
/** @returns {void} */
(() => {
  /** @type {HTMLElement | null} */
  const recording = document.getElementById('showcase-recording');
  /** @type {Element | null} */
  const controls = document.querySelector('.home-recording-controls');
  /** @type {HTMLElement | null} */
  const panel = document.getElementById('showcase-panel');
  /** @type {HTMLElement | null} */
  const title = document.getElementById('showcase-title');
  /** @type {HTMLElement | null} */
  const guide = document.getElementById('showcase-guide');
  /** @type {HTMLElement | null} */
  const pause = document.getElementById('showcase-pause');
  if (!(recording instanceof HTMLObjectElement)
      || !(controls instanceof HTMLElement)
      || !(guide instanceof HTMLAnchorElement)
      || !(pause instanceof HTMLButtonElement) || !panel || !title) return;

  /** @type {HTMLButtonElement[]} */
  const tabs = Array.from(controls.querySelectorAll('button[role="tab"]'))
    .filter(/** @param {Element} tab */ (tab) => tab instanceof HTMLButtonElement);
  if (!tabs.length) return;
  /** @type {MediaQueryList} */
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  /** @type {boolean} */
  let paused = false;

  /** @returns {SVGSVGElement | null} */
  function svgRoot() {
    try {
      /** @type {SVGSVGElement | null} */
      const root = recording.contentDocument?.querySelector('svg') || null;
      return typeof root?.pauseAnimations === 'function' ? root : null;
    } catch {
      return null;
    }
  }

  /** @returns {void} */
  function updatePlayback() {
    /** @type {SVGSVGElement | null} */
    const root = svgRoot();
    pause.disabled = !root || reducedMotion.matches;
    pause.textContent = reducedMotion.matches
      ? 'Reduced motion'
      : paused ? 'Resume recording' : 'Pause recording';
    if (!root) return;
    /** @type {DOMRect} */
    const bounds = root.viewBox.baseVal;
    recording.style.aspectRatio = `${bounds.width} / ${bounds.height}`;
    if (paused || reducedMotion.matches) root.pauseAnimations();
    else root.unpauseAnimations();
  }

  /** @param {HTMLButtonElement} tab @returns {void} */
  function selectTab(tab) {
    /** @type {string | undefined} */
    const source = tab.dataset.recording;
    /** @type {string | undefined} */
    const heading = tab.dataset.title;
    /** @type {string | undefined} */
    const href = tab.dataset.guide;
    if (!source || !heading || !href) return;
    for (/** @type {HTMLButtonElement} */ const item of tabs) {
      /** @type {boolean} */
      const selected = item === tab;
      item.setAttribute('aria-selected', String(selected));
      item.tabIndex = selected ? 0 : -1;
    }
    panel.setAttribute('aria-labelledby', tab.id);
    title.textContent = heading;
    guide.href = href;
    recording.setAttribute('aria-label', `Recorded output: ${heading}`);
    /** @type {HTMLAnchorElement | null} */
    const fallback = recording.querySelector('a');
    if (fallback) fallback.href = href;
    if (recording.getAttribute('data') !== source) {
      pause.disabled = true;
      recording.data = source;
    }
  }

  /** @param {KeyboardEvent} event @param {number} index @returns {void} */
  function navigateTabs(event, index) {
    /** @type {Record<string, number>} */
    const destinations = {
      ArrowRight: (index + 1) % tabs.length,
      ArrowLeft: (index + tabs.length - 1) % tabs.length,
      Home: 0,
      End: tabs.length - 1,
    };
    if (!(event.key in destinations)) return;
    event.preventDefault();
    /** @type {HTMLButtonElement} */
    const tab = tabs[destinations[event.key]];
    tab.focus();
    selectTab(tab);
  }

  /** @param {HTMLButtonElement} tab @param {number} index @returns {void} */
  function attachTab(tab, index) {
    tab.addEventListener('click', /** @returns {void} */ () => selectTab(tab));
    tab.addEventListener('keydown',
      /** @param {KeyboardEvent} event @returns {void} */
      (event) => navigateTabs(event, index));
  }

  tabs.forEach(attachTab);
  pause.addEventListener('click', /** @returns {void} */ () => {
    paused = !paused;
    updatePlayback();
  });
  recording.addEventListener('load', updatePlayback);
  recording.addEventListener('error', /** @returns {void} */ () => {
    pause.disabled = true;
  });
  reducedMotion.addEventListener('change', updatePlayback);
  panel.setAttribute('role', 'tabpanel');
  panel.setAttribute('aria-labelledby', tabs[0].id);
  controls.hidden = false;
  updatePlayback();
})();
