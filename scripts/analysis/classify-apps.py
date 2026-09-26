#!/usr/bin/env python3
"""Classify a captured Tizen `applist` dump into must-keep / optional-candidate
/ unknown buckets, using ordered regex rules on the app ID and name only.

This is a naming/ID triage, NOT a dependency analysis (research doc §7.5): it
flags what is worth asking about, it does not establish that anything is safe
to remove. A random-looking store identifier sharing a bucket with other apps
does not prove a package relationship or that a function is unused elsewhere.

Input is the raw text captured by `scripts/02-capability.sh` via
`sdb shell 0 applist` (see scripts/lib/common.sh:sdb_capture), i.e. a header,
CRLF-terminated `'Name'<TAB> 'AppID'` lines, a `====...` footer and a trailing
`# exit code: N` line. Non-matching lines (header/footer/blank) are skipped.

Usage:
    classify-apps.py [applist.txt] [--unmatched]

If applist.txt is omitted, the newest file matching
evidence/runs/*-02-capability/applist.txt under the repo is used.
--unmatched prints only the entries that fell through to "unidentified", for
extending the rule table below.

Output: the grouped Markdown table (must keep / optional candidate / unknown)
on stdout, and total + per-bucket counts on stderr.
"""
import collections
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

KEEP, CAND, UNK = "must keep", "optional candidate", "unknown"

# Ordered rules: first match wins. (regex on app ID or name, bucket, group, note)
R = [
 # --- optional candidates: third-party store apps (prefix grouping presumed, §7.2) ---
 (r"^(8HwqClkwtp|9FhM0cODbY|aLlph042JZ|B5vuvi1Oky|cg2m3QSB89|g0nt8dscFO|My5jIduosH|GHI3a0zMSx|IpIKeB3u2B|KbRHmu0vrC|MCmYXNxgcu|Mo5FtpAjGy|ndmbVBabXx|rJeHak5zRg|SrAoJxGQUf|yPSlpvfeTf|vbUQClczfR|X1pKpFCiUu|9Ur5IzDKqV|AQKO41xyKP)\.",
  CAND, "store app", "reinstallable from store; package relationship presumed from prefix"),
 (r"^(PK700Cupra|TCVAAnsPTa|SSS02MyT3r|Y9sxevvNCT|NeV3gZvFmN|AkhP5nCr24)\.",
  CAND, "store app (promo/brand)", "lowest-risk first test; never-opened promo/brand app"),

 # --- keep, but switch off via menus (§4.6) ---
 (r"(adplatform|adplayer|ad-web-framework|adagent|yL49PNFmjW\.)", KEEP, "settings: ads", "turn off via privacy / Smart Hub autostart"),
 (r"(acr-service|contents-recognition|vision-data-recognition|content-grab)", KEEP, "settings: viewing info (ACR)", "turn off Viewing Information Services"),
 (r"(samsung-analytics|canalysis|rm-survey)", KEEP, "settings: analytics", "withdraw optional consents"),
 (r"(bixby|alexa|google-assistant|google-fullscreen|ondevice|cnvoice|voice|vif$|utterance|stt-client|multi-assistant)", KEEP, "settings: voice", "voice assistant: none / wake word off"),
 (r"(tvplus|tvPlusDeeplinker)", KEEP, "settings: TV Plus", "hide/disable in menu if offered"),

 # --- keep, inert in consumer mode ---
 (r"(\.ep[.-]|^ep-|ep-hotel|ephotel|ep-plateau|ep-boot|ep-system|ep-event)", KEEP, "inert: hotel/EP", "dormant in consumer mode"),
 (r"(factory|AgingApp|picture-test|sound-test|video-test|cobalt-app-|smarthub-connection-test|widget_viewer_sdk|automation-|remote-service-logging-debug)", KEEP, "inert: factory/test", "dormant; unknown dependencies"),
 (r"(demo-player|UsbSyncDisplay|HVPOP9POZU\.|welcome-mode|rscm-)", KEEP, "inert: retail demo", "store-demo mode"),

 # --- bundled platform apps: optional to the user, but not store-reinstallable as far as known ---
 (r"(netflix-app|primevideo|apple-music|aria-dummy|aria-video|aria-engine|lib-ariafw|^30IKH0OX8U\.|cobalt-(yt|ytkids|yttv|gpm)$)",
  UNK, "bundled platform app", "optional to use, but platform-namespaced; restore route unknown"),

 # --- core keep ---
 (r"(coba\.setting|homesetting|NetworkSetting|volume-setting|menu$|quickpanel|function-osd|alert-syspopup|dpm-syspopup|pvrrecorder-syspopup)", KEEP, "core: settings/UI", ""),
 (r"(coba\.(home|apps|search|source|livetv|dhcategory|home-notification)|commonsearch|searchall|fuzzy-search|ContentsBrowser|content-panel|content-tiles|shortcut|app-selector|RunningApps|notification|MultiScreenWebLauncher|Ja2mti1oVw\.|cloud-launcher|usb-launcher|safLaunchBridge|SAFCommonPlugin|litewebappservice|webappservice|comss$|rct-service|rct-app|ug-load|ug-ttx)", KEEP, "core: launcher/home", ""),
 (r"(tv-viewer|channel|epg|antenna|autosetup|stand-by-scan|broadcastingmenu|hbbtv|ci-app|nagsam|tv-scheduler|schedule-manager|reminder|pvr|SMSourceAPP|5-way-function|mbr-|waapp)", KEEP, "core: tuner/broadcast", ""),
 (r"(hdmicec|hdmi-troubleshooting|av-sync|AVControl|registerav|registertv|register-device|SmartRC|bt|bleproximity|nfc-monitor|NetworkSpeaker|aispeaker|connection-guide|isf-kbd|ise-default|screen-reader|tts-engine|screeneffector)", KEEP, "core: input/devices/accessibility", ""),
 (r"(chromium-efl|browser|knox-browser|csapi-tv-tizenfx|dotnet-policy|hybrid-aot|pvod-appfw|mde-framework|sealayer|autofill)", KEEP, "core: runtime/web engine", ""),
 (r"(\.store$|org\.volt\.apps|built-in-app|billing|CSBilling|preview-downloader|preview-updater|tvkey-preview)", KEEP, "core: store/app updates", ""),
 (r"(swu|update-client)", KEEP, "core: software update", ""),
 (r"(samsung-account|CSAccount|account-extra|coba\.samsungaccount|WebAccountExtension|sso|samsung-service-manager|provider-resetpsid|smarthub-reset|PrivacyChoices|privacychoice|samsung-pass|samsung-cloud|csa$)", KEEP, "core: account/privacy/Smart Hub", ""),
 (r"(easysetup|wizard|cloning|aoc-enabler)", KEEP, "core: setup", ""),
 (r"(ScreenMirroring|airplay|AirPlayWebApp|multiscreen|coba\.mv|coba\.msview|coba\.edenview|coss|csfw|csfs|csft|mobilebff|p2p-asm)", KEEP, "core: mirroring/sharing/MultiView", ""),
 (r"(smartthings|iot-|DeviceGraph|easysetup-mediator)", KEEP, "core: SmartThings/IoT", ""),
 (r"(ambient|-tpl$|coba\.ambient|contentimageapp)", KEEP, "core: Ambient/Art", ""),
 (r"(mycontent|photo-player|video-player|bmplayer|gallery|usb|emanual|EJZZ9Mr6D2|TVDeviceCare|qtMHjALHus|request-support|samsung-easy-support|remote-management)", KEEP, "core: media/manual/support", ""),
]

