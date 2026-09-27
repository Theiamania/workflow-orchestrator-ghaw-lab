#!/usr/bin/env bash
# WOGHAW E-11 runtime-ownership lease (lab instrument, NOT the WO product). Deterministic, no inference.
# Lease  = refs/heads/wo-lease/e11-target (exists <=> owned). Target (mutation boundary) = refs/heads/woghaw-e11-target.
#   acquire : create the lease ref with an owner commit; server-side CAS (expected: ref absent). Rejected -> HOLD.
#   finish  : ONE atomic push, both CAS-fenced: advance the target by one owner commit AND delete the lease
#             (only if the lease still is this owner's commit and the target is still at the observed head).
#   release : CAS-delete the lease without mutating (agent did not succeed).
# Every outcome is emitted as a ::notice / ::error annotation (public check-run API).
set -uo pipefail
mode="${1:?mode}"; LEASE=refs/heads/wo-lease/e11-target; TARGET=refs/heads/woghaw-e11-target
owner="${WO_ATTEMPT_ID:?}@run${GITHUB_RUN_ID:?}"
REPO_URL="${WO_REPO_URL:-https://github.com/${GITHUB_REPOSITORY}.git}"
AUTH="AUTHORIZATION: basic $(printf 'x-access-token:%s' "${GH_TOKEN:?}" | base64 | tr -d '\n')"
g() { git -c http.extraheader="$AUTH" "$@"; }
now() { date -u +%Y-%m-%dT%H:%M:%S.%3NZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ; }
ann() { echo "::$1 title=$2::$3"; }
work=$(mktemp -d); cd "$work"; git init -q .; git config user.name wo-e11; git config user.email wo-e11@invalid
lease_head() { g ls-remote "$REPO_URL" "$LEASE" | cut -f1; }
case "$mode" in
acquire)
  t0=$(now)
  git commit -q --allow-empty -m "WO-LEASE owner=$owner operation=${WO_OPERATION_ID:?} acquired_request_at=$t0"
  c=$(git rev-parse HEAD)
  if g push -q --porcelain --force-with-lease="$LEASE:" "$REPO_URL" "$c:$LEASE" >push.out 2>&1; then
    t1=$(now)
    ann notice WO_E11_ACQUIRED "{\"owner\":\"$owner\",\"lease_commit\":\"$c\",\"request_at\":\"$t0\",\"acquired_at\":\"$t1\"}"
    echo "lease_commit=$c" >> "$GITHUB_OUTPUT"; echo "acquired_at=$t1" >> "$GITHUB_OUTPUT"
  else
    t1=$(now); holder=$(lease_head)
    hmsg=""; if [ -n "$holder" ]; then g fetch -q "$REPO_URL" "$LEASE" && hmsg=$(git log -1 --format=%s FETCH_HEAD); fi
    ann error WO_E11_HOLD "{\"owner\":\"$owner\",\"request_at\":\"$t0\",\"rejected_at\":\"$t1\",\"lease_holder_commit\":\"$holder\",\"lease_holder\":\"$hmsg\",\"push\":\"$(tr '\n\t"' '  ' < push.out | cut -c1-300)\"}"
    exit 1
  fi ;;
finish|release)
  lc="${WO_LEASE_COMMIT:?}"; t0=$(now)
  if [ "$mode" = finish ]; then
    g fetch -q "$REPO_URL" "$TARGET"; base=$(git rev-parse FETCH_HEAD); git checkout -q FETCH_HEAD
    printf '%s run_id=%s attempt=%s lease_commit=%s acquired_at=%s mutation_at=%s\n' "$owner" "$GITHUB_RUN_ID" "$WO_ATTEMPT_ID" "$lc" "${WO_ACQUIRED_AT:?}" "$t0" >> owners.log
    git add owners.log; git commit -q -m "WO-E11 mutation by owner $owner (lease $lc)"; nc=$(git rev-parse HEAD)
    if g push -q --porcelain --atomic --force-with-lease="$LEASE:$lc" --force-with-lease="$TARGET:$base" "$REPO_URL" "$nc:$TARGET" ":$LEASE" >push.out 2>&1; then
      ann notice WO_E11_MUTATION_AND_RELEASE "{\"owner\":\"$owner\",\"lease_commit\":\"$lc\",\"target_base\":\"$base\",\"target_new\":\"$nc\",\"at\":\"$(now)\"}"
    else
      ann error WO_E11_FENCED "{\"owner\":\"$owner\",\"lease_commit\":\"$lc\",\"current_lease\":\"$(lease_head)\",\"push\":\"$(tr '\n\t"' '  ' < push.out | cut -c1-300)\"}"; exit 1
    fi
  else
    if g push -q --porcelain --force-with-lease="$LEASE:$lc" "$REPO_URL" ":$LEASE" >push.out 2>&1; then
      ann notice WO_E11_RELEASED_NO_MUTATION "{\"owner\":\"$owner\",\"lease_commit\":\"$lc\",\"at\":\"$(now)\"}"
    else
      ann error WO_E11_RELEASE_FAILED "{\"owner\":\"$owner\",\"lease_commit\":\"$lc\",\"current_lease\":\"$(lease_head)\"}"; exit 1
    fi
  fi ;;
*) echo "bad mode" >&2; exit 2 ;;
esac
