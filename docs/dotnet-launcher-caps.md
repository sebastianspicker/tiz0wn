# Q60T dotnet launcher capabilities (T-71)

2026-11-04. Static audit of the live-copied `/tmp/dotnet-launcher` only. No TV
command or launcher execution was performed. SHA-256:
`6ba8efbc34cf3767e5d14a9ac660da79aa62c6a2bd0c88d5b62f91c70e500262`.
Addresses below are ELF virtual addresses from `objdump -d -C`. The measured
`Uid: 0 0 0 0`, `Gid: 901 901 901 901`, zero `CapInh`, `CapPrm`, and `CapEff`,
and `CapBnd: 0000000300200040` are supplied live observations, not outcomes of
this audit.

## Standalone is a path argument, not a privilege mode

At `0x6cf8–0x6d20`, the parser compares each token with `--standalone` and
`--PADDING_TO_CHANGE_CMDLINE`. A `--standalone` match loads the **following**
token into `fp` (`0x6ce8: ldr.w fp, [r7, #4]`) and advances past both tokens.
The padding match advances past that token only (`0x6d18–0x6d20`). Other
tokens enter the forwarded-argument vector (`0x6e82–0x6e98`). The standalone
flag also sets `sl=1` at `0x6cee`, which selects the standalone path at
`0x6d76–0x6d7a` **after** `argv[1]` has been classified by
`isManagedAssembly` (`0x6d22–0x6d4e`) and `isNativeImage` (`0x6fba–0x6fe0`).
If `argv[1]` is recognized as a managed assembly, the direct corerun branch
at `0x6e9a` runs instead, regardless of the flag encountered later.

The standalone path calls `aul_app_get_appid_bypid(getpid(), ..., 52)` at
`0x7090–0x709e`. On a zero return it calls `aul_get_app_root_path` at
`0x724e`; the meaning of that return value is in the unavailable AUL library.
It does **not** bypass AUL app info.
It takes `baseName(fp)` at `0x70d4–0x70e6`, then calls
`CoreRuntime::launch(this, app-id-or-root, basename, fp, remaining-argc,
remaining-argv)` at `0x7198–0x71ac`. Before that call, `0x716e–0x7194`
overwrites `argv[0]` using `memset` and `snprintf` to change the displayed
process name; the padding flag changes the available name buffer length at
`0x716e–0x717c`. Neither flag requests or preserves capabilities. A bare
`--standalone <dll>` from a root shell has no registered AUL identity merely
because the path exists.

## Call-ordered capability boundary

The live binary has no dynamic `capset`, `prctl`, `setresuid`, `setresgid`,
`setuid`, `setgid`, or `syscall` import and no `svc`/`swi` instruction in its
disassembled `.text`. The table distinguishes actual calls from possible
effects inside unavailable dependencies. The extracted
`liblaunchpad.so.0.10.3`, `libaul.so.0.20.4`, and `libdotnet_plugin.so` under
`/tmp/tiz-rootfs2/usr/lib` are zero-byte placeholders, so their internals
cannot be disassembled here.

| Order | Call site in `dotnet-launcher` | Capability conclusion |
| --- | --- | --- |
| 0 | Kernel `execve` into the launcher, before `main` (`0x331c`) | A possible credential transition. The supplied `getcap` and parent-shell masks do not measure the launcher's **entry** mask. No `execve` trace is available. |
| 1 | `0x6d66`: `CoreRuntime::CoreRuntime`; inside, `0x49c6`: `initializePluginManager` | External plugin initialization runs on both paths. Its implementation and capability effects are unavailable. |
| 2a, direct DLL | `0x6f74`: `CoreRuntime::initialize(true)` | The recognized-managed-assembly branch goes here, then to `0x71dc–0x71f4`. It does **not** call `launchpad_loader_main`. The observed direct-DLL managed `Main` therefore cannot be attributed to that launchpad call by this binary. |
| 2b, no `--standalone` | `0x6e46`: `LaunchpadAdapterImpl::loaderMain`; `0x3a66`: `launchpad_loader_main` | This is the external launchpad handoff when neither a managed/native `argv[1]` nor the standalone flag selects another path. The installed AUL config supplies `--standalone`, so this call is **not** on that configured route either. Its callback calls `aul_get_app_root_path` at `0x3c1c`; the library body and any cap effect are unavailable. |
| 3, standalone | `0x7090`: `getpid`; `0x7098`: `aul_app_get_appid_bypid`; fallback `0x724e`: `aul_get_app_root_path`; `0x7164`: `CoreRuntime::initialize(true)` | AUL lookup remains in the standalone path. None of these visible instructions changes Linux credentials. |
| 4, both launch paths | `0x71ac` or `0x71f4`: `CoreRuntime::launch`; `0x435a`: `pluginSetAppInfo(app-id-or-root, assembly-path)` | This is the last named app-info call before managed execution. Its library implementation is unavailable, so it is a **candidate boundary**, not a proven cap-clear call. |
| 5, both launch paths | `0x439a`: `pluginBeforeExecute`; `0x43dc–0x43de`: indirect CoreCLR execute call | The measured zero effective mask by managed `Main` means any post-entry clearing happened no later than this transition, but this static binary cannot select `pluginSetAppInfo`, `pluginBeforeExecute`, another dependency, or the earlier `execve` as the exact clearing instruction. |

