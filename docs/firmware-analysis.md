# Firmware static analysis — T-NKLDEUC 2743.0 (GQ55Q60TGUXZG)

Offline analysis of the firmware image for model **GQ55Q60TGUXZG**, firmware
**T-NKLDEUC-2743.0**, followed by bounded live checks against the owner's TV.
The host-side work follows research doc
[§11](Samsung_Q60T_Debloating_Research_2026-09-25.md#11-a-firmware-specific-reverse-engineering-plan).
Live checks used Developer Mode SDB, made no firmware or partition changes,
and are identified explicitly in F13-F15.

This is a public-facing summary: it contains the model string, build/version
identifiers and public URLs/hashes only. It intentionally omits any
device-private identifier (TV serial, IP, MAC, DUID) — those never appear in
firmware artifacts anyway, but the raw working notes this doc is condensed
from (`evidence/fw-analysis/`, `evidence/root-feasibility-2026-09-26.md`) are
private working files and are not tracked in this repository.

## Summary

- **Developer Mode command execution is confirmed on 2743.0.** A live
  SVE-2025-50109 timing probe and callback both succeeded, yielding a shell as
  `uid=901(sdk)` with SMACK label `System`. This is useful diagnostic access,
  but it is not root (F13).
- **Root and factory-app removal are not yet achieved.** `sdb uninstall` and
  `vd_appuninstall` were both empirically observed to
  return exit code 0 while leaving the live application list completely
  unchanged (see `scripts/05-remove-apps.sh` and
  `evidence/root-feasibility-2026-09-26.md`) — a refusal, not a success.
- The firmware container's AES key has **not been rotated** since 2021: a
  five-year-old, publicly known passphrase still decrypts the current 2026
  image. That is a confidentiality finding only — it does not grant root or
  let you forge a bootable modified image (every section still carries an
  independent signature).
- The kernel is Linux 4.1.10 (ARM), built 2026-07-02.
- The extracted base rootfs appeared to block the public SVE-2025-50109
  payload, yet the exact payload works on the live TV. This static/runtime
  discrepancy is unresolved; the live timing and callback evidence controls
  the access conclusion (F13).
- The TV uses a **Mali-G51 Bifrost r11p0** GPU driver. `/dev/mali0` is mode
  `0666`, SMACK `*`, and can be opened read/write by the live `sdk` shell.
  Exact-module disassembly retains the pre-fix JIT mapping/write pattern for
  CVE-2021-44828 and the import/sticky-unmap race behind CVE-2022-46395. The
  latter is the stronger public-chain match. A bounded CVE-2021-44828
  permission-check validator and a Q60T-specific CVE-2022-46395 reclaim-only
  probe are implemented and tested offline. Both the 44828 direct-loader
  self-test and a target-bound, package-manager-installed WGT attempt were
  blocked by `failed to map segment` before `main`. No JIT soft job from that
  validator has run on the TV. Two distinct managed validator transports also
  stopped at their device-free proof gates. The separately armed 46395 final
  credential transport installed and attested successfully but likewise
  stopped at its device-free proof gate before the active launch. No race, GPU
  page-table write, credential write, or root transition ran on the TV (F14).
- The historical Q60T root primitive — an arbitrary physical-memory mapping
  driver (`sdp_mem`, later `sdp_hwmem`) — is **hardened** on this build: a
  whitelist-containment check plus an explicit kernel-region-intersection
  reject close the primitive at the driver level (code-level confirmation,
  not just strings). Full rootfs extraction later confirms the same
  conclusion at the userspace layer: no udev rule grants the `sdp_hwmem`
  device node permissive access either (F12).

## Findings

F1-F12 are condensed from `evidence/fw-analysis/FINDINGS.md` (private offline
working notes). F13-F15 add live evidence recorded on 2026-09-26. Confidence
levels are called out explicitly below rather than left implicit.

**F1 — Provenance. Confidence: first-hand, verified.** Image obtained from
the official Samsung CDN, resolved from the GQ55Q60TGUXZG support page:
`downloadcenter.samsung.com/content/FM/202609/20260915171117277/T-NKLDEUC.zip`,
1,349,064,478 bytes, sha256 `cb717ed98daf9580eb5b84bccbad5adac82f75dd021ed028f1ee1bb6c4abde32`.
Full chain of custody in `evidence/fw-analysis/PROVENANCE.md`.

**F2 — Container. Confidence: first-hand, high.** A stored (uncompressed)
zip containing `image/info.txt` (435 bytes) and `image/upgrade.msd` (1.35 GB);
no path traversal. `info.txt` declares model `T-NKLDEUC`, version `2743.0`,
build `2026-07-02`, release `SWU-OU_T-NKLDEUC-02743-2026-07-02-Release`, key
type "REL key of NikeL". `upgrade.msd`'s magic is `MSDU11`, matching the
container format documented by Synacktiv's `firmware/decrypt.py`.

**F3 — Firmware AES key NOT rotated (major finding). Confidence: first-hand,
high.** Synacktiv's 2021 hardcoded passphrase (originally extracted from a
2201.0 NKLAKUC image) still decrypts this 2026 NikeL-REL image, deriving
`aes_key = 5bab1098dab48792619ebd63650d929f`. Confirmed genuine, not
coincidental: the decrypted header parses into valid TLV descriptors, the
embedded `SecureDowngrade` `ImageGenerationdata` matches the build date
(02/07/2026), and real filenames appear. Samsung has not rotated the
firmware AES key or changed the MSDU container format in roughly five years —
anyone can read this (and presumably future NikeL) firmware offline. This is
a **confidentiality** finding only: it is not root, and not a signing break
(every item still carries a per-item RSA signature — see F5).

