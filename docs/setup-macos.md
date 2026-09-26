# macOS setup: Tizen CLI (sdb) and first connection

Recorded 2026-09-26 on Apple Silicon (arm64) against the Q60T
(`T-NKLDEUC-2743.0`). Exact commands, as run; no steps elided.

## 1. LAN discovery (read-only)

The TV answers on **8001** (local HTTP API) and, with Developer Mode on,
**26101** (sdb). Sweep your subnet (`ipconfig getifaddr en0` to get your own
address first):

```bash
for i in $(seq 1 254); do
  ( for p in 8001 26101; do
      nc -z -G 1 -w 1 192.168.1.$i $p 2>/dev/null && echo "192.168.1.$i:$p open"
    done ) &
done; wait
```

Confirm target identity and Developer-Mode pairing via the HTTP API. The
snippet below prints only non-identifying fields — the raw response contains
device IDs, so don't persist or share it:

```bash
curl -fsS --max-time 5 http://<TV_IP>:8001/api/v2/ | python3 -c 'import json,sys
d=json.load(sys.stdin)["device"]
print({k: d.get(k) for k in ["modelName","developerMode","developerIP","networkType"]})'
```

Expect `developerMode: '1'` and `developerIP` == this host's address. Set
both in `config/tv.env`.

## 2. Install the Tizen CLI

Download the **CLI installer** for macOS from Samsung/Tizen (used here:
`web-cli_Tizen_SDK_10.0_usa_macos-64.bin`, from `usa.sdk-dl.tizen.org`).

### Why it "won't install"

Not a macOS app/package — it's a shell script with a tar archive appended.
Double-click does nothing because it's saved non-executable (`-rw-r--r--`)
and carries Safari's quarantine attribute. No `chmod`/`xattr` needed: invoke
via `bash` directly.

### Verify, then install

The script self-checks its payload with an embedded MD5. Reproduce that
check before installing — payload offset is line 58, per `ORI_FILE_LEN` in
the script header:

```bash
cd ~/Downloads
F=web-cli_Tizen_SDK_10.0_usa_macos-64.bin
head -3 "$F"                         # shows ORI_FILE_md5sum="..."
tail -n +58 "$F" | md5 -q            # must equal that value
```

Install (this accepts the Tizen SDK license — `bash "$F" --show-license`
first if you want to read it):

```bash
bash "$F" --accept-license "$HOME/tizen-studio"
```

Produces `~/tizen-studio` (with `tools/sdb`), `~/tizen-studio-data`, and
`~/.package-manager` (bundled JDK).

**Apple Silicon note:** no system Java required — the installer bundles its
own JDK. That JDK and `sdb` itself are **x86_64**, so Rosetta 2 must be
present: `pgrep oahd` (running → OK; else `softwareupdate --install-rosetta`).

Verify:

```bash
~/tizen-studio/tools/sdb version     # Smart Development Bridge version 4.2.36
scripts/00-preflight.sh
```

`config/tv.env.example`'s default `SDB=` path matches this install location.

## 3. First connection: the "failed to connect" fix

On the first-ever run, `scripts/01-connect.sh` produced:

```
* Server is not running. Start it now on port 26099 *
* Server has started successfully *
error: failed to connect to remote target '<TV_IP>'
```

Port 26101 was independently confirmed reachable at that moment (`nc -z`
succeeded). An immediate manual `sdb connect <TV_IP>:26101` succeeded, and
the failure did **not** reproduce afterward, even from a freshly killed
server. **Root cause unconfirmed** — leading candidates: first-ever pairing
of this host with the TV, or the local sdb server racing its own startup.

Resulting change to `scripts/01-connect.sh`:

- explicit `sdb start-server` before connecting;
- on `connect` failure, retry **exactly once** after 3 s, then abort with a
  diagnostic — deliberately not a retry loop (research doc §6.3).

Two consecutive failures → check TV IP, Developer Mode state, and that the
TV's configured Host PC IP matches this host.

## 4. Result on this TV

(Summary; raw output stays in `evidence/`.) `scripts/02-capability.sh`
succeeded:

| Field | Value |
|---|---|
| platform_version / profile | 5.5 / tv |
| cpu_arch | armv7 |
| secure_protocol | enabled |
| intershell_support | disabled |
| sdbd_rootperm / rootonoff_support | disabled / disabled |
| filesync_support | pushpull |
| appcmd_support | disabled |
| `shell 0 applist` | **works**: live list of 387 entries (name + app ID) |

On 2743.0, live app-list read works without a normal shell or root. Next:
`templates/compatibility-summary.md`.

## Glossary

- **SDB (Smart Development Bridge)** — Tizen's adb-equivalent debug/deploy protocol; client at `tools/sdb`, daemon (`sdbd`) on the TV, default port 26101.
- **sdbd** — the SDB daemon running on the TV that the client connects to.
- **Developer Mode** — TV-side toggle (Apps → `12345`) that starts `sdbd` and binds it to a configured Host PC IP.
- **Rosetta 2** — Apple's x86_64-on-arm64 translation layer; required here because the bundled JDK and `sdb` binary are x86_64.
- **Capability flags** — key/value fields returned by `sdb capability`/`02-capability.sh` describing what the sdbd build permits (shell, root, app control, file sync).
