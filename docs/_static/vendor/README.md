# Vendored assets

| File | Source | Version | License |
| --- | --- | --- | --- |
| `xterm.js`, `xterm.css` | `@xterm/xterm` | 5.5.0 | MIT (`LICENSE-xterm.txt`) |
| `addon-fit.js`, `addon-fit.js.map` | `@xterm/addon-fit` | 0.10.0 | MIT (`LICENSE-addon-fit.txt`) |

Update (bump the version in both commands and this table):

```bash
npm pack @xterm/xterm@5.5.0
tar -xzf xterm-xterm-5.5.0.tgz
cp package/lib/xterm.js docs/_static/vendor/xterm.js
cp package/css/xterm.css docs/_static/vendor/xterm.css
cp package/LICENSE docs/_static/vendor/LICENSE-xterm.txt
rm -rf package xterm-xterm-5.5.0.tgz
```

Update the matching terminal sizing addon:

```bash
npm pack @xterm/addon-fit@0.10.0
tar -xzf xterm-addon-fit-0.10.0.tgz
cp package/lib/addon-fit.js package/lib/addon-fit.js.map docs/_static/vendor/
cp package/LICENSE docs/_static/vendor/LICENSE-addon-fit.txt
rm -rf package xterm-addon-fit-0.10.0.tgz
```