**F4 — Decrypted sections (9). Confidence: first-hand, high.** `ddr.init`
(DDR init blob); `seret.bin` (secure/boot-related ARM code); `uImage` — a
u-boot uImage containing an uncompressed **Linux 4.1.10 ARM kernel**;
`dtb.bin` (Device Tree Blob v17); `sign.bin` (1040-byte signature blob);
`secos.bin` / `secos_drv.bin` (secure OS / secure-OS driver, TrustZone);
`platform.img` — **VDFS** ("VDFS2007"), zlib-compressed, read-only, 1.33 GB
main rootfs; `factory_peq.img` — Squashfs v4, zlib (audio calibration).

**F5 — Kernel. Confidence: first-hand, high.** `Linux version 4.1.10
(abuild@B4404DRG) gcc 6.2.1 Tizen/Linaro ... #1 SMP PREEMPT Thu Jul 2
08:47:01 UTC 2026`. UEP (unsigned-execution protection) strings are present,
a boundary distinct from UID0 (research doc §5.2). Every section carries a
per-item `OURSAValidationDesc` with a public-key id (`0x19fc36c9`), so
authenticity is checked independently of the (broken) encryption — reading
the firmware does not let you forge a bootable modified image. Three
separate questions: *can it be read, can a modified package be
authenticated, will it boot* — see research doc §11.3.

**F6/F7 — The open question, answered: `sdp_hwmem` is present but closed at
driver level. Confidence: medium-high, code-level (disassembly, not just
strings).** The historical `sdp_mem` primitive (renamed `sdp_hwmem`) still
exists in the 2743 kernel, but disassembly of its mmap path (source path
string `drivers/soc/sdp/sdp_hwmem.c`) shows two checks:

1. **Whitelist containment** (`check_mmap_area_is_valid`): a binary search
   over a sorted table of `(base, size, flags)` entries; a requested range
   must be fully contained in a whitelisted region or the call fails with
   `-EFAULT` ("check_mmap_area_is_valid failed!"). The whitelist is populated
   at driver init from a fixed table of device-memory regions (fb/codec/etc.)
   — not attacker-controlled.
2. **Kernel-region intersection reject**: an explicit check —
   `"sdp_hwmem: phys region intersects with kernel region, phys %pa++%zx"` —
   refuses to map any physical range overlapping kernel memory, directly
   blocking the historical technique (map kernel phys → patch cred → root).

Conclusion (confidence medium-high, code-level not just strings): the
arbitrary physical-memory mapping primitive that rooted the 2018-era Q60T is
**closed** on 2743.0, consistent with Samsung's Aug-2021 bulletin
(SVE-2021-50050/50051). A bypass would require a flaw in these checks
themselves (e.g. an integer overflow in the base+size end computation, or a
whitelisted region that itself overlaps sensitive memory) — that would be
**original vulnerability research, not a known route** (confidence for that
possibility: unproven). No alternative world-writable physical-memory device
(`/dev/ntksys`, `sdp_pqe_fdet`, an open `/dev/mem`/`/dev/kmem`) was found in
the kernel strings.

**F8/F9 — VDFS rootfs (`platform.img`): not encrypted, needs a VDFS4 reader.
Confidence: first-hand, high.** The embedded `mkfs.vdfs` invocation (`-i -h
sha256 -V -s <product.key> -z .. -c zlib --read-only`) has no
`--aes-key`/`--encrypt-*` option: content is zlib-compressed and
SHA-256/RSA-signed for integrity only, not encrypted — no key is needed to
read it. Catalog metadata carved via `strings` alone (before full
extraction) already showed the standard kernel-module set (`ext4`, `cifs`,
`ecryptfs`, `dm-crypt`, `exfat`, `btusb`, `ax88179`/`asix`, plus Samsung
`acmd.ko`/`acmd_sec.ko`) and confirmed device nodes are created at runtime by
`systemd-udevd` + `ps_mknod.service` from udev rules whose content lives in
compressed extents (not visible from carving alone). Node permissions
turned out to be moot for the root question regardless — F7's driver-level
checks close the primitive independent of who can open the node; F12 later
confirms the same picture once the udev rules themselves become readable.

