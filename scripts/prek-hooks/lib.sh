#!/usr/bin/env bash
set -euo pipefail

collect_files() {
  if [ "$#" -gt 0 ]; then
    printf '%s\n' "$@"
    return 0
  fi

  local staged unstaged
  staged="$(git diff --name-only --cached 2>/dev/null || true)"
  unstaged="$(git diff --name-only 2>/dev/null || true)"
  printf '%s\n%s\n' "$staged" "$unstaged" | sed '/^$/d' | sort -u
}

require_nf_core() {
  if command -v nf-core >/dev/null 2>&1; then
    return 0
  fi
  echo "ERROR: nf-core CLI not found. Install nf-core tools, then retry."
  echo "Install docs: https://nf-co.re/docs/nf-core-tools/installation"
  return 1
}
