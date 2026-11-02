# Remote PC trigger grammar

This records the character evidence for the password-field trigger on the one
Q60T and firmware build in the [live run](../exploits/tiz0wn-root/LIVE-RUN-2026-10-29.md#4-the-trigger).
“Survived” means the recorded trigger reached its fetch and setup; the
builder's current output is separately pinned by its
[test](../exploits/tiz0wn-root/tests/test_serve.py#L37-L45).

| Class | Result | Evidence |
| --- | --- | --- |
| `$`, `(`, `)`, `>`, `/`, `-`, `:`, `.` | Survived in the recorded two-substitution trigger. | [Live-run §4](../exploits/tiz0wn-root/LIVE-RUN-2026-10-29.md#4-the-trigger); [builder canary note](../exploits/tiz0wn-root/builder/serve.py#L322-L331) |
| ASCII letters and decimal digits used in the command and address | Survived in the recorded trigger; the test pins the current concrete URL. This does not establish every letter in every position. | [Live-run §4](../exploits/tiz0wn-root/LIVE-RUN-2026-10-29.md#4-the-trigger); [exact-output test](../exploits/tiz0wn-root/tests/test_serve.py#L37-L45) |
| `${IFS}` as a complete token | Survived between command words. Braces are evidenced in this token, not as arbitrary standalone characters. | [Live-run §4](../exploits/tiz0wn-root/LIVE-RUN-2026-10-29.md#4-the-trigger); [exact-output test](../exploits/tiz0wn-root/tests/test_serve.py#L37-L45) |
| Literal space | Failed the measured field constraint; the trigger uses `${IFS}` in its place. | [Live-run §4](../exploits/tiz0wn-root/LIVE-RUN-2026-10-29.md#4-the-trigger); [builder canary note](../exploits/tiz0wn-root/builder/serve.py#L322-L331) |
| `<` | Failed the measured field constraint. The record does not specify how it failed. | [Builder canary note](../exploits/tiz0wn-root/builder/serve.py#L322-L331) |
| `\|` | The IME drops it on paste; successful end-to-end execution is unproven. | [Builder canary note](../exploits/tiz0wn-root/builder/serve.py#L322-L331) |
| `=` | Never tried in the recorded trigger; it remains unproven. | [Live-run §4](../exploits/tiz0wn-root/LIVE-RUN-2026-10-29.md#4-the-trigger); [builder canary note](../exploits/tiz0wn-root/builder/serve.py#L322-L331) |
| `;` | Never needed in the recorded trigger; it remains unproven. | [Builder canary note](../exploits/tiz0wn-root/builder/serve.py#L322-L331) |

The recorded form has two adjacent command substitutions: the first fetches
`/d` into `/tmp/x`, and the second sources that file. The current
`serve.build_password` output uses `/tmp/x$$` in both substitutions. The
[caller trace](DISCLOSURE.md#technical-detail) shows that each Shared Folder
action reaches `mount.smb.sh:72` and runs `/bin/bash -c`; `$$` stays equal
across the fetch and source in that shell and changes with a separate Bash
invocation. The [exact-output and two-shell tests](../exploits/tiz0wn-root/tests/test_serve.py#L39-L92)
pin this builder behavior. The builder enforces a **160-byte cap** after
rendering; its [length test](../exploits/tiz0wn-root/tests/test_serve.py#L94-L99)
checks the long-address case. `${IFS}` supplies word separation without a
literal space,
as shown by the [recorded trigger](../exploits/tiz0wn-root/LIVE-RUN-2026-10-29.md#4-the-trigger).

What a change must update:

- `serve.build_password` in [builder/serve.py](../exploits/tiz0wn-root/builder/serve.py#L322-L350).
- Its [exact-output, character-set and length tests](../exploits/tiz0wn-root/tests/test_serve.py#L39-L105).

A new character needs a canary and a test before `build_password` may emit it.
