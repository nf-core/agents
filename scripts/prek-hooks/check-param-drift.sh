#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./lib.sh
source "${SCRIPT_DIR}/lib.sh"

configs=()
while IFS= read -r file; do
  [ -z "${file}" ] && continue
  configs+=("${file}")
done < <(collect_files "$@" | grep -E '(^|/)nextflow\.config$' || true)
[ "${#configs[@]}" -eq 0 ] && exit 0

status=0
for config in "${configs[@]}"; do
  [ -f "${config}" ] || continue
  schema_dir="$(dirname "${config}")"
  schema="${schema_dir}/nextflow_schema.json"
  [ -f "${schema}" ] || continue

  config_params=()
  while IFS= read -r param; do
    [ -z "${param}" ] && continue
    config_params+=("${param}")
  done < <(rg -o 'params\.[A-Za-z_][A-Za-z0-9_]*' "${config}" | sed 's/^params\.//' | sort -u || true)

  schema_params=()
  while IFS= read -r param; do
    [ -z "${param}" ] && continue
    schema_params+=("${param}")
  done < <(jq -r '
    [
      .definitions // {}
      | to_entries[]
      | .value.properties // {}
      | keys[]
    ] | unique[]' "${schema}" 2>/dev/null || true)

  missing=()
  for p in "${config_params[@]}"; do
    if ! printf '%s\n' "${schema_params[@]}" | grep -qx "${p}"; then
      missing+=("${p}")
    fi
  done

  if [ "${#missing[@]}" -gt 0 ]; then
    echo "ERROR: param drift in ${config}"
    for p in "${missing[@]}"; do
      echo "  - params.${p} missing in ${schema}"
    done
    status=1
  fi
done

exit "${status}"
