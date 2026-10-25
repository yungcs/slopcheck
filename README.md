# slopcheck

A linter for the mess AI coding agents leave in Python.

[中文说明](README.zh-CN.md)

[![slop score](docs/slop-score.svg)](docs/slop-score.svg)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB)
![MIT](https://img.shields.io/badge/license-MIT-blue)

One command scans a Python tree, flags agent slop, and prints a **Slop Score** from 0 to 100. Higher is cleaner. The same findings can be handed to Claude Code, Codex, or Cursor as a fix prompt.

```bash
uvx slopcheck .
```

From a checkout of this repo:

```bash
pip install -e ".[dev]"
slopcheck .
```

`pipx install slopcheck` works the same way once the package is published. Python 3.10 or newer.

## Demo

`demo/taskflow` is a small task client written the way an agent writes it on a Friday: a bare `except`, a hallucinated `requets` import, a `_v2` twin of a function that already exists, and a `breakpoint()` left in the fetch path. `demo/taskflow/ok.py` is the control. Scanned on its own, it scores 100.

![slopcheck demo](docs/demo.svg)

```text
$ slopcheck demo
slopcheck  0.1.0
scanned 5 files · 191 lines · 20 findings
score   29 / 100  ███░░░░░░░  sloppy

demo/taskflow/client.py
  11:5  SLP001  error    bare except swallows errors, including KeyboardInterrupt and SystemExit
            except:
                pass
  18:5  SLP002  error    broad except swallows the error
            except Exception:
                return None
  26:9  SLP003  error    except handler returns dummy value {}
                return {}
  33:9  SLP015  warning  except handler returns an error payload instead of raising
                return "Error: failed to fetch title"
  37:5  SLP005  warning  leftover debug print
            print("DEBUG reached task fetch")
  38:5  SLP005  warning  leftover debug f-string
            print(f"{tasks=}")
  39:5  SLP005  warning  leftover breakpoint or set_trace()
            breakpoint()
  46:13  SLP011  warning  try/except nested to depth 3 (limit 2)
                    try:
                        return url.strip()

demo/taskflow/imports_hallucinated.py
  3:8  SLP010  error    import `requets` does not resolve
        import requets
  4:1  SLP010  error    import `jason` does not resolve
        from jason import loads
  5:25  SLP010  error    `defaultdictx` is not an attribute of `collections`
        from collections import defaultdictx

demo/taskflow/utils.py
  7:5  SLP004  note     narrating comment restates the code
            # increment index
            index += 1
  12:1  SLP004  note     narrating comment restates the code
        # This function returns the count
        def task_count(tasks):
  13:1  SLP012  note     docstring is 11 lines on a 1-statement function
        def task_count(tasks):
            """Return the number of tasks.
  28:1  SLP006  warning  private function `_format_legacy_banner` is never used
        def _format_legacy_banner(text):
            return "*** " + text + " ***"
  34:5  SLP008  note     over-defensive check: `name` is a non-None literal here
            if name is not None:
                return name.upper()
  39:1  SLP009  warning  function body is only pass
        def export_tasks(tasks, path):
            """Write tasks somewhere eventually."""
  45:5  SLP014  note     commented-out code (2 lines)
            # status = "archived"
            # owner = "ada"
  70:1  SLP007  warning  duplicate of `summarize_tasks` (100% similar)
        def summarize_tasks_v2(tasks, limit):
            rows = []
  70:1  SLP013  warning  `summarize_tasks_v2` looks like a leftover versioned name
        def summarize_tasks_v2(tasks, limit):
            rows = []

SLP001 1  SLP002 1  SLP003 1  SLP004 2  SLP005 3  SLP006 1  SLP007 1  SLP008 1  SLP009 1  SLP010 3  SLP011 1  SLP012 1  SLP013 1  SLP014 1  SLP015 1
20 findings · score 29 · fail
```

The same run as a self-contained page: [docs/demo-report.html](docs/demo-report.html). Open it in a browser. Filters are in the file; nothing is loaded from the network.

Regenerate the picture, the transcript, the badge, and the HTML sample with:

```bash
python scripts/render_assets.py
```

## Rules

| ID | Severity | Name | What it catches |
| --- | --- | --- | --- |
| SLP001 | error | bare-except | Bare `except:` swallows KeyboardInterrupt and SystemExit |
| SLP002 | error | broad-except-swallow | `except Exception` whose body only passes, continues, or returns None/False |
| SLP003 | error | fake-fallback | `except` returns `{}`, `[]`, `""`, `0`, `"ok"`, `"todo"`, and similar stand-ins |
| SLP004 | note | narrating-comment | `# increment i`, `# This function returns the count` |
| SLP005 | warning | debug-leftover | Debug `print`, `f"{var=}"`, `breakpoint()`, `pdb.set_trace()` |
| SLP006 | warning | unused-private | `_helper` that nothing in the file calls |
| SLP007 | warning | near-duplicate | A second function with almost the same structure |
| SLP008 | note | over-defensive | `None` or `isinstance` check that cannot fail |
| SLP009 | warning | placeholder-stub | Body is only `pass`, `...`, `NotImplementedError`, or a TODO return |
| SLP010 | error | hallucinated-import | Module or stdlib attribute that does not resolve |
| SLP011 | warning | try-nesting | `try` nested deeper than 2 inside one function |
| SLP012 | note | verbose-docstring | A long docstring on a one or two statement function |
| SLP013 | warning | versioned-name | `*_v2`, `*_fixed`, `*_copy`, and a sibling `*_new` |
| SLP014 | note | commented-out-code | Comments that are really code |
| SLP015 | warning | error-string-return | `except` returns `"Error: ..."` or `{"success": false}` |

`slopcheck rules` prints the live list, including the hint each finding carries.

Left alone on purpose:

- A comment that says why (`# Retry once: the upstream closes idle sockets`).
- `print(f"tasks={tasks}")`. The self-documenting form `f"{tasks=}"` is the one that gets flagged.
- An import inside `try/except ImportError`.
- Abstract methods, `Protocol` bodies, and `.pyi` stubs.
- `return False` from `__exit__` / `__aexit__`.
- A function named `brand_new` when no `brand` function sits beside it.

Silence one line, or a whole file:

```python
result = load()  # slopcheck: ignore[SLP003]
```

```python
# slopcheck: disable
# slopcheck: enable=SLP001
```

`# slopcheck: ignore` with no ids silences every rule on that line. A comment-only line applies to the next non-blank line.

## Score

An error weighs 8, a warning weighs 4, a note weighs 2.

```text
budget = lines / 5
raw    = sum of weights
score  = round(100 * budget / (budget + raw))
```

No findings is 100, whatever the line count. A 200-line project with five errors (raw 40) scores 50.

| Score | Label |
| --- | --- |
| 90–100 | clean |
| 75–89 | light residue |
| 50–74 | needs a wash |
| 25–49 | sloppy |
| 0–24 | hazardous sludge |

Exit status:

| Code | When |
| --- | --- |
| 0 | No errors, no warnings, and the score is at least `--min-score` |
| 1 | An error, a warning, a parse error, or a score under the minimum |
| 2 | Bad arguments or a broken config file |

Notes alone do not fail the process. They do lower the score, so a `min-score` of 100 fails on a note. `--exit-zero` always exits 0 after the report is written.

## Config

`slopcheck` reads `[tool.slopcheck]` from the nearest `pyproject.toml`. Hyphens and underscores are the same key. Unknown keys are warned about and ignored. `--no-config` skips the file. `--config other.toml` loads that file instead.

```toml
[tool.slopcheck]
exclude = ["demo/**", "tests/fixtures/**"]
ignore = ["SLP004"]
min-score = 90

[tool.slopcheck.severity]
SLP008 = "warning"

[tool.slopcheck.per-file-ignores]
"tests/**" = ["SLP009"]

[tool.slopcheck.rules.SLP007]
min_lines = 12
min_tokens = 25
threshold = 0.92

[tool.slopcheck.rules.SLP010]
allowed_modules = ["pytest"]

[tool.slopcheck.rules.SLP011]
max_depth = 2

[tool.slopcheck.rules.SLP012]
min_doc_lines = 8
max_body_statements = 2
```

`--select` replaces the config selection. `--ignore` is added on top of it. This repo excludes `demo/**` and `tests/fixtures/**` and sets `min-score = 100`, so `slopcheck .` fails on any finding. Passing those paths on the command line opts them back in: `slopcheck demo` scans the demo.

## Output

| Format | Command |
| --- | --- |
| Terminal | `slopcheck .` |
| JSON | `slopcheck . --format json` |
| SARIF 2.1.0 | `slopcheck . --format sarif -o slopcheck.sarif` |
| HTML | `slopcheck . --format html -o report.html` |
| SVG badge | `slopcheck badge . -o slop-score.svg` |
| Fix prompt | `slopcheck prompt .` |

`--quiet` prints one line per finding plus the score. `--verbose` adds the hint. `--no-color` and `--no-snippet` are there for logs.

JSON includes the score, the weights, every finding, parse errors, and counts by rule. SARIF uses relative URIs with `uriBaseId` `%SRCROOT%` and lists all 15 rules on the driver. The HTML report is one file: inline CSS, a filter row, and the findings. The badge uses inline fills, so it renders in a GitHub README.

## Hand the findings to an agent

```bash
slopcheck prompt demo > fix.md
slopcheck src/app.py --fix-with-agent
```

The prompt tells the agent to preserve behavior, to raise instead of returning a dummy, and to run slopcheck again. Pasting it into Claude Code, Codex, or Cursor is enough. The skill at [`skills/slopcheck/SKILL.md`](skills/slopcheck/SKILL.md) says the same thing and tells the agent not to silence rules to inflate the score. The same file is linked from `.claude/skills`, `.cursor/skills`, and `.agents/skills`.

```python
from slopcheck import scan

report = scan(["src"])
print(report.score, report.label)
```

## Integrations

**pre-commit.** [`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml) runs slopcheck on staged Python files. Wire it up from [`examples/pre-commit-config.yaml`](examples/pre-commit-config.yaml). Replace `OWNER` with the repo that actually hosts the package.

**GitHub Actions.** [`action.yml`](action.yml) installs slopcheck, writes SARIF, and uploads it to code scanning. [`examples/workflows/slopcheck.yml`](examples/workflows/slopcheck.yml) calls that action. [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs the tests and `slopcheck .` on Python 3.10 through 3.13.

**Claude Code hook.** [`examples/hooks/slopcheck.sh`](examples/hooks/slopcheck.sh) lints a `.py` file after Write or Edit. The matcher lives in [`examples/hooks/claude-code.settings.json`](examples/hooks/claude-code.settings.json).

## Comparison

Prose linters and UI linters already have an audience. [no-ai-slop](https://github.com/petergyang/no-ai-slop) (about 12.8k stars when this was written) flags AI-shaped writing. [hallmark](https://github.com/Nutlope/hallmark) (about 32.6k) flags AI-shaped interface. [eslint-plugin-slop](https://github.com/antfu/eslint-plugin-slop) does this job for TypeScript. slopcheck is the Python one: AST and tokens, a score, SARIF, and a prompt an agent can execute.

## Roadmap

- Safe autofix for narrating comments, commented-out code, and debug leftovers.
- A baseline file, so a dirty tree can ratchet forward instead of boiling the ocean.
- An LSP, so the score shows up while the agent is still typing.
- Hallucinated keyword arguments, not only hallucinated imports.
- A plugin API for rules that only make sense in one codebase.

## License

[MIT](LICENSE)
