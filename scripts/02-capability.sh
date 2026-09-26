#!/usr/bin/env bash
# Phase C step 2: read-only capability + application inventory.
# This is the core "what can this build actually do" evidence-gathering step.
#
# It queries the capability descriptor and attempts the community-observed
# management app-list command (research doc §6.3). A refusal or "unsupported"
# is a VALID, useful result — we record it and do not retry with guessed
# alternatives. Nothing here removes or writes anything.
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"
load_config
start_run
require_target_connected

# Capability descriptor: reveals fields like intershell_support, sdbd_rootperm,
# rootonoff_support, filesync_support, appcmd_support (§6.3). Interpret these as
# observations of THIS connection, not guarantees about command categories.
sdb_capture capability capability

# Community-observed TV management command. May be unsupported on 2743.0.
# If it hangs, Ctrl-C it — do not start a retry loop (§6.3).
sdb_capture applist shell 0 applist

log "Review capability.txt and applist.txt in ${RUN_DIR#"$REPO_ROOT"/}/"
log "Fill in templates/compatibility-summary.md from what you observed."
