# Q60T `dotnet-launcher` contract (T-70)

2026-11-04. Static audit only. No TV command or launcher execution was performed.
The live-copied `/tmp/dotnet-launcher` is a symbolized, 32-bit ARM PIE with
SHA-256 `6ba8efbc34cf3767e5d14a9ac660da79aa62c6a2bd0c88d5b62f91c70e500262`.
The earlier directory extraction under `/private/tmp/tiz-rootfs` and
`/private/tmp/tiz-rootfs2` has **zero-byte placeholders** for both
`usr/bin/dotnet-launcher` and `usr/share/dotnet_dummy/dotnet-launcher`; the
live copy, rather than those placeholders, supplies the executable evidence.
The extraction does contain readable loader configuration and scripts.

## Entry and argument evidence

`gobjdump -d -C /tmp/dotnet-launcher` shows `main` at `0x331c` branching
directly to `realMain` at `0x6c98` (`0x3320: b.w 6c98`). The following
instructions establish the argument split; addresses are ELF virtual
addresses, and the notes after the quotes are static inferences:

```text
6cac: cmp.w r9, #1             ; argc
6cfa: ldr.w r1, [r5, r4, lsl #2]  ; argv[i]
6d02: blx 2e04 <...basic_string...::compare(char const*) const@plt>
6ce8: ldr.w fp, [r7, #4]      ; argv[i+1] after first flag matches
6d0c: ldr r1, [r5, r6]       ; second flag comparison
6d22: ldr r6, [r5, #4]       ; argv[1]
6d46: blx 2bc4 <isManagedAssembly(...)@plt>
6fda: blx 2ee8 <isNativeImage(...)@plt>
```

The two compared global strings are constructed at `0x32d0` from rodata
`0x7bd8` (`--standalone`) and at `0x32e8` from `0x7be8`
(`--PADDING_TO_CHANGE_CMDLINE`). `--standalone` consumes its next token into
`fp`; the padding token is skipped. There is **no `--clr-path` string** in the
complete string inventory of this binary, nor a comparison for it in this
parser. `--help` is not a usage mode. The parser dereferences `argv[1]` at
`0x6d22` even when `argc <= 1` (branch `0x6cba` to `0x7344`), consistent with
the previously observed no-argument C++ null-string abort. That is an
implementation defect, not a meaningful help response.

For a direct DLL call, a positive `isManagedAssembly(argv[1])` result selects the binary's
"corerun mode" at `0x6d4c`/`0x6e9a`; the literal mode log is at rodata
`0x899c`. In that branch `0x71dc–0x71f4` passes the DLL and the remaining
arguments to `CoreRuntime::launch`. In the other path, the binary logs
"standalone mode" (rodata `0x8a00`), queries
`aul_app_get_appid_bypid` (`0x7090–0x709e`) and
`aul_get_app_root_path` (`0x724e`), then calls `CoreRuntime::launch`
at `0x71ac`. The AUL path is app registration and process-context dependent;
putting `--standalone` before an arbitrary staged DLL does not make it a
generic `dotnet` command.

`CoreRuntime::launch` checks the chosen executable path with `isFileExist`
at `0x4300–0x4314`, calls `pluginSetAppInfo` at `0x4356`, sets
`XDG_DATA_HOME` from `app_get_data_path` at `0x437e–0x4392`, then calls its
CoreCLR execute function through an initialized function pointer at
`0x43c8–0x43e0`. Its log strings include exact fragments
`File not exist : %s`, `execute assembly : %s`, and
`Failed to Execute Assembly %s (0x%08x)` (rodata `0x7cbc`, `0x7d60`,
`0x7d84`). `initializeCoreClr` calls the resolved `coreclr_initialize`
pointer with five properties at `0x4816–0x4832`; the binary imports
`getTPA`, `getRuntimeDir`, and `initializePathManager` from
`libdotnet_launcher_util`. Thus this is a direct CoreCLR host, not evidence
that it delegates to `/usr/bin/dotnet` or `hostfxr`.

## Exact contract table

