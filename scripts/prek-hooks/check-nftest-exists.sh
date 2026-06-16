#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./lib.sh
source "${SCRIPT_DIR}/lib.sh"

nf_files=()
while IFS= read -r file; do
  [ -z "${file}" ] && continue
  nf_files+=("${file}")
done < <(collect_files "$@" | grep -E '(^|/)(modules/local|subworkflows/local|workflows)/.*\.nf$' || true)
[ "${#nf_files[@]}" -eq 0 ] && exit 0

status=0
for file in "${nf_files[@]}"; do
  [ -f "${file}" ] || continue
  nf_test="${file%.nf}.nf.test"
  dir="$(dirname "${file}")"
  base="$(basename "${file}" .nf)"
  if [ -f "${nf_test}" ] || [ -f "${dir}/tests/${base}.nf.test" ] || [ -f "${dir}/tests/main.nf.test" ]; then
    continue
  fi
  echo "ERROR: missing nf-test for ${file}"
  echo "Expected one of:"
  echo "  - ${nf_test}"
  if [ "${base}" != "main" ]; then
    echo "  - ${dir}/tests/${base}.nf.test"
  fi
  echo "  - ${dir}/tests/main.nf.test"
  status=1
done

exit "${status}"
