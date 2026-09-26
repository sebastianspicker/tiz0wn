# Firmware static analysis — T-NKLDEUC 2743.0 (GQ55Q60TGUXZG)

Offline, read-only analysis of the currently installed firmware image for
model **GQ55Q60TGUXZG**, firmware **T-NKLDEUC-2743.0**. Nothing in this
document was run against a television; everything here is host-side analysis
of the firmware artifact per research doc [§11](Samsung_Q60T_Debloating_Research_2026-09-25.md#11-a-firmware-specific-reverse-engineering-plan).

This is a public-facing summary: it contains the model string, build/version
identifiers and public URLs/hashes only. It intentionally omits any
device-private identifier (TV serial, IP, MAC, DUID) — those never appear in
firmware artifacts anyway, but the raw working notes this doc is condensed
from (`evidence/fw-analysis/`, `evidence/root-feasibility-2026-09-26.md`) are
private working files and are not tracked in this repository.

## Summary

- **No evidence-backed route to root, or to factory-app removal, on 2743.0.**
  `sdb uninstall` and `vd_appuninstall` were both empirically observed to
  return exit code 0 while leaving the live application list completely
  unchanged (see `scripts/05-remove-apps.sh` and
  `evidence/root-feasibility-2026-09-26.md`) — a refusal, not a success.
- The firmware container's AES key has **not been rotated** since 2021: a
  five-year-old, publicly known passphrase still decrypts the current 2026
  image. That is a confidentiality finding only — it does not grant root or
  let you forge a bootable modified image (every section still carries an
  independent signature).
- The kernel is Linux 4.1.10 (ARM), built 2026-07-02.
- The historical Q60T root primitive — an arbitrary physical-memory mapping
  driver (`sdp_mem`, later `sdp_hwmem`) — is **hardened** on this build: a
  whitelist-containment check plus an explicit kernel-region-intersection
  reject close the primitive at the driver level (code-level confirmation,
  not just strings). Full rootfs extraction later confirms the same
  conclusion at the userspace layer: no udev rule grants the `sdp_hwmem`
  device node permissive access either (F12).

## Findings

Condensed from `evidence/fw-analysis/FINDINGS.md` (private working notes,
**F1–F12**). Confidence levels are as recorded during analysis, and are
called out explicitly below rather than left implicit.

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

None of the above yields a usable app-removal or root path on this
firmware today. The research doc's non-root recommendations remain the
practical route (§4.6, §7, §13):

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
