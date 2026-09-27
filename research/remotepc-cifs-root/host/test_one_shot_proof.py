"""Offline contracts for the Remote PC/CIFS one-shot proof harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import one_shot_proof as proof


class FakeRunner(proof.Runner):
    def __init__(self, results=()):
        self.results = list(results)
        self.calls: list[tuple[str, ...]] = []

    def run(self, arguments, **_kwargs):
        self.calls.append(tuple(arguments))
        if self.results:
            return self.results.pop(0)
        return subprocess.CompletedProcess(arguments, 0, "", "")


def completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess((), returncode, stdout, stderr)


def absent(name: str):
    return completed(1, "[]\n", f"error: no such object: {name}\n")


IMAGE_ID = "sha256:" + "a" * 64


def image_inspect(context_sha256: str, *, image_id: str = IMAGE_ID, labels=True):
    configured = {proof.LAB_CONTEXT_LABEL: context_sha256} if labels else None
    return completed(stdout=json.dumps([{"Id": image_id, "Config": {"Labels": configured}}]))


def identity() -> proof.RunIdentity:
    return proof.RunIdentity(
        run_id="1" * 16,
        share="Q6" + "2" * 10,
        marker="/tmp/q60t-rpc-" + "3" * 16,
        gate_token="4" * 16,
        stage="/home/owner/share/tmp/sdk_tools/r" + "5" * 16,
        container="tiz0wn-rpc-" + "1" * 16,
    )


def config(sdb: Path = Path("/bin/sh")) -> proof.TargetConfig:
    return proof.TargetConfig(
        sdb=sdb,
        tv_ip="192.168.50.20",
        tv_serial="192.168.50.20:26101",
        host_ip="192.168.50.10",
        model=proof.MODEL,
        firmware=proof.FIRMWARE,
        tv_id_sha256="a" * 64,
    )


class ProofContracts(unittest.TestCase):
    def test_pinned_local_firmware_members_and_sink(self):
        self.assertEqual(proof.sha256_file(proof.DEFAULT_ROOTFS), proof.ROOTFS_SHA256)
        observed = proof.audit_firmware(proof.DEFAULT_ROOTFS)
        self.assertEqual(observed, proof.MEMBER_HASHES)

    def test_default_mode_is_offline_and_does_not_read_config(self):
        with mock.patch.object(proof, "audit_firmware", return_value=proof.MEMBER_HASHES) as audit, \
             mock.patch.object(proof, "load_target_config") as load, \
             mock.patch.object(proof.socket, "create_connection") as connect, \
             mock.patch.object(proof.subprocess, "run") as run:
            self.assertEqual(proof.main([]), 0)
        audit.assert_called_once()
        load.assert_not_called()
        connect.assert_not_called()
        run.assert_not_called()

    def test_live_options_are_rejected_without_live_mode(self):
        with mock.patch.object(proof, "audit_firmware") as audit:
            self.assertEqual(proof.main(["--confirm", proof.LIVE_CONFIRMATION]), 1)
        audit.assert_not_called()

    def test_all_exact_live_authorizations_are_required(self):
        base = argparse.Namespace(live=True, confirm=proof.LIVE_CONFIRMATION,
                                  ack_saved_profile=proof.PROFILE_ACK,
                                  ack_no_retry=proof.NO_RETRY_ACK)
        proof.require_live_authorization(base)
        for field in ("confirm", "ack_saved_profile", "ack_no_retry"):
            values = vars(base).copy()
            values[field] = "wrong"
            with self.subTest(field=field), self.assertRaises(proof.ProofError):
                proof.require_live_authorization(argparse.Namespace(**values))

    def test_fresh_names_are_valid_and_nonreused(self):
        values = iter(("01" * 8, "02" * 5, "03" * 8, "04" * 8, "05" * 8))
        item = proof.fresh_identity(lambda _size: next(values))
        self.assertEqual(item.share, "Q6" + "02" * 5)
        self.assertEqual(item.payload, "$(/usr/bin/id>/tmp/q60t-rpc-" + "03" * 8 + ")")
        self.assertRegex(item.stage, r"/r[0-9a-f]{16}$")
        duplicate = iter(("01" * 8,) * 5)
        with self.assertRaises(proof.ProofError):
            proof.fresh_identity(lambda _size: next(duplicate))

    def test_identity_ledger_stores_only_hashes_and_rejects_reuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger = Path(temporary) / "used.sha256"
            item = identity()
            proof.reserve_identity(item, ledger)
            contents = ledger.read_text().splitlines()
            self.assertEqual(len(contents), 5)
            self.assertTrue(all(len(line) == 64 for line in contents))
            self.assertNotIn(item.marker, ledger.read_text())
            with self.assertRaises(proof.ProofError):
                proof.reserve_identity(item, ledger)

    def test_payload_is_literal_and_never_host_shell_expanded(self):
        marker = "/tmp/q60t-rpc-" + os.urandom(8).hex()
        path = Path(marker)
        self.assertFalse(path.exists())
        payload = proof.build_payload(marker)
        result = subprocess.run(("/usr/bin/printf", "%s", payload), capture_output=True,
                                text=True, check=True)
        self.assertEqual(result.stdout, payload)
        self.assertFalse(path.exists())
        self.assertNotIn("shell=True", Path(proof.__file__).read_text())

    def test_safe_config_parser_expands_only_known_values(self):
        values = proof.parse_config_text(
            'SDB="$HOME/tizen/sdb"\nTV_IP="192.168.1.2"\n'
            'TV_SERIAL="${TV_IP}:26101"\n', home="/safe/home")
        self.assertEqual(values["SDB"], "/safe/home/tizen/sdb")
        self.assertEqual(values["TV_SERIAL"], "192.168.1.2:26101")
        for bad in ('SDB="$(touch /tmp/no)"', 'SDB=`id`', 'SDB="$UNKNOWN/x"',
                    'EVIL="x"'):
            with self.subTest(bad=bad), self.assertRaises(proof.ProofError):
                proof.parse_config_text(bad, home="/safe/home")

    def test_target_api_identity_fails_closed(self):
        observed_id = "uuid:11111111-1111-1111-1111-111111111111"
        cfg = config()
        cfg = proof.TargetConfig(**{**cfg.__dict__,
            "tv_id_sha256": hashlib.sha256(observed_id.encode()).hexdigest()})

        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def read(self, _size):
                return json.dumps({"device": {
                    "id": observed_id, "modelName": proof.MODEL,
                    "developerMode": "1", "developerIP": cfg.host_ip,
                    "firmwareVersion": proof.FIRMWARE,
                }}).encode()

        proof.require_target_api(cfg, urlopen=lambda *_a, **_k: Response())
        wrong = proof.TargetConfig(**{**cfg.__dict__, "tv_id_sha256": "b" * 64})
        with self.assertRaises(proof.ProofError):
            proof.require_target_api(wrong, urlopen=lambda *_a, **_k: Response())

    def test_device_json_helper_emits_only_the_identity_hash(self):
        identifier = "uuid:11111111-1111-4111-8111-111111111111"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tv-info-private.json"
            path.write_text(json.dumps({"device": {"id": identifier}}))
            observed = proof.hash_device_id_json(path)
        self.assertEqual(observed, hashlib.sha256(identifier.encode()).hexdigest())
        self.assertNotIn(identifier, observed)

    def test_state_machine_permits_one_trigger_and_one_classification(self):
        state = proof.OneShotState()
        for phase in (proof.Phase.OFFLINE_AUDITED, proof.Phase.TARGET_VERIFIED,
                      proof.Phase.LAB_RUNNING, proof.Phase.LAB_SELFTESTED,
                      proof.Phase.FORM_VERIFIED, proof.Phase.RDP_VISIBLE):
            state.advance(phase)
        state.claim_trigger()
        with self.assertRaises(proof.ProofError):
            state.claim_trigger()
        state.close_trigger_window()
        state.claim_classification()
        with self.assertRaises(proof.ProofError):
            state.claim_classification()

    def _classification_state(self):
        state = proof.OneShotState(phase=proof.Phase.TRIGGER_WINDOW_CLOSED,
                                   trigger_claimed=True)
        return state

    def test_two_push_uid0_success_and_no_retry(self):
        runner = FakeRunner((completed(), completed(), completed()))
        with tempfile.TemporaryDirectory() as temporary:
            local = Path(temporary) / "marker"
            local.write_bytes(b"x")
            state = self._classification_state()
            self.assertTrue(proof.classify_uid0_once(config(), identity(), local, state,
                                                      runner=runner))
            self.assertEqual(len(runner.calls), 3)
            self.assertEqual(runner.calls[1][-3], "push")
            self.assertEqual(runner.calls[2][-1], identity().stage + "/attest")
            with self.assertRaises(proof.ProofError):
                proof.classify_uid0_once(config(), identity(), local, state, runner=runner)

    def test_two_push_treats_textual_rc0_not_directory_as_no_proof(self):
        runner = FakeRunner((completed(), completed(),
            completed(0, stderr="error: target: Not a directory\n")))
        with tempfile.TemporaryDirectory() as temporary:
            local = Path(temporary) / "marker"
            local.write_bytes(b"x")
            self.assertFalse(proof.classify_uid0_once(
                config(), identity(), local, self._classification_state(), runner=runner))

    def test_two_push_rejects_unexpected_textual_errors_even_with_rc0(self):
        runner = FakeRunner((completed(), completed(),
            completed(0, stderr="error: permission denied\n")))
        with tempfile.TemporaryDirectory() as temporary:
            local = Path(temporary) / "marker"
            local.write_bytes(b"x")
            with self.assertRaises(proof.ProofError):
                proof.classify_uid0_once(
                    config(), identity(), local, self._classification_state(), runner=runner)

    def test_injection_contains_combined_regular_owner_and_content_predicate(self):
        command = proof.uid0_predicate(identity())
        self.assertIn("[ -f /tmp/q60t-rpc-", command)
        self.assertIn("stat -c %u", command)
        self.assertIn("^uid=0(root) gid=0(root)", command)
        self.assertEqual(command.count("mkdir /home/owner/share/tmp/sdk_tools/r"), 1)
        self.assertLess(len(proof.injection_argument(command, identity().gate_token)),
                        proof.MAX_APPINSTALL_BYTES + 1)

    def test_lab_command_binds_only_exact_address_and_never_puts_password_in_argv(self):
        item = identity()
        runner = FakeRunner()
        lab = proof.Lab(item, bind="127.0.0.1", rdp_port=13389, smb_port=11445,
                        runner=runner)
        inspect = json.dumps([{"NetworkSettings": {"Ports": {
            "3389/tcp": [{"HostIp": "127.0.0.1", "HostPort": "13389"}],
            "445/tcp": [{"HostIp": "127.0.0.1", "HostPort": "11445"}],
        }}}])
        runner.results = [completed(stdout=IMAGE_ID + "\n"),
                          image_inspect(lab.context_sha256),
                          absent(item.container), absent(lab.client_container),
                          image_inspect(lab.context_sha256), completed(stdout="id\n"),
                          completed(stdout="true healthy\n"), completed(stdout=inspect)]
        with mock.patch.object(proof, "require_ports_available"):
            lab.build()
            lab.start()
        run_call = runner.calls[5]
        self.assertIn("127.0.0.1:13389:3389", run_call)
        self.assertIn("127.0.0.1:11445:445", run_call)
        self.assertNotIn("0.0.0.0:13389:3389", run_call)
        self.assertNotIn(item.payload, " ".join(run_call))
        self.assertEqual(run_call[-1], IMAGE_ID)
        runner.results = [completed(), absent(lab.client_container),
                          completed(), absent(item.container)]
        lab.stop()

    def test_lab_build_labels_and_start_verifies_exact_source_context(self):
        item = identity()
        runner = FakeRunner((completed(stdout=IMAGE_ID + "\n"),
                             image_inspect(proof.lab_context_sha256())))
        lab = proof.Lab(item, bind="127.0.0.1", rdp_port=13389, smb_port=11445,
                        runner=runner)
        lab.build()
        self.assertIn("--label", runner.calls[0])
        self.assertIn("--quiet", runner.calls[0])
        self.assertIn(f"{proof.LAB_CONTEXT_LABEL}={lab.context_sha256}", runner.calls[0])
        self.assertRegex(lab.context_sha256, r"^[0-9a-f]{64}$")

        stale = FakeRunner((completed(stdout=IMAGE_ID + "\n"), image_inspect("0" * 64)))
        stale_lab = proof.Lab(item, bind="127.0.0.1", rdp_port=13389, smb_port=11445,
                              runner=stale)
        with self.assertRaises(proof.ProofError):
            stale_lab.build()
        self.assertFalse(any(call[:2] == ("docker", "run") for call in stale.calls))

        unbuilt = proof.Lab(item, bind="127.0.0.1", rdp_port=13389, smb_port=11445,
                            runner=FakeRunner((absent(item.container),
                                               absent(item.container + "-client"))))
        with mock.patch.object(proof, "require_ports_available"), \
             self.assertRaises(proof.ProofError):
            unbuilt.start()

    def test_lab_build_refuses_source_changes_during_snapshot_or_build(self):
        for digests in (("a" * 64, "b" * 64),
                        ("a" * 64, "a" * 64, "b" * 64)):
            with self.subTest(digests=digests):
                runner = FakeRunner((completed(stdout=IMAGE_ID + "\n"),))
                lab = proof.Lab(identity(), bind="127.0.0.1", rdp_port=13389,
                                smb_port=11445, runner=runner)
                with mock.patch.object(proof, "lab_context_sha256",
                                       side_effect=digests), \
                     self.assertRaises(proof.ProofError):
                    lab.build()
                self.assertIsNone(lab._image_id)
                if len(digests) == 2:
                    self.assertFalse(runner.calls)
                else:
                    self.assertEqual(runner.calls[0][:3], ("docker", "build", "--quiet"))

    def test_lab_start_refuses_source_change_after_build(self):
        item = identity()
        runner = FakeRunner((completed(stdout=IMAGE_ID + "\n"),
                             image_inspect(proof.lab_context_sha256()),
                             absent(item.container), absent(item.container + "-client")))
        lab = proof.Lab(item, bind="127.0.0.1", rdp_port=13389, smb_port=11445,
                        runner=runner)
        lab.build()
        with mock.patch.object(proof, "lab_context_sha256", return_value="0" * 64), \
             mock.patch.object(proof, "require_ports_available"), \
             self.assertRaises(proof.ProofError):
            lab.start()
        self.assertFalse(any(call[:2] == ("docker", "run") for call in runner.calls))

    def test_lab_policy_authenticates_the_exact_runtime_password(self):
        pam = (proof.LAB_CONTEXT / "xrdp-sesman.pam").read_text()
        entrypoint = (proof.LAB_CONTEXT / "entrypoint.sh").read_text()
        dockerfile = (proof.LAB_CONTEXT / "Dockerfile").read_text()
        client = (proof.LAB_CONTEXT / "client.sh").read_text()
        server = (proof.LAB_CONTEXT / "server.py").read_text()
        self.assertNotIn("pam_permit.so", pam)
        self.assertIn("auth required pam_unix.so", pam)
        self.assertIn("account required pam_unix.so", pam)
        self.assertNotIn("passwd --delete q60t", dockerfile)
        self.assertIn("pamtester", dockerfile)
        self.assertIn("| /usr/sbin/chpasswd", entrypoint)
        self.assertLess(entrypoint.index("| /usr/sbin/chpasswd"),
                        entrypoint.index("/usr/sbin/xrdp-sesman"))
        self.assertNotIn("/auth-only", client)
        self.assertNotIn("/p:", client)
        self.assertIn("/from-stdin:force", client)
        self.assertNotIn("-password", entrypoint)
        self.assertIn("addCredential", server)

    def test_lab_rejects_runtime_password_in_process_arguments(self):
        item = identity()
        clean = FakeRunner((completed(stdout="COMMAND\n/usr/sbin/xrdp\n"),
                            completed(stdout="COMMAND\n/usr/bin/xfreerdp /from-stdin:force\n")))
        proof.Lab(item, bind="127.0.0.1", rdp_port=13389, smb_port=11445,
                  runner=clean)._require_secret_absent_from_process_arguments()

        exposed = FakeRunner((completed(stdout="COMMAND\n" + item.payload + "\n"),))
        with self.assertRaises(proof.ProofError):
            proof.Lab(item, bind="127.0.0.1", rdp_port=13389, smb_port=11445,
                      runner=exposed)._require_secret_absent_from_process_arguments()

    def test_rdp_log_counts_require_one_rejection_and_one_success(self):
        logs = (
            "[INFO ] AUTHFAIL: user=q60t ip=127.0.0.1 time=1\n"
            "[INFO ] login failed for user q60t\n"
            "[INFO ] login successful for user q60t on display 10"
        )
        self.assertEqual(proof.Lab._count_rdp_rejections(logs), 1)
        self.assertEqual(proof.Lab._count_rdp_logins(logs), 1)
        self.assertEqual(proof.Lab._count_rdp_rejections(logs + "\n" + logs), 2)

    def test_lab_pam_probe_rejects_decoy_accepts_exact_and_keeps_secret_off_argv(self):
        class InputRunner(FakeRunner):
            def __init__(self, results):
                super().__init__(results)
                self.inputs: list[str | None] = []

            def run(self, arguments, **kwargs):
                self.inputs.append(kwargs.get("input_text"))
                return super().run(arguments, **kwargs)

        runner = InputRunner((completed(1), completed()))
        lab = proof.Lab(identity(), bind="127.0.0.1", rdp_port=13389,
                        smb_port=11445, runner=runner)
        lab._require_exact_password_authentication()
        self.assertEqual(runner.calls[0], runner.calls[1])
        self.assertEqual(runner.inputs,
                         [proof.INVALID_LAB_PASSWORD + "\n", identity().payload + "\n"])
        self.assertNotIn(identity().payload, " ".join(runner.calls[1]))

        for results in ((completed(),), (completed(1), completed(1))):
            with self.subTest(results=[result.returncode for result in results]):
                failing = proof.Lab(identity(), bind="127.0.0.1", rdp_port=13389,
                                    smb_port=11445, runner=FakeRunner(results))
                with self.assertRaises(proof.ProofError):
                    failing._require_exact_password_authentication()

    def test_docker_start_failure_still_arms_exact_cleanup(self):
        item = identity()

        class StartFailureRunner(FakeRunner):
            def run(self, arguments, **kwargs):
                self.calls.append(tuple(arguments))
                if arguments[:2] == ("docker", "build"):
                    return completed(stdout=IMAGE_ID + "\n")
                if arguments[:3] == ("docker", "image", "inspect"):
                    return image_inspect(proof.lab_context_sha256())
                if arguments[:2] == ("docker", "run"):
                    raise proof.ProofError("simulated Docker client timeout")
                if arguments[:3] == ("docker", "rm", "--force"):
                    return completed()
                return absent(arguments[-1]) if arguments[1] == "inspect" else completed()

        runner = StartFailureRunner()
        lab = proof.Lab(item, bind="127.0.0.1", rdp_port=13389, smb_port=11445,
                        runner=runner)
        lab.build()
        with mock.patch.object(proof, "require_ports_available"), \
             self.assertRaises(proof.ProofError):
            lab.start()
        lab.stop()
        removed = [call[-1] for call in runner.calls if call[:3] == ("docker", "rm", "--force")]
        self.assertEqual(removed, [lab.client_container, item.container])

    def test_signal_guard_turns_sigterm_into_terminal_interruption_and_restores(self):
        previous = proof.signal.getsignal(proof.signal.SIGTERM)
        with self.assertRaises(proof.InterruptedRun), proof.SignalGuard():
            handler = proof.signal.getsignal(proof.signal.SIGTERM)
            self.assertTrue(callable(handler))
            if callable(handler):
                handler(proof.signal.SIGTERM, None)
        self.assertIs(proof.signal.getsignal(proof.signal.SIGTERM), previous)

    def test_signal_during_cleanup_is_deferred_until_cleanup_finishes(self):
        events: list[str] = []
        with self.assertRaises(proof.InterruptedRun), proof.SignalGuard() as guard:
            guard.begin_cleanup()
            handler = proof.signal.getsignal(proof.signal.SIGINT)
            self.assertTrue(callable(handler))
            if callable(handler):
                handler(proof.signal.SIGINT, None)
            events.append("cleanup-completed")
        self.assertEqual(events, ["cleanup-completed"])

    def test_docker_daemon_error_is_not_mistaken_for_container_absence(self):
        item = identity()
        runner = FakeRunner((
            completed(1, stderr="daemon unavailable"),
            completed(1, stderr="cannot connect to Docker daemon"),
            completed(), absent(item.container),
        ))
        lab = proof.Lab(item, bind="127.0.0.1", rdp_port=13389, smb_port=11445,
                        runner=runner)
        lab._cleanup_armed = True
        with self.assertRaises(proof.ProofError):
            lab.stop()
        self.assertTrue(lab._cleanup_armed)

    def test_execute_live_success_exercises_one_shot_and_cleanup(self):
        events: list[str] = []
        prompts: list[str] = []
        records: list[tuple[str, tuple[str, ...]]] = []

        class FakeLiveLab:
            def __init__(self, *_args, **_kwargs): events.append("lab-init")
            def build(self): events.append("build")
            def start(self): events.append("start")
            def selftest(self): events.append("selftest")
            def certificate_fingerprint(self): return "AA:" * 31 + "AA"
            def require_rdp_login(self): events.append("rdp-login")
            def logs(self, *, since=None):
                self.assert_since = since
                events.append("smb-window")
                return "NetrShareEnum Level: 1\n"
            def stop(self): events.append("stop")

        def classify(_config, _identity, _marker, state, **_kwargs):
            events.append("classify")
            state.claim_classification()
            return True

        def write_record(record, _directory):
            records.append((record.result, tuple(record.events)))
            return Path("/tmp/fake-run-record.json")

        args = proof.build_parser().parse_args((
            "--live", "--confirm", proof.LIVE_CONFIRMATION,
            "--ack-saved-profile", proof.PROFILE_ACK,
            "--ack-no-retry", proof.NO_RETRY_ACK,
        ))
        with mock.patch.object(proof, "audit_firmware"), \
             mock.patch.object(proof, "load_target_config", return_value=config()), \
             mock.patch.object(proof, "require_target_api") as target_api, \
             mock.patch.object(proof, "require_sdb_device") as sdb_device, \
             mock.patch.object(proof, "require_ports_available"), \
             mock.patch.object(proof, "require_ports_closed") as ports_closed, \
             mock.patch.object(proof, "fresh_identity", return_value=identity()), \
             mock.patch.object(proof, "reserve_identity"), \
             mock.patch.object(proof, "Lab", FakeLiveLab), \
             mock.patch.object(proof, "classify_uid0_once", side_effect=classify), \
             mock.patch.object(proof.RunRecord, "write", autospec=True,
                               side_effect=write_record), \
             mock.patch.object(proof.time, "sleep"):
            result = proof.execute_live(
                args, runner=FakeRunner(),
                prompt=lambda _instruction, expected: prompts.append(expected),
            )
        self.assertEqual(result, "uid0-proof")
        self.assertEqual(prompts, [proof.FIRMWARE_GATE, proof.FORM_GATE,
                                   proof.RDP_GATE, proof.TRIGGER_GATE])
        self.assertEqual(events, ["lab-init", "build", "start", "selftest", "rdp-login",
                                  "smb-window", "classify", "stop"])
        self.assertEqual(records[0][0], "uid0-proof")
        self.assertIn("uid0-proof", records[0][1])
        self.assertIn("host-listeners-closed", records[0][1])
        self.assertEqual(target_api.call_count, 2)
        self.assertEqual(sdb_device.call_count, 2)
        ports_closed.assert_called_once()

    def test_execute_live_failure_still_cleans_and_records_terminal_result(self):
        events: list[str] = []
        records: list[str] = []

        class FakeLiveLab:
            def __init__(self, *_args, **_kwargs): pass
            def build(self): pass
            def start(self): pass
            def selftest(self): pass
            def certificate_fingerprint(self): return "AA:" * 31 + "AA"
            def require_rdp_login(self): pass
            def logs(self, *, since=None): return ""
            def stop(self): events.append("stop")

        def write_record(record, _directory):
            records.append(record.result)
            return Path("/tmp/fake-run-record.json")

        args = proof.build_parser().parse_args((
            "--live", "--confirm", proof.LIVE_CONFIRMATION,
            "--ack-saved-profile", proof.PROFILE_ACK,
            "--ack-no-retry", proof.NO_RETRY_ACK,
        ))
        with mock.patch.object(proof, "audit_firmware"), \
             mock.patch.object(proof, "load_target_config", return_value=config()), \
             mock.patch.object(proof, "require_target_api"), \
             mock.patch.object(proof, "require_sdb_device"), \
             mock.patch.object(proof, "require_ports_available"), \
             mock.patch.object(proof, "require_ports_closed") as ports_closed, \
             mock.patch.object(proof, "fresh_identity", return_value=identity()), \
             mock.patch.object(proof, "reserve_identity"), \
             mock.patch.object(proof, "Lab", FakeLiveLab), \
             mock.patch.object(proof.RunRecord, "write", autospec=True,
                               side_effect=write_record), \
             mock.patch.object(proof.time, "sleep"), \
             self.assertRaises(proof.ProofError):
            proof.execute_live(args, runner=FakeRunner(), prompt=lambda *_args: None)
        self.assertEqual(events, ["stop"])
        self.assertEqual(records, ["terminal-failure"])
        ports_closed.assert_called_once()

    def test_occupied_port_is_refused(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
            with self.assertRaises(proof.ProofError):
                proof.require_ports_available("127.0.0.1", (port,))

    def test_secret_redaction_covers_payload_ip_uuid_and_explicit_values(self):
        source = "failure 192.168.1.20 uuid:11111111-1111-1111-1111-111111111111 SECRET"
        result = proof.redacted(source, ("SECRET",))
        self.assertNotIn("192.168.1.20", result)
        self.assertNotIn("uuid:111", result)
        self.assertNotIn("SECRET", result)

    def test_no_ui_automation_or_route_two_surface(self):
        source = Path(proof.__file__).read_text()
        parser_help = proof.build_parser().format_help()
        for forbidden in ("ProcessMouseDevice", "websocket", "send_key", "remote-control",
                          "share-name-injection", "--route", "--smbpath"):
            self.assertNotIn(forbidden, source + parser_help)
        self.assertIn("No UI automation is used", source)

    def test_run_record_contains_no_raw_identity_or_payload(self):
        item = identity()
        record = proof.RunRecord(item.fingerprint, "live", ["uid0-proof"], "uid0-proof")
        with tempfile.TemporaryDirectory() as temporary:
            path = record.write(Path(temporary))
            data = path.read_text()
        for secret in (item.run_id, item.share, item.marker, item.stage, item.payload):
            self.assertNotIn(secret, data)


if __name__ == "__main__":
    unittest.main()
