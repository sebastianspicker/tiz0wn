# Archive route prerequisites on GQ55Q60TGUXZG, T-NKLDEUC-2743.0

Offline inventory of the supplied `fw-analysis/dec/platform.img` (1,328,484,368
bytes) and `fw-analysis/extract`. Offsets below are **zero-based byte offsets in
`platform.img`**, found with bounded `grep -abo` matches and checked with short
`dd`/`strings` windows. A later partial extraction (`/tmp/tiz-rootfs2`) has
46,258 files, but every binary body is **zero bytes** and symlinks are unresolved; the earlier
`extract` tree has directories only. Treat both as path/name evidence, not as
proof that an ELF body or mode is usable. Directory names alone are not evidence that a binary exists or runs.
Raw catalog names and plaintext windows support the findings below; executable
modes, symlink targets, on-device overlays and effective capabilities remain
unverified.

| Prerequisite | Result | Path, image evidence and method |
| --- | --- | --- |
| .NET host | **absent** | No `/usr/bin/dotnet` catalog entry was found in the image's `/usr/bin` name region; the two exact `dotnet\0` catalog names at offsets `1283237338` and `1287483314` are under `/usr/share`, not `/usr/bin`. Text references to `/usr/bin/dotnet` at `738246748` and `741457973` are launcher configuration, not a host entry. The bounded capability list at `745717760–745722623` has no `/usr/bin/dotnet =` line. This is an absence in the base image, not a claim about a live overlay. |
| .NET launcher | **pass** | `/usr/bin/dotnet-launcher`: catalog name at `1314248642`; launcher configuration names it as `EXE` at `741457973` and supplies `--standalone` at `741458072` (short `dd` windows). Its extracted file and mode are unavailable. |
| Launcher file capability assignment | **pass** | `/usr/bin/dotnet-launcher = cap_setgid,cap_sys_admin+ei` at `745720183` in the raw capability assignment list. `/usr/bin/dotnet-hydra-launcher` has the same assignment at `745722529`. These are static assignments, not a measured `getcap` result. |
| Capability list source filename | **unknown** | The list begins at image offset `745717760` and contains the launcher assignment above, but the directory-only extraction does not associate that content with a source pathname. No pathname is inferred from the adjacent `/usr/share/security-config` directory. |
| .NET runtime and version | **pass** | Extracted directory `/usr/share/dotnet-runtime/shared/Microsoft.NETCore.App`; raw catalog has `Microsoft.NETCore.App` at `1283226634` and `3.0.0` at `1283226258`. A plaintext configuration path `/usr/share/dotnet/shared/Microsoft.NETCore.App/3.0.0` starts at `743849984`. The image also names `/usr/share/dotnet.tizen/framework`; the runtime's actual file bodies and live mount selection are unverified. |
| Signed-archive launcher | **pass** | `/usr/sbin/sdbd-tarlauncher`: catalog name at `1318423682` (also `1318504050`) in the `/usr/sbin` name region. The extracted `/usr/sbin` is empty, so existence is based on the raw catalog entry; mode and body are unverified. |
| Signed-archive public key | **pass** | `/usr/share/sdbd/public.pem`: the extracted `/usr/share/sdbd` directory exists, and the raw catalog window pairs `sdbd` at `1283249794` with `public.pem` at `1283249826` (another `public.pem` entry is at `1283249442`). Key bytes are unavailable in this extraction. Other `public.pem` strings in the image refer to unrelated certificate names. |
| SDK temporary tools default | **pass** | `/home/owner/share/tmp/sdk_tools` is derived from the image's SDK variable file: `TZ_SYS_DEFAULT_USER=owner` at `703915084`, `TZ_SDK_HOME=/home/${TZ_SDK_USER_NAME}` at `703917093`, and `TZ_SDK_TOOLS=${TZ_SDK_HOME}/share/tmp/sdk_tools` at `703917131`. A separate SDB plugin command string names the concrete path in `docs/firmware-analysis.md` (F13). This is a configured writable-home path, not a directory expected in the read-only rootfs. |
| Private namespace and mount | **unknown** | The image catalog names `unshare` at `1314041226` and `mount` at `1313770634`; `/usr/bin/mount` also occurs in script text at `1150685226`. Creating a mount namespace and mounting need `CAP_SYS_ADMIN`; the launcher assignment includes it, but this inventory cannot show that an app-started process retains it across execution or that the TV permits the operations. |
| Assembly path and argument forwarding | **unknown** | `/usr/bin/dotnet-launcher` is selected by launcher configuration at `741457973`, with `EXTRA_ARG --standalone` at `741458072`. That establishes configured arguments, not acceptance of an arbitrary assembly pathname and trailing arguments. Its binary body is unavailable for offline parsing here. |
| Developer Mode runtime setup | **pass** | `/usr/bin/dotnet-developer-mode.sh` is a catalog name at `1314247562`, and a raw script refers to and invokes it at `1150220177–1150220283`. A separate plaintext setup window at `1149898752` tests `db/sdk/develop/mode`, uses `CORECLR_VERSION="3.0.0"` at `1149899552`, and sets up `/opt/dotnet/runtime/` symlinks to `/usr/share/dotnet_org/shared/Microsoft.NETCore.App/`. The empty extraction does not let us attribute that setup window to a specific script file or verify its execution on the TV. |

Counts: **7 pass, 3 unknown, 1 absent**. The three live-probe questions are:

1. Does the running TV expose the same host/launcher paths and effective file capabilities, including any overlay changes?
2. Does an app-started `dotnet-launcher` accept an assembly path plus trailing arguments?
3. Can that process create the private mount namespace and mount needed for the signed-archive launcher, and does the launcher accept an archive under the installed public key?
