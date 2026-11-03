# Privileged-service shell script inventory

This is an offline inventory of the recoverable script bodies in
`evidence/fw-analysis/dec/platform.img`, identified by
`SWU-OU_T-NKLDEUC-02743-2026-07-02-Release`. The image has now been fully
extracted, so the body-to-name pairing is confirmed rather than inferred:
`mount.smb.sh` and `umount.smb.sh` live in
`/usr/apps/privileged-service/bin/`, and `systemctl.sh` in
`/usr/apps/privileged-service/scripts/` (not `bin/`, as the bounded reads
suggested). `/usr/apps/privileged-service/bin/ps_agent` is a zero-byte file;
`systemctl.sh` picks it up through its `ps_` glob, so it is a service name, not
a script body.

Extraction method, for reproduction: `vdfs-tools` (Synacktiv) with the VDFS
layout set to 2007 and the compressed-file layout set to 6, built in an Alpine
container. The macOS host needs `-fcommon`, `-fgnu89-inline` and a small compat
header; extraction straight onto the macOS filesystem segfaults on
`security.SMACK64` xattrs, so it has to run inside the container.

Confirmed facts per body:

| Script (inode; size; SHA-256) | Interpreter |
| --- | --- |
| `bin/mount.smb.sh` (inode 6370191; 2027 B; `37aaf2f05bf714332a6bf8f14b543ac9584a1b9a051341674a74fc0dd753c57e`) | `#!/bin/bash` |
| `bin/umount.smb.sh` (inode 6370194; 1221 B; `d0dffdaedd33243445a85019cbfadb8d281ab48d29b7a68d7eedec7f13ccc782`) | `#!/bin/bash` |
| `scripts/systemctl.sh` (inode 6457161; 358 B; `2756cf78e21da1b3b65ecbdc20bf44e540e4aec5d18e0c8c9971218d60365f6a`) | `#!/bin/bash` |

The sizes agree with the earlier bounded-window observations (2027, 1221 and
358 nonzero body bytes), which independently checks both readings. No other
`.sh` exists under `/usr/apps/privileged-service`.

The ranking counts distinct external value streams that contribute bytes to
the command passed to a shell: caller arguments, credential-file lines other
than `smbpath=`, and the file's `smbpath=` line. It does not count alternate
regex branches as separate inputs or infer who can control a value. Among the
`shell-argv` scripts, `mount.smb.sh` has three streams and `umount.smb.sh` has
two. `systemctl.sh` is third in the inventory because it does not build a
`sh -c`/`bash -c` argument. The reviewed Remote PC path establishes the file
origin for the mount helper; this scan alone does not establish the unmount
caller's provenance or any candidate's exploitability.

To verify a candidate next, using read-only steps:

1. ~~Fully extract the same image and confirm each filename, filesystem byte
   size, complete line, and inode-to-body mapping.~~ Done; see the table above.
2. Trace each helper's caller and privileged-service rule to establish where
   its arguments and credential file come from and which values are constrained.
3. Compare the file read and substitution lines with the final command line,
   including the unmount helper's unassigned `FileContent`, without executing
   the helper or contacting the TV.

| Rank | Script (inode; size) | Interpreter and purpose | Input and exact execution line | Class |
| --- | --- | --- | --- | --- |
| 1 | `/usr/apps/privileged-service/bin/mount.smb.sh:72` (inode 6370191; 2027 B) | `#!/bin/bash`; assembles a CIFS mount command. | Caller arguments enter `UTIL_OPT=$*` at line 9. A `credentials=` argument selects a file; lines 18–27 read its non-`smbpath=` lines and its `smbpath=` line. Lines 37–43 (or 50–55, 62–67) substitute them into `UTIL_OPT`. Line 72: `[[ "$debug" == "false" ]] && /bin/bash -c "$UTIL $UTIL_OPT"`. | `shell-argv` |
| 2 | `/usr/apps/privileged-service/bin/umount.smb.sh:46` (inode 6370194; 1221 B) | `#!/bin/bash`; assembles an SMB unmount command. | Caller arguments enter `UTIL_OPT=$*` at line 9. A `credentials=` argument selects a file; line 27 reads its `smbpath=` line, and lines 37–41 substitute the value into `UTIL_OPT`. Line 40 also references `FileContent`, with no assignment visible in this complete body; it is not counted as a file-derived stream. Line 46: `[[ "$debug" == "false" ]] && /bin/bash -c "$UTIL $UTIL_OPT"`. | `shell-argv` |
| 3 | `/usr/apps/privileged-service/scripts/systemctl.sh:20` (inode 6457161; 358 B) | `#!/bin/bash`; applies a systemctl action to names beginning `ps_` in `bin/`. | Line 3 takes the action from `$1`; line 16 obtains names from `ls ${DIR} \| grep ps_`. Line 20: `systemctl ${SYSTEMCTL_CMD} ${A}.service`. This invokes `systemctl` with shell-expanded arguments, not through `-c`. | `argv-direct` |
