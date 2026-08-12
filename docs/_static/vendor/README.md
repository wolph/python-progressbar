# Vendored assets

| File | Source | Version | License |
| --- | --- | --- | --- |
| `xterm.js`, `xterm.css` | `@xterm/xterm` | 5.5.0 | MIT (`LICENSE-xterm.txt`) |

Update (bump the version in both commands and this table):

```bash
npm pack @xterm/xterm@5.5.0
tar -xzf xterm-xterm-5.5.0.tgz
cp package/lib/xterm.js docs/_static/vendor/xterm.js
cp package/css/xterm.css docs/_static/vendor/xterm.css
cp package/LICENSE docs/_static/vendor/LICENSE-xterm.txt
rm -rf package xterm-xterm-5.5.0.tgz
```
