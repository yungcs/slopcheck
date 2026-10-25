# Contributing

Issues and pull requests go to [yonguyungcs-pixel/slopcheck](https://github.com/yonguyungcs-pixel/slopcheck).

## Setup

```bash
pip install -e ".[dev]"
pytest
slopcheck .
```

`slopcheck .` has to score 100. The demo and the test fixtures are excluded on purpose. Scan them by passing the path: `slopcheck demo`.

Python 3.10 through 3.13. CI runs that matrix.

## A new rule

1. Add `SLP0xx` in `src/slopcheck/rules/`, and register it in `src/slopcheck/rules/__init__.py`.
2. Add `tests/fixtures/sloppy/SLP0xx_*.py` that the rule flags, and a case in `tests/test_rules.py` for something it must keep.
3. Put the id in both `README.md` and `README.zh-CN.md`.
4. Keep the tool's own tree clean. Do not silence a rule to hide a hit in `src/`.

Rule ids are stable. Do not renumber one that has shipped.

## Pictures

```bash
python scripts/render_assets.py    # SVG terminal, badge, HTML sample
python scripts/render_launch.py    # hero, GIF, report shot, before/after, social card
```

`render_launch.py` needs Pillow (installed with `.[dev]`) and ffmpeg. The GIF is built from a real `slopcheck demo` run (score 29) and a fixed tree tuned to score 94. Headless Chrome takes `docs/report.png`. If Chrome stays open after writing the PNG, the script stops it.

`docs/social-preview.png` is 1280×640 for the GitHub social preview setting. It is not embedded in the README.

## Releasing

Tag `vX.Y.Z` only when `src/slopcheck/version.py` has the same version. [`.github/workflows/release.yml`](.github/workflows/release.yml) publishes to PyPI with trusted publishing.

On PyPI, add this GitHub repo as a trusted publisher:

- Owner: `yonguyungcs-pixel`
- Repository: `slopcheck`
- Workflow: `release.yml`
- Environment: `pypi`

The GitHub environment named `pypi` needs the `id-token: write` permission the workflow already requests.
