#!/bin/sh
set -eu

for name in sesman xrdp smb; do
    pid=$(cat "/run/tiz0wn/$name.pid")
    kill -0 "$pid"
done
