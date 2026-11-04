# Token sdb relay and `/cmd` operating rule

Verified 2026-11-04 evening on the owned Q60T.

## What the relay is for

Host PC IP must stay `127.0.0.1` for boot self-root and the app probe. That
normally costs the Mac its sdb session. The relay listens on `26103`, requires
a 32-hex token, and forwards to `127.0.0.1:26101`, so `sdbd` sees a loopback
client. It carries `sdb push` and `sdb install` from the Mac.

## Verified

- correct token + CNXN through `26103` returns the server `CNXN` (raw check)
- `sdb push` and `tizen install` succeed through `127.0.0.1:<local proxy>`
- `POST /cmd` succeeds while the connector runs and no Mac sdb session is open
- wrong token closes immediately with no reply
- a token change needs a bridge restart; the token is read once at start

## The single-client rule

`sdbd` serves **one loopback client at a time**. The relay opens one upstream
connection per client, so the Mac's sdb transport and the app probe cannot be
upstream together. In practice:

| Mac sdb session | `/cmd`, `/run` | push/install |
| --- | --- | --- |
| closed | work (through the relay) | work |
| open | fail (`ECONNRESET`/truncated) | work |

So: `sdb kill-server` before using the app endpoints, and close the app calls
before opening a maintenance sdb session. An idle connector process does not
block anything.

## Files on the TV

```text
/opt/usr/share/tvroot/bridge       arm marker (must exist)
/opt/usr/share/tvroot/bridge.sh    staged payload
/opt/usr/share/tvroot/bridge.token 33 bytes, 0644 owner:users, label _
/opt/usr/share/tvroot/bridge.pid   "<pid> <port> <starttime>"
/opt/usr/share/tvroot/bridge.log   bounded, no token bytes
/opt/usr/share/tvroot/bridge-port  optional 1024..65535, default 26103
```

The token is `0644` and label `_` because the app (`User::Pkg::tiz0wnprob`,
uid 5001) must read it. It is not a strong secret; it gates the LAN, it does
not encrypt.

## Arm, restart, disarm

Run through the app endpoint or an agent job, with no Mac sdb session:

```sh
sh -c "$(cat /opt/usr/share/tvroot/bridge.sh)" sh status
sh -c "$(cat /opt/usr/share/tvroot/bridge.sh)" sh stop
sh -c "$(cat /opt/usr/share/tvroot/bridge.sh)" sh start
```

Pass `sh` as `$0`; `sh -c "$(cat f)" stop` reaches the usage branch.

On the Mac:

```sh
python3 exploits/tiz0wn-root/live/bridge-connect.py <TV_IP> \
  --bridge-port 26103 --token-file exploits/tiz0wn-root/live/bridge-private.token
sdb connect 127.0.0.1:<printed port>
```

The connector binds loopback only and prints the chosen port. It holds the
token, never logs it, and exits on a listener error.

## Boot and disarm

The boot hook starts the relay after the agent when the marker, a valid token
and `bridge.sh` exist. It does not wait for `sdbd`. `app-run.sh stop` stops the
relay and clears the marker.

## Failure modes seen

- **Token mismatch** — every relayed connection closes in ~30 ms with no reply.
  Rewrite the token from the local file, restart the bridge.
- **Stale bridge after a token rewrite** — the process keeps the old token in
  memory; always stop/start.
- **`EHOSTUNREACH 127.0.0.1:26103` in the app** — the bridge was down. The probe
  falls back to `26101`; it still fails if a Mac session is open.
- **sdbd wedge** — a power-cycle is the reliable clear.
