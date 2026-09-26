#!/usr/bin/env bash
# Phase D: remove ONE positively-identified, optional, reinstallable app.
# This is the only script here that writes to the TV, so it is heavily gated.
#
# It does NOT contain a package list. You must pass the identifier you verified
# yourself (research doc §7.2 — application ID vs package ID are NOT
# interchangeable; establish the mapping from real metadata first).
#
# Usage:
#   scripts/04-remove-one-app.sh --route sdb    --id <VERIFIED_PACKAGE_ID>
#   scripts/04-remove-one-app.sh --route tizen  --id <VERIFIED_APPLICATION_ID> --tizen /abs/path/to/tizen
#
# STOP conditions (§7 / roadmap Phase D): uncertain dependencies, no verified
# reinstall path, or ambiguous target. If any apply, do not run this.
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

ROUTE=""; APP_ID=""; TIZEN_BIN=""
while [ $# -gt 0 ]; do
  case "$1" in
    --route|--id|--tizen) [ $# -ge 2 ] || die "$1 needs a value" ;;
  esac
  case "$1" in
    --route) ROUTE="$2"; shift 2 ;;
    --id)    APP_ID="$2"; shift 2 ;;
    --tizen) TIZEN_BIN="$2"; shift 2 ;;
    *) die "Unknown argument: $1" ;;
  esac
done

# Validate everything BEFORE touching the TV or asking for confirmation.
case "$ROUTE" in
  sdb) ;;
  tizen) [ -n "$TIZEN_BIN" ] && [ -x "$TIZEN_BIN" ] || die "Route tizen needs --tizen /abs/path/to/tizen (executable)" ;;
  *) die "Pass --route sdb|tizen" ;;
esac
[ -n "$APP_ID" ] || die "Pass --id <verified identifier> (no default, by design)"
[ -t 0 ] || die "Needs an interactive terminal for confirmation."

load_config
start_run
require_target_connected

# Before-state snapshot (read-only), taken first so you can see whether the
# identifier actually appears in the live inventory before confirming.
sdb_capture applist-before shell 0 applist
if grep -qF -- "$APP_ID" "${RUN_DIR}/applist-before.txt"; then
  BEFORE="present"
else
  BEFORE="NOT FOUND"
fi

# Confirmation checklist — the operator must affirm the §7.5 allowlist criteria.
cat >&2 <<EOF

About to remove ONE app from ${TV_SERIAL} via route: ${ROUTE}
  Identifier: ${APP_ID}
  In applist-before: ${BEFORE}

Confirm ALL of the following (research doc §7.5). If any is "no", abort:
  1. This is an optional app you recognize (not launcher/store/account/tuner/settings).
  2. You resolved the identifier from real metadata (not by splitting at the first dot).
  3. You verified a working reinstall path for this model/region.
  4. You captured before-state evidence (storage in Manage Storage, applist above).
EOF
[ "$BEFORE" = "present" ] || log "WARNING: identifier not in the live app list. Unless you know why, abort."
read -r -p "Type EXACTLY 'remove ${APP_ID}' to proceed: " CONFIRM
[ "$CONFIRM" = "remove ${APP_ID}" ] || die "Confirmation did not match. Aborted (nothing changed)."

# The write. No timeout (killing it mid-operation is worse than waiting), and a
# failure must NOT abort the script — the after-snapshot is always taken.
RESULT="${RUN_DIR}/remove-result.txt"
RC=0
case "$ROUTE" in
  sdb)
    # Direct sdb route as reported on the NU7400 (§7.3). Argument is a PACKAGE ID.
    log "sdb -s ${TV_SERIAL} uninstall ${APP_ID}"
    "$SDB" -s "$TV_SERIAL" uninstall "$APP_ID" >"$RESULT" 2>&1 || RC=$?
    ;;
  tizen)
    # Samsung TV-specific CLI (§7.2/§7.3). -p takes an APPLICATION ID here despite
    # being named --pkgid.
    log "tizen uninstall -s ${TV_SERIAL} -p ${APP_ID}"
    "$TIZEN_BIN" uninstall -s "$TV_SERIAL" -p "$APP_ID" >"$RESULT" 2>&1 || RC=$?
    ;;
esac
printf '\n# exit code: %s\n' "$RC" >>"$RESULT"
cat "$RESULT" >&2

# After-state snapshot. A zero exit code is NOT proof of removal (§7.4).
sdb_capture applist-after shell 0 applist
if grep -qF -- "$APP_ID" "${RUN_DIR}/applist-after.txt"; then
  AFTER="still present"
else
  AFTER="absent"
fi
diff "${RUN_DIR}/applist-before.txt" "${RUN_DIR}/applist-after.txt" >"${RUN_DIR}/applist-diff.txt" || true

log "Command exit code: ${RC}   before: ${BEFORE}   after: ${AFTER}"
log "Inventory diff: ${RUN_DIR#"$REPO_ROOT"/}/applist-diff.txt"
log "Now complete templates/app-change-record.md:"
log "  - did storage change on the TV (Manage Storage)?"
log "  - do Settings, HDMI, sound and your regular apps still work?"
log "  - re-check after a normal restart and network reconnect (permanence)."