# Matches one raw `applist` line: '<Name>'<TAB or spaces>'<AppID>'.
# The header, "====" separator, and "# exit code: N" footer never match this.
_LINE_RE = re.compile(r"^'(.*?)'\s+'(.*?)'$")


def default_applist_path():
    """Newest evidence/runs/*-02-capability/applist.txt under the repo, or None."""
    candidates = list(REPO_ROOT.glob("evidence/runs/*-02-capability/applist.txt"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def parse_applist(path):
    """Yield (app_id, name) pairs from a raw `sdb shell 0 applist` capture.

    Tolerates the header/footer noise added by sdb and sdb_capture(), and
    CRLF line endings (str.splitlines() treats \\r\\n, \\r and \\n alike).
    """
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    for raw_line in text.splitlines():
        m = _LINE_RE.match(raw_line.strip())
        if not m:
            continue
        name, aid = m.group(1), m.group(2)
        yield aid, name


def classify(pairs):
    rows = []
    for aid, name in pairs:
        for pat, b, g, n in R:
            if re.search(pat, aid):
                rows.append((b, g, aid, name.strip(), n))
                break
        else:
            rows.append((UNK, "unidentified", aid, name.strip(), "purpose unclear from name/ID"))
    return rows


def main(argv):
    args = [a for a in argv if a != "--unmatched"]
    unmatched = "--unmatched" in argv

    if args:
        path = Path(args[0])
    else:
        path = default_applist_path()
        if path is None:
            print(
                "No applist.txt given and none found under "
                "evidence/runs/*-02-capability/applist.txt — run scripts/02-capability.sh "
                "first, or pass a path explicitly.",
                file=sys.stderr,
            )
            return 1

    rows = classify(parse_applist(path))
    if not rows:
        print(f"No applist entries parsed from {path}", file=sys.stderr)
        return 1

    if unmatched:
        for r in rows:
            if r[1] == "unidentified":
                print(r[2], "|", r[3])
        return 0

    cnt = collections.Counter(r[0] for r in rows)
    out = sys.stdout
    order = [KEEP, CAND, UNK]
    print(f"Total: {len(rows)} = " + " + ".join(f"{cnt[b]} {b}" for b in order), file=sys.stderr)
    for b in order:
        sub = sorted([r for r in rows if r[0] == b], key=lambda r: (r[1], r[2].lower()))
        print(f"\n## {b.capitalize()} ({len(sub)})\n", file=out)
        gc = collections.Counter(r[1] for r in sub)
        print("Groups: " + ", ".join(f"{g} ({c})" for g, c in sorted(gc.items())) + "\n", file=out)
        print("| Group | App ID | Name | Note |\n|---|---|---|---|", file=out)
        for _, g, aid, name, n in sub:
            print(f"| {g} | `{aid}` | {name.replace('|', '/')} | {n} |", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
