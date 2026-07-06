# Major-version backlog

Breaking changes that the quality audit identified as worth making but that
are **intentionally deferred** to the next major version, because fixing them
now would change the public API or long-standing rendered/CLI behaviour that
users may depend on. Each item is kept working as-is in the current release
line; this document records *why* it is deferred and *where* the code lives so
the change is easy to pick up later.

Nothing here is a bug that affects correctness of the documented API today —
those were fixed in the audit PRs. These are design debts whose fix is a
compatibility break.

## MultiBar composes over `dict` instead of subclassing it

`MultiBar` subclasses `dict` (`progressbar/multi.py`,
`class MultiBar(dict[str, bar.ProgressBar])`). The subclassing leaks several
surprising behaviours: an auto-vivifying `__getitem__` that creates a bar on
missing-key access, state that is dual-keyed by both label and bar object, and
`print` redirection installed by monkeypatching (`bar.print` / `self.print`).
Composition over inheritance (holding a private mapping and exposing an
explicit, documented interface) would remove the auto-vivification foot-gun and
clarify the threading/rendering API, but it changes the type's identity and the
mapping methods callers can use, so it must wait for a major version.

## `FormatLabelBar.__call__` diamond dispatch and incompatible override

`FormatLabelBar` (`progressbar/widgets.py`) manually dispatches to both parents
via `FormatLabel.__call__(self, ...)` and `Bar.__call__(self, ...)`, and its
`__call__` override carries a `# type: ignore` because its signature is not
compatible with the base `WidgetBase.__call__` contract. A CodeQL alert on the
incompatible override was dismissed as by-design: the diamond is deliberate and
the widths line up at runtime. Making the signatures genuinely compatible (or
folding the composition into a cooperative call chain) is a public-signature
change, so it is deferred.

## CLI no-op `pv`-compatibility flags

`progressbar/__main__.py` declares a `pv(1)`-compatible flag set, but only a
few (`--buffer-size`, `--eta`, `--input`/positional, `--line-mode`, `--size`)
actually feed the runtime. The rest — `--timer`, `--rate`, `--numeric`,
`--delay-start`, `--interval`, `--height`, `--width`, and friends — are parsed
and then silently ignored. They exist so `pv`-style command lines do not error
out. The next major version should either wire each flag to real behaviour or
reject unsupported flags explicitly; both are user-visible CLI changes, so they
are deferred.

## `__next__` / `next` manual-iteration path

`ProgressBar.__next__` (`progressbar/bar.py`) advances the bar on manual
iteration but bypasses the fast redraw gate that `update()` goes through, so
hand-rolled `next(bar)` loops render on a different schedule than the normal
paths. `next = __next__` (same file) is a Python-2-era alias kept so old code
calling `bar.next()` keeps working. Routing `__next__` through the gate and
dropping the `next` alias are behaviour/API changes, so they are deferred.

## `ColorBase` and `WindowsColor` no-op public classes

`ColorBase` (`progressbar/terminal/base.py`) is an abstract base that its own
docstring describes as deprecated (it only exists because `typing.NamedTuple`
cannot be used as a base for the real `Color`). `WindowsColor` (same file) is
effectively a no-op that duplicates `DummyColor`: recent Windows terminals
support ANSI, so it passes text through unstyled. Both are importable public
names, so removing them is a compatibility break for the next major version.

## Unused `Colors` lookup indexes

`Colors.register` (`progressbar/terminal/base.py`) populates four reverse
indexes on every registration — `by_name`, `by_lowername`, `by_hex`, and
`by_hls` — but nothing in the tree ever reads them. For the 256-colour table
that is 256×4 list appends plus the backing dicts at import time, for lookups
no code performs. Dropping the unused indexes would cut import work and memory,
but they are public class attributes, so their removal is deferred.

## 16-colour terminals receive the `38;5;N` SGR form

For a detected 16-colour terminal (`env.ColorSupport.XTERM`), `Color.ansi`
(`progressbar/terminal/base.py`) still emits the indexed `38;5;N` / `48;5;N`
256-colour SGR form (with `N` derived from the 16-colour palette) rather than
the canonical `30`–`37` / `90`–`97` direct codes. This is a pre-existing
convention that real terminals tolerate; switching to the direct codes changes
the exact bytes emitted for every colour on those terminals, so it is deferred.

## Deferred `DeprecationWarning` upgrades (silent-compat policy)

Several backwards-compatibility shims currently accept legacy usage silently
rather than warning:

- `apply_colors(**kwargs)` (`progressbar/terminal/base.py`) swallows unknown
  keyword arguments instead of rejecting them.
- Legacy aliases such as `RotatingMarker` (for `AnimatedMarker`) and
  `DynamicMessage` (for `Variable`) in `progressbar/widgets.py`.
- The `%s` → `%(elapsed)s` / `%(eta)s` format shims in `Timer` / `ETA`
  (`progressbar/widgets.py`).

Emitting `DeprecationWarning` from these paths is the right long-term move, but
warnings are observable behaviour (and can break `-W error` test suites), so
the upgrade is a coordinated major-version change.

## `deltas_to_seconds` sentinel/`ValueError` contract

`deltas_to_seconds` (`progressbar/utils.py`) is now expressed as typed
overloads, but its runtime contract around the not-a-number / default sentinel
still leans on raising `ValueError` for a class of inputs. A cleaner redesign
(an explicit sentinel type or an `Optional`-returning overload set) would be a
signature/behaviour change for callers that catch `ValueError`, so it is
deferred to the API redesign in the next major version.
