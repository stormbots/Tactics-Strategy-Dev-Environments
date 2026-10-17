"""W2g focused checks. Mock faults are not additional native schedules."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('w2g_checks', Path(__file__).with_name('run_experiment.py'))
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


def evidence_path():
    root = Path(__file__).parent / 'evidence'
    reviewed = root / 'reviewed-linux-run.json'
    return reviewed if reviewed.exists() else root / 'linux-run.json'


class Checks(unittest.TestCase):
    def setUp(self):
        self.enrolled = dict(pid=1234, uid=1000, gid=1000, start_ticks=50, ppid=123)

    def evaluate(self, alive, variant='guarded', kernel=None, raw=None):
        conn = Mock()
        if kernel is None:
            kernel = {k: self.enrolled[k] for k in ('pid', 'uid', 'gid')}
        if raw is None:
            raw = json.dumps(w.fixed_request(self.enrolled['pid'])).encode()
        with patch.object(w.peer, 'data_receive', return_value=raw), patch.object(w, 'credentials', return_value=kernel), patch.object(w, 'live', return_value=alive), patch.object(w.os, 'get_inheritable', return_value=False):
            return w.evaluate(conn, self.enrolled, 99, variant)

    def test_healthy_action(self):
        result = self.evaluate(True)
        self.assertEqual(result['authorized_actions'], 1)
        self.assertEqual(result['reason'], 'enrolled-client-live')

    def test_exited_original_denied_despite_matching_credentials(self):
        result = self.evaluate(False)
        self.assertEqual(result['authorized_actions'], 0)
        self.assertEqual(result['reason'], 'original-client-exited')

    def test_mutant_exposes_stale_peer_action(self):
        result = self.evaluate(False, 'TEST-ONLY-omitted-liveness')
        self.assertEqual(result['authorized_actions'], 1)
        self.assertEqual(result['reason'], 'TEST-ONLY-stale-peer-authorized')

    def test_wrong_kernel_pid_still_denied_in_mutant(self):
        result = self.evaluate(False, 'TEST-ONLY-omitted-liveness', dict(pid=9999, uid=1000, gid=1000))
        self.assertEqual(result['authorized_actions'], 0)
        self.assertEqual(result['reason'], 'kernel-credentials-mismatch')

    def test_payload_claim_cannot_choose_different_identity(self):
        with self.assertRaisesRegex(RuntimeError, 'fixed test request'):
            self.evaluate(True, raw=json.dumps(w.fixed_request(9999)).encode())

    def test_unknown_variant_stops_before_read(self):
        with patch.object(w.peer, 'data_receive', side_effect=AssertionError('must validate first')):
            with self.assertRaisesRegex(RuntimeError, 'unknown guard variant'):
                w.evaluate(Mock(), self.enrolled, 99, 'unknown')

    def test_missing_request_is_failure(self):
        with patch.object(w.peer, 'data_receive', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'missing test request'):
                w.evaluate(Mock(), self.enrolled, 99, 'guarded')

    def test_pidfd_query_error_cannot_authorize(self):
        raw = json.dumps(w.fixed_request(self.enrolled['pid'])).encode()
        with patch.object(w.peer, 'data_receive', return_value=raw), patch.object(w, 'credentials', return_value={k: self.enrolled[k] for k in ('pid', 'uid', 'gid')}), patch.object(w, 'live', side_effect=OSError('test-only pidfd failure')):
            with self.assertRaises(OSError):
                w.evaluate(Mock(), self.enrolled, 99, 'guarded')

    def test_identity_change_closes_bound_handle(self):
        changed = dict(self.enrolled, start_ticks=51)
        with patch.object(w.peer, 'identity', side_effect=[self.enrolled, changed]), patch.object(w.os, 'pidfd_open', return_value=99), patch.object(w.os, 'close') as close:
            with self.assertRaisesRegex(RuntimeError, 'changed during binding'):
                w.bind_process(self.enrolled)
        close.assert_called_once_with(99)

    def test_bind_rejects_exited_peer(self):
        with patch.object(w.peer, 'identity', return_value=self.enrolled), patch.object(w.os, 'pidfd_open', return_value=99), patch.object(w, 'live', return_value=False), patch.object(w.os, 'close') as close:
            with self.assertRaises(RuntimeError):
                w.bind_process(self.enrolled)
        close.assert_called_once_with(99)

    def test_unknown_case_creates_no_root(self):
        with patch.object(w.tempfile, 'mkdtemp', side_effect=AssertionError('no allocation permitted')):
            with self.assertRaises(RuntimeError):
                w.Case('unknown')

    def test_descriptor_identity_includes_inode(self):
        first = dict(fd=3, device=1, inode=2, uid=1000, gid=1000, socket=True, type=1, inheritable=False)
        second = dict(first, fd=8, inheritable=True)
        self.assertTrue(w.same_socket(first, second))
        self.assertFalse(w.same_socket(first, dict(second, inode=3)))

    def test_partial_startup_without_pidfd_is_reaped(self):
        proc = Mock()
        proc.poll.return_value = None
        proc.communicate.return_value = (b'', b'')
        proc.returncode = -9
        obj = w.Actor.__new__(w.Actor)
        with patch.object(w.subprocess, 'Popen', return_value=proc), patch.object(w.peer, 'identity', return_value=dict(self.enrolled, ppid=os.getpid())), patch.object(w, 'bind_process', side_effect=OSError('test-only binding failure')):
            with self.assertRaises(OSError):
                obj.__init__('server', '/unused/test-only')
        result = obj.cleanup()
        proc.kill.assert_called_once_with()
        self.assertTrue(result['reaped'])
        self.assertTrue(result['forced'])

    def test_native_snapshot_oracle_rejects_corruption(self):
        report = json.loads(evidence_path().read_text())
        for original in report['cases']:
            w.validate_result(original)
            for field, value in [('authorized_actions', True), ('original_client_live', 1), ('variant', 'other')]:
                bad = copy.deepcopy(original)
                bad['evaluation'][field] = value
                with self.subTest(case=original['case'], field=field), self.assertRaises(RuntimeError):
                    w.validate_result(bad)
            bad = copy.deepcopy(original)
            bad['evaluation']['kernel']['pid'] += 1
            with self.assertRaises(RuntimeError):
                w.validate_result(bad)
            bad = copy.deepcopy(original)
            bad['holder_after']['descriptor']['inode'] += 1
            with self.assertRaises(RuntimeError):
                w.validate_result(bad)


    def test_oracle_rejects_privileged_holder_snapshot(self):
        report = json.loads(evidence_path().read_text())['cases'][0]
        report['holder_before']['privilege']['euid'] = 0
        with self.assertRaises(RuntimeError):
            w.validate_result(report)

    def test_oracle_requires_holder_ping_reply(self):
        report = json.loads(evidence_path().read_text())['cases'][0]
        report['holder_after']['event'] = 'holder-exiting'
        with self.assertRaises(RuntimeError):
            w.validate_result(report)

    def test_oracle_requires_boolean_pidfd_inheritance(self):
        report = json.loads(evidence_path().read_text())['cases'][0]
        report['evaluation']['retained_pidfd_inheritable'] = None
        with self.assertRaises(RuntimeError):
            w.validate_result(report)

    def test_case_identity_failure_allocates_no_root(self):
        allocated = []
        original = w.tempfile.mkdtemp
        def track(*args, **kwargs):
            path = original(*args, **kwargs)
            allocated.append(Path(path))
            return path
        try:
            with patch.object(w.tempfile, 'mkdtemp', side_effect=track), patch.object(w.peer, 'identity', side_effect=OSError('test-only process identity failure')):
                with self.assertRaises(OSError):
                    w.Case('healthy')
            self.assertEqual(allocated, [])
        finally:
            for path in allocated:
                path.rmdir()  # only empty roots created by this unit check

    def test_cleanup_continues_after_handle_close_failure(self):
        case = w.Case.__new__(w.Case)
        case.actors = []
        case.holder_fd, case.holder_reaped, case.holder_identity = 99, True, dict(pid=1234)
        case.parent_control, case.child_control = Mock(), Mock()
        case.parent_control.close.side_effect = OSError('test-only control close failure')
        case.root, case.root_before, case.sockets = Path('/unused/test-only'), {}, {}
        case.report = dict(failures=[], result='Pass', root_removed=False)
        with patch.object(w.os, 'close', side_effect=OSError('test-only pidfd close failure')), patch.object(w.support, 'direct_children', return_value=[]), patch.object(w.peer, 'cleanup_root') as remove:
            case.cleanup()
        case.parent_control.close.assert_called_once_with()
        case.child_control.close.assert_called_once_with()
        remove.assert_not_called()
        self.assertEqual(case.report['result'], 'Fail')
        self.assertFalse(case.report['root_removed'])



if __name__ == '__main__':
    unittest.main(verbosity=2)
