#!/usr/bin/env bash
# Claude Code PostToolUse hook. Reads the hook JSON on stdin and lints Python files.
set -euo pipefail

if ! command -v slopcheck >/dev/null 2>&1; then
  exit 0
fi

input=$(cat || true)
if [ -z "$input" ]; then
  exit 0
fi

file=$(printf '%s' "$input" | python3 -c '
import json
import sys

raw = sys.stdin.read()
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print("")
    raise SystemExit(0)
tool = data.get("tool_input") or data.get("tool_response") or {}
if not isinstance(tool, dict):
    tool = {}
path = tool.get("file_path") or tool.get("filePath") or tool.get("path") or ""
print(path)
')

case "$file" in
  *.py|*.pyi)
    slopcheck "$file" --quiet
    ;;
esac
