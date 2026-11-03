# Q60T 2743.0 physical mapping audit (offline)

Scope: the supplied raw `/tmp/vmlinux` and partial `/tmp/tiz-rootfs2` extraction
for the owned `GQ55Q60TGUXZG`. This is a static review. It does not establish
live device modes, runtime range-table contents, or a physical write. The raw
image is ARM code linked at `0xc0008000` (the address rule and image digest are
in [the UEP map](uep-q60t.md)). Instruction addresses below are virtual; file
offset is the address minus `0xc0008000`. Disassembly used `radare2` in ARM
32-bit mode at that base. The extracted module paths named below contain **zero
bytes**, including in `/tmp/tiz-rootfs.tar`; a filename is not a driver body.

The mode source is
`/tmp/tiz-rootfs2/etc/smack_device/pre-devattr.list`:
`sdp_mem`, `mali0`, and `eeprom` have `MODE="0666",SMACK="*"` (lines 5, 8,
9); `dmabuf_kds` has only `SMACK="*"` (line 10); `i2c-6` and `i2c-7` have
`MODE="0666",SMACK="*"` (lines 13–14). The extracted
`/tmp/tiz-rootfs2/usr/lib/udev/rules.d/99-GPU-Acceleration.rules`
also sets `mali*` to mode `0666`, group `display`, SMACK `*` (line 2).
`/tmp/tiz-rootfs2/usr/lib/udev/rules.d/51-system-plugin-hawkp.rules`
sets `tzmem` and the `dmabuf_kds` subsystem to group `video`, SMACK `*`,
without setting their modes (lines 4–5). These are image rules, not observed
post-boot `stat` results.

## Built-in `sdp_hwmem` check

The kernel embeds `drivers/soc/sdp/sdp_hwmem.c` at `0xc05c1600` and the
`sdp_hwmem` name at `0xc05c161c`. The physical mmap path begins at
`0xc02831cc`; a static table points to it at `0xc0575820`. It derives
the requested start from `vma->vm_pgoff << 12` (`0xc02831e8`–`0xc0283200`)
and the length from `vm_end - vm_start` (`0xc02831e0`–`0xc02831ec`). The
first guard calls `0xc001b4b0`, whose `0xc001b4bc`–`0xc001b4c8` instructions
compare `pgoff + (length >> 12)` with `0x10000000`. Failure branches at
`0xc028320c` to the `invalid phys addr range` diagnostic and the shared
`-EFAULT` return (`0xc02833e8`). This is a 32-bit address-space bound, not
an authorization of the whole space.

The remainder has **three distinct range decisions**:

1. At `0xc0283244`–`0xc0283264`, the sequence `cmp r7,r1; cmpeq r6,r0;
   blo 0xc0283268` tests the start against an entry base, and `cmp r1,r3;
   cmpeq r0,r2; bls 0xc028335c` accepts an end within that entry. A request
   wholly contained in the runtime table at `0xc07a6c20` therefore reaches
   the mapping path at
   `0xc028335c`. That path calls `0xc00d4130` at `0xc0283394`. This early
   acceptance does not pass through the later kernel-region rejection. The
   table lives in zero-initialized runtime memory; its populated entries are
   absent from the raw image.
2. A second range table at `0xc07a6c70` is checked at
   `0xc0283298`–`0xc02832d0`. `cmp r7,r3; cmpeq r6,r2; bhs
   0xc02832bc` skips a non-overlapping entry; `cmp r5,r1; cmpeq r4,r0;
   bhi 0xc02833f4` reaches
   the literal diagnostic `sdp_hwmem: phys region intersects with dts memory
   region, phys %pa++%zx` and then returns `-EFAULT` (`0xc02833d0`–
   `0xc02833f0`).
3. The sorted table addressed through `0xc068f250` is searched at
   `0xc02832d4`–`0xc0283350`. `cmp r7,r1; cmpeq r6,r0; blo 0xc02833bc`
   (`0xc028330c`–`0xc0283314`) rejects a request overlapping the selected
   range; the diagnostic is `sdp_hwmem: phys region intersects with kernel
   region, phys %pa++%zx`, followed by `-EFAULT` (`0xc02833bc`–
   `0xc02833f0`).

