#!/bin/sh
set -eu

secret_dir=/run/q60t-secrets
for name in username password host rdp_port smb_port share; do
    test -f "$secret_dir/$name" || {
        echo "missing client secret file" >&2
        exit 64
    }
done

python3 /usr/local/lib/tiz0wn-lab-client.py

username=$(cat "$secret_dir/username")
host=$(cat "$secret_dir/host")
rdp_port=$(cat "$secret_dir/rdp_port")

Xvfb :99 -screen 0 1024x768x16 -nolisten tcp >/tmp/xvfb.log 2>&1 &
xvfb_pid=$!
export DISPLAY=:99

stop_all() {
    kill "$rdp_pid" "$xvfb_pid" 2>/dev/null || true
    wait "$rdp_pid" "$xvfb_pid" 2>/dev/null || true
}
rdp_pid=
trap stop_all INT TERM EXIT

i=0
while ! xset q >/dev/null 2>&1; do
    i=$((i + 1))
    test "$i" -lt 50 || exit 70
    sleep 0.1
done

# Exercise the published RDP port with a deliberate authentication failure.
# The host verifies that this did not create a successful XRDP session before
# accepting the exact-credential session below.
{ printf '%s\n' 'TIZ0WN-INVALID-RDP-PASSWORD'; } | timeout \
    --foreground \
    --signal=TERM \
    --kill-after=2s \
    8s \
    xfreerdp \
    /v:"$host:$rdp_port" \
    /u:"$username" \
    /from-stdin:force \
    /cert:ignore \
    /size:1024x768 \
    /bpp:16 \
    /network:lan \
    /log-level:WARN \
    >/tmp/invalid-rdp.log 2>&1 || true

{ cat "$secret_dir/password"; printf '\n'; } | xfreerdp \
    /v:"$host:$rdp_port" \
    /u:"$username" \
    /from-stdin:force \
    /cert:ignore \
    /size:1024x768 \
    /bpp:16 \
    /network:lan \
    /log-level:WARN &
rdp_pid=$!
wait "$rdp_pid"
