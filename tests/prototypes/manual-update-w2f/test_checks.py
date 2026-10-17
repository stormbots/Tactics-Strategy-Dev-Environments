"""Focused fail-closed checks; synthetic credentials are NOT native evidence."""
import importlib.util
from pathlib import Path
import json
import tempfile
import struct
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('w2f', Path(__file__).with_name('run_experiment.py'))
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class Peer:
    def __init__(self, raw):
        self.raw = raw

    def getsockopt(self, *args):
        return self.raw


class Checks(unittest.TestCase):
    def setUp(self):
        self.enrolled = dict(pid=123, uid=1000, gid=1000, ppid=100, start_ticks=77)

    def test_same_uid_unexpected_pid_denied_before_proc_access(self):
        with patch.object(w, 'identity', side_effect=AssertionError('must not access unexpected PID')):
            r = w.verify(Peer(struct.pack('3i', 124, 1000, 1000)), self.enrolled)
        self.assertFalse(r['accepted'])
        self.assertEqual(r['reason'], 'pid-mismatch')

    def test_uid_mismatch(self):
        self.assertEqual(w.verify(Peer(struct.pack('3i', 123, 1001, 1000)), self.enrolled)['reason'], 'uid-mismatch')

    def test_gid_mismatch(self):
        self.assertEqual(w.verify(Peer(struct.pack('3i', 123, 1000, 1001)), self.enrolled)['reason'], 'gid-mismatch')

    def test_short_kernel_record(self):
        self.assertFalse(w.verify(Peer(b'bad'), self.enrolled)['accepted'])

    def test_creation_change_closes_pidfd(self):
        altered = dict(self.enrolled, start_ticks=78)
        with patch.object(w, 'identity', side_effect=[self.enrolled, altered]), patch.object(w.os, 'pidfd_open', return_value=99), patch.object(w.select, 'select', return_value=([], [], [])), patch.object(w.os, 'close') as close:
            result = w.verify(Peer(struct.pack('3i', 123, 1000, 1000)), self.enrolled)
        self.assertEqual(result['reason'], 'process-instance-mismatch')
        close.assert_called_once_with(99)

    def test_exited_peer_denied(self):
        with patch.object(w, 'identity', return_value=self.enrolled), patch.object(w.os, 'pidfd_open', return_value=99), patch.object(w.select, 'select', return_value=([99], [], [])), patch.object(w.os, 'close'):
            self.assertEqual(w.verify(Peer(struct.pack('3i', 123, 1000, 1000)), self.enrolled)['reason'], 'process-exited')

    def test_kernel_error_denied(self):
        peer = Peer(b'')
        with patch.object(peer, 'getsockopt', side_effect=OSError('test failure')):
            self.assertFalse(w.verify(peer, self.enrolled)['accepted'])

    def test_missing_enrollment_denied(self):
        self.assertFalse(w.verify(Peer(struct.pack('3i', 123, 1000, 1000)), {})['accepted'])


    def test_invalid_enrollment_types_denied(self):
        for bad in (None, [], dict(self.enrolled, pid=True), dict(self.enrolled, start_ticks=0)):
            with self.subTest(bad=bad):
                self.assertFalse(w.verify(Peer(struct.pack('3i', 123, 1000, 1000)), bad)['accepted'])

    def test_pidfd_open_failure_is_denial(self):
        with patch.object(w, 'identity', return_value=self.enrolled), patch.object(w.os, 'pidfd_open', side_effect=OSError('test pidfd failure')):
            self.assertFalse(w.verify(Peer(struct.pack('3i', 123, 1000, 1000)), self.enrolled)['accepted'])

    def test_partial_actor_startup_still_reaped(self):
        proc = Mock()
        proc.poll.return_value = None
        proc.communicate.return_value = (b'', b'')
        proc.returncode = -9
        obj = w.Actor.__new__(w.Actor)
        with patch.object(w.subprocess, 'Popen', return_value=proc), patch.object(w.os, 'pidfd_open', side_effect=OSError('test pidfd open failure')):
            with self.assertRaises(OSError):
                obj.__init__('client', '/unused/test-only')
        result = obj.cleanup()
        proc.kill.assert_called_once_with()
        proc.communicate.assert_called_once_with(timeout=w.TIMEOUT)
        self.assertTrue(result['reaped'])
        self.assertFalse(result['pidfd_registered'])

    def test_cleanup_preserves_unknown_entry(self):
        with tempfile.TemporaryDirectory(prefix='W2f-unit-') as directory:
            root = Path(directory) / 'root'
            root.mkdir(mode=0o700)
            before = w.metadata(root)
            unknown = root / 'unknown'
            unknown.write_text('preserve')
            with self.assertRaisesRegex(RuntimeError, 'unregistered'):
                w.cleanup_root(root, before, {})
            self.assertEqual(unknown.read_text(), 'preserve')

    def test_cleanup_preserves_replaced_root(self):
        with tempfile.TemporaryDirectory(prefix='W2f-unit-') as directory:
            root, moved = Path(directory) / 'root', Path(directory) / 'moved'
            root.mkdir(mode=0o700)
            before = w.metadata(root)
            root.rename(moved)
            root.mkdir(mode=0o700)
            with self.assertRaisesRegex(RuntimeError, 'root identity changed'):
                w.cleanup_root(root, before, {})
            self.assertTrue(root.exists() and moved.exists())

    def test_cleanup_preserves_replaced_entry(self):
        with tempfile.TemporaryDirectory(prefix='W2f-unit-') as directory:
            root = Path(directory) / 'root'
            root.mkdir(mode=0o700)
            entry = root / 'entry'
            entry.write_text('original')
            before, original = w.metadata(root), w.metadata(entry)
            # Retain old inode to exclude inode reuse in this regression check.
            retained_fd = w.os.open(entry, w.os.O_RDONLY)
            try:
                entry.unlink()
                entry.write_text('replacement')
                with self.assertRaisesRegex(RuntimeError, 'socket identity changed'):
                    w.cleanup_root(root, before, {entry: original})
                self.assertEqual(entry.read_text(), 'replacement')
            finally:
                w.os.close(retained_fd)

    def test_rejected_server_does_not_issue_request_or_trust_ack(self):
        conn = Mock()
        ack = b'{"test_ack":true,"claimed_pid":123}'
        with patch.object(w, 'data_receive', return_value=ack), patch.object(w, 'data_send') as send:
            result = w.exchange(conn, 'client', dict(accepted=False), self.enrolled, 123, False)
        send.assert_not_called()
        self.assertEqual(result['requests_sent'], 0)
        self.assertEqual(result['trusted_status'], 0)
        self.assertEqual(result['probe_bytes_discarded'], len(ack))

    def test_rejected_client_does_not_authorize_spoofed_request(self):
        conn = Mock()
        request = b'{"test_request":"fixed-ack","claimed_pid":123}'
        with patch.object(w, 'data_receive', return_value=request), patch.object(w, 'data_send') as send:
            result = w.exchange(conn, 'server', dict(accepted=False), self.enrolled, 123, False)
        send.assert_not_called()
        self.assertEqual(result['authorized_actions'], 0)
        self.assertEqual(result['probe_bytes_discarded'], len(request))

    def test_unknown_scenario_creates_no_resources(self):
        with patch.object(w.tempfile, 'mkdtemp', side_effect=AssertionError('must validate first')):
            with self.assertRaises(ValueError):
                w.scenario('unknown')

    def test_oracle_rejects_inconsistent_native_evidence(self):
        # Recorded native snapshots are fixtures here, not repeated native runs.
        import copy
        report = json.loads((Path(__file__).parent / 'evidence/linux-run-reviewed.json').read_text())
        for original in report['cases']:
            with self.subTest(case=original['case']):
                fixture = copy.deepcopy(original)
                for owned in fixture['ownership']:
                    owned['identity']['ppid'] = w.os.getpid()
                for key in ('server_verifies_client', 'client_verifies_server'):
                    v = fixture[key]['verification']
                    for item in ('enrolled', 'before', 'after'):
                        if item in v:
                            v[item]['ppid'] = w.os.getpid()
                w.validate_case(fixture)
                bad = copy.deepcopy(fixture)
                bad['server_verifies_client']['verification']['kernel']['pid'] += 10000
                with self.assertRaises(RuntimeError):
                    w.validate_case(bad)
                bad = copy.deepcopy(fixture)
                bad['server_result']['authorized_actions'] = True
                with self.assertRaises(RuntimeError):
                    w.validate_case(bad)
                bad = copy.deepcopy(fixture)
                bad['client_result']['trusted_status'] = 2
                with self.assertRaises(RuntimeError):
                    w.validate_case(bad)
                bad = copy.deepcopy(fixture)
                bad['client_result']['completed_at'] = -1
                with self.assertRaises(RuntimeError):
                    w.validate_case(bad)
                bad = copy.deepcopy(fixture)
                if original['case'] == 'intended':
                    bad['server_verifies_client']['verification']['pidfd_live'] = False
                else:
                    key = 'server_result' if original['case'] == 'unexpected-client' else 'client_result'
                    bad[key]['probe_bytes_discarded'] = 0
                with self.assertRaises(RuntimeError):
                    w.validate_case(bad)


if __name__ == '__main__':
    unittest.main(verbosity=2)
