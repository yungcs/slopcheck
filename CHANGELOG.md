# Changelog

## 0.1.1 — 2026-10-26

- `slopcheck demo` is a real command: it scans packaged sample files, so it works from an empty directory after `pip install slopcheck-lint` or `uvx --from slopcheck-lint slopcheck demo`. Scan a local folder named `demo` with `slopcheck ./demo` or `slopcheck scan demo`.

## 0.1.0 — 2026-10-26

First release.

- Published on PyPI as `slopcheck-lint`, because `slopcheck` on PyPI belongs to another project. The CLI command and the import package are `slopcheck`: `pip install slopcheck-lint`, then run `slopcheck`.
- Fifteen rules, `SLP001` through `SLP015`, and a Slop Score from 0 to 100.
- Terminal, JSON, SARIF, HTML, SVG badge, and an agent fix prompt.
- Config in `[tool.slopcheck]`, inline `# slopcheck: ignore`.
- pre-commit hook, GitHub Action, and a skill for Claude Code, Codex, and Cursor.
- Python 3.10 through 3.13.
