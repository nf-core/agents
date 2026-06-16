#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./lib.sh
source "${SCRIPT_DIR}/lib.sh"

[ -f CHANGELOG.md ] || exit 0

files=()
while IFS= read -r file; do
  [ -z "${file}" ] && continue
  files+=("${file}")
done < <(collect_files "$@")
[ "${#files[@]}" -eq 0 ] && exit 0

visible_regex='(^|/)(workflows/|modules/local/|subworkflows/local/|nextflow\.config$|nextflow_schema\.json$|conf/|assets/)'
has_visible=0
has_changelog=0

for file in "${files[@]}"; do
  [ -z "${file}" ] && continue
  if echo "${file}" | grep -qE "${visible_regex}"; then
    has_visible=1
  fi
  if [ "${file}" = "CHANGELOG.md" ] || echo "${file}" | grep -q '/CHANGELOG.md$'; then
    has_changelog=1
  fi
done

if [ "${has_visible}" -eq 1 ] && [ "${has_changelog}" -eq 0 ]; then
  echo "ERROR: user-visible files changed but CHANGELOG.md not updated."
  echo "Add entry under ## [Unreleased]."
  exit 1
fi

exit 0