**Cap-clear call site: unresolved.** There is no direct cap-clear call site in
the available launcher. The narrowest visible post-entry interval for the
direct DLL path is external plugin initialization (`0x49c6`) through
`pluginSetAppInfo` (`0x435a`) and `pluginBeforeExecute` (`0x439a`) before the
CoreCLR execute call (`0x43de`); the earlier `execve` remains an alternative
without an entry mask. Calling `0x3a66` the cause of the observed direct-DLL
drop would contradict the branch at `0x6d70–0x6d72`.

## Vendor registration and packaging

The rootfs contains two `type="dotnet"` vendor service examples. The source
`/tmp/tiz-rootfs2/usr/apps/com.samsung.tv.bt-mdemanager/tizen-manifest.xml`
declares `package` and `appid` `com.samsung.tv.bt-mdemanager`,
`exec="BtMdeManager.dll"`, `type="dotnet"`, and an empty `<privileges>`.
Its installed registry copy at
`/tmp/tiz-rootfs2/usr/share/packages/com.samsung.tv.bt-mdemanager.xml`
resolves `exec` to
`/usr/apps/com.samsung.tv.bt-mdemanager/bin/BtMdeManager.dll`.
`com.samsung.tv.tvkey-preview` has the same registered type and an absolute
DLL path in `/usr/share/packages/com.samsung.tv.tvkey-preview.xml`; it lists
`appmanager.launch`, an **API privilege**, not a Linux capability. Neither
manifest declares `CAP_SETGID` or `CAP_SYS_ADMIN`.

The installed AUL launcher record
`/tmp/tiz-rootfs2/usr/share/aul/dotnet.launcher` selects
`EXE /usr/bin/dotnet-launcher`, `APP_TYPE dotnet`, and ordered extra tokens
`--PADDING_TO_CHANGE_CMDLINE`, `--standalone`. The loader record
`/tmp/tiz-rootfs2/usr/share/dotnet-runtime/dotnet.loader` selects the same
executable and app type with `DETECTION_METHOD TIMEOUT|DEMAND` and `ON_BOOT
OFF`. AUL therefore selects the host from `type="dotnet"` and supplies the
registered executable path and app identity; the registry's absolute `exec`
is not an alternate shell command. The exact runtime `argv` layout assembled
inside AUL is unavailable, but the parser requires this shape:

```text
AUL launch of <package>.ArchiveService (registered type=dotnet)
  -> /usr/bin/dotnet-launcher
     --PADDING_TO_CHANGE_CMDLINE --standalone <registered-absolute-DLL-path>
     [AUL-supplied application arguments]
```

This is a **configuration and parser reconstruction**, not an observed AUL
command line. In contrast, `/usr/bin/dotnet-launcher <dll> <arg>` selects the
direct corerun branch. The script
`/tmp/tiz-rootfs2/usr/bin/dotnet-run-ni.sh:53–54` assigns broad file caps to
the real launcher and `cap_setgid,cap_sys_admin=ei` to the separate dummy
path; those assignments and the supplied live `getcap` do not establish
effective caps inside managed `Main`.

The supported minimal deployment is a **separate dotnet service `.tpk`**,
registered by AUL, alongside the existing web `.wgt` if the web component
is still needed. The [Tizen TV compliance specification, §§2.8.1–2.8.2 and
4.2](https://docs.tizen.org/platform/compliance/media/tizen-6.0-compliance-specification-for-tv-profile-v1.0.pdf)
requires `.wgt` for Web apps and `.tpk` for .NET apps. Tizen's
[hybrid packaging guide](https://docs.tizen.org/application/web/guides/development/)
describes a `.wgt` with a Web UI and **native** service applications; it does
not extend that combination to a dotnet component. Thus a Web app plus a
`type="dotnet"` component in one `.wgt` is **not a documented supported
package** on this TV profile. No hybrid/dotnet `.wgt` skeleton is proposed.

Minimal `.tpk` manifest skeleton, following the two vendor service manifests
(illustrative IDs and DLL name; the install path is assigned by the package
manager):

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns="http://tizen.org/ns/packages"
          package="example.archive" version="1.0.0"
          api-version="4" type="tpk">
  <profile name="tv"/>
  <service-application appid="example.archive.ArchiveService"
                       exec="SamsungTvArchiveRoot.dll"
                       type="dotnet" multiple="false"
                       nodisplay="true" launch_mode="single"/>
  <privileges/>
</manifest>
```

The package also needs the matching managed DLL and its runtime assets under
its installed `bin/` tree. The existing web package remains defined by
`exploits/tiz0wn-app/config.xml`; the managed project is
`exploits/tiz0wn-app/payload/SamsungTvArchiveRoot.csproj`. A separate build
task would need a `.tpk` manifest, package output, and an AUL launch by the
registered app ID. No current file or manifest element proves that an
ordinary developer-signed dotnet app can retain `CAP_SETGID` and
`CAP_SYS_ADMIN`; Tizen's [TV privilege rules, §2.7](https://docs.tizen.org/platform/compliance/media/tizen-6.0-compliance-specification-for-tv-profile-v1.0.pdf)
govern API privileges and signing level, not a request for raw Linux caps.
Registration fixes the supported host/app identity path, **not** the measured
capability failure. There is no `--standalone` or padding invocation shown by
this binary to preserve caps.
