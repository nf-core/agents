#!/usr/bin/env bash
# Bump tool versions and move nf-core modules from quay.io to Seqera Containers.
# Usage: convert.sh <module> [<module> ...]   (run from the nf-core/modules root)
# Parallel nf-core runs race on ~/.config/nfcore's git cache, including runs from
# other sessions, so each module holds a machine-wide lock. macOS has no flock.
set -uo pipefail

lock="$HOME/.config/nfcore/seqera-containers.lock"
mkdir -p "$(dirname "$lock")"
acquire_lock() {
    until mkdir "$lock" 2>/dev/null; do
        echo "waiting for $lock (rmdir it if no other convert.sh is running)"
        sleep 10
    done
    trap 'rmdir "$lock"' EXIT
}
release_lock() {
    rmdir "$lock"
    trap - EXIT
}

log_dir="${TMPDIR:-/tmp}/seqera-containers"
mkdir -p "$log_dir"
failed=()

for m in "$@"; do
    dir="modules/nf-core/$m"
    log="$log_dir/$(echo "$m" | tr / _).log"
    [[ -f "$dir/main.nf" ]] || { echo "SKIP $m: no $dir/main.nf"; failed+=("$m"); continue; }

    acquire_lock
    nf-core modules bump-versions "$m" > "$log" 2>&1
    # bump-versions builds containers itself when it bumps; only create when still on quay.
    if grep -qE "quay.io|depot.galaxyproject.org" "$dir/main.nf"; then
        nf-core modules containers create "$m" >> "$log" 2>&1
    fi
    release_lock

    if grep -qE "quay.io|depot.galaxyproject.org" "$dir/main.nf"; then
        echo "FAIL $m (see $log)"
        failed+=("$m")
    else
        echo "OK   $m $(grep -o "community.wave.seqera.io/library/[^'\"]*" "$dir/main.nf")"
    fi
done

if (( ${#failed[@]} )); then
    echo "Failed: ${failed[*]}"
    exit 1
fi
