# Node 4.4 service audit (T-65)

2026-11-04. Scope: the owned Q60T, measured service runtime `v4.4.3`. The
reported TV observations are `/run` returning a UID line and `/root` ending in
an empty reply. This is an offline audit; no TV command was run. The current
`config.xml` has no `on-boot` attribute.

## API compatibility

“TV” below is an API conclusion from the official v4.4.3 manuals, **not** a
claim that the TV executed that call. “4.9” is the `node:4.9-alpine` image,
which reported `v4.9.1`. The Node history pages give mainline introduction
versions; the v4.9 branch contains some later backports, so the version number
alone is insufficient. The [v4.4.3 Buffer](https://nodejs.org/download/release/v4.4.3/docs/api/buffer.html),
[fs](https://nodejs.org/download/release/v4.4.3/docs/api/fs.html),
[crypto](https://nodejs.org/download/release/v4.4.3/docs/api/crypto.html),
[zlib](https://nodejs.org/download/release/v4.4.3/docs/api/zlib.html), and
[child process](https://nodejs.org/download/release/v4.4.3/docs/api/child_process.html)
manuals are the baseline.

| API / caller | Introduced | TV v4.4.3 | Docker v4.9.1 | Evidence and implication |
| --- | --- | --- | --- | --- |
| `Buffer.alloc`, `Buffer.from` in `service.js` and `sdb.js` | v5.10.0 mainline | **Missing natively**; service installs a local shim before loading `sdb.js` | Available natively | [Buffer history](https://nodejs.org/api/buffer.html) and v4.4.3 manual omit both. `/run` reaching SDB supports the *used shim path*, not native availability. The shim covers the string/UTF-8 and allocation forms used here; it is not a full `Buffer.from` replacement. |
| `crypto.generateKeyPairSync` in [Vetro's `platform.js`](https://github.com/andrearicci93/vetro/blob/main/rooting/service/platform.js), **not this service** | v10.12.0 | Missing | Missing | [Crypto history](https://nodejs.org/download/release/v14.21.3/docs/api/crypto.html). Vetro guards the call and reports `platformUnsupported`; this service uses external `openssl` plus `createSign` instead. |
| `fs.mkdtempSync`, used in the host test suite, **not this service** | v5.10.0 mainline | Missing from v4.4.3 manual | Available (4.x backport) | [FS history](https://nodejs.org/api/fs.html); v4.4.3 manual has no entry, while [v4.9.1 manual](https://r2.nodejs.org/docs/latest-v4.x/api/fs.html) does. The service uses `mkdirSync` with a random name. |
| `fs.rmSync`, used in the host test suite, **not this service or Vetro's runtime** | v14.14.0 | Missing | Missing | [FS history](https://nodejs.org/api/fs.html). Vetro implements recursive removal with `lstatSync`, `readdirSync`, `unlinkSync`, and `rmdirSync`. |
| `zlib.gzipSync` in `tarArchive` | v0.11.12 | Available by documentation; not proved on TV `/root` | Available; exercised | [Zlib history](https://nodejs.org/api/zlib.html) and v4.4.3 manual. Its presence does not explain an API-missing crash. |
| `crypto.createSign` / `createVerify` in `prepareArchive` | v0.1.92 | Available by documentation; not proved on TV `/root` | Available; exercised | [Crypto history](https://nodejs.org/api/crypto.html) and v4.4.3 manual. Vetro's separate one-shot `crypto.sign` is [v12.0.0](https://nodejs.org/api/crypto.html) and unavailable here. |
| `child_process.execFile` with `timeout` for `openssl` | v0.1.91 (`execFile`) | Available by documentation; `openssl` executable and its TV behavior unknown | Available; exercised | [Child process history](https://nodejs.org/api/child_process.html) and v4.4.3 manual. The executable is an external prerequisite, not a Node API. |
| `fs.writeFileSync(path, data, {mode, flag:'wx'})` | v0.1.29 (`writeFileSync`) | Available by documentation; `/run` does not reach archive writes | Available; exercised | [FS history](https://nodejs.org/api/fs.html) and v4.4.3 manual document the `mode` and `flag` options. |

The **only newer-than-v4.4 native calls in the current service source** are
`Buffer.alloc` and `Buffer.from`; the compatibility shim precedes their first
use. `crypto.randomBytes`, `fs.mkdirSync`, `fs.readFileSync`, and `net`/`http`
are baseline APIs. `/run` does not traverse tar creation, `openssl`, signing,
the .NET launcher, or archive callback handling. It therefore cannot establish
that any of those `/root` dependencies work on the TV. Their TV runtime status
remains **unknown** even when their Node API is documented available.

## Local reproduction and crash stack

`docker run --rm --platform linux/amd64 node:4.9-alpine node --version`
returned `v4.9.1` (exit 0). A temporary copy of the current service, dummy
assembly bytes, and a local fake SDB socket on `127.0.0.1:26101` exercised the
real `/run` and `/root` HTTP handlers with the required loopback `Origin`.
The fake spoke the service's CNXN/capability/shell frames and returned a
synthetic UID callback. It did **not** run the TV launcher or establish root.

The unmodified Alpine image has no `openssl` executable. `/run` returned HTTP
200 with the synthetic `uid=0(root)` line; `/root` returned **HTTP 502** with
`{"error":"spawn openssl ENOENT"}`. Calling exported `archiveRoot` directly
captured this exact handled exception stack:

```text
Error: spawn openssl ENOENT
    at exports._errnoException (util.js:907:11)
    at Process.ChildProcess._handle.onexit (internal/child_process.js:189:32)
    at onErrorNT (internal/child_process.js:363:16)
    at nextTickCallbackWith2Args (node.js:511:9)
    at process._tickCallback (node.js:425:17)
```

When a temporary `openssl` fixture supplied a valid host-generated RSA key
pair, the same Node 4.9 run returned HTTP 200 for **both** `/run` and `/root`,
and `archiveRoot` reported no exception. This proves the current path can
complete under 4.9 with fake SDB replies; it does **not** reproduce the TV's
empty reply or prove v4.4.3 behavior. In particular, 4.9 has native
`Buffer.alloc`/`Buffer.from` and `fs.mkdtempSync` while the v4.4.3 manual does
not. The real TV failure remains unresolved; assigning it to `gzipSync` or
`createSign` would contradict the v4.4.3 documentation.

## Archive design: prebuild and sign once

**Choose a prebuilt archive.** The local [archive payload](../exploits/tiz0wn-app/payload/SamsungTvArchiveRoot.cs)
passes the validated package name separately to `sdbd-tarlauncher`; it selects
`on-demand/<package>.tar.gz` by path. The tar built by `tarArchive` contains
only `launch.sh`, so the package name need not be signed into the tar. Make the
script bytes independent of each random staging path (the current script
embeds `paths.launchLog`), then package one byte-stable `launch.sh` tarball,
its RSA-SHA256 signature, and the matching public key into the WGT. Copy the
identical tar and signature bytes to each per-request package filename; keep
the private signing key **offline and out of the WGT**. Confirm the exact
archive member, signature, and launcher argument contract in the existing
[archive tests](../exploits/tiz0wn-app/tests/archive/test_chain.py).

This removes runtime tar compression, `openssl` process creation, key
generation, and signing. It also removes per-run signing-key churn. It does
**not** remove all runtime `crypto`: the current package ID, token, and SDB
gate values still use `crypto.randomBytes`, which is a supported v4.4 API and
should remain unpredictable. A fixed key increases the consequence of an
offline private-key leak; rotate it deliberately. Each change to `launch.sh`
requires regenerating the tar.gz and its signature, updating their pinned
hashes/test fixtures, rebuilding and signing the WGT, and verifying that the
WGT contains the new bytes. Regenerate the public key too **only if** the RSA
key changes. The archive path and staged public key must match on every run.

## Persistence without USB

| Route | Privilege / prerequisite | Cold-boot evidence | Reversal | Confidence |
| --- | --- | --- | --- | --- |
| `<tizen:service on-boot="true">` | [Tizen runtime spec](https://docs.tizen.org/platform/compliance/media/tizen-3.0-wrt-core-spec.pdf) requires Partner level; [Samsung](https://developer.samsung.com/smarttv/develop/faq/privileges.html) requires a Partner distributor certificate bound to the test DUID. An author cert alone is insufficient. | None for this app; current manifest does not request it. | Remove flag and reinstall. | High for entitlement rule, unknown for this TV. |
| `package_app_info.app_onboot` | Root access to `/opt/dbspace/.pkgmgr_parser.db`; [Vetro's implementation](https://github.com/andrearicci93/vetro/blob/main/app/service/component-actions.js) backs up and updates the flag. It is a registry workaround, not a documented entitlement. | Vetro source reports its own public-signed service flags could be false; no Q60T cold boot result. | Restore saved field value, then read it back. | Medium for Vetro mechanism, low for Q60T boot effect. |
| Existing `profile.d` hook invoking signed `/usr/bin/app_launcher -s tiz0wnprob.Service` | Existing UID-0 carrier/boot hook and installed app; service manager readiness and launcher behavior need testing. Use the hook's content-invoked form under UEP. | Hook survived three full power cycles; **app launch from it has not been observed**. Vendor units use `app_launcher -s` for named services ([local boot inventory](../exploits/tiz0wn-app/docs/BOOT.md)). | Disable the app-start branch; existing hook enable/rollback remains available. | High for hook, low for app-start step. |
| Already-persistent root agent | Existing root hook, enabled agent, and its PID/start-time identity checks. It can supervise a later app-start request without requiring the app's own boot entitlement. | Agent/root hook persistence documented in [root runbook](../exploits/tiz0wn-root/README.md); no app relaunch proof. | Disable the supervisor job or hook and use existing rollback. | High for agent survival, low for proposed app supervision. |

**Recommendation:** use the existing persistent root agent as the controller
for a bounded, logged `app_launcher -s` attempt after app services are ready;
have the existing `profile.d` hook start that agent. This needs no USB and no
Partner entitlement. Do not claim the app starts at boot until a full power
cycle shows its service process, `/state`, and `/run` again. The
[Tizen Web-service guide](https://github.com/Samsung/tizen-docs/blob/master/docs/application/web/guides/applications/service-app.md)
documents service registration, `onStart`/`onStop`, and UI `startService`, but
it does not establish this Q60T's cold-boot behavior.

## Three offline gates for each design

| Gate | Prebuilt archive | Agent-controlled app start |
| --- | --- | --- |
| 1 | Under Docker Node 4.9, run `/run` then `/root` against a fake SDB socket with no runtime `openssl` dependency; assert HTTP status and bounded callback. | In a shell/container fixture, replay the existing boot hook with the agent enabled and app manager initially absent, then present; assert one bounded launch attempt and no boot stall. |
| 2 | Extract the packaged tar, assert exactly `launch.sh` and byte-exact expected script; verify the signature with the packaged public key; mutate one byte and assert refusal. | Stub `app_launcher -s` and agent PID/start-time reads; assert idempotency, retry bound, failure log, and no false `agentAlive` when a PID is reused. |
| 3 | Stage the same tar/signature under two distinct valid package filenames; fake the launcher and assert the selected archive, signature, key, and argument order match, without a per-package tar rebuild. | Exercise the disable and rollback fixture: stop launch attempts, preserve recovery state, and verify the previous agent/hook path still starts. |

These gates can reject a bad design before TV contact. They cannot prove TV
certificate policy, launcher timing, or cold-boot survival; those require a
separately authorized live power-cycle observation.
