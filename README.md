# tiz0wn

An evidence-first security research workspace for a personally owned Samsung
Q60T (`GQ55Q60TGUXZG`, firmware `T-NKLDEUC-2743.0`).

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
loopback rehearsal, without contacting the TV. The test suites, ledger and
handoff notes are local-only and untracked, so a clone gets the tooling and the
documentation rather than the bookkeeping.

## Three routes, one community effort

Three people reached root on this TV generation within weeks of each other, on
three models, and published what they learned. Nobody started from nothing:
each route borrows a piece the others proved. The routes are complementary
rather than competing: each solves a different problem and each has a weak half
the others do not.

| | [metaljay](https://github.com/metaljay) (Q90T) | [cfloinc](https://github.com/cfloinc/samsung-q70t-tizen-root) (Q70T) | this repo (`GQ55Q60TGUXZG`) |
|---|---|---|---|
| Entry | USB image, via [Luminger/samsung-tv-usb-root](https://github.com/Luminger/samsung-tv-usb-root), after kernel work | exFAT kernel LPE from a USB stick | Remote PC credential sink, network only |
| Privilege step | kernel patch plus per-image addresses | kernel exploit | none; the vendor's own root `bash -c` |
| Persistence | `profile.d` single-block swap | `profile.d` single-block swap | same mechanism, plus a hash-gated whole-window check |
| Rollback | needs the USB stick or the dossier | needs the stick or a second run | another trigger; the backup hashes to the vendor image |
| Reach | physical USB port | physical USB port | the TV's own network, one password field |
| UEP | derived the gates but shipped content-form per hop, since a verifier-entry patch boot-looped | chose the signed-`/bin/bash` variant rather than patch UEP; content-form for the hook | never touched; content-form throughout |

Read together, the three cover each other's gaps. The USB routes work on a set
with no network path and no Developer Mode. This route works with no stick, no
kernel primitive and no image, but needs the Remote PC feature reachable. The
kernel work documents the UEP gates and how to disable them, which this route
avoids needing. None of the three is a superset, and a reader landing on any of
them should know the others exist.

One difference the Reach row hides: the entry is not the whole surface. cfloinc's
chain ends by firing the kernel stage from a loop device at ~60 s, so UEP is down
at boot and dropbear serves root SSH on `:22` — a booted set is reachable over
the network. This route has no listener at all: `cmd/in` is `0777`, so anything
already local at `sdk` can drive root, and nothing else can. Keeping UEP armed is
what that costs; an agent instead of a listener.

What all three converged on, independently, is the persistence primitive: a
776-byte `/etc/profile.d/bash_prompt_custom.sh` replaced in place with a same-size
block write at a per-image offset, backed up byte-exactly, and reached through
`tizen-system-env.service` → `/etc/profile` → `profile.d`. metaljay's Q90T hit is
byte `752541696` on p18, cfloinc's Q70T hit is `1612972032` on p19, and ours is
`704753664` on p19. Three images, three offsets, one method. The offset is
per-image and the method is portable, which is exactly why three independent
derivations are worth more than one.

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

That is why this chain keeps UEP armed end to end and pays for it only in style:
every step is a script invoked by content. Where UEP is disabled, the kernel work
above already documents how, and its symbols are the reference for the family.

## Attribution

These three routes are one effort, and the sections below are theirs to write.
Thanks to both, and to everyone in issue #1 who tested, corrected and
cross-checked:

- [metaljay](https://github.com/metaljay), first public root on this generation;
  the Q90T `profile.d` offset and the reusable shape of the method (same-size
  swap, byte-exact backup, one-command rollback); the kernel symbol table; the
  correction that `kill -47` is halt rather than reboot; and the correction that
  the REL build stamp, not the `2743.0` string, is the firm identifier. Also
  reviewed the compatibility wording.
- [cfloinc](https://github.com/cfloinc/samsung-q70t-tizen-root), the Q70T writeup
  and `persistent-hook/` kit (MIT); the UEP file-loading finding that `sh -c
  "$(cat …)"` exists to defeat; the negative result that archive-root is
  impossible without `/usr/bin/dotnet`; and the attribution that keeps the
  per-inode UEP model with txtsamu rather than folding it into the Q70T work.

`NOTICE.md` keeps the used-versus-investigated distinction and the licenses.
Where a technique here is theirs, the credit sits on the technique rather than
only in this section.

Two sections below are for cfloinc and metaljay. Both offered to write or review
a short section for this README rather than be paraphrased (issue #1, 28 and 29
October). cfloinc's text arrived on 29 October and is reproduced verbatim;
metaljay's section stays empty until his does.

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

> _reserved_

## Running it

`make -C exploits/tiz0wn-root check` lints the shell and Python and runs the
loopback rehearsal on a block file. Nothing contacts the TV.

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
