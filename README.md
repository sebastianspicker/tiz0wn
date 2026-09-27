# tiz0wn

An evidence-first security research workspace for a personally owned Samsung
GQ55Q60TGUXZG television running `T-NKLDEUC-2743.0`.

This began as a reversible debloating project. Firmware analysis eventually
exposed a much shorter path: Remote PC writes user-controlled SMB credentials,
the privileged CIFS helper substitutes them into a shell command, and the
shipped script executes that command as root. A bounded live validation on
2026-09-27 proved that path with only:

```text
$(/usr/bin/id>/tmp/<fresh-marker>)
```

A fresh two-push classifier proved that the resulting regular file was owned
by UID 0 and began with `uid=0(root) gid=0(root)`. This is a root-command proof,
not persistence, a root shell, a firmware modification, or a claim about
firmware versions other than the exact assessed build.

Read [From debloating to tiz0wn](docs/from-debloating-to-tiz0wn.md) for the
project story and
[the Remote PC/CIFS research](research/remotepc-cifs-root/README.md) for the
source trace, offline harness, and guarded reproduction contract.

## Current results

| Area | Result |
|---|---|
| Reversible debloating | Inventory and one-change-at-a-time tooling; no bulk uninstall list |
| Firmware analysis | Exact 2743.0 image decrypted and statically examined; proprietary firmware is not redistributed |
| Remote PC/CIFS | Command injection through the password field demonstrated as UID 0 on the assessed TV |
| One-shot harness | Offline audit and loopback RDP/SMB lab complete; the fresh harness has not been run live |
| Mali CVE-2022-46395 route | Target-specific research remains separate and inconclusive; no Mali root claim |

## Safe local checks

The Remote PC harness is offline by default. Its default command reads only the
local rootfs tar and does not load TV configuration, open a socket, invoke SDB,
or start Docker:

```bash
make -C research/remotepc-cifs-root dry-run
make -C research/remotepc-cifs-root test
make -C research/remotepc-cifs-root lab-test  # services bind to 127.0.0.1
```

The Docker build can download its pinned Debian base and Python dependency. A
fresh build from a frozen, allowlisted source snapshot is mandatory for each
run; the harness verifies source stability around the build, captures its
immutable image ID, checks the embedded snapshot digest, and runs that exact
ID. All lab service and self-test traffic is confined to the Mac. Neither local
mode contacts the TV.

Live mode is deliberately separate. It requires exact target identity and
firmware gates, three authorization phrases, an interactive terminal, two
visual form/session confirmations, one manual Shared Folder click, and one
non-retriable classification. Do not use it on a device you do not own and do
not expose RDP, SMB, SDB, or TV-control ports to the Internet.

## Repository map

| Path | Purpose |
|---|---|
| [`research/remotepc-cifs-root/`](research/remotepc-cifs-root/) | Validated Remote PC/CIFS finding and offline-first one-shot harness |
| [`docs/firmware-analysis.md`](docs/firmware-analysis.md) | Exact firmware extraction and static-analysis findings |
| [`research/mali-cve-2022-46395/`](research/mali-cve-2022-46395/) | Separate, firmware-bound Mali research and offline tests |
| [`scripts/`](scripts/) | Explicit-target SDB inventory and one-package removal workflow |
| [`templates/`](templates/) | Baseline, rollback, compatibility, and change records |
| [`evidence/`](evidence/) | Private run output; identifying evidence is gitignored |

The original research plan remains available at
[`docs/Samsung_Q60T_Debloating_Research_2026-09-25.md`](docs/Samsung_Q60T_Debloating_Research_2026-09-25.md).
Statements in dated checkpoints describe what was known at that time; the
table above is the current project status.

## Safety and scope

- Own device, trusted local network, explicit target only.
- Measure first; make one reversible change at a time.
- Treat IP addresses, DUID/device IDs, tokens, and raw evidence as private.
- Never infer a firmware range from one verified build.
- Do not confuse the disposable RDP host's `q60t` terminal with a TV shell.
- The proof harness leaves target markers and terminal evidence untouched; TV
  profile and allowed-device cleanup are manual and separately documented.

## License

MIT; see [`LICENSE`](LICENSE). Firmware and third-party tools are not
redistributed. Their attribution and licensing are described in
[`NOTICE.md`](NOTICE.md).
