"""Focused W2c fixture checks, not production journal/parser acceptance."""
import json
import io
import os
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import unittest

from run_experiment import inspect_intent, publish_intent, expected_fixture, Experiment, support, main


class FixtureChecks(unittest.TestCase):
    def test_only_absence_has_no_intent(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2c-check-') as root:
            self.assertEqual(inspect_intent(Path(root)), dict(present=False, reason='absent'))

    def test_published_fixture_remains_unresolved_on_repeated_inspection(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2c-check-') as root:
            path = Path(root)
            published = publish_intent(path)
            self.assertEqual(published['operations'], ['exclusive_create_temporary_0600',
                'write_complete', 'fsync_temporary_file', 'link_into_intent_name_without_replacement',
                'remove_temporary_name', 'fsync_parent_directory'])
            self.assertEqual(published['observed']['reason'], 'unresolved_fixture')
            self.assertEqual(inspect_intent(path), published['observed'])
            self.assertEqual(inspect_intent(path), published['observed'])
            with self.assertRaisesRegex(RuntimeError, 'already exists'):
                publish_intent(path)

    def test_malformed_unknown_boolean_and_oversized_fixtures_block(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2c-check-') as root:
            path = Path(root)
            for raw in (b'{', b'x' * 4097,
                        json.dumps({**expected_fixture(path), 'schema': 2}).encode(),
                        json.dumps({**expected_fixture(path), 'schema': True}).encode(),
                        json.dumps({**expected_fixture(path), 'extra': 'ignored?'}).encode()):
                with self.subTest(raw=raw[:30]):
                    (path / 'intent.json').write_bytes(raw)
                    self.assertTrue(inspect_intent(path)['present'])
                    self.assertEqual(inspect_intent(path)['reason'], 'invalid_or_unreadable_fixture')

    def test_duplicate_fields_block(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2c-check-') as root:
            path = Path(root)
            raw = json.dumps(expected_fixture(path))
            (path / 'intent.json').write_text(raw[:-1] + ', "state": "unresolved"}')
            self.assertEqual(inspect_intent(path)['reason'], 'invalid_or_unreadable_fixture')

    def test_dangling_symlink_is_not_absence(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2c-check-') as root:
            path = Path(root)
            (path / 'intent.json').symlink_to('missing-fixture')
            self.assertTrue(inspect_intent(path)['present'])
            self.assertEqual(inspect_intent(path)['reason'], 'invalid_or_unreadable_fixture')

    def test_publication_does_not_overwrite_intent_created_during_flush(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2c-check-') as directory:
            root = Path(directory)
            original_fsync = os.fsync
            created = False
            def flush(fd):
                nonlocal created
                if not created:
                    (root / 'intent.json').write_bytes(b'previous-unresolved-intent')
                    created = True
                return original_fsync(fd)
            with patch('run_experiment.os.fsync', side_effect=flush):
                with self.assertRaises(FileExistsError):
                    publish_intent(root)
            self.assertEqual((root / 'intent.json').read_bytes(), b'previous-unresolved-intent')

    def fixture_experiment(self, directory, known=True):
        root = Path(directory) / 'run'
        root.mkdir(mode=0o700)
        e = Experiment(root, dict(result='Pass', trace=[], failures=[]))
        for name in ('O', 'A', 'S'):
            (root / name).touch(mode=0o600)
            e.expected_locks[name] = support.inode((root / name).stat())
        published = publish_intent(root)
        e.fixture = published['observed'] if known else None
        e.child_reaped = True
        return e

    def test_teardown_preserves_fixture_without_recorded_identity(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2c-check-') as directory:
            e = self.fixture_experiment(directory, known=False)
            before = (e.root / 'intent.json').read_bytes()
            with patch('run_experiment.support.direct_children', return_value=[]):
                e.cleanup()
            self.assertTrue((e.root / 'intent.json').exists())
            self.assertEqual((e.root / 'intent.json').read_bytes(), before)
            self.assertEqual(e.report['result'], 'Fail')

    def test_orphan_handle_close_error_does_not_skip_known_handles(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2c-check-') as directory:
            e = self.fixture_experiment(directory)
            process = Mock(pid=23456, returncode=0, stdin=None, stdout=None)
            process.poll.return_value = 0
            e.actors = [dict(role='known', process=process, pidfd=2222, expected_exit=0)]
            identity = dict(pid=12345, ppid=os.getpid(), uid=os.geteuid(), start_ticks=100)
            original_close = os.close
            closed = []
            def close(fd):
                closed.append(fd)
                if fd == 1111:
                    raise OSError('injected orphan close failure')
                if fd != 2222:
                    original_close(fd)
            with patch('run_experiment.support.direct_children', return_value=[12345]), \
                 patch('run_experiment.support.process_identity', return_value=identity), \
                 patch.object(e, 'bind', return_value=1111), \
                 patch('run_experiment.support.wait_pidfd', return_value=Mock(si_pid=12345, si_status=0)), \
                 patch('run_experiment.os.close', side_effect=close):
                e.cleanup()
            self.assertIn(2222, closed)
            self.assertEqual(e.report['result'], 'Fail')

    def test_initialization_failure_after_root_creation_is_not_blocked(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2c-check-') as directory:
            root = Path(directory) / 'run'
            root.mkdir(mode=0o700)
            output = io.StringIO()
            with patch('run_experiment.support.privilege', return_value=dict(effective_capabilities='0')), \
                 patch('run_experiment.os.geteuid', return_value=1000), \
                 patch('run_experiment.support.direct_children', return_value=[]), \
                 patch('run_experiment.support.subreaper', side_effect=[0, None, 1, None, 0]), \
                 patch('run_experiment.tempfile.mkdtemp', return_value=str(root)), \
                 patch('run_experiment.Experiment', side_effect=RuntimeError('injected initialization failure')), \
                 patch('sys.stdout', output):
                self.assertEqual(main(), 1)
            report = json.loads(output.getvalue())
            self.assertEqual(report['result'], 'Fail')
            self.assertFalse(report['cleanup']['root_removed'])
            self.assertTrue(root.exists())

    def test_teardown_preserves_changed_fixture(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2c-check-') as directory:
            e = self.fixture_experiment(directory)
            (e.root / 'intent.json').write_bytes(b'changed-uncertain-state')
            with patch('run_experiment.support.direct_children', return_value=[]):
                e.cleanup()
            self.assertEqual((e.root / 'intent.json').read_bytes(), b'changed-uncertain-state')
            self.assertEqual(e.report['result'], 'Fail')
            self.assertFalse(e.report['cleanup']['root_removed'])

    def test_teardown_removes_known_fixture_only_after_quiescence(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2c-check-') as directory:
            e = self.fixture_experiment(directory)
            with patch('run_experiment.support.direct_children', return_value=[]):
                e.cleanup()
            self.assertFalse(e.root.exists())
            self.assertEqual(e.report['result'], 'Pass')
            self.assertTrue(e.report['cleanup']['root_removed'])
            self.assertEqual(e.report['trace'][-1]['event'], 'teardown_only_fixture_removal')


if __name__ == '__main__':
    unittest.main()
