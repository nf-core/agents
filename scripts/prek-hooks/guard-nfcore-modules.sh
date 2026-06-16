#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./lib.sh
source "${SCRIPT_DIR}/lib.sh"

status=0
while IFS= read -r file; do
  [ -z "${file}" ] && continue
  if echo "${file}" | grep -q 'modules/nf-core/'; then
    echo "ERROR: blocked edit: ${file}"
    echo "Use: nf-core modules patch <tool>"
    status=1
  fi
done < <(collect_files "$@")

exit "${status}"
