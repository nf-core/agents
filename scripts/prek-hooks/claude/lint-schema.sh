#!/usr/bin/env bash
set -euo pipefail

file_path="$(echo "${CLAUDE_TOOL_INPUT:-}" | jq -r '.file_path // empty' 2>/dev/null || true)"
exec scripts/prek-hooks/lint-schema.sh "${file_path}"
