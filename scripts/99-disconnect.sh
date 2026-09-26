#!/usr/bin/env bash
# Session teardown (§6.5): drop the sdb connection deliberately.
# Reminder: for a one-off diagnostic session, also disable Developer Mode on the
# TV afterward and restart if prompted — UNLESS you intentionally installed a
# tool (e.g. TizenBrew) that needs the development service to keep running.
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"
load_config

"$SDB" disconnect "$TV_SERIAL" || true
log "Disconnected from ${TV_SERIAL}."
log "If this was a one-off session: turn Developer Mode OFF on the TV and restart."
