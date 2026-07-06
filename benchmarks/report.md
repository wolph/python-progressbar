# Python progress-bar library benchmark

_Generated 2026-06-27 03:03. Subject: **progressbar2** (version 4.5.0)._

Compares `progressbar2` against the most common alternatives across three independent dimensions. All rendered output is written to a real pseudo-terminal (pty) that is continuously drained, so every library believes it is attached to a TTY and actually draws — the comparison is apples-to-apples, not "is output suppressed when piped".

![benchmark chart](chart.png)

## Environment

| | |
|---|---|
| Python | CPython 3.13.12 |
| Platform | macOS-26.5-arm64-arm-64bit-Mach-O |
| Processor | arm (18 cores) |
| Terminal | 80x24 (pty) |

| Library | Version |
|---|---|
| progressbar2 | 4.5.0 |
| tqdm | 4.68.3 |
| rich | 15.0.0 |
| alive-progress | 3.3.0 |
| click | 8.4.1 |

## A. Default iterator-wrap overhead (headline)

Idiomatic "wrap my loop" call with each library's **default** settings, over **1,000,000** iterations with a trivial body. This is the real-world cost of dropping a progress bar around a fast loop. Overhead = (wrapped time − bare-loop time) / iterations. Lower is faster.

Bare loop baseline: **5.47 ms** for 1,000,000 iterations.

| Library | Total time | Overhead/iter | vs progressbar2 |
|---|--:|--:|--:|
| **progressbar2** | 10.5 ms | 5.1 ns | baseline |
| rich | 24.5 ms | 19.0 ns | 3.76x |
| tqdm | 59.3 ms | 53.8 ns | 10.64x |
| alive-progress | 253.5 ms | 248.0 ns | 49.06x |
| click | 1861.4 ms | 1855.9 ns | 367.13x |

## B. Forced per-update render cost

Rendering **forced on every single update** over **30,000** updates — i.e. the cost of one full bar redraw, throttling disabled. Lower is faster.

| Library | Total time | Per rendered update | vs progressbar2 |
|---|--:|--:|--:|
| **progressbar2-fast** | 148.9 ms | 4.96 us | 0.19x |
| tqdm | 332.7 ms | 11.08 us | 0.44x |
| **progressbar2** | 764.6 ms | 25.48 us | baseline |
| rich | 5156.6 ms | 171.88 us | 6.75x |

Excluded from this panel (no per-update force-render API):
- **alive-progress** — renders on a background timer thread; no per-update render API
- **click** — self-throttles writes (renders only when the drawn line changes); no force-every-update API

## C. Cold import time

Wall-clock cost of importing the library in a fresh interpreter (minimum of 9 runs), with bare-interpreter startup (15 ms) subtracted. Matters for short-lived CLIs. Lower is lighter.

| Library | Import time (net) |
|---|--:|
| **progressbar2** | 1.5 ms |
| alive-progress | 8.5 ms |
| tqdm | 21.6 ms |
| click | 23.5 ms |
| rich | 46.9 ms |

## Takeaways

- **Default per-iteration overhead:** `progressbar2` is 5 ns/iter, ranking #1 of 5. `progressbar2` is the lightest per iteration (5 ns), `click` the heaviest (1856 ns).
  - `progressbar2` and `tqdm` win here because their default settings do almost no per-iteration work (counter compare / background refresh thread); `progressbar2` calls a monotonic clock and evaluates its redraw predicate on every `update()`.
- **Render cost:** when a redraw actually happens, `progressbar2` draws one update in 25.5 us — 5.14x the cheapest (`progressbar2-fast`) but 6.7x cheaper than rich's full-display re-render.
- **Why both numbers matter:** `progressbar2` caps redraws at ~20/sec by default (50 ms floor), so in practice the cheap render in B fires rarely and the per-iteration cost in A dominates real workloads.
- **Import weight:** `progressbar2` is mid-pack to import; `alive-progress` is the lightest, `rich` the heaviest.

## Methodology & caveats

- Timing: `time.perf_counter`, GC disabled during measurement, one untimed warmup per case, **minimum** of N repeats reported (A: 7, B: 5). Minimum is used to reduce scheduler/JIT noise.
- Output goes to a real pty sized 80x24, drained by a background thread so writes never block.
- "Overhead/iter" subtracts the bare-loop baseline, isolating the library's own cost.
- Default settings reflect out-of-the-box behaviour; tuning (`mininterval`, `poll_interval`, etc.) shifts these numbers. Results are specific to the environment above and will vary by machine.
- This measures CPU/throughput overhead only — not feature set, output quality, nesting, or multi-bar support.

Reproduce: `python benchmarks/bench.py && python benchmarks/report.py`
