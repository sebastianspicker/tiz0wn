#!/usr/bin/env bash
# Shared helpers for the Q60T investigation scripts.
# Sourced by every numbered script; not meant to be run directly.
#
# Design rules (from research doc §6):
#   - Read-only by default. Nothing here uninstalls, writes to the TV, or
#     exploits anything.
#   - Explicit target only. We never fall back to "the first connected device".
#   - Raw output is written under evidence/ with a restrictive umask, because
#     it can contain device identifiers.
#   - Every run gets its own evidence directory, so a later run never
#     overwrites earlier evidence.

set -euo pipefail

# Resolve repo root regardless of where the script is invoked from.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EVIDENCE_DIR="${REPO_ROOT}/evidence"
CONFIG_FILE="${REPO_ROOT}/config/tv.env"

# Evidence may contain serials / MACs / tokens: keep it private.
umask 077

log()  { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

load_config() {
  [ -f "$CONFIG_FILE" ] || die "Missing config/tv.env — copy config/tv.env.example and edit it."
  # shellcheck disable=SC1090
  . "$CONFIG_FILE"

  : "${SDB:?SDB not set in config/tv.env}"
  : "${TV_IP:?TV_IP not set in config/tv.env}"
  : "${TV_SERIAL:?TV_SERIAL not set in config/tv.env}"
  # Read-only queries are killed after this many seconds (§6.3: stop a hang,
  # don't retry). Never applied to the removal command itself.
  SDB_TIMEOUT="${SDB_TIMEOUT:-60}"

  [ -x "$SDB" ] || die "sdb not found or not executable at: $SDB"
}

# Create this run's evidence directory: evidence/runs/<timestamp>-<script>/
# Call after load_config in any script that records evidence.
start_run() {
  RUN_DIR="${EVIDENCE_DIR}/runs/$(date +%Y%m%d-%H%M%S)-$(basename "$0" .sh)"
  mkdir -p "$RUN_DIR"
  log "Evidence for this run: ${RUN_DIR#"$REPO_ROOT"/}"
}

# Run a command with a wall-clock limit. macOS has no coreutils `timeout`,
# so use perl's alarm (SIGALRM terminates the exec'd process; exit 142).
with_timeout() {
  local secs="$1"; shift
  perl -e 'alarm shift; exec @ARGV or die "exec failed: $!\n"' "$secs" "$@"
}

# Run a READ-ONLY sdb subcommand against the EXPLICIT serial, recording raw
# output plus the exit code. A non-zero exit is evidence, not a script failure.
# Usage: sdb_capture <evidence-basename> <sdb args...>
sdb_capture() {
  local name="$1"; shift
  local out="${RUN_DIR}/${name}.txt" rc=0
  log "sdb -s ${TV_SERIAL} $* -> ${name}.txt"
  # We always pass -s so the command can never target the wrong device.
  with_timeout "$SDB_TIMEOUT" "$SDB" -s "$TV_SERIAL" "$@" >"$out" 2>&1 || rc=$?
  printf '\n# exit code: %s\n' "$rc" >>"$out"
  cat "$out" >&2
  if [ "$rc" -eq 142 ]; then
    log "  (timed out after ${SDB_TIMEOUT}s — recorded; do not retry in a loop)"
  elif [ "$rc" -ne 0 ]; then
    log "  (exited ${rc} — recorded as evidence, not treated as failure)"
  fi
}

# Confirm the intended target is listed by 'sdb devices' AND in the "device"
# state. Exact match on the serial column — no substring/regex matching, and an
# "offline" or "unauthorized" entry does not count.
require_target_connected() {
  local devices
  devices="$(with_timeout 15 "$SDB" devices || true)"
  printf '%s\n' "$devices" >&2
  if ! printf '%s\n' "$devices" | awk -v s="$TV_SERIAL" '$1 == s && $2 == "device" { found = 1 } END { exit !found }'; then
    die "Intended target ${TV_SERIAL} is not listed as 'device' in 'sdb devices'. Run 01-connect.sh first; do not proceed against another device."
  fi
}
