# tiz0wn

An evidence-first security research workspace for a personally owned Samsung
Q60T (`GQ55Q60TGUXZG`, firmware `T-NKLDEUC-2743.0`).

<details>
<summary>Status and limitations</summary>

> [!NOTE]
> tiz0wn is an independent exploratory security research project. Developed
> independently alongside my main professional work. The code and write-ups
> are references for investigation and adaptation, rather than a ready-to-use
> rooting product. Recorded results cover one owned Q60T and an exact firmware
> build; sibling-model values and offsets are not interchangeable.
>
> **Disclaimer.** Findings do not guarantee the security, compatibility or
> recoverability of another device. Use only systems you own or are authorized
> to test. Root access and persistent filesystem changes can cause data loss,
> outages or an unusable device; validate the documented gates and recovery
> path before proceeding. You are responsible for any changes you make.

</details>

```mermaid
flowchart LR
    Offline["Offline image analysis"] --> Scope["Exact-build findings and limits"]
    Scope --> Lab["Authorized lab validation"]
    Lab --> Evidence["Evidence and recovery record"]
```

Scope: one device and one exact build. Everything below was measured on that
unit, including the offsets. Sibling models are discussed where the work
overlaps, and their values are theirs, not portable here.

The project began as reversible debloating. Firmware analysis then exposed a
shorter path: Remote PC writes user-controlled SMB credentials, the privileged
CIFS helper substitutes them into a shell command, and the shipped script
executes that command as root. A live validation on 2026-09-27 proved that with
only:

```text
$(/usr/bin/id>/tmp/<fresh-marker>)
```

The follow-up in [`exploits/tiz0wn-root/`](exploits/tiz0wn-root/) took
the same trigger further: one click to a root shell that survives reboots. A
same-size block patch in the read-only rootfs is hash-gated, backed up, written
and re-verified, and a boot hook fires it once per boot. `sdk` was also turned
into a root login. Three full power cycles confirmed the persistence.

The measured password-field characters and limits are in the
[trigger grammar](docs/trigger-grammar.md).

Read [the report](docs/DISCLOSURE.md) for the source trace and the reproduction
notes.
## Current results

| Area | Result |
|---|---|
| Reversible debloating | Inventory and one-change-at-a-time tooling; no bulk uninstall list |
| Firmware analysis | The exact 2743.0 image decrypted and statically examined; no firmware redistributed |
| Remote PC/CIFS | Command injection through the password field, executed as UID 0 |
| One-shot exploit | Complete and live. One trigger writes a same-size block patch in the read-only rootfs, verifies it by re-read, backs up the vendor bytes and installs a root agent |
| Persistence | Proven over three full power cycles; the hook fires once per boot as `uid=0` and restores the agent |
| `sdk` as root login | Done. `sdk` resolves to `uid 0` with `/root` and `/bin/bash` and a password, surviving power cycles, with no mode loosened |
| Root capability | Root over the whole filesystem, block devices, `/proc` and sysctl, but no unsigned binary executes (see below) |

The chain needs one trigger, no USB stick, no kernel exploit, no kernel module
and no UEP patch. The full procedure, measurements and limits are in
[`exploits/tiz0wn-root/LIVE-RUN-2026-10-29.md`](exploits/tiz0wn-root/LIVE-RUN-2026-10-29.md).

UEP is not a privilege boundary. Measured as `uid=0`: a copy of bash on tmpfs is
refused with `EPERM` and `[uep][bash] the file is NOT signed!!`. The verdict is a
signature check bound to the **inode**, not to a path or to the bytes: a
byte-identical copy of a signed binary is refused too. One kernel handler covers
`execve` and `PROT_EXEC` mappings, and the shells gate script *paths* separately
through `libkUEPUser`. Neither half is lifted by privilege, so no unsigned binary
runs and every step is a script invoked by content via `sh -c "$(cat …)"`.
Dropbear, custom tooling as processes and kernel modules are therefore
unavailable even as root.

`make -C exploits/tiz0wn-root check` lints the shell and Python and runs the
loopback rehearsal, without contacting the TV. The ledger and handoff notes are
local-only and untracked; the synthetic tests and security controls are public,
so a clone can run them.

## Three routes, one community effort

Three people reached root on this TV generation within weeks of each other, on
three models, and published what they learned. Nobody started from nothing:
each route borrows a piece the others proved. The routes are complementary
rather than competing: each solves a different problem and each has a weak half
the others do not. Since publication a fourth set joined the effort: on a
Q74T the same CIFS path reached a persistent root agent, and its owner
supplied the two platform gotchas below that matter for anyone building on
this family.