Thus the kernel-intersection rejection is **confirmed for requests reaching
the third decision**. A universal “whitelist containment plus kernel reject”
description is too strong: the first containment branch reaches the mapping
call without the third decision. Nothing in this static image proves that a
live first-table entry overlaps the kernel, so this is also **not evidence of
a kernel-capable mapping**. The exact live table and physical placement remain
unknown. This qualifies the earlier [F6/F7 conclusion](firmware-analysis.md)
instead of treating its log strings alone as proof.

## Candidate table

`unknown` means the supplied artifacts do not support either a kernel-capable
or a device-only verdict. “No reject observed” for an unavailable module is
not a claim that its handler lacks one. No alternative's kernel physical reach
or bound is asserted without its mmap handler.

| Candidate | Mode / SMACK source | Driver and mmap evidence | Reach and checks | Verdict |
| --- | --- | --- | --- | --- |
| `/dev/sdp_mem` | `0666` / `*`, pre-devattr line 8 | Built-in `drivers/soc/sdp/sdp_hwmem.c`; mmap at `0xc02831cc` | Physical page offset and VMA length; address-space bound at `0xc001b4bc`–`c8`; early contained-range acceptance at `0xc0283240`–`64`; DTS intersection reject at `0xc02832b0`–`b8`; kernel intersection reject at `0xc028330c`–`14`. The accepted runtime table's populated ranges are unavailable. | **unknown**: the generic path rejects kernel overlap, but the early branch needs live table evidence. |
| `/dev/mali0` | `0666` / `*`, pre-devattr line 5 and GPU udev rule line 2 | `usr/lib/modules/4.1.10/kernel/soc/sdp_gpu.ko` is zero bytes here. [F14](firmware-analysis.md) identifies Mali-G51 r11p0 from an earlier module analysis, but gives no physical mmap bound for this task. | GPU mmap handler and its range checks cannot be disassembled from this extraction; no arbitrary physical reach is established. | **unknown**: missing handler bytes. |
| `/dev/tzmem` | Group `video`, SMACK `*`, no explicit mode, `51-system-plugin-hawkp.rules` line 4 | No `tzmem` handler body in the supplied raw kernel or nonempty extracted module set was identified. | Mapping target, source of any physical allocation, and checks unknown. The rule alone does not prove world write access. | **unknown**: handler and mode unresolved. |
| `/dev/dmabuf_kds` | SMACK `*` in pre-devattr line 10; group `video`, SMACK `*` in plugin rule line 5; neither specifies a mode | No handler body identified in the supplied artifacts. | An allocator or shared-buffer name is not a physical-memory mapping contract; range and checks unknown. | **unknown**: handler and mode unresolved. |
| `sdp_pqe_dp` node, if any | No matching pre-devattr or reviewed udev mode rule | `usr/lib/modules/4.1.10/kernel/soc/sdp_pqe_dp.ko` is zero bytes. | Node creation, mmap handler, and physical register or memory window cannot be established. | **unknown**: module body missing. |
| `sdp_pqe_frc` node, if any | No matching pre-devattr or reviewed udev mode rule | `usr/lib/modules/4.1.10/kernel/soc/sdp_pqe_frc.ko` is zero bytes. | Node creation, mmap handler, and physical register or memory window cannot be established. | **unknown**: module body missing. |
| `/dev/eeprom` | `0666` / `*`, pre-devattr line 9 | `usr/lib/modules/4.1.10/kernel/tztv-eeprom.ko` is zero bytes. | Whether its file operations include mmap is unverified; EEPROM access cannot be equated with system RAM access. | **unknown**: handler body missing. |

The `i2c-6` and `i2c-7` modes above and the broader `i2c-[0-9]` mode `0666`
in `/tmp/tiz-rootfs2/usr/lib/udev/rules.d/99-system.rules`
(lines 1–2) establish bus-node access only. The built-in kernel carries the
`drivers/i2c/i2c-dev.c` source-path string at `0xc05d9780`; this review did
not identify an mmap operation or a physical-memory exposure for those bus
nodes. They are therefore outside the physical-mapping candidate count, not
declared safe on the strength of their names.

**Single candidate for a later live, read-only probe:** `/dev/sdp_mem`, to
resolve the early accepted-range table and the handler's verdict on the exact
running build. Its static generic path rejects kernel overlap; a live probe
must not infer kernel reach from mode `0666`. No device was opened or mapped in
this audit.
