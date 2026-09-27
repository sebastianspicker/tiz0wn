#!/bin/sh
set -eu

secret_dir=/run/q60t-secrets
for name in username password share; do
    test -f "$secret_dir/$name" || {
        echo "missing required secret file" >&2
        exit 64
    }
done

username=$(cat "$secret_dir/username")
password=$(cat "$secret_dir/password")
share=$(cat "$secret_dir/share")

case "$username" in
    q60t) ;;
    *) echo "invalid fixed lab username" >&2; exit 64 ;;
esac
case "$share" in
    Q6[0-9A-F][0-9A-F][0-9A-F][0-9A-F][0-9A-F][0-9A-F][0-9A-F][0-9A-F][0-9A-F][0-9A-F]) ;;
    *) echo "invalid one-shot share name" >&2; exit 64 ;;
esac
# The command-substitution spelling is intentionally a literal case pattern.
# shellcheck disable=SC2016
case "$password" in
    '$(/usr/bin/id>/tmp/q60t-rpc-'[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]')') ;;
    *) echo "invalid literal one-shot password" >&2; exit 64 ;;
esac

# Feed the validated literal through stdin, never shell syntax or process argv.
# XRDP's PAM stack then authenticates the same exact credential as SMB.
printf '%s:%s\n' "$username" "$password" | /usr/sbin/chpasswd
unset password

rm -f /run/xrdp/xrdp.pid /run/xrdp/xrdp-sesman.pid
mkdir -p /run/dbus /run/xrdp
dbus-daemon --system --fork

/usr/sbin/xrdp-sesman --nodaemon &
sesman_pid=$!
/usr/sbin/xrdp --nodaemon &
xrdp_pid=$!
/usr/bin/python3 /usr/local/lib/tiz0wn-lab-server.py &
smb_pid=$!

mkdir -p /run/tiz0wn
printf '%s\n' "$sesman_pid" > /run/tiz0wn/sesman.pid
printf '%s\n' "$xrdp_pid" > /run/tiz0wn/xrdp.pid
printf '%s\n' "$smb_pid" > /run/tiz0wn/smb.pid

# Invoked indirectly by the trap below.
# shellcheck disable=SC2329
stop_all() {
    kill "$smb_pid" "$xrdp_pid" "$sesman_pid" 2>/dev/null || true
    wait "$smb_pid" "$xrdp_pid" "$sesman_pid" 2>/dev/null || true
}
trap stop_all INT TERM EXIT

while kill -0 "$smb_pid" "$xrdp_pid" "$sesman_pid" 2>/dev/null; do
    sleep 1
done
exit 1