**F10/F11 — VDFS4 extraction: layout "2007" vs "2006", resolved. Confidence:
first-hand, high (build reproduced, superblock CRC32-validated).** The
volume signature is `VDFS4_VOLUME 1.43-191204`; the on-disk superblock
declares layout version **"2007"**. The publicly available `unpack.vdfs`
build (HinTak/vdfs-tools, the Samsung `0010` tarball) only accepts layout
`"2006"` and refuses to mount `"2007"` images outright. Relaxing that version
gate to also accept `"2007"` let the tool's own superblock CRC32 check pass —
which *validates*, rather than assumes, that the 2006 on-disk superblock
struct still matches this 2007 image. With that one-line gate change, the
full directory tree (21,998 directories: `boot`, `core`, `dev`, `etc`, `opt`,
`plugins`, `usr`, `var`, `mnt`, `run`, ...) extracted successfully. Per-file
*compressed* content, however, uses a newer descriptor layout —
`VDFS4_COMPR_LAYOUT_VER_06` — that the `0010` tree's decoder does not
understand: layout v6's `struct vdfs4_comp_file_descr` prepends
`reserved[7]` and a `sign_type` field ahead of the record and replaces the
v5 trailing padding with an `aes_nonce[8]`, shifting every offset after it.
That decoder exists in the upstream `HinTak/vdfs-tools` history (the
`read_descriptor_info` implementation added in commit `b87531e`), but that
newer `unpack.c` sits on top of an incompatible older library tree and would
need to be ported, not just enabled — see F12 for the completed port and the
resulting full extraction.

**F12 — Full rootfs extraction and device-node permissions. Confidence:
first-hand, high.** The v6 compressed-descriptor decoder identified in
F10/F11 was ported into the `0010` tree, and the full rootfs then extracted
and decompressed cleanly: **44,530 files / 21,998 directories**, content
verified as plaintext (not just decompressed-looking) by direct inspection
of extracted files. With the rootfs readable, the udev rules that create
device nodes at boot (referenced but opaque in F8/F9) are now inspectable
directly, closing that open item:

- `/dev/mem`, `/dev/kmem` and `/dev/port` are created `GROUP=kmem MODE=0640`
  — not world-writable.
- **No udev rule grants a permissive mode to `sdp_hwmem`/`hwmem`** — the
  physmem character device is not exposed with permissive userspace
  permissions either.

This does not change the root verdict: F7's rejection of arbitrary/
kernel-overlapping physical-memory mapping operates at the kernel-driver
level regardless of who can open the device node. F12 corroborates that
conclusion at the userspace layer — it closes a previously open item (device
node permissions), it does not reopen the question.

