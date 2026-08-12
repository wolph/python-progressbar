================
Widget reference
================

One page per widget, each with a live animation and runnable source. Use the
table below to pick a widget by what it shows and whether it needs a known
``max_value`` -- the widgets marked "No" work fine for indeterminate-length
progress too.

.. list-table::
   :header-rows: 1
   :widths: 20 60 20

   * - Widget
     - Purpose
     - Needs known ``max_value``

   * - :doc:`AbsoluteETA <absolute-eta>`
     - Wall-clock time the run is expected to finish
     - Yes
   * - :doc:`AdaptiveETA <adaptive-eta>`
     - Time remaining estimated from the last few seconds, reacting to pace changes
     - Yes
   * - :doc:`AdaptiveTransferSpeed <adaptive-transfer-speed>`
     - Transfer speed averaged over a short recent window
     - No
   * - :doc:`AnimatedMarker <animated-marker>`
     - Spinner cycling through characters for indeterminate work
     - No
   * - :doc:`Bar <bar>`
     - Classic left-to-right fill bar for a known total
     - Yes
   * - :doc:`BouncingBar <bouncing-bar>`
     - Marker bouncing back and forth for indeterminate work
     - No
   * - :doc:`Counter <counter>`
     - Running count with no total to compare against
     - No
   * - :doc:`CurrentTime <current-time>`
     - Wall-clock date and time, updated live
     - No
   * - :doc:`DataSize <data-size>`
     - Single byte count scaled to a sensible unit, e.g. "12.5 MiB"
     - No
   * - :doc:`DynamicMessage <dynamic-message>`
     - Legacy alias for Variable
     - No
   * - :doc:`ETA <eta>`
     - Time remaining estimated from the whole-run average rate
     - Yes
   * - :doc:`FileTransferSpeed <file-transfer-speed>`
     - Transfer rate averaged over the whole run
     - No
   * - :doc:`FormatCustomText <format-custom-text>`
     - Arbitrary text rendered independent of the bar's own progress
     - No
   * - :doc:`FormatLabel <format-label>`
     - Arbitrary %-style format string over the bar's data snapshot
     - No
   * - :doc:`FormatLabelBar <format-label-bar>`
     - Formatted label centered inside a fill bar
     - Yes
   * - :doc:`GranularBar <granular-bar>`
     - Fill bar with sub-character resolution via block glyphs
     - Yes
   * - :doc:`JobStatusBar <job-status-bar>`
     - Marks each discrete job as succeeded or failed on the bar
     - No
   * - :doc:`MultiProgressBar <multi-progress-bar>`
     - Several sub-jobs' progress stacked into one bar's fill levels
     - No
   * - :doc:`MultiRangeBar <multi-range-bar>`
     - Several named categories shown as proportional segments of one bar
     - No
   * - :doc:`Percentage <percentage>`
     - Current progress as a plain N% readout
     - Yes
   * - :doc:`PercentageLabelBar <percentage-label-bar>`
     - Percentage centered inside a fill bar
     - Yes
   * - :doc:`Postfix <postfix>`
     - Live key=value mapping (or string) rendered after the bar
     - No
   * - :doc:`ReverseBar <reverse-bar>`
     - Fill bar whose marker grows right to left
     - Yes
   * - :doc:`RotatingMarker <rotating-marker>`
     - Legacy alias for AnimatedMarker
     - No
   * - :doc:`SimpleProgress <simple-progress>`
     - Raw count against its total, e.g. "5 of 47"
     - Yes
   * - :doc:`SmoothingETA <smoothing-eta>`
     - Time remaining via an exponential-moving-average rate, the library default
     - Yes
   * - :doc:`Timer <timer>`
     - Elapsed time since the bar started, no max_value required
     - No
   * - :doc:`UnitProgress <unit-progress>`
     - Count against its total with a unit label, e.g. "12 of 24 files"
     - Yes
   * - :doc:`Variable <variable>`
     - Live, named value with custom formatting, e.g. a training loss
     - No

.. toctree::
   :maxdepth: 1

   absolute-eta
   adaptive-eta
   adaptive-transfer-speed
   animated-marker
   bar
   bouncing-bar
   counter
   current-time
   data-size
   dynamic-message
   eta
   file-transfer-speed
   format-custom-text
   format-label
   format-label-bar
   granular-bar
   job-status-bar
   multi-progress-bar
   multi-range-bar
   percentage
   percentage-label-bar
   postfix
   reverse-bar
   rotating-marker
   simple-progress
   smoothing-eta
   timer
   unit-progress
   variable
