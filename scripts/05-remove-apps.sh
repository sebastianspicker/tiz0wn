#!/usr/bin/env bash
# Phase D (generalized): remove one or more apps by ID or package-prefix.
# Like 04-remove-one-app.sh, this WRITES to the TV — it is the only other
# script here that does. Unlike 04, it takes a package-ID PREFIX (or a full
# app ID) and derives the expected removals for that prefix from the LIVE
# applist captured immediately beforehand, instead of any canned/offline
# list (research doc §7.5: no prewritten removal list; §7.2: application ID
# and package ID are not interchangeable — verify which one you are passing).
#
# NOTE: on this device's firmware (T-NKLDEUC-2743.0), both `sdb uninstall`
# and `vd_appuninstall` were empirically observed to return exit code 0 while
# leaving the live app list completely unchanged, for every store-app prefix
# tested — see evidence/root-feasibility-2026-09-26.md (the raw before/after
# captures are private, under evidence/runs/*-remove-apps*/). A zero exit
# code is NOT evidence of removal (§7.4). This script exists to make that
# observation reproducible and safe to repeat — it is mainly a harness, not
# a working debloat tool on this build.
#
# Usage:
#   METHOD=uninstall|vd CONTINUE_ON_REFUSAL=0|1 \
#     scripts/05-remove-apps.sh <id-or-prefix> [<id-or-prefix> ...]
#
#   id-or-prefix: a package prefix (the text before the first dot) or a full
#     app ID under that prefix. Expected removals = every LIVE applist entry
#     starting with "<prefix>." — never a static/offline list.
#   METHOD=uninstall (default): sdb uninstall <id>
#   METHOD=vd:                  sdb shell 0 vd_appuninstall <id>
#   CONTINUE_ON_REFUSAL=1: on a refusal (nothing changed), log it and move on
#     to the next identifier instead of aborting. Default: abort.
#
# Safety model (same spirit as 04, applied per identifier):
#   - Capture applist BEFORE and AFTER each removal attempt.
#   - Diff the two. If ANYTHING other than exactly the expected app IDs
#     changed (an unexpected removal, or anything added), ABORT immediately
#     — before touching the next identifier.
#   - If exactly nothing changed, that is a refusal, not a failure: stop
#     unless CONTINUE_ON_REFUSAL=1.
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

METHOD="${METHOD:-uninstall}"
case "$METHOD" in
  uninstall|vd) ;;
  *) die "METHOD must be uninstall|vd" ;;
esac
[ $# -ge 1 ] || die "Usage: METHOD=uninstall|vd $0 <id-or-prefix> [...]"

# Extract the app ID from one 'applist' line: it is the last single-quoted
# token on the line (raw format: <tab>'Name'<tab> 'AppID', CRLF line endings).
ids() { grep -o "'[^']*'[[:space:]]*\$" "$1" | tr -d "' \t\r" | sort; }

load_config
start_run
require_target_connected

for ID in "$@"; do
  P="${ID%%.*}"
  log "=== ${ID} (prefix ${P}, method ${METHOD})"

  sdb_capture "${P}-before" shell 0 applist
  ids "${RUN_DIR}/${P}-before.txt" >"${RUN_DIR}/${P}-before.ids"
  [ "$(wc -l <"${RUN_DIR}/${P}-before.ids")" -gt 100 ] || die "before-applist looks broken; stopping"

  # Expected removals: derived from the LIVE before-list, not a canned file.
  expected="$(grep -- "^${P}\." "${RUN_DIR}/${P}-before.ids" | sort)"
  [ -n "$expected" ] || die "no live applist entries under prefix ${P}."

  rc=0
  case "$METHOD" in
    uninstall) cmd=(uninstall "$ID") ;;
    vd)        cmd=(shell 0 vd_appuninstall "$ID") ;;
  esac
  log "sdb -s ${TV_SERIAL} ${cmd[*]}"
  "$SDB" -s "$TV_SERIAL" "${cmd[@]}" >"${RUN_DIR}/${P}-uninstall.txt" 2>&1 || rc=$?
  printf '\n# exit code: %s\n' "$rc" >>"${RUN_DIR}/${P}-uninstall.txt"
  cat "${RUN_DIR}/${P}-uninstall.txt" >&2

  sdb_capture "${P}-after" shell 0 applist
  ids "${RUN_DIR}/${P}-after.txt" >"${RUN_DIR}/${P}-after.ids"
  removed="$(comm -23 "${RUN_DIR}/${P}-before.ids" "${RUN_DIR}/${P}-after.ids")"
  added="$(comm -13 "${RUN_DIR}/${P}-before.ids" "${RUN_DIR}/${P}-after.ids")"
  printf '%s\t rc=%s\t removed=[%s]\t added=[%s]\n' "$P" "$rc" "${removed//$'\n'/ }" "${added//$'\n'/ }" >>"${RUN_DIR}/summary.tsv"
  log "rc=${rc} removed=[${removed//$'\n'/ }] added=[${added//$'\n'/ }]"

  if [ -n "$added" ] || { [ -n "$removed" ] && [ "$removed" != "$expected" ]; }; then
    die "UNEXPECTED inventory change for ${P}; stopping before any further removal"
  fi
  if [ "$removed" != "$expected" ]; then
    [ "${CONTINUE_ON_REFUSAL:-0}" = 1 ] || die "${P} not removed (rc=${rc}); stopping — see ${P}-uninstall.txt"
    log "REFUSED/not removed: ${P} ($(grep -m1 -iE 'can not|not installed|error' "${RUN_DIR}/${P}-uninstall.txt" || echo 'no message'))"
    continue
  fi
  log "OK: ${P} removed exactly as expected"
done
log "All requested identifiers processed. Summary: ${RUN_DIR#"$REPO_ROOT"/}/summary.tsv"
