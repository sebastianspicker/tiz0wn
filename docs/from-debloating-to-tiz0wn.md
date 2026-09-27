# From debloating to tiz0wn

## How a TV cleanup project found a short SMB-to-root chain

The project did not begin with a root exploit. It began with an ordinary
question: could a 2020 Samsung Q60T be made less cluttered and more responsive
without breaking the television?

That framing mattered. Instead of importing a bulk-removal list, the first
tools measured what was installed, recorded one change at a time, pinned every
SDB action to one target, and kept rollback evidence. The repository was named
`q60t-debloat` because that was genuinely its scope.

Then the scope widened.

## Firmware before folklore

Internet recipes mixed different Samsung model years, Tizen generations, and
firmware families. The only useful way forward was to obtain the exact
`T-NKLDEUC-2743.0` archive, verify its hash, decrypt it, extract the rootfs, and
inspect what this TV actually shipped.

That work closed some attractive shortcuts. An older physical-memory root
primitive was constrained on this build. A target-specific Mali path was worth
researching, but it demanded careful ABI recovery, race and reclaim work, GPU
page-table reasoning, and managed-entry transport. Several bounded live checks
never established the necessary managed launch. The correct conclusion was
not to make the test more reckless; it was that the difficult route remained
unproven.

Meanwhile, the rootfs held a much smaller clue.

## The needle in the privileged-service haystack

Samsung's privileged service includes rules for operations ordinary
applications cannot perform themselves. One rule allows the signed Remote PC
application to request a CIFS mount through `ps_agent`. Its shell wrapper,
`mount.smb.sh`, looked innocuous at first: read a credentials file, assemble
mount options, run `/bin/mount`.

The dangerous detail was how it assembled them. The script read raw credential
lines, substituted their contents into a string, and passed that string to
root `/bin/bash -c`.

That changed the investigation. The question was no longer "Can the complex
Mali chain reach root?" It was "Can a Remote PC field reach this existing root
shell boundary unchanged?"

Disassembly supplied the backward trace. Remote PC writes `username=`,
`password=`, and `smbpath=` into a temporary file. Its launcher enumerates SMB
shares and calls the privileged CIFS method. The RDP client—not VNC—sends the
`SAMBA_MOUNT` request when the user activates Shared Folder from a hidden
in-session toolbar. The same checkbox state that enables the feature also
selects remembered-profile storage.

Once that chain was understood, the exploit itself was comparatively
low-complexity: a command substitution in a credential field. Finding and
proving the full route was not.

## The failed observations were useful

An SMB listener alone saw nothing, because connecting to Remote PC was not the
same as opening Shared Folder. VNC was the wrong protocol. Early attempts to
prepare the TV form used an incorrect focus model: an address landed in the
wrong field, VNC became selected, and the shared-folder checkbox was not set.
Those mistakes were stopped before Connect, recorded, and used to remove UI
automation from the final design.

The successful path kept human eyes in the loop:

1. A disposable, unprivileged xrdp host and authenticated SMB2 share ran on the
   owner's trusted LAN.
2. The Remote PC form was filled and visually checked field by field with RDP
   selected.
3. The disposable certificate was compared before connecting; persistent
   certificate trust stayed off.
4. The terminal shown by the TV was confirmed to be the container's UID-1000
   `q60t` shell, not a TV root shell.
5. A physical pointing device revealed the top toolbar.
6. One Shared Folder click produced one fresh SMB share-enumeration event.

The password contained only a volatile identity proof:

```text
$(/usr/bin/id>/tmp/q60t-rpc-root-proof)
```

## Proving root without turning proof into post-exploitation

The first instinct—push a file to the marker path and inspect success—was not
sound. SDB can create a file at a missing destination, so a single successful
push does not prove a directory or an existing marker.

The corrected classifier used a fresh terminal stage and a combined target
predicate. Only a regular marker owned by UID 0 whose contents began with the
root `id` signature caused that stage to become a directory. A first push was
followed by exactly one push to a child path. The child push could succeed only
if the predicate-created directory existed. It did.

That established the claim the project needed: this Remote PC/CIFS path ran
the bounded command as UID 0. It did not establish a root shell, persistence,
arbitrary post-root capability, a flash change, or a firmware range.

## Why `tiz0wn`

`q60t-debloat` described the starting task but not the repository that emerged.
The work now spans reversible device management, exact-firmware archaeology,
failed and successful exploit research, safety-gated reproduction, and a
vendor-ready vulnerability report. `tiz0wn` captures that broader Tizen
security focus while keeping the slightly mischievous spirit of the discovery.

The rename is not a declaration that every Tizen device is owned, or even that
every Q60T firmware is affected. It marks one carefully bounded result on one
exact build—and the method that found it: measure, disassemble, trace both
directions, test the smallest claim, and stop when the evidence is sufficient.

## What comes next

The repository now contains an offline-by-default one-shot harness. Its default
mode only verifies pinned local firmware artifacts. Its Docker lab binds to the
Mac and proves that the payload-shaped password remains literal across full RDP
and SMB sessions. Live mode exists for a reviewed future session, but is
guarded by exact identity checks, manual visual gates, one click, one
classification, no retry, unconditional listener cleanup, and redacted
evidence.

That is the lasting connection to the original debloating project: root was
never the excuse to abandon reversibility. It was another change boundary to
measure and constrain.
