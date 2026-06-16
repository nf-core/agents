#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./lib.sh
source "${SCRIPT_DIR}/lib.sh"

schema_files=()
while IFS= read -r file; do
  [ -z "${file}" ] && continue
  schema_files+=("${file}")
done < <(collect_files "$@" | grep -E '(^|/)nextflow_schema\.json$' || true)
[ "${#schema_files[@]}" -eq 0 ] && exit 0

require_nf_core

status=0
schema_dirs=()
while IFS= read -r dir; do
  [ -z "${dir}" ] && continue
  schema_dirs+=("${dir}")
done < <(printf '%s\n' "${schema_files[@]}" | xargs -I{} dirname "{}" | sort -u)
for dir in "${schema_dirs[@]}"; do
  if ! nf-core pipelines schema lint --dir "${dir}"; then
    status=1
  fi
done

exit "${status}"