“Required” here means supported by the cited static path. Unknowns stay
unknown where the extracted dependent libraries have zero-byte bodies.

| Invocation | Required files | Cwd | Environment / registration | Capability expectation | Evidence |
| --- | --- | --- | --- | --- | --- |
| `/usr/bin/dotnet-launcher /absolute/SamsungTvArchiveRoot.dll archive-root-<16 hex>` | A readable managed DLL at `argv[1]`; installed CoreCLR runtime and Tizen path-manager inputs. The assembly's own dependencies must resolve, but this binary does not establish that its adjacent `.deps.json` or `.runtimeconfig.json` is read. | No `chdir` import or direct `chdir` call in this binary; use an absolute DLL path. Behavior inside `libdotnet_launcher_util` is unavailable. | Direct “corerun mode” if `isManagedAssembly` accepts the DLL; `argv[2]` is forwarded as a managed argument. Initialization sets runtime and CoreCLR properties, including `TRUSTED_PLATFORM_ASSEMBLIES`, `APP_PATHS`, `APP_NI_PATHS`, and `NATIVE_DLL_SEARCH_DIRECTORIES` (rodata `0x8ae8–0x8b40`). No `AUL_APPID` is proven for this route. | The payload checks effective `CAP_SETGID` and `CAP_SYS_ADMIN` before mounts. The image capability assignment previously recorded in `archive-root-prereqs.md:18` names both; `dotnet-run-ni.sh:53` names a broader set. Actual live effective capabilities after this launch are unmeasured. | `realMain` `0x6d22–0x6d4e`, `0x6e9a`, `0x71dc–0x71f4`; `CoreRuntime::launch` `0x4300–0x4314`, `0x43c8–0x43e0`; `service.js:145–148`; `SamsungTvArchiveRoot.cs:20–52`; `archive-root-prereqs.md:18`. |
| AUL launch of a registered `type="dotnet"` app, with the configured padding and `--standalone` arguments | Installed app manifest/registry entry with executable path, app root, package and runtime assets. An arbitrary DLL path alone does not supply these. | Determined by AUL/launchpad; not recoverable from this binary alone. | Requires AUL process identity or root-path lookup. `/usr/share/aul/dotnet.launcher:1–6` supplies both extra args; `/usr/share/dotnet-runtime/dotnet.loader:1–11` selects `/usr/bin/dotnet-launcher`, `APP_TYPE dotnet`, `TIMEOUT|DEMAND`. | Same launcher binary and its configured file capability; app manager may further restrict process capabilities. | Parser `0x6cf8–0x6d20`; AUL calls `0x7090–0x709e`, `0x724e`; standalone launch `0x7160–0x71ac`; two config files named above. |
| `/usr/share/dotnet_dummy/dotnet-launcher ...` | Real binary and its zone/runtime tree are needed; extraction only has a zero-byte placeholder. | Unknown. | `dotnet-run-ni.sh:54` assigns the dummy path `cap_setgid,cap_sys_admin=ei`; zone configs bind the dummy tree. This does not prove that path is executable or accepts this DLL on the live TV. | Same named capabilities in the script, but no live result. | `/private/tmp/tiz-rootfs/usr/bin/dotnet-run-ni.sh:53–55`; zero-byte extracted `dotnet_dummy/dotnet-launcher`; zone config bind entries. **Not recommended.** |
| Vendor `corerun` host as a fallback | A real signed `corerun`, its matching CoreCLR files, and a valid app deployment. | Unknown; use absolute paths if examined later. | `dotnet-apps.txt:1` names `corerun`; developer-mode script links it into `/opt/dotnet/runtime` (`:22–36`). Its argument parser and live presence were not recovered here. | No file-capability assignment for `corerun` was established; running as root does not by itself prove the payload's effective capability mask. | `/private/tmp/tiz-rootfs/usr/bin/dotnet-apps.txt:1`; `dotnet-developer-mode.sh:22–36`. **Fallback candidate, not a proven call.** |

