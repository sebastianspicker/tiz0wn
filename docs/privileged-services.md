# Privileged-service shell script inventory

This is an offline inventory of the recoverable script bodies in
`evidence/fw-analysis/dec/platform.img`, identified by
`SWU-OU_T-NKLDEUC-02743-2026-07-02-Release`. No extracted rootfs was available.
`grep -abo '/usr/apps/privileged-service'` found image offsets `1080066083`
(inside `systemctl.sh`) and `1165598970` (a systemd unit naming `ps_agent`).
Bounded `dd`/`strings` reads around those hits and the adjacent 4 KiB-aligned
shebangs found three Bash bodies. Nearby VDFS name records at about
`1305107130` and `1305116730` list `systemctl.sh`, `mount.smb.sh`, and
`umount.smb.sh`; the body-to-name pairing is supported by their commands but
still needs a full extraction to confirm inode mapping. `ps_agent` is named by
a unit but was not counted as a shell script.

Sizes below are the nonzero body bytes before zero padding in each bounded
4 KiB window, not independently verified filesystem sizes. The first 4 KiB
window starting at the path hit `1080066083` cut `mount.smb.sh` line 3 after
`function join_by { loc`; a separate window starting at its shebang
`1080070144` contained that full line and the complete execution line. No
execution line in the three recorded bodies was cut. Raw-window coverage cannot
prove that the extracted directory has no further scripts.

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

1. Fully extract the same image and confirm each filename, filesystem byte
   size, complete line, and inode-to-body mapping.
2. Trace each helper's caller and privileged-service rule to establish where
   its arguments and credential file come from and which values are constrained.
3. Compare the file read and substitution lines with the final command line,
   including the unmount helper's unassigned `FileContent`, without executing
   the helper or contacting the TV.

| Rank | Script (image body offset; observed bytes) | Interpreter and purpose | Input and exact execution line | Class |
| --- | --- | --- | --- | --- |
| 1 | `/usr/apps/privileged-service/bin/mount.smb.sh:72` (`1080070144`; 2027 B) | `#!/bin/bash`; assembles a CIFS mount command. | Caller arguments enter `UTIL_OPT=$*` at line 9. A `credentials=` argument selects a file; lines 18–27 read its non-`smbpath=` lines and its `smbpath=` line. Lines 37–43 (or 50–55, 62–67) substitute them into `UTIL_OPT`. Line 72: `[[ "$debug" == "false" ]] && /bin/bash -c "$UTIL $UTIL_OPT"`. | `shell-argv` |
| 2 | `/usr/apps/privileged-service/bin/umount.smb.sh:46` (`1080074240`; 1221 B) | `#!/bin/bash`; assembles an SMB unmount command. | Caller arguments enter `UTIL_OPT=$*` at line 9. A `credentials=` argument selects a file; line 27 reads its `smbpath=` line, and lines 37–41 substitute the value into `UTIL_OPT`. Line 40 also references `FileContent`, with no assignment visible in this complete body; it is not counted as a file-derived stream. Line 46: `[[ "$debug" == "false" ]] && /bin/bash -c "$UTIL $UTIL_OPT"`. | `shell-argv` |
| 3 | `/usr/apps/privileged-service/bin/systemctl.sh:20` (`1080066048`; 358 B) | `#!/bin/bash`; applies a systemctl action to names beginning `ps_` in the service directory. | Line 3 takes the action from `$1`; line 16 obtains names from `ls ${DIR} \| grep ps_`. Line 20: `systemctl ${SYSTEMCTL_CMD} ${A}.service`. This invokes `systemctl` with shell-expanded arguments, not through `-c`. | `argv-direct` |
