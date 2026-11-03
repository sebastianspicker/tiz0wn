# Q90T: getting the SWU passphrase through the TrustZone TA

Target: `QE75Q90TATXXU`, `T-NKMDEUC-REL-202607031800` (reported as
`T-NKMDEUC-2743.0`), Tizen 5.5, ARMv7. Status: **procedure, not yet run on this
set.** It exists because the offline keys and the direct pull both stop:

- `upgrade.msd` parses as `MSDU11` with a `T-NKMDEUC` header, but none of the
  ten candidate keys in the decryptor produces a valid `OUIT` header. The
  container key is per-container, not a static model key.
- `sdb pull /usr/share/org.tizen.tv.swu/itemsAESPassphraseEncrypted.txt` is
  refused by path, while a live SDK diagnostic confirms the file exists
  (416 bytes, `root:root`, `0644`) and is readable by `uid=901(sdk)` with
  `READ_RC=0`. The refusal is a pull-path allowlist, not a permission problem.
- `/usr/lib/libteec.so` is 32-bit ARM and exports `TEEC_InitializeContext`,
  `TEEC_OpenSession`, `TEEC_CloseSession`, `TEEC_InvokeCommand`; it references
  `/dev/tzmem`. That is the SWU TrustZone TA, and it is the component that can
  unwrap the passphrase for the SDK identity.

cfloinc derived the Q70T kernel table through this same TA with the legacy
TEEC ABI and no `T-NKM` key, so the route has one working precedent in this
family. What follows is that route adapted to a read-only passphrase read.

## 1. Read the encrypted file without `sdb pull`

The SDB appinstall shell runs as root in the `System` domain, so a plain read
works and the result can be posted out over the callback channel:

```
sh live/q.sh 'base64 /usr/share/org.tizen.tv.swu/itemsAESPassphraseEncrypted.txt'
```

Store the decoded 416 bytes; they are the TA input, not a ciphertext to attack.

## 2. Establish the ABI before writing a client

Confirm the legacy TEEC calling convention on this set instead of assuming it:

- the four exported symbols above and the struct shapes of Tizen 5.5's
  `tee_client_api.h` (the Q70T precedent used this header);
- `/dev/tzmem` present and openable from the appinstall domain;
- the SWU TA UUID, taken from the vendor unit/service that handles
  `itemsAESPassphraseEncrypted.txt` (grep the service binary and unit files;
  do not hardcode a UUID from another model).

If the helper already in hand does not recognise the 5.5 ABI, patch its struct
layout against the header rather than forcing a modern ABI.

## 3. Invoke the TA

Open a context, open a session against the SWU TA UUID, and invoke its decrypt
command with the 416-byte blob as a temporary shared memory block. Expect the
passphrase in the output buffer, or a status word that names the failure
(invalid header, session refused, bus busy). Capture the status word verbatim;
it distinguishes "wrong ABI" from "TA accepted but refused the caller".

## 4. Use the passphrase offline

Feed it to the MSD decryptor in place of the candidate-key list, confirm the
`OUIT` header, and continue with the normal image workflow. The passphrase is
per-container; do not publish it with dump contents.

## Decision points

- **TA returns the passphrase** → proceed; the rest of the offline workflow is
  unchanged.
- **TA returns a refusal** → record the status word; check the invoking label
  (`priv_tee_client` is in the SDK identity's groups) before changing anything.
- **No SWU TA UUID can be resolved** → fall back to the manifest/unit strings
  and, only then, to a wider key search.

## Limits

One set, and this document has not been executed on it. Nothing here depends on
the USB-root chain or on UEP being disabled; it is a read-only passphrase
retrieval, separate from both entry routes.
