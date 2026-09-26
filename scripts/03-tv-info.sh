#!/usr/bin/env bash
# Phase C optional: local HTTP identity probe against your own TV (§6.4).
# Read-only. A timeout or missing endpoint is NOT proof the TV is inaccessible
# by sdb — the same identity is also readable from the TV's ordinary menus.
#
# The response may contain identifying info; it is written -private (gitignored)
# and must not be shared wholesale.
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"
load_config
start_run

out="${RUN_DIR}/tv-info-private.json"
log "Probing http://${TV_IP}:8001/api/v2/ (3s connect / 5s total timeout)"
if curl --connect-timeout 3 --max-time 5 -fsS "http://${TV_IP}:8001/api/v2/" -o "$out"; then
  log "Wrote ${out} (private, gitignored). Do not upload it wholesale."
else
  log "Endpoint absent or timed out. Not a failure — record 'endpoint: not available'."
fi