| | [metaljay](https://github.com/metaljay) (Q90T) | [cfloinc](https://github.com/cfloinc/samsung-q70t-tizen-root) (Q70T) | this repo (`GQ55Q60TGUXZG`) |
|---|---|---|---|
| Entry | USB image, via [Luminger/samsung-tv-usb-root](https://github.com/Luminger/samsung-tv-usb-root), after kernel work | exFAT kernel LPE from a USB stick | Remote PC credential sink, network only |
| Privilege step | kernel patch plus per-image addresses | kernel exploit | none; the vendor's own root `bash -c` |
| Persistence | `profile.d` single-block swap | `profile.d` single-block swap | same mechanism, plus a hash-gated whole-window check |
| Rollback | needs the USB stick or the dossier | needs the stick or a second run | another trigger; the backup hashes to the vendor image |
| Reach | physical USB port | physical USB port | the TV's own network, one password field |
| UEP | derived the gates but shipped content-form per hop, since a verifier-entry patch boot-looped | chose the signed-`/bin/bash` variant rather than patch UEP; content-form for the hook | never touched; content-form throughout |

Coverage so far, one verified build per row: offsets are per-image and never
transfer, but the 776-byte carrier is byte-identical on every set, which is
what makes the comparison meaningful. These rows are the working state of
issue #1's *Q-Series Coverage & Affected-Version Matrix* milestone: confirmed
roots per exact build, not a claimed affected range.

| Set (model, build) | Route to root | Persistence offset | Verified on the set |
|---|---|---|---|
| Q60T `GQ55Q60TGUXZG`, `T-NKLDEUC-2743.0` | Remote PC/CIFS credential sink | p19 byte `704753664` | three full power cycles; `sdk` root login |
| Q90T `QE75Q90TATXXU`, `T-NKMDEUC-REL-202607031800` | USB image (Luminger), after two bounded CIFS UID-0 proofs | p18 byte `752541696` (512-block `1469808`) | USB-free boots via boot IDs; set planned back to stock |
| Q70T `QN65Q70TAFXZA`, `T-NKMAKUC-2743.0` | exFAT USB kernel LPE after the SDB foothold | p19 byte `1612972032` (512-block `3150336`) | two power cycles; dropbear root SSH |
| Q74T `QE55Q74TATXZT`, `T-NKMDEUC-2743.0` (Tizen 5.5) | Remote PC/CIFS, via the [vetro remote-pc prototype](https://github.com/andrearicci93/vetro) | derived from its own image | persistence and the agent's loopback channel after the two fixes below |

Read together, the three cover each other's gaps. The USB routes work on a set
with no network path and no Developer Mode. This route works with no stick, no
kernel primitive and no image, but needs the Remote PC feature reachable. The
kernel work documents the UEP gates and how to disable them, which this route
avoids needing. None of the three is a superset, and a reader landing on any of
them should know the others exist.

One difference the Reach row hides: the entry is not the whole surface. cfloinc's
chain ends by firing the kernel stage from a loop device at ~60 s, so UEP is down
at boot and dropbear serves root SSH on `:22` — a booted set is reachable over
the network. On the TV, this route adds no network listener: `cmd/in` is `0777`, so anything
already local at `sdk` can drive root, and nothing else can. Keeping UEP armed is
what that costs; an agent instead of a listener.

What all three converged on, independently, is the persistence primitive: a
776-byte `/etc/profile.d/bash_prompt_custom.sh` replaced in place with a same-size
block write at a per-image offset, backed up byte-exactly, and reached through
`tizen-system-env.service` → `/etc/profile` → `profile.d`. metaljay's Q90T hit is
byte `752541696` on p18, cfloinc's Q70T hit is `1612972032` on p19, and ours is
`704753664` on p19; tenda96 derived the offset from his Q74T's own image and
found the carrier byte-identical again. Four images, four offsets, one method.
The offset is per-image and the method is portable, which is exactly why four
independent derivations are worth more than one.

The sharpest shared finding is that root alone is not enough, because of UEP.
cfloinc lost a day to it: `sh /opt/…/boot.sh` still trips UEP even from a root
shell, so the boot hook silently did nothing, and only `sh -c "$(cat …)"` fixed
it. metaljay needed the verifier gate and the status global (`0xc01de028`,
`0xc069342c`) for the binary path, and reports a boot loop from patching the
verifier entry and an unstable state from zeroing the global, which is why
cfloinc used the signed-`/bin/bash` variant. This repo measured the consequence
directly as `uid=0`: an unsigned ELF on tmpfs returns `EPERM` and `the file is
NOT signed!!`, and a byte-identical copy of a signed binary is refused as well,
which is the evidence for the inode binding. UEP is independent of privilege, so
being root does not let you run a single unsigned binary. No dropbear, no custom
tooling as a process, no kernel modules.

The inode model, and the split between the kernel handler (`execve`,
`PROT_EXEC`) and the user-space shell gate for script paths, are txtsamu's T6500
correction. cfloinc flags them as such and marks his own Q70T controls for the
shell layer as still queued, so the two are kept apart here as well.

The Q74T cross-check adds two gotchas for anyone building a longer-lived
channel on this family. First, the content rule runs recursively: a hook that
arrives by content but starts a second, longer-lived helper *by path*
(`setsid /path/helper &`) has that second `execve` silently refused — the
parent runs on and `$!` still reports a plausible PID, but the helper dies
immediately after the single refusal, with no other symptom. The fix is the
same principle one level deeper, `setsid sh -c "$(cat /path/helper)" args &`;
a side effect is that `pgrep -f` stops matching, so a PID file is the
reliable liveness test. This chain already follows both: every hop is
content, and the agent's single-instance check is a PID file. Second, a
separate, non-UEP wall: SMACK denied a `_`-labelled root agent's own loopback
`connect()` to a socket labelled for an installed app
(`subject="_"` against `User::Pkg::<appid>`, requested `w`). `uid=0` does not
grant an implicit pass to app-labelled sockets; the fix is to load explicit
rules both ways through `/sys/fs/smackfs/load2` first, reading the app label
from `/proc/self/attr/current` rather than hardcoding it.

That is why this chain keeps UEP armed end to end and pays for it only in style:
every step is a script invoked by content. Where UEP is disabled, the kernel work
above already documents how, and its symbols are the reference for the family.

## Attribution

These routes are one effort, and the sections below are theirs to write.
Thanks to all three, and to everyone in issue #1 who tested, corrected and
cross-checked:

- [metaljay](https://github.com/metaljay), first public root on this generation;
  the Q90T `profile.d` offset and the reusable shape of the method (same-size
  swap, byte-exact backup, one-command rollback); the kernel symbol table; the
  correction that `kill -47` is halt rather than reboot; and the correction that
  the REL build stamp, not the `2743.0` string, is the firm identifier. Also
  reviewed the compatibility wording.
- [cfloinc](https://github.com/cfloinc/samsung-q70t-tizen-root), the Q70T writeup
  and `persistent-hook/` kit (MIT); the UEP file-loading finding that `sh -c
  "$(cat …)"` exists to defeat; the independent cross-check of the NIKEM kernel
  symbol table from the Q70T kernel via the SWU TrustZone TA; the negative
  result that archive-root is impossible without `/usr/bin/dotnet`; and the
  attribution that keeps the per-inode UEP model with txtsamu rather than
  folding it into the Q70T work.
- [tenda96](https://github.com/tenda96), the fourth NIKEM-family cross-check on
  a Q74T (`QE55Q74TATXZT`): the carrier byte-identity confirmed on a fourth set
  with the offset derived from his own image; the finding that the
  content-invocation rule applies recursively, so a helper started by path from
  a content-invoked hook is silently refused by UEP; and the finding that a
  `_`-labelled root agent is denied loopback TCP to app-labelled sockets unless
  explicit SMACK `load2` rules are loaded both ways. Both findings stand behind
  the persistent root agent on the [vetro remote-pc prototype](https://github.com/andrearicci93/vetro)
  on that set.

`NOTICE.md` keeps the used-versus-investigated distinction and the licenses.
Where a technique here is theirs, the credit sits on the technique rather than
only in this section.

The sections below are for the people who did the work. cfloinc offered to write
his rather than be paraphrased (issue #1, 29 October) and his text is
reproduced verbatim. metaljay offered the same, and his section is summarised
from his issue #1 reports (13, 20, 21 and 28 October) until his own text
arrives; it is meant to be replaced, not amended. tenda96's section is likewise
summarised from his 2 November comment.

## From cfloinc (Q70T)
As sent in [issue #1](https://github.com/sebastianspicker/tiz0wn/issues/1#issuecomment-6504466699)
on 29 October:

> **QN65Q70TAFXZA (2020 Q70T, NIKEM, Tizen 6.0, kernel 4.1.10, `T-NKMAKUC-2743.0`).** No `/usr/bin/dotnet` host, so archive-root is not applicable; root came from the exFAT USB kernel LPE after the SDB foothold, then a 776-byte in-place `profile.d` patch (same-size replacement, per-image block offset) made it stick. Every hop passes script content (`sh -c "$(cat …)"`) because UEP gates script file loading; the boot hook runs at ~0.73 s, applies 13 runtime masks, fires UEP down from a loop device at ~60 s, and starts dropbear root SSH. Details: https://github.com/cfloinc/samsung-q70t-tizen-root

What is not transferable to the Q60T, in his own terms and confirmed here: the
offset (`1612972032` on p19 there, `704753664` on p19 here) and the dotnet host
question. What carried over is the content form and the block surgery, both used
in this chain. The loop-device UEP-down half did not carry over: on the Q60T UEP
stays armed and the reach is local, not `:22`.

## From metaljay (Q90T)

> _Summarised from his [issue #1](https://github.com/sebastianspicker/tiz0wn/issues/1)
> reports; intended to be replaced by his own text if and when he sends it._

**QE75Q90TATXXU (2020 Q90T, NIKEM, Tizen 5.5, ARMv7, kernel 4.1.10, build stamp
`T-NKMDEUC-REL-202607031800`).** The CIFS route held first: five relevant
Remote PC / privileged-service files matched the Q60T reference hashes, and a
manually adapted harness produced two independent one-shot UID-0 marker proofs
— bounded command execution only, no shell and no persistence, and not the
route his final root used. That came from adapting
[Luminger/samsung-tv-usb-root](https://github.com/Luminger/samsung-tv-usb-root)
from its 2019 Muse.M target to this 2020 NikeM set: root from a USB image, then
boot persistence without the stick through a single-block swap of the
root-sourced `profile.d` carrier (p18, byte `752541696` = 512-block
`1469808`; the remaining 264 file bytes in the next block stay untouched) with
a maintenance chain under `/opt`. USB-free reboots were confirmed through
changed boot IDs and boot-chain logs; maintenance is authenticated and
outbound-only through a manually started Mac endpoint; the root console is
line-oriented — a fresh subshell per command, not a PTY. Developer Mode is off
and the set does not need a Pi. Recovery, should it ever be needed, requires
the set to boot far enough to mount a USB device.

For the UEP-disabled half he recovered the kernel symbols from the image:
`call_usermodehelper` `0xc003b87c`, `memcpy` `0xc020b120`, the
`ldm ip,{r2,r3,r4,r7,r8,r9,sl,sp,lr,pc}` landing pad `0xc05455bc`, the UEP
verifier gate `0xc01de028`, the status global `0xc069342c`, and the unreferenced
cave `0xc0008358..0xc0009000` with copy destination `0xc00083d8`. Patching the
verifier entry boot-looped the set, and zeroing the status global allowed
unsigned binaries but left the state unstable — which is why he shipped
content-form per hop. cfloinc independently derived the same six values from
his Q70T kernel through the SWU TrustZone TA and every shared value matched,
which supports calling the table NIKEM-family; the chain itself remains
verified on one set, and that limit stands.

His MSD container parses (`MSDU11`, header `T-NKMDEUC`) but none of the ten
candidate keys yields a valid decrypted header, and SDB refuses to pull the
SWU passphrase file even though the SDK diagnostic proves it is readable — so
the TEE passphrase route is the open item on his set. He plans to return the
TV to stock (debloat retained, maintenance channel removed), so no fresh live
testing is available from it.

## From tenda96 (Q74T)

> _Summarised from his [issue #1 comment](https://github.com/sebastianspicker/tiz0wn/issues/1#issuecomment-6590976026)
> of 2 November._

**QE55Q74TATXZT (`20_NIKEM_QTV`, Tizen 5.5, `T-NKMDEUC-2743.0`)** — a fourth
NIKEM-family set. The 776-byte `bash_prompt_custom.sh` carrier hashes
identically again, with the offset derived independently from this image.
Two platform gotchas, each confirmed over real power cycles, that shaped the
persistent root agent from the [vetro remote-pc prototype](https://github.com/andrearicci93/vetro)
on that set (whose own branch had already reached a working root agent through
the same credential-injection path):

1. The content-invocation rule is recursive. A boot hook that arrives by
   content but starts a second, longer-lived helper by path
   (`setsid /path/helper &`) has that launch silently rejected by UEP: the
   parent runs on, `$!` still gives a plausible PID, and nothing looks wrong
   until the helper's stderr is pointed at a file instead of `/dev/null` — it
   dies immediately after the one refused `execve`. The fix is content one
   level deeper, `setsid sh -c "$(cat /path/helper)" name arg1 arg2 &`
   (positional args pass through), with the side effect that a path-based
   liveness check (`pgrep -f`) no longer matches, so a PID file is the
   reliable test.
2. SMACK is a separate wall, not UEP: the root agent's own loopback
   `connect()` to a specific app's socket was denied
   (`lsm=SMACK fn=smack_socket_sock_rcv_skb`, `subject="_"` against
   `object="User::Pkg::<appid>"`, requested `w`, on `lo`). The usual "I'm
   root, SMACK doesn't apply to me" assumption does not hold for
   app-labelled sockets on this platform's SMACK build. Root can still fix
   it for itself: load explicit rules both ways through
   `/sys/fs/smackfs/load2`, with the real app label read from
   `/proc/self/attr/current` rather than hardcoded.

## Running it

`make -C exploits/tiz0wn-root check` lints the shell and Python and runs the
loopback rehearsal on a block file. Nothing contacts the TV.

A run follows `plan` → `build-run` → `check` offline, then `serve` on a specific
private IPv4 address and a port from 1 to 65535. The account is off by default;
enabling it requires `--account` together with `--password`. The
[runbook](exploits/tiz0wn-root/README.md#using-it-offline) has the commands and
the verified rollback path for a live trigger.

A live run needs the offset from your own image and one Remote PC trigger. The
procedure, gates and limits are in
[`LIVE-RUN-2026-10-29.md`](exploits/tiz0wn-root/LIVE-RUN-2026-10-29.md). Do not
use it on a device you do not own, and do not expose RDP, SMB, SDB or the
TV-control port to the Internet.

## Repository map

| Path | Purpose |
|---|---|
| [`exploits/tiz0wn-root/`](exploits/tiz0wn-root/) | The chain: builder, payloads, session tooling |
| [`exploits/tiz0wn-root/LIVE-RUN-2026-10-29.md`](exploits/tiz0wn-root/LIVE-RUN-2026-10-29.md) | The live session: offset derivation, trigger, verification, boot proofs |
| [`exploits/tiz0wn-root/builder/accounts.py`](exploits/tiz0wn-root/builder/accounts.py) | The `sdk` and `shadow` patch: builder and gates |
| [`exploits/tiz0wn-root/payload/rootlogin`](exploits/tiz0wn-root/payload/rootlogin) | The same patch as a device script |
| [`exploits/tiz0wn-root/HANDOFF-SAMSUNG.md`](exploits/tiz0wn-root/HANDOFF-SAMSUNG.md) | Vendor-facing summary |
| [`docs/DISCLOSURE.md`](docs/DISCLOSURE.md) | The vulnerability report, timeline and fix guidance |
| [`docs/firmware-analysis.md`](docs/firmware-analysis.md) | The image analysis the offset comes from |
| [`docs/trigger-grammar.md`](docs/trigger-grammar.md) | The measured password-field character classes, proven and rejected |
| [`docs/privileged-services.md`](docs/privileged-services.md) | The privileged-service inventory: shell-argv versus argv-direct sinks |
| [`docs/testing.md`](docs/testing.md) | What the public suites cover, what stays local |
| [`SECURITY.md`](SECURITY.md) | Reporting, what is public, how to run it safely |

## Safety and scope

- Own device, trusted local network, explicit target only.
- Measure first; make one reversible change at a time.
- Treat IP addresses, DUID/device IDs, tokens, and raw evidence as private.
- Never infer a firmware range from one verified build.
- Do not confuse the disposable RDP host's `q60t` account with the TV's `sdk`.
- Nothing is written before the window hash matches, and the backup is verified
  before it is needed.

## License

MIT; see [`LICENSE`](LICENSE). Firmware and third-party tools are not
redistributed. Their attribution and licensing are described in
[`NOTICE.md`](NOTICE.md).

## Tooling security checks

GitHub runs synthetic offline security controls; CodeQL default setup is
configured for Python. General shell/Python lint runs manually or for
Dependabot-authored pull requests. The workflow never contacts a TV,
starts a delivery server on the LAN, deploys a payload or publishes a release.
Action versions are tracked by Dependabot. Detailed field suites and device
evidence remain local.

Generated shadow-table windows and baked setup/resume scripts are atomically
written with owner-only permissions. The optional host callback receiver now
binds the explicit `HOST_IP`, accepts only the configured `TV_HOST` source IPv4,
and limits a response to 16 MiB, 10 seconds of idle time and 35 seconds total
(including at most 25 seconds waiting for the peer). It publishes only complete
output, mode 0600. Wrong-peer, oversized and timed-out callbacks leave existing
output unchanged. The `q.sh` caller passes these addresses explicitly and stops
if its receiver fails.

The address filter is not cryptographic authentication; base64 is not encryption.
Use an isolated, trusted lab network. These limits are not evidence of broader
model or firmware compatibility, and no live target was used by the CI checks.
