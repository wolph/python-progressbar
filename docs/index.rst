============
progressbar2
============

.. only:: html and not epub

   .. raw:: html

      <section class="home-hero" aria-labelledby="home-title">
        <div class="home-hero-top">
          <div>
            <p class="home-eyebrow">Python progress bars</p>
            <h1 id="home-title">Your work.<br><span>In full colour.</span></h1>
            <p class="home-description">From a single loop to several jobs at once. Show progress, keep your logs readable, and choose the details that matter.</p>
          </div>
          <div class="home-install">
            <p class="home-install-label">Add progress to your next script.</p>
            <pre><code>pip install progressbar2</code></pre>
            <div class="home-actions">
              <a class="home-button primary" href="tutorial/index.html">Get started</a>
              <a class="home-button secondary" href="#showcase">Explore examples</a>
            </div>
            <p class="home-install-note">Already using tqdm? <a href="howto/tqdm-style.html">Find the migration guide.</a></p>
          </div>
        </div>
        <div class="home-showcase" id="showcase">
          <div class="home-terminal-title" id="showcase-title">Colours, gradients, and animated markers</div>
          <div id="showcase-panel" role="region" aria-label="Recorded progressbar2 output">
            <div class="home-recording-scroll" tabindex="0" aria-label="Recording, scroll horizontally to see the full terminal">
              <object id="showcase-recording" type="image/svg+xml" data="_static/demos/readme-colors.svg" aria-label="Recorded output: colours, gradients, and animated markers">
                <p>Recording unavailable. <a href="howto/colors.html">Read the colours guide and run the source locally.</a></p>
              </object>
            </div>
          </div>
          <div class="home-recording-controls" hidden>
            <div class="home-recording-tabs" role="tablist" aria-label="Choose a recorded demonstration">
              <button id="showcase-colours" type="button" role="tab" aria-selected="true" aria-controls="showcase-panel" tabindex="0" data-recording="_static/demos/readme-colors.svg" data-title="Colours, gradients, and animated markers" data-guide="howto/colors.html">Colours and widgets</button>
              <button id="showcase-jobs" type="button" role="tab" aria-selected="false" aria-controls="showcase-panel" tabindex="-1" data-recording="_static/demos/readme-multibar.svg" data-title="Several jobs in one terminal" data-guide="howto/multibar.html">Multiple jobs</button>
              <button id="showcase-logging" type="button" role="tab" aria-selected="false" aria-controls="showcase-panel" tabindex="-1" data-recording="_static/demos/readme-hero.svg" data-title="Log messages above a running bar" data-guide="howto/redirect-stdout.html">Clean logging</button>
            </div>
            <button id="showcase-pause" type="button" disabled>Pause recording</button>
          </div>
        </div>
        <p class="home-caption">Recorded progressbar2 output. <a id="showcase-guide" href="howto/colors.html">Read the guide and run the source locally.</a> <span class="home-motion-note">Reduced motion: showing the final frame.</span></p>
      </section>
      <section class="home-use-cases" aria-labelledby="use-cases-title">
        <h2 id="use-cases-title">What are you working on?</h2>
        <div class="home-cards">
          <article class="home-card transfer">
            <h3>Downloads and files</h3>
            <p>Show transfer speed, data size, and the estimated time remaining.</p>
            <a href="howto/file-transfer.html">Track a transfer <span aria-hidden="true">&rarr;</span></a>
          </article>
          <article class="home-card jobs">
            <h3>Several jobs at once</h3>
            <p>Follow each task with its own bar, including <a href="howto/parallel-execution.html">batches running in parallel</a>.</p>
            <a href="howto/multibar.html">Show multiple bars <span aria-hidden="true">&rarr;</span></a>
          </article>
          <article class="home-card logs">
            <h3>Scripts with logs</h3>
            <p>Keep printed messages readable above the bar while your loop runs.</p>
            <a href="howto/redirect-stdout.html">Keep your output tidy <span aria-hidden="true">&rarr;</span></a>
          </article>
        </div>
      </section>
      <section class="home-learn" aria-labelledby="quickstart-title">
        <div class="home-learn-intro">
          <h2 id="quickstart-title">Start with one loop.</h2>
          <p>Wrap your iterable with <code>progressbar</code>. The bar updates as each item is processed.</p>
          <p>Then add the widgets you need: an ETA, a counter, a transfer speed, or your own value.</p>
          <a class="home-button secondary" href="tutorial/index.html">Follow the tutorial</a>
        </div>
        <div class="home-quickstart">
          <h3>Try a complete example</h3>
          <p class="home-code-note">Run this example in your browser. Python downloads when you press Run.</p>

   .. demo:: tutorial/step1

   .. raw:: html

          <noscript><p>JavaScript is needed to run examples here. Install progressbar2 and run this source locally.</p></noscript>
        </div>
      </section>
      <nav class="home-guide-links" aria-label="Documentation guides">
        <a href="tutorial/index.html"><strong>Tutorial</strong><span>Build your first progress bar</span></a>
        <a href="widgets/index.html"><strong>Widgets</strong><span>Choose what your bar shows</span></a>
        <a href="howto/index.html"><strong>How-to guides</strong><span>Solve a specific problem</span></a>
        <a href="reference/index.html"><strong>API reference</strong><span>Look up an argument or class</span></a>
      </nav>

.. only:: not html or epub

   Install progressbar2 with ``pip install progressbar2``. See
   :doc:`installation` for the available installation methods.

   Wrap an iterable to show its progress:

   .. demo:: tutorial/step1

   The :doc:`tutorial/index` builds from this loop to custom widgets.
   :doc:`howto/index` covers file transfers, several bars at once and printing
   while a bar runs. :doc:`widgets/index` describes what each widget shows.
   Use :doc:`reference/index` to look up arguments and classes.

   The HTML documentation includes recorded output and examples you can run
   in your browser. MultiBar examples use threads, so run their source locally.
   The source above is the complete first tutorial example.

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Documentation

   installation
   tutorial/index
   howto/index
   widgets/index
   reference/index
   explanation/index

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Project

   contributing
   history
   sponsor
