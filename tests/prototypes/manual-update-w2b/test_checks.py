"""Focused W2b safety checks; no additional native schedules or privilege scope."""
import os
import io
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from run_experiment import Case, wait_pidfd, write_message, main, inode


class SafetyChecks(unittest.TestCase):
    def test_reap_watchdog_does_not_enter_waitid_after_timeout(self):
        with patch('run_experiment.select.select', return_value=([], [], [])), \
             patch('run_experiment.os.waitid') as wait:
            with self.assertRaisesRegex(RuntimeError, 'exit timeout'):
                wait_pidfd(999)
            wait.assert_not_called()

    def test_reap_is_nonblocking_after_pidfd_readability(self):
        status = Mock()
        with patch('run_experiment.select.select', return_value=([999], [], [])), \
             patch('run_experiment.os.waitid', return_value=status) as wait:
            self.assertIs(wait_pidfd(999), status)
            wait.assert_called_once_with(os.P_PIDFD, 999, os.WEXITED | os.WNOHANG)

    def test_wrong_process_identity_rejected_before_binding(self):
        case = object.__new__(Case)
        case.event = Mock()
        expected = dict(pid=12345, ppid=1, uid=os.geteuid(), start_ticks=100)
        with patch('run_experiment.process_identity', return_value={**expected, 'start_ticks': 101}), \
             patch('run_experiment.os.pidfd_open') as opened:
            with self.assertRaisesRegex(RuntimeError, 'identity mismatch'):
                case.bind_pidfd(expected)
            opened.assert_not_called()

    def test_identity_change_during_pidfd_binding_closes_handle(self):
        case = object.__new__(Case)
        case.event = Mock()
        expected = dict(pid=12345, ppid=1, uid=os.geteuid(), start_ticks=100)
        with patch('run_experiment.process_identity', side_effect=[expected, {**expected, 'start_ticks': 101}]), \
             patch('run_experiment.os.pidfd_open', return_value=999), \
             patch('run_experiment.os.close') as close:
            with self.assertRaisesRegex(RuntimeError, 'changed while binding'):
                case.bind_pidfd(expected)
            close.assert_called_once_with(999)

    def test_partial_barrier_write_is_completed(self):
        parts = []
        def short_write(fd, data):
            part = bytes(data[:2])
            parts.append(part)
            return len(part)
        with patch('run_experiment.os.write', side_effect=short_write), \
             patch('run_experiment.os.get_blocking', return_value=True), \
             patch('run_experiment.os.set_blocking'), \
             patch('run_experiment.select.select', return_value=([], [999], [])):
            write_message(999, {'command': 'ping'})
        self.assertEqual(b''.join(parts), b'{"command":"ping"}\n')

    def test_subreaper_setup_failure_preserves_original_error_and_restores(self):
        output = io.StringIO()
        with patch('run_experiment.privilege', return_value=dict(effective_capabilities='0')), \
             patch('run_experiment.os.geteuid', return_value=1000), \
             patch('run_experiment.direct_children', return_value=[]), \
             patch('run_experiment.subreaper', side_effect=[0, RuntimeError('injected enable failure'), None, 0]), \
             patch('sys.stdout', output):
            self.assertEqual(main(), 1)
        report = json.loads(output.getvalue())
        self.assertEqual(report['result'], 'Blocked')
        self.assertEqual(report['subreaper']['restored'], 0)
        self.assertEqual(len(report['failures']), 1)
        self.assertIn('injected enable failure', report['failures'][0])

    def test_close_error_does_not_skip_later_resources(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2b-review-') as directory:
            root = Path(directory) / 'run'
            root.mkdir(mode=0o700)
            (root / 'O').touch(mode=0o600)
            case = Case('exclude', root, dict(trace=[], failures=[], result='Pass'))
            case.expected_file = inode((root / 'O').stat())
            case.child_reaped = True
            case.parent_socket = Mock()
            case.parent_socket.close.side_effect = OSError('injected close error')
            case.child_socket = Mock()
            with patch('run_experiment.direct_children', return_value=[]):
                case.cleanup()
            case.child_socket.close.assert_called_once()
            self.assertEqual(case.report['result'], 'Fail')
            self.assertTrue(any('injected close error' in error for error in case.cleanup_errors))

    def test_write_timeout_restores_mode_without_writing(self):
        with patch('run_experiment.os.get_blocking', return_value=True), \
             patch('run_experiment.os.set_blocking') as mode, \
             patch('run_experiment.select.select', return_value=([], [], [])), \
             patch('run_experiment.os.write') as write:
            with self.assertRaisesRegex(RuntimeError, 'write timeout'):
                write_message(999, {'command': 'ping'})
            write.assert_not_called()
            self.assertEqual(mode.call_args_list[-1].args, (999, True))

    def test_zero_byte_write_is_failure(self):
        with patch('run_experiment.os.get_blocking', return_value=True), \
             patch('run_experiment.os.set_blocking'), \
             patch('run_experiment.select.select', return_value=([], [999], [])), \
             patch('run_experiment.os.write', return_value=0):
            with self.assertRaisesRegex(RuntimeError, 'zero-byte'):
                write_message(999, {'command': 'ping'})

    def alive_fixture(self):
        case = object.__new__(Case)
        case.child_identity = dict(pid=12345, ppid=1, uid=os.geteuid(), start_ticks=100)
        case.child_pidfd = 999
        case.sentinel_lock_fd = 3
        reply = dict(event='alive', identity={**case.child_identity, 'ppid': os.getpid()}, lock_fd=3)
        return case, reply

    def test_alive_replies_require_full_original_identity(self):
        case, reply = self.alive_fixture()
        with patch('run_experiment.select.select', return_value=([], [], [])):
            case.validate_alive(reply)
            for key in ('pid', 'uid', 'start_ticks', 'ppid'):
                with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, 'identity changed'):
                    case.validate_alive({**reply, 'identity': {**reply['identity'], key: reply['identity'][key] + 1}})

    def test_queued_alive_reply_does_not_prove_live_process(self):
        case, reply = self.alive_fixture()
        with patch('run_experiment.select.select', return_value=([999], [], [])):
            with self.assertRaisesRegex(RuntimeError, 'exited before liveness'):
                case.validate_alive(reply)

    def test_alive_reply_requires_expected_descriptor_state(self):
        case, reply = self.alive_fixture()
        with patch('run_experiment.select.select', return_value=([], [], [])):
            with self.assertRaisesRegex(RuntimeError, 'descriptor state changed'):
                case.validate_alive({**reply, 'lock_fd': -1})

    def test_unregistered_adopted_child_is_not_signaled(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2b-review-') as directory:
            root = Path(directory) / 'run'
            root.mkdir(mode=0o700)
            case = Case('exclude', root, dict(trace=[], failures=[], result='Fail'))
            candidate = dict(pid=12345, ppid=os.getpid(), uid=os.geteuid(), start_ticks=case.runner_start_ticks + 1)
            with patch('run_experiment.direct_children', side_effect=[[12345], []]), \
                 patch('run_experiment.process_identity', return_value=candidate), \
                 patch.object(case, 'bind_pidfd', return_value=999), \
                 patch('run_experiment.wait_pidfd', return_value=Mock(si_pid=12345, si_code=1, si_status=1)), \
                 patch('run_experiment.signal.pidfd_send_signal') as signal_process, \
                 patch('run_experiment.os.close'):
                case.cleanup()
            signal_process.assert_not_called()
            self.assertTrue(root.exists())  # ownership was not fully established; preserve it


if __name__ == '__main__':
    unittest.main()
