#!/usr/bin/env bash
# Phase C step 1: connect to the EXPLICIT television target and confirm identity.
# Read-only. Establishes the connection the later steps depend on.
#
# Prerequisite: Developer Mode enabled on the TV (Apps > enter 12345 > set this
# computer's IP as Host PC IP > restart the TV). See research doc §6.1.
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"
load_config

# Start the local sdb server explicitly so its startup doesn't overlap the connect.
"$SDB" start-server >/dev/null 2>&1 || true

# The very first connect after installing sdb failed once on 2026-09-26 and an
# immediate retry succeeded (not reproducible afterwards; see docs/setup-macos.md).
# So: exactly ONE retry after a short pause — never a loop (§6.3).
log "Connecting to ${TV_SERIAL} (TV_IP=${TV_IP})"
if ! "$SDB" connect "$TV_SERIAL"; then
  log "First connect failed; retrying once in 3s"
  sleep 3
  "$SDB" connect "$TV_SERIAL" || die "sdb connect failed twice. Check TV_IP, that Developer Mode is on, and that HOST_IP on the TV matches this computer."
fi

require_target_connected
log "Target connected and verified. Next: 02-capability.sh"
