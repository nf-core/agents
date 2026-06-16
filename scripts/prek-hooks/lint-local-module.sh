#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./lib.sh
source "${SCRIPT_DIR}/lib.sh"

files=()
while IFS= read -r file; do
  [ -z "${file}" ] && continue
  files+=("${file}")
done < <(collect_files "$@" | grep -E '(^|/)modules/local/' || true)
[ "${#files[@]}" -eq 0 ] && exit 0

require_nf_core

status=0
checked=""
for file in "${files[@]}"; do
  [ -f "${file}" ] || continue
  module="$(echo "${file}" | sed -n 's|.*/modules/local/\([^/]*\).*|\1|p')"
  [ -n "${module}" ] || continue

  dir="$(dirname "${file}")"
  while [ "${dir}" != "/" ] && [ ! -f "${dir}/nextflow.config" ]; do
    dir="$(dirname "${dir}")"
  done
  if [ ! -f "${dir}/nextflow.config" ]; then
    continue
  fi

  key="${dir}:${module}"
  if echo "${checked}" | grep -qx "${key}"; then
    continue
  fi
  checked="${checked}"$'\n'"${key}"

  if ! nf-core modules lint --local "${module}" --dir "${dir}"; then
    status=1
  fi
done

exit "${status}"
