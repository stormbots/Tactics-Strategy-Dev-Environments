"""Focused fail-closed checks; synthetic credentials are NOT native evidence."""
import importlib.util
from pathlib import Path
import socket
import struct
import unittest
from unittest.mock import patch

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


if __name__ == '__main__':
    unittest.main(verbosity=2)
