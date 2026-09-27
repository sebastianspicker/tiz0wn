# Live checkpoint — stop before a fresh one-shot

Date prepared: 2026-09-27. The next intended live review date was 2026-09-28.

## Current boundary

The original, manually assembled proof already established UID-0 command
execution on the owner-controlled GQ55Q60TGUXZG / T-NKLDEUC 2743.0. The fresh
`one_shot_proof.py` harness has not been run on the TV. Its unit suite and
Mac-local Docker lab are safe to run without the TV.

Do not start live mode merely because this file exists. Reconfirm ownership,
exact target, recovery expectations, and the one-trigger/no-retry contract at
the beginning of the session.

## Before live mode

- [ ] Read the uncommitted diff and obtain an independent review.
- [ ] Run `make -C research/remotepc-cifs-root test`.
- [ ] Run `make -C research/remotepc-cifs-root lab-test`.
- [ ] Confirm both the lab's PAM probe and published-port XRDP login rejected
      the deliberate wrong password before the exact-credential session.
- [ ] Run `git diff --check`.
- [ ] Confirm no disposable lab container is running.
- [ ] Confirm host TCP 3389, 445, and 1445 are free.
- [ ] Fill the private, gitignored `config/tv.env` identity fields.
- [ ] Confirm model `GQ55Q60TGUXZG` and firmware `T-NKLDEUC-2743.0` visually.
- [ ] Confirm Developer Mode names this Mac as the host.
- [ ] Confirm the TV is on a trusted LAN with no relevant port forwarding.
- [ ] Decide who controls the physical pointer and who watches terminal gates.
- [ ] Accept that a temporary Remote PC profile will be saved and later removed.

## During live mode

- Use RDP, never VNC.
- Fill only the field named by the form card; visually recheck every field.
- Compare the displayed RDP certificate fingerprint and leave persistent
  certificate trust unchecked.
- The visible `q60t` xterm is the disposable host, not a root terminal on the
  TV.
- Do not open Shared Folder until the harness has armed its one observation
  window.
- Click Shared Folder once. Do not retry a missed click, SMB event, injection,
  or classifier.
- Stop on any identity mismatch, extra SMB event, unexpected SDB text, timeout,
  signal, or uncertain UI state.

## Existing target evidence — never touch

Do not query, retry, reuse, remove, uninstall, or clean these earlier SDB
stages under `/home/owner/share/tmp/sdk_tools/`:

```text
q60t-rpc-08321aece7cdd36f-v1
q60t-rpcdb-ecabaf55-v1
r17674731
f73610f5f
m83626cb5
ue5c522d3
v6f7bb0e1
wa3b65ad0
w761cf313
w63dd51c7
rbe1823666208
q60t-pf-0be88330-v11
```

`rbe1823666208` is the successful earlier UID-0 classification stage.
`/tmp/q60t-rpc-root-proof` is the earlier volatile proof marker. The harness
generates unrelated, fresh names and never cleans either old or new target
evidence automatically.

## Manual cleanup after a reviewed live run

1. Exit Remote Access Player without reopening the share.
2. Delete the saved disposable Remote PC profile through the TV UI.
3. Revoke `Q60TValidation` from the allowed-device list if that pairing is no
   longer required.
4. Confirm on the Mac that TCP 3389, 445, and 1445 are closed and no
   `tiz0wn-rpc-*` container remains.
5. Preserve the redacted run record before deciding whether to reboot. A reboot
   is expected to clear a volatile `/tmp` marker, but it is not automatic
   cleanup and is not required merely to stop the lab.

Do not perform target cleanup through a new SDB injection. Visual profile and
pairing cleanup is deliberately separate from proof execution.
