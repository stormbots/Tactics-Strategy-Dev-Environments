"""W2h focused checks; snapshot/mocked failures are not native schedules."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('w2h_checks', Path(__file__).with_name('run_experiment.py'))
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


def cases():
    root = Path(__file__).parent / 'evidence'
    reviewed = root / 'reviewed-linux-run.json'
    path = reviewed if reviewed.exists() else root / 'linux-run.json'
    return json.loads(path.read_text())['cases']


class Checks(unittest.TestCase):
    def evaluation(self, alive, actual_pid=1234):
        enrolled = dict(pid=1234, uid=1000, gid=1000, ppid=100, start_ticks=55)
        with patch.object(w.peer, 'data_receive', return_value=json.dumps(w.g.fixed_request(1234)).encode()), patch.object(w.g, 'credentials', return_value=dict(pid=actual_pid, uid=1000, gid=1000)), patch.object(w.g, 'live', return_value=alive), patch.object(w.os, 'get_inheritable', return_value=False):
            return w.g.evaluate(Mock(), enrolled, 99, 'guarded')

    def test_existing_guard_accepts_live_enrolled_connection(self):
        self.assertEqual(self.evaluation(True)['authorized_actions'], 1)

    def test_existing_guard_rejects_exited_original(self):
        self.assertEqual(self.evaluation(False)['authorized_actions'], 0)

    def test_existing_guard_rejects_different_kernel_pid(self):
        self.assertEqual(self.evaluation(True, 9999)['authorized_actions'], 0)

    def test_healthy_control_is_not_general_authentication_proof(self):
        result = w.validate_result(cases()[0])
        self.assertEqual(result['result'], 'Pass')
        self.assertEqual(result['authentication_safety'], 'HealthyControlOnly')
        self.assertIsNone(result['counterexample'])

    def test_delegated_action_is_counterexample(self):
        result = w.validate_result(cases()[1])
        self.assertEqual(result['result'], 'CounterexampleDetected')
        self.assertEqual(result['authentication_safety'], 'CounterexampleDetected')
        self.assertNotEqual(result['counterexample']['actual_sender']['pid'], result['counterexample']['enrolled_client']['pid'])

    def test_guard_disable_or_mutant_variant_is_rejected(self):
        for field, value in [('credential_guard_enabled', False), ('liveness_guard_enabled', False), ('variant', 'TEST-ONLY-omitted-liveness')]:
            report = cases()[1]
            report['evaluation'][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                w.validate_result(report)

    def test_dead_original_cannot_establish_live_delegation(self):
        for field in ('evaluation', 'client_before', 'client_after'):
            report = cases()[1]
            if field == 'evaluation':
                report[field]['original_client_live'] = False
            else:
                report[field]['runner_observed']['pidfd_live'] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                w.validate_result(report)

    def test_non_sender_write_is_detected(self):
        report = cases()[1]
        report['client_after']['requests_sent_total'] = 1
        with self.assertRaisesRegex(RuntimeError, 'accounting'):
            w.validate_result(report)

    def test_payload_identity_cannot_replace_actual_sender(self):
        report = cases()[1]
        report['request_sender']['identity'] = copy.deepcopy(report['enrolled_client'])
        with self.assertRaises(RuntimeError):
            w.validate_result(report)

    def test_extra_or_changed_inherited_descriptor_is_rejected(self):
        for extra in (True, False):
            report = cases()[1]
            if extra:
                report['inheritance']['spawned']['pass_fds'].append(9999)
            else:
                report['holder_after']['descriptor']['inode'] += 1
            with self.subTest(extra=extra), self.assertRaises(RuntimeError):
                w.validate_result(report)

    def test_privilege_and_reply_event_corruption_is_rejected(self):
        for field in ('privilege', 'event'):
            report = cases()[1]
            if field == 'privilege':
                report['holder_before']['privilege']['euid'] = 0
            else:
                report['holder_after']['event'] = 'holder-exiting'
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                w.validate_result(report)

    def test_counts_require_integer_evidence(self):
        for field in ('authorized_actions', 'requests_received'):
            report = cases()[1]
            report['evaluation'][field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                w.validate_result(report)

    def test_unexpected_rejection_is_not_diagnostic_success(self):
        report = cases()[1]
        report['evaluation']['authorized_actions'] = 0
        with self.assertRaisesRegex(RuntimeError, 'unexpected guard outcome'):
            w.validate_result(report)

    def test_request_before_liveness_barrier_is_rejected(self):
        report = cases()[1]
        report['request_sender']['sent_at'] = report['client_before']['runner_observed']['observed_at'] - 1
        with self.assertRaisesRegex(RuntimeError, 'ordering'):
            w.validate_result(report)

    def test_unknown_case_allocates_nothing(self):
        with patch.object(w.tempfile, 'mkdtemp', side_effect=AssertionError('must validate before allocation')):
            with self.assertRaises(RuntimeError):
                w.Case('unknown')


    def test_authentication_after_request_is_rejected(self):
        for index in (0, 1):
            report = cases()[index]
            report['server_auth']['verification']['verified_at'] = report['evaluation']['evaluated_at'] + 1
            with self.subTest(case=report['case']), self.assertRaises(RuntimeError):
                w.validate_result(report)

    def cleanup_fixture(self):
        case = w.Case.__new__(w.Case)
        case.actors = []
        case.holder_fd, case.holder_reaped = 99, False
        case.holder_identity = dict(pid=1234, uid=1000, gid=1000, ppid=100, start_ticks=55)
        case.parent_control = case.child_control = None
        case.root, case.root_before, case.sockets = Path('/unused/W2h-mock-only'), {}, {}
        case.report = dict(result='Fail', root_removed=False, failures=['injected prior failure'], counterexample=None)
        return case

    def test_cleanup_reaps_after_exit_signal_race(self):
        case = self.cleanup_fixture()
        status = SimpleNamespace(si_pid=1234, si_code=w.os.CLD_EXITED, si_status=0)
        with patch.object(w.g, 'live', return_value=True), patch.object(w.signal, 'pidfd_send_signal', side_effect=ProcessLookupError('mock exit race')), patch.object(w.support, 'wait_pidfd', return_value=status) as wait, patch.object(w.os, 'close'), patch.object(w.support, 'direct_children', return_value=[]), patch.object(w.peer, 'cleanup_root', return_value=True):
            case.cleanup()
        wait.assert_called_once_with(99)
        self.assertTrue(case.holder_reaped)
        self.assertEqual(case.report['holder_reap']['pid'], 1234)
        self.assertEqual(case.report['result'], 'Fail')  # exceptional cleanup is not a diagnostic Pass

    def test_cleanup_rejects_wrong_reaped_process(self):
        case = self.cleanup_fixture()
        status = SimpleNamespace(si_pid=9999, si_code=w.os.CLD_EXITED, si_status=0)
        with patch.object(w.g, 'live', return_value=False), patch.object(w.support, 'wait_pidfd', return_value=status), patch.object(w.os, 'close'), patch.object(w.support, 'direct_children', return_value=[]), patch.object(w.peer, 'cleanup_root', return_value=True) as remove:
            case.cleanup()
        self.assertFalse(case.holder_reaped)
        self.assertFalse(case.report['root_removed'])
        remove.assert_not_called()



if __name__ == '__main__':
    unittest.main(verbosity=2)
