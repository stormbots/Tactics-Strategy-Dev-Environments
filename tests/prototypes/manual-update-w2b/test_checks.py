"""Focused W2b safety checks; no additional native schedules or privilege scope."""
import os
import unittest
from unittest.mock import Mock, patch

from run_experiment import Case, wait_pidfd


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


if __name__ == '__main__':
    unittest.main()
