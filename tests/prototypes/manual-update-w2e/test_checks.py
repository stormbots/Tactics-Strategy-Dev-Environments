"""Focused W2e buffer/error checks; no additional native schedules."""
import errno
import json
import os
import unittest
from unittest.mock import Mock, patch

from run_experiment import Progress, FRAME, Case, support, validate_progress, validate_reader


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

    def receive_fixture(self, stats):
        case = object.__new__(Case)
        case.event = Mock()
        case.baseline = {}
        identity = dict(pid=12345, ppid=os.getpid(), uid=os.geteuid(), start_ticks=100)
        entry = dict(role='supervisor', identity=identity, pidfd=999, process=Mock())
        reply = dict(event='status', identity=identity, held=[], held_identities={}, progress=stats,
                     privilege=dict(euid=os.geteuid(), effective_capabilities='0'))
        return case, entry, reply

    def zero_stats(self):
        return dict(updates=0, frames_written=0, bytes_written=0, backpressure_events=0,
                    last_errno=None, coalesced_updates=0, pending_entries=0, pending_bytes=0,
                    high_entries=0, high_bytes=0, frame_bytes=FRAME, discarded_updates=0)

    def test_later_supervisor_queue_violation_is_rejected(self):
        case, entry, reply = self.receive_fixture({**self.zero_stats(), 'high_entries': 2, 'high_bytes': FRAME * 2})
        with patch.object(support, 'read_message', return_value=reply), \
             patch('run_experiment.select.select', return_value=([], [], [])):
            with self.assertRaisesRegex(RuntimeError, 'progress'):
                case.receive(entry)

    def test_unaccounted_progress_is_rejected(self):
        case, entry, reply = self.receive_fixture({**self.zero_stats(), 'updates': 1})
        with patch.object(support, 'read_message', return_value=reply), \
             patch('run_experiment.select.select', return_value=([], [], [])):
            with self.assertRaisesRegex(RuntimeError, 'accounting'):
                case.receive(entry)

    def test_deferral_discard_is_counted_once_and_conserves_updates(self):
        with patch('run_experiment.os.get_blocking', return_value=False), \
             patch('run_experiment.os.fpathconf', return_value=4096), \
             patch('run_experiment.os.write', side_effect=BlockingIOError(errno.EAGAIN, 'full')):
            progress = Progress(999)
            for _ in range(3):
                progress.update()
            progress.discard()
            progress.discard()
        stats = progress.snapshot()
        self.assertEqual((stats['discarded_updates'], stats['pending_entries']), (1, 0))
        self.assertEqual(stats['coalesced_updates'], 2)
        validate_progress(stats)

    def test_progress_counters_cannot_regress_between_replies(self):
        before = {**self.zero_stats(), 'updates': 2, 'frames_written': 2, 'bytes_written': FRAME * 2,
                  'high_entries': 1, 'high_bytes': FRAME}
        after = {**before, 'updates': 1, 'frames_written': 1, 'bytes_written': FRAME}
        validate_progress(before)
        validate_progress(after)
        with self.assertRaisesRegex(RuntimeError, 'regressed'):
            validate_progress(after, before)

    def test_boolean_progress_counter_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'counters'):
            validate_progress({**self.zero_stats(), 'updates': True})

    def test_final_reader_bytes_must_reconcile_with_writer(self):
        progress = {**self.zero_stats(), 'updates': 1, 'frames_written': 1, 'bytes_written': FRAME,
                    'high_entries': 1, 'high_bytes': FRAME}
        responsive = dict(mode='responsive', endpoint_open=True, bytes_read=FRAME, queued_bytes=0)
        stalled = dict(mode='stalled', endpoint_open=True, bytes_read=0, queued_bytes=FRAME)
        validate_reader(responsive, progress, 'responsive')
        validate_reader(stalled, progress, 'stalled')
        with self.assertRaisesRegex(RuntimeError, 'byte accounting'):
            validate_reader({**responsive, 'bytes_read': FRAME - 1}, progress, 'responsive')
        with self.assertRaisesRegex(RuntimeError, 'mode/endpoint'):
            validate_reader(responsive, progress, 'stalled')


if __name__ == '__main__':
    unittest.main()
