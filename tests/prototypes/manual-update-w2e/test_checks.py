"""Focused W2e buffer/error checks; no additional native schedules."""
import errno
import json
import unittest
from unittest.mock import patch

from run_experiment import Progress, FRAME


class ProgressChecks(unittest.TestCase):
    def test_nonblocking_mode_is_required(self):
        with patch('run_experiment.os.get_blocking', return_value=True):
            with self.assertRaisesRegex(RuntimeError, 'nonblocking'):
                Progress(999)

    def test_backpressure_coalesces_latest_in_one_bounded_slot(self):
        with patch('run_experiment.os.get_blocking', return_value=False), \
             patch('run_experiment.os.fpathconf', return_value=4096), \
             patch('run_experiment.os.write', side_effect=BlockingIOError(errno.EAGAIN, 'full')):
            progress = Progress(999)
            for _ in range(10000):
                progress.update()
        observed = progress.snapshot()
        self.assertEqual((observed['high_entries'], observed['high_bytes']), (1, FRAME))
        self.assertEqual((observed['pending_entries'], observed['pending_bytes']), (1, FRAME))
        self.assertEqual(observed['coalesced_updates'], 9999)
        self.assertEqual(observed['backpressure_events'], 10000)
        self.assertEqual(observed['bytes_written'], 0)
        self.assertEqual(json.loads(progress.pending)['sequence'], 10000)

    def test_successful_write_releases_pending_slot(self):
        with patch('run_experiment.os.get_blocking', return_value=False), \
             patch('run_experiment.os.fpathconf', return_value=4096), \
             patch('run_experiment.os.write', return_value=FRAME):
            progress = Progress(999)
            progress.update()
        self.assertEqual(progress.snapshot()['frames_written'], 1)
        self.assertEqual(progress.snapshot()['pending_entries'], 0)

    def test_partial_atomic_write_fails(self):
        with patch('run_experiment.os.get_blocking', return_value=False), \
             patch('run_experiment.os.fpathconf', return_value=4096), \
             patch('run_experiment.os.write', return_value=FRAME - 1):
            progress = Progress(999)
            with self.assertRaisesRegex(RuntimeError, 'partial atomic'):
                progress.update()

    def test_broken_reader_is_not_misreported_as_backpressure(self):
        with patch('run_experiment.os.get_blocking', return_value=False), \
             patch('run_experiment.os.fpathconf', return_value=4096), \
             patch('run_experiment.os.write', side_effect=BrokenPipeError(errno.EPIPE, 'closed')):
            progress = Progress(999)
            with self.assertRaises(BrokenPipeError):
                progress.update()
            self.assertEqual(progress.snapshot()['backpressure_events'], 0)


if __name__ == '__main__':
    unittest.main()
