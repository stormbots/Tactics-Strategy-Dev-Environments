"""W2a cleanup failure-path checks, using fakes rather than extra native scope."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from run_experiment import Experiment, LOCKS, identity, remove_root, worker


class FakeProcess:
    def __init__(self, alive=False, exitcode=0):
        self.pid = 12345
        self.alive = alive
        self.exitcode = exitcode
        self.joins = 0

    def is_alive(self):
        return self.alive

    def join(self, timeout):
        self.joins += 1

    def terminate(self):
        self.alive = False
        self.exitcode = -15

    def kill(self):
        self.alive = False
        self.exitcode = -9


class CleanupChecks(unittest.TestCase):
    def fixture(self, root):
        for name in LOCKS:
            (root / name).touch(mode=0o600)
        return Experiment(root, dict(trace=[], cleanup={}))

    def test_unexpected_dead_actor_exit_is_failure(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2a-review-') as directory:
            e = self.fixture(Path(directory))
            e.actors['gui'] = FakeProcess(exitcode=1), Mock()
            with self.assertRaises(RuntimeError):
                e.cleanup()

    def test_one_cleanup_error_does_not_skip_other_actors(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2a-review-') as directory:
            e = self.fixture(Path(directory))
            a, b = FakeProcess(alive=True), FakeProcess(alive=True)
            e.actors = dict(gui=(a, Mock()), peer=(b, Mock()))
            e.expect = Mock(side_effect=ValueError('injected malformed reply'))
            with self.assertRaises(RuntimeError):
                e.cleanup()
            self.assertFalse(a.is_alive())
            self.assertFalse(b.is_alive())
            self.assertEqual(len(e.report['cleanup']['children']), 2)

    def test_dead_actor_is_joined(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2a-review-') as directory:
            e = self.fixture(Path(directory))
            actor = FakeProcess()
            e.actors['gui'] = actor, Mock()
            e.expected_exits['gui'] = 0
            e.cleanup()
            self.assertGreater(actor.joins, 0)

    def test_unplanned_zero_exit_is_failure(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2a-review-') as directory:
            e = self.fixture(Path(directory))
            e.actors['gui'] = FakeProcess(exitcode=0), Mock()
            with self.assertRaises(RuntimeError):
                e.cleanup()

    def test_remove_root_refuses_surviving_actor(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2a-review-') as directory:
            root = Path(directory)
            e = self.fixture(root)
            with self.assertRaisesRegex(RuntimeError, 'still alive'):
                remove_root(root, identity(root), e.baseline, [dict(alive=True)])
            self.assertTrue(all((root / name).exists() for name in LOCKS))

    def test_remove_root_refuses_unknown_entries(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2a-review-') as directory:
            root = Path(directory)
            e = self.fixture(root)
            (root / 'unknown').touch()
            with self.assertRaisesRegex(RuntimeError, 'unknown'):
                remove_root(root, identity(root), e.baseline, [])
            self.assertTrue((root / 'unknown').exists())

    def test_remove_root_refuses_changed_file(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2a-review-') as directory:
            root = Path(directory)
            e = self.fixture(root)
            (root / 'O').write_text('changed')
            with self.assertRaisesRegex(RuntimeError, 'file changed'):
                remove_root(root, identity(root), e.baseline, [])
            self.assertEqual((root / 'O').read_text(), 'changed')

    def test_remove_root_known_inventory_after_all_actors_exit(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2a-review-') as directory:
            root = Path(directory) / 'run'
            root.mkdir(mode=0o700)
            e = self.fixture(root)
            remove_root(root, identity(root), e.baseline, [dict(alive=False)])
            self.assertFalse(root.exists())

    def test_worker_rejects_opened_descriptor_identity_mismatch(self):
        with tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2a-review-') as directory:
            root = Path(directory)
            e = self.fixture(root)
            e.baseline['O'] = {**e.baseline['O'], 'inode': e.baseline['O']['inode'] + 1}
            connection = Mock()
            connection.recv.return_value = dict(action='acquire', lock='O', mode='exclusive')
            worker(connection, str(root), e.baseline)
            reply = connection.send.call_args_list[-1].args[0]
            self.assertEqual(reply['result'], 'error')
            self.assertIn('descriptor identity', reply['error'])
            connection.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
