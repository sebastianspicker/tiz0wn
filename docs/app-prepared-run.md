# Prepared app run on the owned Q60T

This is a later operator procedure. The preparation and tests for T-58 are local;
no TV action or `uid=` result is recorded here. Use the exact owned Q60T and
firmware documented in the repository. Keep the TV and Mac on a trusted LAN.

From the repository root, set the two private addresses in the shell. Choose
either the existing `tv_research` Samsung profile or a self-signed author
certificate and its password. `TV_HOST` is the TV's LAN IPv4 address;
`HOST_IP` is this Mac's LAN IPv4 address. The helper pins the package and service
IDs, payload and WGT paths. It accepts only a phase name.

```sh
export TV_HOST='<TV_LAN_IP>' HOST_IP='<MAC_LAN_IP>'
export PROFILE='tv_research'      # existing Samsung profile; omit for self-signing
# or: export AUTHOR_PASSWORD='<OWN_AUTHOR_CERT_PASSWORD>'
sh exploits/tiz0wn-root/live/app-run.sh install
sh exploits/tiz0wn-root/live/app-run.sh bootstrap
sh exploits/tiz0wn-root/live/app-run.sh restart
# Fully power-cycle the TV, then:
sh exploits/tiz0wn-root/live/app-run.sh run
```

Set Developer Mode **Host PC IP** to the Mac's address and restart before
`install`. The `install` phase checks the v2 API's `developerIP`, builds and signs
the current source tree, checks the WGT archive and its SHA-256 stability, then
uses `tizen install -s "$TV_HOST:26101"` for the pinned WGT. The local author
certificate belongs to the operator. `PROFILE=tv_research` uses the owner's
existing Samsung author and distributor certificate. Without `PROFILE`, the
script self-signs with `AUTHOR_PASSWORD`.
See `exploits/tiz0wn-app/docs/SIGNING.md`.

`bootstrap` first submits `id -u` to the root agent and requires `0`; a stale
pidfile is not enough. It submits `payload/app-smack-job` through `live/job.sh`
-> `job-put.sh`. That body carries `app-smack`, checks its pinned SHA-256, writes the marker, then
invokes the content-form helper:

```sh
sh -c "$(cat /opt/usr/share/tvroot/app-smack)" app-smack tiz0wnprob
```

A failed `job-put` hash leaves its remote `cmd/in/<name>.tmp` for inspection.
The `app-smack-job` payload removes its own `app-smack.tmp` on a failed hash.

The helper waits for `app SMACK rule loaded for tiz0wnprob` and reads both
exact `load2` lines back:

```text
User::Pkg::tiz0wnprob System rwxat
System User::Pkg::tiz0wnprob rwxat
```

The image policy has no default `User::Pkg::*` → `System` access, so the
hypothesis is that the app cannot reach the `System`-labelled sdbd before this
rule exists. No direct denial was captured; `TRANSPORT.md` keeps that
qualification. The first load therefore comes from the running root agent. The payload saves the app ID marker, and the boot
hook reloads the same two runtime rules after each full power cycle. The
helper checks the current `buxton2ctl get system db/sdk/develop/ip` value before
setting it to `127.0.0.1`, then verifies `developerIP` through the v2 API.

`run` first stops the host `sdb` daemon: sdbd accepts one client, and a live
host session resets the app's connection. It then uses the v2 API to
launch `tiz0wnprob.Main`, waits for page port `18735`, then checks the latest
boot log segment for `app SMACK rule loaded for tiz0wnprob` and checks the
root agent PID and process start time against `/proc/<pid>/stat` through the
app's read-only `/state` response. If either gate fails, it stops. Finally it sends
`GET http://$TV_HOST:18734/run` with the exact
`Origin: http://127.0.0.1:18735` and prints the returned line only when it
starts with **`uid=`**. The 2026-11-04 live run reached exactly this line. An
install, page response or accepted launch alone does not prove it. Keep the full error and `uid=` line in a private run
record.

When Host PC IP is `127.0.0.1`, expect host SDB from the Mac to be unavailable.
The exact reversal is: on the TV open **Apps → 12345 → Developer Mode**, set
**Host PC IP** back to `$HOST_IP`, and fully power-cycle. Then run:

```sh
sh exploits/tiz0wn-root/live/app-run.sh recover
```

`recover` checks the v2 `developerIP` readback and prints the pinned host SDB
serial. It cannot change the TV setting remotely after host SDB has been lost.
If any gate fails after the switch, perform this same reversal. The helper
never silently assumes a failed callback means a write succeeded.
