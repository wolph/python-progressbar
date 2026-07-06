# Developer tools

Maintenance scripts that are not shipped as part of the package.

## `generate_colors.py`

Regenerates the 256-colour table in `progressbar/terminal/colors.py`,
deriving every `HSL` value from its `RGB` via `HSL.from_rgb` (the RGB, xterm
index, colour name and Python binding name are authoritative and left
untouched). Run it in place:

```console
python tools/generate_colors.py progressbar/terminal/colors.py
```

It is idempotent; `--check` verifies the committed file is up to date
without writing.
