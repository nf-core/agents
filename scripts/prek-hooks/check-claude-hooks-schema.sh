#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./lib.sh
source "${SCRIPT_DIR}/lib.sh"

settings_files=()
while IFS= read -r file; do
  [ -z "${file}" ] && continue
  settings_files+=("${file}")
done < <(collect_files "$@" | grep -E '(^|/)\.claude/settings\.json$' || true)
[ "${#settings_files[@]}" -eq 0 ] && exit 0

status=0
for file in "${settings_files[@]}"; do
  [ -f "${file}" ] || continue

  # Check for bare `command` keys directly inside hook entries (wrong schema).
  # Correct: hooks[*].hooks[*].type + command
  # Wrong:   hooks[*].command
  bad_entries="$(jq -r '
    .hooks // {}
    | to_entries[]
    | .key as $event
    | .value[]
    | select(has("command"))
    | "\($event): entry has bare \"command\" — wrap in hooks:[{type,command}]"
  ' "${file}" 2>/dev/null || true)"

  if [ -n "${bad_entries}" ]; then
    echo "ERROR: invalid Claude Code hook schema in ${file}"
    while IFS= read -r line; do
      echo "  ${line}"
    done <<< "${bad_entries}"
    echo "  Expected format: {\"matcher\": \"...\", \"hooks\": [{\"type\": \"command\", \"command\": \"...\"}]}"
    status=1
  fi
done

exit "${status}"
