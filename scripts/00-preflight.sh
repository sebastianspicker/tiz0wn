#!/usr/bin/env bash
# Phase C preflight: verify the toolchain exists and record its version.
# Touches nothing on the TV. Safe to run any time.
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"
load_config
start_run

log "sdb path: $SDB"
"$SDB" version | tee "${RUN_DIR}/sdb-version.txt"

log "Preflight OK. Next: enable Developer Mode on the TV, then run 01-connect.sh"
