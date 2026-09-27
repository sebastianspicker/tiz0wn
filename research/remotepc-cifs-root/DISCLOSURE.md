# Remote PC CIFS credential command injection

## Summary

On Samsung GQ55Q60TGUXZG firmware `T-NKLDEUC-2743.0`, Remote PC forwards raw
SMB credential values into a privileged CIFS helper. The helper substitutes
the credential-file contents into a command string and executes it through
root `/bin/bash -c`. Shell syntax accepted by the Remote PC password field can
therefore execute as UID 0 when the in-session Shared Folder action reaches
the mount path.

This report is limited to the exact assessed firmware and a bounded `id`
marker. It does not establish an affected version range, persistence, a root
shell, firmware modification, or remote Internet reachability.

## Affected product

- Product: Samsung Smart TV, model GQ55Q60TGUXZG
- Firmware: `T-NKLDEUC-2743.0` (`SWU-OU_T-NKLDEUC-02743-2026-07-02-Release`)
- Official archive SHA-256:
  `cb717ed98daf9580eb5b84bccbad5adac82f75dd021ed028f1ee1bb6c4abde32`

The first affected release, other affected models, fixed release, and backport
status are unknown because proprietary source and change history were not
available.

## Technical detail

The reviewed chain is:

1. Remote PC's connect path associates the shared-folder checkbox with both
   Samba support and remembered-profile storage.
2. An active RDP session exposes a top toolbar. Its Shared Folder callback
   calls `startMyContent`, and `remotepc_rdp` sends `SAMBA_MOUNT`.
3. `remotepc_uilauncher` handles that request in `Samba::Connect`, enumerates
   shares, writes raw `username=`, `password=`, and `smbpath=` lines, then calls
   `PS_Mount_Cifs`.
4. The privileged rule constrains caller identity and argument/path shape.
   It does not validate shell metacharacters inside the credential file.
5. `/usr/apps/privileged-service/bin/mount.smb.sh` reads those values at lines
   18–27, substitutes them into `UTIL_OPT` at lines 32–67, and executes
   `/bin/bash -c "$UTIL $UTIL_OPT"` at line 72.

VNC was excluded: the reviewed VNC path has no normal `SAMBA_MOUNT` sender.
Simply connecting over RDP is also insufficient; Shared Folder is the action
that reaches CIFS mounting.

## Reproduction

The validating environment exposed one disposable xrdp session and one
authenticated SMB2 share on the owner's trusted LAN. The Remote PC profile used
fixed unprivileged user `q60t` and this password shape:

```text
$(/usr/bin/id>/tmp/<fresh-marker>)
```

The owner connected once, verified the disposable RDP certificate, revealed
the TV's in-session top toolbar with a physical pointing device, and clicked
Shared Folder once. The SMB server observed one new share enumeration.

A separate fresh SDB predicate required all of the following before creating a
classification directory:

- marker is a regular file;
- marker owner UID is 0; and
- marker begins `uid=0(root) gid=0(root)`.

Exactly two pushes distinguished the created directory from a missing path.
The result was `uid0-proof`. The marker was not pulled from the TV.

## Security impact

An attacker who can configure and activate Remote PC on the local TV can turn
credential text into root command execution when Shared Folder invokes the
privileged CIFS path. Practical exploitation requires local UI interaction,
an RDP endpoint, SMB service, and the feature's saved/shared-folder state in
the assessed workflow. These preconditions reduce reachability but do not
reduce the resulting process privilege: the demonstrated command ran as UID 0.

## Remediation guidance

- Remove `/bin/bash -c` from the mount path.
- Pass mount arguments as an argv array directly to `execve`/`execv`.
- Keep credentials in a file consumed by the mount implementation rather than
  interpolating their contents into command arguments.
- Reject control characters and enforce explicit length/character constraints
  at both Remote PC input and privileged-service boundaries.
- Decouple shared-folder enablement from credential persistence.
- Add regression tests with command substitution, quoting, separators,
  whitespace, newlines, and option-like credential values.

## Validation boundary

Only the exact 2743.0 artifacts and one owner-controlled device were tested.
No destructive or persistent payload was used. The test did not modify flash,
install a startup component, change credentials, or attempt post-root actions.
