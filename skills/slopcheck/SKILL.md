---
name: slopcheck
description: Scan Python for AI-agent slop (swallowed exceptions, fake fallbacks, hallucinated imports, leftover debug, duplicate rewrites). Use when editing Python, reviewing agent-written code, or when the user mentions slop, slopcheck, or cleanup of generated Python.
---

# slopcheck

A linter for the mess AI coding agents leave in Python. The Slop Score runs from 0 to 100. Higher is cleaner.

## When to run

Run slopcheck after you write or edit Python (`.py` or `.pyi`), and again before you tell the user the change is done. Also run it when the user asks to clean generated code, or mentions slop or slopcheck.

## How to run

From the project root:

```bash
slopcheck .
```

On the files you touched:

```bash
slopcheck path/to/file.py --format json
```

If the command is not on `PATH`:

```bash
uvx slopcheck .
```

From a checkout of this repo:

```bash
python -m slopcheck .
```

Read the terminal report. Use `--format json` when you need stable fields: `rule`, `path`, `line`, `message`, `hint`.

## How to fix

Change the code. Do not add `# slopcheck: ignore` to raise the score, and do not disable rules in `pyproject.toml` to game it.

Keep behavior. A swallowed exception that hid a failure should raise, or handle one specific exception type. Do not replace it with another dummy return (`{}`, `""`, `"ok"`, `"Error: ..."`).

Do not rename a public function only because the name looks versioned (`_v2`, `_fixed`, `_new`). Drop the extra copy when it is private and unused.

Apply the `hint` on each finding. Re-run slopcheck on the same paths. Stop when the score stops rising, or when the user has accepted the findings that remain.

## Rules

| ID | What it flags |
| --- | --- |
| SLP001 | Bare `except:` that does not re-raise |
| SLP002 | `except Exception` whose body only swallows the error |
| SLP003 | `except` that returns a dummy literal |
| SLP004 | Comment that narrates the next line |
| SLP005 | `print` debug, `breakpoint()`, `pdb.set_trace()`, `{var=}` |
| SLP006 | Unused private helper |
| SLP007 | Near-duplicate function left beside the original |
| SLP008 | `None` or `isinstance` check that cannot fail |
| SLP009 | Body that is only `pass`, `...`, or `NotImplementedError` |
| SLP010 | Import that does not resolve |
| SLP011 | `try` nested deeper than 2 inside one function |
| SLP012 | Long docstring on a function with almost no body |
| SLP013 | Versioned name (`_v2`, `_fixed`, `_copy`, sibling `_new`) |
| SLP014 | Commented-out Python |
| SLP015 | `except` that returns an error string or error dict |

`slopcheck rules` prints the live list, including summaries and hints.

## Do not

Do not invent a green score by deleting tests or excluding the files you just wrote. Do not add narrating comments, debug `print`s, or a second copy of a function named `_v2`. Do not leave `except: pass` or `except Exception: return {}` behind.
