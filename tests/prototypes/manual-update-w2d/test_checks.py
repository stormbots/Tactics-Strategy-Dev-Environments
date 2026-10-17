"""Focused W2d oracle/ownership/teardown checks; not extra native schedules."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from run_experiment import Case, LOCKS, admission_violation, fixture, support


class Checks(unittest.TestCase):
    def case(self, root):
        c = Case('legacy_wins', root, dict(trace=[], failures=[], result='Pass'))
        for name in LOCKS:
            (root / name).touch(mode=0o600)
            c.baseline[name] = support.inode((root / name).stat())
        return c

    def test_oracle_uses_actual_intent_not_skipped_actor_check(self):
        reply = dict(entered_normal=True, second={'skipped': True})
        self.assertTrue(admission_violation(reply, dict(present=True)))
        self.assertFalse(admission_violation(reply, dict(present=False)))

    def test_recovery_rejection_is_not_unsafe_admission(self):
        self.assertFalse(admission_violation(dict(entered_normal=False), dict(present=True)))

    def test_unregistered_fixture_preserved_at_teardown(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2d-check-') as directory:
            root = Path(directory) / 'run'
            root.mkdir(mode=0o700)
            c = self.case(root)
            fixture.publish_intent(root)
            original = (root / 'intent.json').read_bytes()
            with patch.object(support, 'direct_children', return_value=[]):
                c.cleanup()
            self.assertEqual((root / 'intent.json').read_bytes(), original)
            self.assertEqual(c.report['result'], 'Fail')

    def test_live_actor_without_bound_handle_is_not_signaled_or_disposed(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2d-check-') as directory:
            root = Path(directory) / 'run'
            root.mkdir(mode=0o700)
            c = self.case(root)
            process = Mock(pid=12345, returncode=None, stdin=None, stdout=None)
            process.poll.return_value = None
            c.actors = [dict(role='startup', process=process, pidfd=None, expected_exit=0)]
            with patch.object(support, 'direct_children', return_value=[12345]), \
                 patch('run_experiment.signal.pidfd_send_signal') as send:
                c.cleanup()
            send.assert_not_called()
            self.assertTrue(root.exists())
            self.assertFalse(c.report['cleanup']['root_removed'])
            self.assertEqual(c.report['result'], 'Fail')

    def test_inconsistent_held_lock_evidence_is_rejected(self):
        c = object.__new__(Case)
        c.event = Mock()
        c.baseline = {}
        identity = dict(pid=12345, ppid=os.getpid(), uid=os.geteuid(), start_ticks=100)
        entry = dict(role='startup', variant='guarded', identity=identity, process=Mock(), pidfd=999)
        reply = dict(role='startup', variant='guarded', identity=identity, held=['S'], held_identities={},
                     privilege=dict(euid=os.geteuid(), effective_capabilities='0'))
        with patch.object(support, 'read_message', return_value=reply):
            with self.assertRaisesRegex(RuntimeError, 'evidence inconsistent'):
                c.receive(entry)

    def test_quiescent_known_empty_case_teardown_succeeds(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2d-check-') as directory:
            root = Path(directory) / 'run'
            root.mkdir(mode=0o700)
            c = self.case(root)
            with patch.object(support, 'direct_children', return_value=[]):
                c.cleanup()
            self.assertFalse(root.exists())
            self.assertTrue(c.report['cleanup']['root_removed'])
            self.assertEqual(c.report['result'], 'Pass')

    def test_recorded_but_invalid_fixture_is_preserved(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2d-check-') as directory:
            root = Path(directory) / 'run'
            root.mkdir(mode=0o700)
            c = self.case(root)
            (root / 'intent.json').write_bytes(b'malformed-uncertain-fixture')
            c.intent = fixture.inspect_intent(root)
            with patch.object(support, 'direct_children', return_value=[]):
                c.cleanup()
            self.assertTrue((root / 'intent.json').exists())
            self.assertEqual((root / 'intent.json').read_bytes(), b'malformed-uncertain-fixture')
            self.assertEqual(c.report['result'], 'Fail')

    def test_reply_from_wrong_variant_is_rejected(self):
        c = object.__new__(Case)
        c.event = Mock()
        c.baseline = {}
        identity = dict(pid=12345, ppid=os.getpid(), uid=os.geteuid(), start_ticks=100)
        entry = dict(role='startup', variant='guarded', identity=identity, process=Mock(), pidfd=999)
        reply = dict(role='startup', variant='omit_second_check', identity=identity,
                     held=[], held_identities={}, privilege=dict(euid=os.geteuid(), effective_capabilities='0'))
        with patch.object(support, 'read_message', return_value=reply), \
             patch('run_experiment.select.select', return_value=([], [], [])):
            with self.assertRaisesRegex(RuntimeError, 'variant mismatch'):
                c.receive(entry)

    def test_startup_wins_requires_evidence_of_second_check(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2d-check-') as directory:
            root = Path(directory) / 'run'
            root.mkdir(mode=0o700)
            c = Case('startup_wins', root, dict(trace=[], failures=[], result='Not run'))
            absent = dict(present=False, reason='absent')
            c.launch = Mock(side_effect=[{}, {}])
            c.command = Mock(side_effect=[
                dict(held=['A'], first=absent),
                dict(decision='NormalSession', entered_normal=True, held=['S'], first=absent, second={'skipped': True}),
                dict(publication=None, mutation_starts=0, held=[], history=['S_exclusive_busy'])])
            c.probe = Mock()
            c.exit_actor = Mock()
            with self.assertRaisesRegex(RuntimeError, 'second check'):
                c.run()

    def test_conflicting_normal_decision_cannot_hide_oracle_violation(self):
        self.assertTrue(admission_violation(dict(decision='NormalSession', entered_normal=False), dict(present=True)))


if __name__ == '__main__':
    unittest.main()
