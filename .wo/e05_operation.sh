#!/usr/bin/env bash
# WOGHAW E-05 operation (lab instrument, not the WO product). One deterministic sequence:
#   phase A: write fixture/e05/recovery.txt  ->  marker E05_LOCAL_MUTATION_DONE  ->  [interrupt: block]  ->  phase B: complete.txt
set -euo pipefail
mode="${1:?mode}"; att="${2:?attempt}"
case "$mode" in interrupt|complete) ;; *) echo "E05_BAD_MODE" >&2; exit 2 ;; esac
case "$att" in ATT-E05-[0-9]) ;; *) echo "E05_BAD_ATTEMPT" >&2; exit 2 ;; esac
mkdir -p fixture/e05
printf 'E05_PARTIAL_STATE operation=OP-E05-RECOVERY-1 attempt=%s\n' "$att" > fixture/e05/recovery.txt
sync
d=$(sha256sum fixture/e05/recovery.txt | cut -c1-64)
printf 'E05_LOCAL_MUTATION_DONE attempt=%s recovery_sha256=%s at=%s\n' "$att" "$d" "$(date -u +%FT%TZ)" > fixture/e05/marker.txt
sync
echo "E05_LOCAL_MUTATION_DONE attempt=$att recovery_sha256=$d"
if [ "$mode" = interrupt ]; then sleep 600; fi
printf 'E05_OPERATION_COMPLETE operation=OP-E05-RECOVERY-1 attempt=%s\n' "$att" > fixture/e05/complete.txt
sync
echo "E05_OPERATION_COMPLETE attempt=$att"