The launcher configuration's `EXTRA_ARG --standalone` is evidence for the
registered AUL path, not a reason to prefix the direct DLL invocation. The
`dotnet_dummy` tree is a development/zone fixture with a distinct capability
assignment; its copied file body is unavailable. `/usr/bin/dotnet` is absent
from this image inventory, so the Vetro/Chris `/usr/bin/dotnet <assembly>`
example is not a call for this set.

## Managed deployment and the present failure

The current project declares `<OutputType>Exe</OutputType>` but targets
`netstandard2.0` (`SamsungTvArchiveRoot.csproj:3–4`). The staged
`runtimeconfig.json` is handwritten for `netcoreapp3.0`; the service stages
only the DLL and that config, with no app `.deps.json`
(`service.js:46–62, 73–85`). This is **not a validated framework-dependent
`netcoreapp3.0` app deployment**. Microsoft documents the normal published
app output as a matching DLL, `.deps.json`, and `.runtimeconfig.json`
([publish guide](https://learn.microsoft.com/en-us/dotnet/core/tutorials/publishing-with-visual-studio?pivots=dotnet-6-0));
`netstandard2.0` and `netcoreapp3.0` are distinct target frameworks
([TFM list](https://learn.microsoft.com/en-us/dotnet/standard/frameworks/)).
That does **not** prove the missing deps file caused this TV failure: this
vendor binary calls CoreCLR directly and the unavailable
`libdotnet_launcher_util` may resolve dependencies without the usual
`hostfxr` files. [CoreCLR's hosting API](https://github.com/dotnet/runtime/blob/main/src/coreclr/hosts/inc/coreclrhost.h)
accepts host-supplied properties and an assembly path; this binary's imports
and calls follow that model.

The offline archive test substitutes `b"synthetic assembly"` for the DLL and
fakes the SDB command's reply (`test_chain.py:277–322`). It verifies staging
and command construction, not that this launcher loads managed code. The
compiled payload DLL is absent in this checkout, so its metadata and
dependencies could not be inspected. The reported TV `rc=1` with no
`launch.log` is consistent with rejection before managed `Main`, but does
not distinguish an initialization failure, a missing file, a CoreCLR load
failure, or an exception before the managed log write.

**Recommended call, once a real app deployment and runtime path are verified:**

```text
/usr/bin/dotnet-launcher /home/owner/share/tmp/sdk_tools/<package>/SamsungTvArchiveRoot.dll <package>
```

This is the existing direct invocation shape (`service.js:145–148`), and the
binary's `argv[1]` classification plus `0x71dc–0x71f4` argument forwarding
support it. Keep it unprefixed by `--standalone`, `--clr-path`, or the padding
token. A normal `netcoreapp3.0` publish with matching generated runtime files
is the smallest artifact correction to assess in a **separate code task**;
this audit does not claim that republishing alone will resolve the vendor
host's runtime or capability requirements.

If the call is wrong, distinguish these **exact** signatures, rather than
assuming every `rc=1` means bad CLI:

| Stage | Evidence-backed signature |
| --- | --- |
| No `argv[1]` | C++ abort with `basic_string::_M_construct null not valid` (reported no-arg observation and binary string `0x7720`; parser `0x6d22–0x6d40`). |
| File absent | Dlog `File not exist : %s` (`CoreRuntime::launch` `0x4300–0x4314`, string `0x7cbc`); launcher returns failure before managed `Main`. The dlog may not appear in redirected stdout/stderr. |
| Runtime initialization fails | Dlog `Failed to initialize` or `Failed to initialize coreclr` (strings `0x89dc`, `0x8830`), then nonzero launcher status. A missing `/opt/dotnet/runtime` or dependent library is one possible cause, not established here. |
| CoreCLR cannot execute the assembly | Dlog `Failed to Execute Assembly %s (0x%08x)` (string `0x7d84`, call `0x43dc`); inspect the hex result to separate load failure from managed exit. |
| Current observed invocation | `invoke.reply` contains `rc=1` and no managed `launcher.log`; no diagnostic text was reported. This observation by itself is not a unique failure signature. |

`--help`, no argument, the plain DLL call, and `--standalone <dll> <arg>`
were already observed to fail on the TV. No new live behavior is claimed here.