**F13 — SVE-2025-50109 gives a live `sdk` shell on 2743.0. Confidence: high
(two independent live checks).** The earlier research correctly identified
SVE-2025-50109 as a possible initial foothold, but its statement that no
public proof of concept existed is now stale. The actively maintained
[`chris-ritsen/samsung-tv-root`](https://github.com/chris-ritsen/samsung-tv-root)
project includes a generic implementation of the published SDB package-name
injection. Its QN90B/QN90F root stages remain hardware-specific and were not
used on this Q60T.

Two bounded checks confirmed command execution on the exact TV and firmware:

1. A control package name completed in 0.107 seconds; an otherwise identical
   injected delay completed in 4.090 seconds, a 3.983-second separation.
2. A separate callback connected from the TV and reported `uid=901(sdk)`,
   `gid=901(sdk)`, SMACK context `System`, kernel 4.1.10 ARMv7, and the
   supplementary groups `audio`, `video`, `display`, `input`, `system_share`,
   plus several privilege groups. `CapPrm` and `CapEff` were both zero.

The shell subsequently read the Smart Hub application database, inspected
process and service state, and opened `/dev/mali0` read/write. Normal `sdb
shell` remains disabled; the foothold is the package-name injection path.

The extracted 2743.0 base rootfs contains the corresponding path in
`/usr/lib/libsdbd_plugin.so` (`sdbd-plugin-3.8.0`): the `appinstall` handler
formats `/usr/bin/wascmd -i %s -p /home/owner/share/tmp/sdk_tools/%s -G`.
Static inspection found `_verify_shell_cmd` rejecting backticks, `$`, pipes
and redirection and an `is_debug()` implementation that returns false. That
would appear to reject the public payload. The live result proves this static
model is incomplete: the running system may use an overlay or a different
dispatch path, or the call flow may have been interpreted incorrectly. No
specific explanation has been established, so the discrepancy is recorded
rather than resolved by assumption.

**F14 — Reachable Mali-G51 r11p0 driver retains two known vulnerable paths.
Confidence: high for identity, reachability, and exact disassembly matches;
unproven for a successful CVE-2021-44828 trigger, CVE-2022-46395 race, or
root.** The extracted `sdp_gpu.ko` identifies as Mali-G51 Bifrost
`r11p0-01rel0 (UK version 11.6)`. Its udev rule creates `mali*` mode `0666`
with SMACK label `*`; live inspection confirmed `/dev/mali0` has those
attributes, and an `sdk` process opened it read/write.

Disassembly of `kbase_jit_allocate_process` shows it calling `kbase_vmap`,
then writing through the returned pointer. `kbase_vmap` calls
`kbase_vmap_prot` with protection argument zero. Google Project Zero's
[CVE-2021-44828 analysis](https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2021/CVE-2021-39793.html)
identifies that exact JIT call/write pattern and says the fix replaces
`kbase_vmap()` with `kbase_vmap_prot(..., KBASE_REG_CPU_WR)`. The module
therefore visibly retains the pre-fix pattern despite its 2026 firmware build.

A separate bounded validator in
[`research/mali-cve-2021-44828/`](../research/mali-cve-2021-44828/) exercises
only that permission decision. It first requires a writable JIT-result positive
control, then repeats the soft JIT allocation with a fresh result page that has
`CPU_RD|GPU_RD` but deliberately lacks `CPU_WR`. It contains no GPU instruction
descriptor, race, reclaim, physical scan, PTE operation, credential write, or
root payload. An aligned nonzero driver write after the no-`CPU_WR` request is
the positive result; an unchanged word plus the exact `JOB_INVALID` event is
reported only as `not_observed`; every other result is inconclusive.

The validator's current evidence boundary is important:

- Native and managed implementations agree on the recovered UK 11.6 ioctl,
  atom, JIT record, and event layouts and pass deterministic offline tests.
- Live guards have matched the exact kernel string, `sdp_gpu.ko`, `libmali.so`,
  firmware launcher, device type, Developer Mode identity, and SDB serial.
- One authorized invocation of the pinned dynamic ARM ELF through the exact
  system loader failed with `failed to map segment` before `main()`. The
  `sdk_tools` stage is consumed, retained, and disabled as a live route. It was
  never invoked in a Mali mode.
- Samsung TVs do not support the investigated native `.tpk` alternative. A
  Web `.wgt` transport carried the exact pinned ELF into internal application
  storage without launching the inert Web app. The TV package manager accepted
  the target-bound signature, and package-DB/path/hash attestation succeeded.
  Its device-free loader self-test nevertheless produced the same
  `failed to map segment` result before `main`.
- The WGT audit is deliberately structural. The TV installer remains the
  authority for XML signature validity, Samsung trust, signing privilege, and
  target-DUID authorization. Profile `tv_research` was issued for this TV and
  the installer accepted WGT SHA-256
  `62e644cdf1e4b07ba5316722b2ed50f3e5204cdd76c53957553de829e952021a`.
- The WGT recovery self-test's completion gate was absent. Read-only predicates
  found `failed to map segment` and later confirmed no matching process, but
  fail-closed semantics retained the installed package and recovery stage. It
  was not retried or automatically uninstalled.
- A separate managed transport then installed and attested package
  `q60t04482m`, copied the exact .NET Core 2.2 payload into a fresh writable
  stage, and reached its device-free proof gate. The launcher returned zero
  with an empty redirected output file, but none of the three exclusive proof
  files existed. This is consistent with the firmware launcher consuming the
  unprefixed `--self-test-proof` argument and running the assembly's no-argument
  dry-run path. The failed proof gate preceded the detached launch gate, so no
  `/dev/mali0` open, ioctl, or JIT soft job occurred. The package and stage are
  retained as a terminal one-shot state; they must not be retried, removed, or
  reused automatically.
- Live transport diagnostics also established a target-shell constraint that
  is easy to misclassify as a profile or payload failure. In the SDB injection
  context, `bash profile.sh` and even `bash -n /dev/null` failed, whereas
  `bash <profile.sh` and `bash </dev/null` succeeded. Staged scripts therefore
  have to be read on standard input; scripts needing positional arguments use
  `bash -s pre <package.sh` or `bash -s post <package.sh`. Hash, profile,
  package, copy, proof, launch, and classification gates in the current
  transports follow this form.
- Tizen Studio supplies two similarly named but incompatible command-line
  front ends. The current transport pins `tools/tizen-core/tz` (SHA-256
  `fc88160a1e2d7ee0ce6d2fd821d821bf4c421c698c53ba1534b7643ba6034cb2`),
  whose packaging command is `tz pack` and whose repack flags include `-b`,
  `-o`, and `-p`; it rejects `tz package`. The older
  `tools/ide/bin/tizen` front end instead exposes `tizen package` and rejects
  `tizen pack`. Their command names and option sets must not be mixed. The WGT
  builders and guarded installers in this investigation intentionally use the
  pinned `tz pack` / `tz install` interface.
- Consequently, no version ioctl, JIT initialization, allocation/free soft
  atom, or protected-result observation from this validator has occurred on
  the TV. The live driver has not been classified as `vulnerable` or
  `not_observed` by the PoC.

The native route is therefore **blocked permanently for these consumed
stages**, and both managed routes are terminal. The second managed package,
`q60t04482n`, used a fresh `-v4` stage and accepted only the leading-`--run` forms
`--run --preflight --arm Q60T-44828-MANAGED-ONE-SHOT-ARM` and
`--run --probe-jit-write-proof /dev/mali0 --arm
Q60T-44828-MANAGED-ONE-SHOT-ARM`. That exact device-free form passed
reproducible ARM-container tests. On the TV the package installed and its
members were attested, but the launcher returned zero with empty output and no
durable proofs; the host therefore did not admit the Mali launch. Package
`q60t04482n` and its stage are retained and must not be retried or removed
automatically.

The final `q60t046395` CVE-2022-46395 credential transport behaved the same
way at its full-DLL preflight: install, member attestation, copy, and launcher
exit gates passed, but output was empty and the exclusive preflight proof was
absent. Separate predicates confirmed no completion, result, attempt, or child
entry marker. Its active gate was never reached, so it provides no root proof.
The package and credential stage are retained terminal evidence.

The same module also matches the independently disclosed CVE-2022-46395 race:

- `kbase_mem_import` accepts user-buffer import type 3.
- `kbase_map_external_resource` increments the imported allocation's use count
  and pins its userspace pages when that count becomes one.
- `kbase_unmap_external_resource` decrements the count and releases those pages
  at zero.
- The sticky-unmap ioctl holds the GPU VM lock while calling the release path,
  while `kbase_soft_event_update` uses a different context lock. Its call to
  `kbase_vmap` obtains a temporary kernel mapping, and the underlying
  `kbase_vmap_prot` drops the GPU VM lock before returning. A concurrent sticky
  unmap can therefore release the backing page before the soft-event handler
  performs its one-byte status store through that mapping. This is the
  use-after-unpin interval described by GitHub Security Lab's
  [GHSL-2022-127 advisory](https://securitylab.github.com/advisories/GHSL-2022-127_Arm_Mali/).

The ioctl dispatcher establishes the narrow Samsung UK 11.6 ABI required for
that path: job submit `0x40108002` with a 48-byte atom, memory import
`0xc0188016` with a 24-byte union, sticky map/unmap `0x4010801d` and
`0x4010801e` with 16-byte records, and soft-event update `0x4010801c` with a
16-byte record (`u64 event`, `u32 new_status`, `u32 flags`). GHSL's advisory
also gives JIT allocation as an example sink for the same underlying race, but
the published exploit and this port use the simpler soft-event sink. The JIT
mapping pattern independently supports the CVE-2021-44828 analysis and is not
required by this port.
These recovered layouts and exact disassembly offsets are recorded in
[`research/mali-cve-2022-46395/ABI-EVIDENCE.md`](../research/mali-cve-2022-46395/ABI-EVIDENCE.md).

The offline port now contains an executable Q60T vendor probe and separately armed candidate credential chain. It implements
the exact UK 11.6 ioctl/atom ABI; all 31 ARM32 pending SAME_VA cookies; a
128-event AIO pin/release primitive; a multi-signal, process-supervised race;
sparse alias and allocator shaping; unambiguous Mali L3 leaf-table discovery;
owned-page GPU read/write calibration; bounded physical RAM scanning; one-shot,
canary-guarded GPU write VAs; and a transactional data-only credential
transition with readback and restoration. Reads and scans use only the first 19
pages of the proven region. The remaining 13 pages are reserved for one frozen
write epoch, with one credential word per slot and no driver reset until
rollback completes. The probe captures the stale alias before target mapping,
then requires exactly one absent-before/present-after, peer-backed Mali L3
candidate table page. Expected, unobserved success output is `POC_WINDOW ...`
and `POC_RESULT reclaim_transition=confirmed commit_zero_with_alias=accepted
before_run=absent post_run=present ... candidate_table_pages=1
credential_write=not_attempted`. The intended race byte is offset 4, written
through the imported Mali mapping only after `io_destroy`; the exact binary's
`kbase_mem_commit` reads `gpu_alloc+4` at `0x19e68`.
The supervisor first creates a permanent, fsynced one-shot marker for the
intact stage. The child verifies its exact no-follow contents and exclusively
creates and fsyncs a second entry marker before profile or device access. The
pair prevents accidental or concurrent reuse of that intact stage, but cannot
stop the same authority from deleting, copying, or restaging it. The supervisor
can terminate and reap a child only before a two-way handoff. An inherited
random pipe/PID handshake rejects accidental direct child entry, while a
child-local default-action 15-second `SIGALRM` independently enforces the
pre-handoff bound even if a wrapper reproduces that handshake. The child sends
`ready` before AIO preparation, the race, or reclaim. The parent commits to
no-kill before acknowledging on a second pipe; the child records that state as
soon as the acknowledgment is valid, before fallible post-ack signal setup.
Every successfully started race worker is joined on all exceptional paths.
Once handed off, the parent deliberately waits for actual reaping, without
console output or a timeout, rather than risk abandoning driver, PTE, or
credential state; an uninterruptible ioctl can make that wait hang, so
post-handoff completion has no guaranteed bound.

Active EGL, race, and credential output is bounded in memory and emitted only
after successful cleanup and verified credential rollback. Physical, target,
or checked EGL teardown failure prevents race and owner release. Race teardown
then orders infrastructure close, live-AIO destruction, sticky unmap,
drain/signal, alias, sparse source, and imported backing; a failed boundary
does not release later dependencies. Such a post-handoff failure closes
progress telemetry and silently holds the noninteractive child with remaining
backing pinned. This reduces a concrete release-order risk but does not attest
GPU PTE/TLB recovery, and SIGKILL, OOM, watchdog reset, or power loss bypasses
the hold. The active path launches no privileged child. Exact profile checks,
including the signed
launcher SHA-256 `a29ac61fd330b23b24c14d1733795e28a731af5a1bd95aee4f5d7b797ec44cae`,
precede EGL and every Mali open.

The optional `--credential-proof` path does not patch or execute kernel instructions. Before EGL or Mali setup it requires uniform non-root UID/GID quartets, zero active capabilities, the exact 38-bit bounding set, securebits zero, and a visible SMACK label, then uses the exact vendor kernel's value-preserving raw `setresuid32(-1,-1,-1)` path to obtain a private current-thread credential. It proves the candidate `0x80000000` linear-map delta with exact kernel-head words and `init_task`'s `swapper` name, identifies the current task with two changing 15-byte tags, validates that private credential against `/proc/thread-self/status`, changes only its eight ID words and permitted/effective capabilities for one in-process identity/capability check, and restores them. It launches no privileged child or arbitrary payload and has no global UEP write path. The two older ARM-state payload encoders and recovered UEP address remain offline audit artifacts only.

Credential rollback marks every dispatch as possibly modifying its word, then
restores that word unconditionally through the same frozen slot before PTE
reset. Capabilities are established before IDs. Rollback restores every ID in
two passes and verifies all ID targets while capability authority remains
raised; only then does it restore permitted/effective words. A reset attempt
retires the prior descriptor generation before commit-zero; cleanup skips those
descriptors if the reset becomes uncertain and accepts a replacement only after
exact zero/restored proof. If physical rollback or epoch teardown remains
unavailable, the current thread restores and verifies GIDs, then UIDs, then the
required zero active-capability baseline, stopping before the next privilege
boundary after any failure. Final verification includes all IDs, all capability
sets, securebits, keepcaps, and SMACK, and the run still fails. It does not
resume writes to the old physical credential address after this fallback. A
stuck syscall or fatal device/process failure remains unrecoverable.

The code passes host deterministic tests, a fully gated Linux compile, an
ARM EABI soft-float cross-compile, and an ARMv7 .NET Core 2.2 build/self-test.
The exact extracted firmware launcher and CoreCLR also dispatched both a
predecessor full candidate's offline suite and the separate minimal profile
verifier's self-test under network-disabled, read-only ARM emulation after only
the two package-plugin callbacks that require the missing live package database
were neutralized. The launcher differed by exactly those eight bytes. That
predecessor candidate run reported that no device was opened and made no `/dev/mali0`,
EGL/GLES, profile-file, or Mali-sysfs access. The minimal verifier completed its
distinctive device-free temporary proof self-test and exited zero; launcher
redirection hid its console text, so the syscall trace establishes that result.
This establishes managed IL/CoreCLR compatibility. On 2026-09-27, the
unmodified live package path also dispatched the pinned minimal verifier: its
fresh-stage, exact-hash, launcher-exit, and exact-proof gates all passed. The
full PoC remained offline. The current containment/output-hardened candidate
was independently built twice and self-tested in the network-disabled ARMv7
SDK image; its packaged files matched byte-for-byte. It was not dispatched
through the extracted launcher or any live TV path.
These results establish source and ABI consistency, not target behavior.
Race timing, allocator reuse, page-table reclamation, runtime cache behavior,
the static-address proof, restoration under device failure, and effective
SMACK privileges remain
unvalidated because no GPU exploit ioctl, reclaim, PTE modification, or
credential write was run on the TV. The active CLI requires exactly one mode,
`--preflight`, `--probe`, or `--credential-proof`, plus
`--run --arm Q60T-UK11.6-EXPLICIT-DEVICE-ARM`; credential proof separately
requires `--credential-arm Q60T-DATA-ONLY-CREDENTIAL-WRITE`. Preflight exits
before EGL or Mali access and exclusively creates a fixed fsynced proof file
only after every profile check passes. The guarded host deployer goes further:
it transfers a separate minimal verifier containing no EGL, Mali device, race,
reclaim, PTE, credential, or payload implementation, so the full PoC stays
offline during live profile validation. It pins that bundle, the SDB binary,
TV identity, fresh stage, remote hashes, managed proof, and a separate shell
exit marker; its opt-in route still uses active SDB package-name injection and
exposes no exploit mode. Every exploit invocation makes exactly one attempt;
`--attempts`, UEP, and arbitrary managed-payload options are rejected.
Fanout/timing options are `--epolls` (1–500), `--watches` (1–128), product at
most 50,000, `--lead-us` (1–1,000,000), and `--unmap-us` (0–1,000,000).

The later full-candidate WGT transport preserves the same shell finding: every
uploaded target script is executed from standard input rather than by filename,
including `bash -s pre/post <package.sh`. It uses a distinct package and stage,
requires the copied full DLL's leading-`--run` device-free preflight proof, and
only then admits one detached reclaim or credential-proof launch. The signed
credential transport was installed once, but the copied launcher returned zero
with empty output and no preflight proof. The active launch was not admitted;
the package and stage remain retained.

**F15 — A reversible non-root debloat control works. Confidence: high (live
change and verification).** `com.samsung.tv.multiscreen.service` has a vendor
condition that suppresses startup when
`/home/owner/share/multiviewnotsupport` exists. That directory is writable by
`sdk`. The investigation created the empty marker, terminated
`com.samsung.tv.multiscreen`, and verified the unit became `inactive/dead`.
It had used about 60 MiB RSS. Removing the marker and rebooting reverses the
change. No application files or databases were modified.

## Reproduction runbook

Everything below is **offline** — nothing touches a television. It
reproduces the analysis above using **unmodified third-party tools by
reference** (URL only). This repository does not vendor, copy or include any
of their source code.

1. **Download and verify the official firmware.**
   Get the exact CDN URL from `evidence/fw-analysis/PROVENANCE.md` (or
   re-resolve it from the GQ55Q60TGUXZG support page) and verify the hash:

   ```bash
   curl -fSL -o T-NKLDEUC.zip "<URL from PROVENANCE.md>"
   shasum -a 256 T-NKLDEUC.zip   # expect cb717ed9...4abde32 for the 2743.0 build
   unzip T-NKLDEUC.zip -d T-NKLDEUC   # yields image/info.txt, image/upgrade.msd
   ```

2. **Decrypt `upgrade.msd`.**
   Use Synacktiv's decryptor: <https://github.com/synacktiv/samsung-q60t-exploit>
   (`firmware/decrypt.py`). As of this analysis the 2021 hardcoded key still
   works against the 2026 image (F3) — follow that project's own
   instructions/README for invocation and dependencies. This repository does
   not reproduce or vendor that script.

3. **Build a VDFS4 unpacker.**
   Use HinTak/vdfs-tools: <https://github.com/HinTak/vdfs-tools> (the
   Samsung-derived, GPLv2 `0010` tree). Its vendored `openssl-1.0.1g` needs
   an amd64 build environment (it predates aarch64 support), so build inside
   an `x86_64` container, e.g.:

   ```bash
   docker run --rm --platform linux/amd64 -v "$PWD":/w -w /w/tools-vdfs gcc:5 \
     bash -c 'make CC="gcc -fgnu89-inline" host=x86_64 unpack'
   ```

   `gcc:5` (not a newer gcc) is needed for the vendored `lzo-2.06` autoconf
   test; `-fgnu89-inline` works around a C99 inline-linkage error in
   `vdfs4_get_cur_elem_data_from_list`.

4. **Apply the two patches this analysis needed — to the third-party tree,
   not to anything in this repository.** No third-party code is committed
   here. The exact applyable diff is kept privately at
   `private/fw-analysis/patches/vdfs-tools-2007-v6.patch` (gitignored, along
   with a prebuilt `unpack.vdfs` and a re-run runbook in `private/README.md`).
   To reproduce against a fresh checkout of HinTak/vdfs-tools (commit
   `b09b74e`): `git apply vdfs-tools-2007-v6.patch`. The two changes:

   - **Accept on-disk layout `"2007"`.** `unpack/unpack.c`'s
     `init_sb_info()` rejects any superblock whose `layout_version` is not
     `"2006"`. Relax that single comparison to also accept `"2007"`; the
     tool's own CRC32 superblock check then validates whether the 2006
     on-disk struct still matches (see F10/F11 — it did, for this image).
   - **Port layout-v6 compressed-descriptor support.** The `0010` tree's
     decoder only understands compressed-file descriptor layout v5. To fully
     decompress file content from a v6 image you need
     `VDFS4_COMPR_LAYOUT_VER_06` support: a `struct vdfs4_comp_file_descr`
     variant that prepends `reserved[7]` + `sign_type` and replaces the
     trailing padding with `aes_nonce[8]`, and the corresponding
     `read_descriptor_info` logic — present in the upstream
     `HinTak/vdfs-tools` history from commit `b87531e` onward, but built
     against a newer/incompatible `unpack.c` and library tree, so it was
     ported (from `b87531e`) rather than dropped in. With both patches the
     full rootfs decodes and extracts cleanly (44,530 files / 21,998 dirs;
     plaintext verified — F12). (`--no-decode` is not a fallback: the tool
     refuses it on a read-only image.)

## Practical outcome

The investigation now yields diagnostic `sdk` access, one working reversible
service disable, a successful non-exploit exact-profile validation, two
terminal managed CVE-2021-44828 transport results, and a fully implemented
CVE-2022-46395 PoC whose guarded live transport stopped before its active
launch. It still does not yield demonstrated root or factory-app removal. The
remaining uncertainty has moved from missing code to runtime facts: winning
the race, obtaining the modeled allocator/page-table reuse, confirming the
physical mapping and cache behavior, and observing the resulting UEP/SMACK
policy. Supported settings therefore remain the practical route for
background services (§4.6, §7, §13):

- **Multiscreen is disabled** through the firmware's own condition marker
  (F15). To restore it, delete `/home/owner/share/multiviewnotsupport` through
  the same `sdk` foothold and reboot.

- **Hide/remove apps through the ordinary menus** where Samsung offers it
  (`Home → Apps → App-Einstellungen → Löschen`), and disable automatic Smart
  Hub / last-app autostart (§4.3–4.4).
- **Turn off optional data collection through supported settings** —
  Viewing Information Services (ACR), advertising personalization, voice
  assistant wake word, TV Plus — rather than trying to remove the underlying
  components (§4.6).
- **Block ad and ACR network endpoints at the router**, not on the device:
  either take the TV fully offline (HDMI-source-only operation) or apply a
  narrow, verified deny-WAN/allow-LAN policy, understanding that DNS/IP
  blocking reduces network calls but does not uninstall anything or reduce
  local resource use (§13.3–13.5).

Developer Mode itself exposes the confirmed SDB command-execution path. After
active research, disconnect SDB and disable Developer Mode; do not expose the
TV's development ports beyond the trusted LAN.

`scripts/05-remove-apps.sh` remains in this repository as a safety-checked
harness (before/after inventory diff, abort on any unexpected change) for
re-testing app removal on a future firmware — not as a working debloat tool
on 2743.0.

## Glossary

- **SDB** — Smart Development Bridge, Tizen's device-control protocol/tool
  (`sdb`), analogous to Android's `adb`. `sdb uninstall` is one of the two
  refused uninstall paths (Summary, F1's sibling evidence).
- **UEP** — Unsigned-Execution Protection. A code-execution-authenticity
  boundary present in the 2743 kernel (F5), distinct from UID/privilege
  boundaries (UID0).
- **VDFS4** — Samsung's proprietary, GPLv2-licensed-tooling read-only
  filesystem (Virtual/V-something Distributed File System, v4) used for
  `platform.img`; has its own on-disk layout versions ("2006", "2007") and
  per-file compressed-descriptor layout versions (v5, v6) — see F10–F12.
- **MSDU** — The magic/format identifier (`MSDU11`) of Samsung's firmware
  container format (`upgrade.msd`), as documented by Synacktiv's decryptor.
- **TLV descriptor** — Type-Length-Value encoded structure; used here for
  the decrypted firmware header's internal records (F3).
- **cred struct** — The Linux kernel's per-task credentials structure
  (`struct cred`); overwriting it via an arbitrary-physical-memory write is
  the classical "map kernel phys → patch cred → root" technique that F7's
  checks block.
- **mmap** — Memory-map a device or file into a process's address space;
  the `sdp_hwmem` primitive's exposed operation, gated by the checks in F7.
- **physmem** — Physical memory (as opposed to virtual address space); the
  resource an arbitrary-`mmap` primitive over a physmem device would expose.
- **sdp_hwmem** — The current name (`drivers/soc/sdp/sdp_hwmem.c`) of the
  historical `sdp_mem` physical-memory-mapping driver that rooted earlier
  Q60T-era firmware; present but access-gated on 2743.0 (F6/F7, F12).
