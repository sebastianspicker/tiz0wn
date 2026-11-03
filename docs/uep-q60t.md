# Q60T 2743.0 UEP state map (offline)

This records the unmodified `T-NKLDEUC-2743.0` ARM kernel from the owned
`GQ55Q60TGUXZG`. It is a static image result, not a live memory measurement.
The [QN90B reproduction](https://github.com/chris-ritsen/samsung-tv-root/blob/master/docs/research-notes/QN90B_REPRODUCTION.md#uep)
describes a separate, volatile `1` to `0` UEP transition; none of its addresses
are used here.

## Image and address rule

The uImage declares a 7,040,960-byte uncompressed ARM Linux payload, load and
entry `0x80008000`, header CRC `da7f60ca`, and payload CRC `7cc989f0`.
There are 272 padding bytes after the declared payload. Running
`extract_vmlinux.py` on the declared payload yields SHA-256
`88cfa2ecb7e8f6b6507e6651b7569d3fd77c9cc0c1ea60c17fb48fa517c182d0`,
byte-for-byte the supplied `/tmp/vmlinux`.

The image's linked ARM lowmem base is `PAGE_OFFSET = 0xc0000000`: a startup
literal at file offset `0xa8` points to its own linked address `0xc00080a8`,
and the handler's `0xc05699d0` log-name pointer points to file offset
`0x5619d0`. Both give the same `0xc0008000` virtual image base. The uImage
load base is `0x80008000`, so the **header-derived image mapping** is:

```text
virtual = 0xc0008000 + file_offset
physical = 0x80008000 + file_offset
physical = virtual - 0xc0000000 + 0x80000000
```

The companion DTB describes Nike-L RAM banks beginning at `0x40000000`,
`0xa2000000`, and `0xe4000000`; it does not itself place the kernel at the
uImage header's load address. This table's physical values follow the declared
uImage load base, not a live `/proc/iomem` or page-table observation. Confirm
the running kernel's mapping before treating them as live physical addresses.

The raw payload has no ELF symbol table. `vmlinux-to-elf` was unavailable in
the throwaway venv (the package index could not be resolved), so these names
and boundaries come from literal function-name strings, their ARM references,
and disassembly. No kallsyms table was parsed. In particular, the literal
`SfdUepPacketHandler` at file offset `0x5619d0` is loaded as a log label at
`0xc01dedc8`; it is not by itself a symbol-table entry. The handler entry is
the prologue at `0xc01ded54` preceding that reference.

| Item | Virtual | Header-derived physical | File offset | Evidence |
| --- | --- | --- | --- | --- |
| `SfdUepPacketHandler` entry | `0xc01ded54` | `0x801ded54` | `0x1d6d54` | prologue and its `SfdUepPacketHandler` log label |
| handler registration | `0xc01dd738` | `0x801dd738` | `0x1d5738` | `0xc01dd778` builds handler address; `0xc01dd7b0` stores it in callback slot `[r4,#16]`; `0xc01dd7c4` registers that object |
| disable-state word | `0xc069342c` | `0x8069342c` | `0x68b42c` | `movw/movt` and `str` at `0xc01dedc0`–`0xc01dede0`; verifier also loads it at `0xc01de104`–`0xc01de114` |

No direct ARM `bl` to `0xc01ded54` appears in the scanned kernel text. The
identified caller path is callback registration at `0xc01dd738` and later
indirect dispatch; the dispatcher's exact call site was not resolved. The
helper calls within the handler are `0xc01decf8` for packet operation 6 and
`0xc01dec94` for operation 3; both reach `0xc01de028`.

## Guarded transition

These are the compares and branches on the path to the store, quoted from
`objdump -D -b binary -m arm --adjust-vma=0xc0008000` over
`0xc01ded54`–`0xc01dee14`. Branches to `0xc01ded74`, `0xc01ded78`, or
`0xc01dedf4` avoid the store.

```text
c01ded60  cmp   r0, #0             ; packet pointer
c01ded64  beq   0xc01ded74
c01ded6c  cmp   r3, #7             ; outer packet type
c01ded70  bhi   0xc01ded84
c01ded88  cmp   r0, #0             ; nested packet pointer
c01ded8c  beq   0xc01ded74
c01ded94  cmp   r3, #7             ; nested packet type
c01ded98  bls   0xc01ded74
c01deda0  cmp   r3, #3             ; operation 3
c01deda4  beq   0xc01dee04
c01deda8  cmp   r3, #6             ; operation 6
c01dedac  bne   0xc01dedf4
c01dedb0  bl    0xc01decf8        ; operation 6 parser
c01dedb8  cmp   r4, #8             ; parser return code
c01dedbc  bne   0xc01ded78
c01dee04  bl    0xc01dec94        ; operation 3 parser
c01dee0c  b     0xc01dedb8        ; same return-code check
c01dedc0  movw  ip, #0x342c
c01dedc4  mov   lr, #0
c01dedcc  movt  ip, #0xc069
c01dede0  str   lr, [ip]           ; *(u32 *)0xc069342c = 0
```

The type checks use `>7` for the outer and nested packet fields. The parser
path is substantive: `0xc01de760`–`0xc01de780` checks the literal `:UEP`
bytes, `0xc01de798` requests eight bytes, and `0xc01de90c`–`0xc01de930`
checks a decoded field before deeper processing. The handler's final gate is
still the parser's exact return code `8`; the handler has **no compare of the
state word with `1`** before clearing it. This static trace does not establish
that a direct physical write would reproduce certificate validation.

The image stores `0x00000001` at the state word. The other read at
`0xc01de10c` loads this same address and `c01de110: cmp r3,#0` selects a
different verifier path when it is zero. A live inspection would need to read
the word and these adjacent little-endian words together:

| Virtual address | Image word |
| --- | --- |
| `0xc0693424` | `0xc05b9c70` |
| `0xc0693428` | `0xc05b9b98` |
| `0xc069342c` | `0x00000001` |
| `0xc0693430` | `0xffffffe0` |
| `0xc0693434` | `0xc0693434` |
| `0xc0693438` | `0xc0693434` |
| `0xc069343c` | `0xc01dfa68` |

Decision: **inspect** means check that the mapped word is `1` and its
neighbourhood matches this exact image, or report `0` as already disabled;
any other value or mapping is unknown. **Disable** is the handler's guarded
one-word `0` store after parser return `8`. The guard shape matches the
upstream transition, while the physical mapping and live state remain
unverified on this TV. No image or device was patched for this map.
