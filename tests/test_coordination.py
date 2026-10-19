"""Synthetic supervised processes only; never invoke package managers."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import call, patch

REPO = Path(__file__).resolve().parents[1]
ENGINE = REPO / 'linux/lib/coordination.py'
spec = importlib.util.spec_from_file_location('coordination', ENGINE)
coordination = importlib.util.module_from_spec(spec)
if sys.platform == 'linux':
    spec.loader.exec_module(coordination)

@unittest.skipUnless(sys.platform == 'linux' and os.geteuid() == 0,
                     'Full protected coordination tests require a disposable Linux root runner')
class Supervision(unittest.TestCase):
    def setUp(self):
        self.fixture = tempfile.TemporaryDirectory(prefix='sde-coordination-test-', dir='/var/lib')
        self.root = Path(self.fixture.name)
        self.root.chmod(0o755)
        for name in ('sessions.gate', 'operations.gate', 'admission.gate'):
            (self.root / name).touch(mode=0o444)
        self.old_root, self.old_journal = coordination.ROOT, coordination.JOURNAL
        coordination.ROOT = self.root
        coordination.JOURNAL = self.root / 'transaction.json'
    def tearDown(self):
        coordination.ROOT, coordination.JOURNAL = self.old_root, self.old_journal
        self.fixture.cleanup()
    def command(self, program):
        # Override the fixture path only in a test driver that imports the real
        # engine. Production CLI has no path/environment override.
        return [sys.executable, '-c',
                'import importlib.util,sys;from pathlib import Path;'
                's=importlib.util.spec_from_file_location("c",sys.argv[1]);'
                'c=importlib.util.module_from_spec(s);s.loader.exec_module(c);'
                'c.ROOT=Path(sys.argv[2]);c.JOURNAL=c.ROOT/"transaction.json";'
                'sys.exit(c.run("system",[sys.executable,"-c",sys.argv[3]]))',
                str(ENGINE), str(self.root), program]
    def test_child_failure_completes_without_blind_reexecution(self):
        result = coordination.run('system', [sys.executable, '-c', 'import sys;sys.exit(7)'])
        self.assertEqual(result, 7)
        self.assertFalse(coordination.JOURNAL.exists())
    def test_inherited_lease_is_real_and_forged_descriptor_is_rejected(self):
        fd = coordination.gate('operations.gate', False)
        session = coordination.gate('sessions.gate', True)
        try:
            old = dict(os.environ)
            os.environ[coordination.OPERATION] = str(fd)
            os.environ[coordination.SESSION] = str(session)
            coordination.check()
            os.environ[coordination.OPERATION] = str(session)
            with self.assertRaises(coordination.CoordinationError):
                coordination.check()
            os.environ.clear(); os.environ.update(old)
        finally:
            os.close(fd); os.close(session)
    def test_wrapper_crash_keeps_child_lease_and_journal(self):
        ready = self.root / 'ready'
        stop = self.root / 'stop'
        child = ('import time;from pathlib import Path;'
                 f'p=Path({str(ready)!r});p.write_text("ready");'
                 f's=Path({str(stop)!r});'
                 '\nwhile not s.exists():time.sleep(0.05)')
        process = subprocess.Popen(self.command(child))
        try:
            deadline = time.monotonic() + 10
            while not ready.exists() and time.monotonic() < deadline:
                self.assertIsNone(process.poll()); time.sleep(0.05)
            self.assertTrue(ready.exists())
            record = json.loads(coordination.JOURNAL.read_text())
            self.assertEqual(record['schema'], 1)
            self.assertEqual(coordination.JOURNAL.stat().st_mode & 0o777, 0o600)
            process.kill(); process.wait(timeout=10)
            with self.assertRaises(BlockingIOError):
                coordination.gate('operations.gate', False)
            stop.touch()
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                try:
                    lease = coordination.gate('operations.gate', False); os.close(lease); break
                except BlockingIOError:
                    time.sleep(0.05)
            else:
                self.fail('Child did not finish and release the inherited gate')
            with self.assertRaises(coordination.CoordinationError):
                coordination.run('system', [sys.executable, '-c', 'raise Exception("must not start")'])
            self.assertTrue(coordination.JOURNAL.exists())
        finally:
            stop.touch()
            if process.poll() is None:
                process.kill(); process.wait(timeout=10)
    def test_signalled_child_retains_uncertain_transaction(self):
        result = coordination.run('system', [sys.executable, '-c', 'import os,signal;os.kill(os.getpid(),signal.SIGTERM)'])
        self.assertEqual(result, 1)
        self.assertTrue(coordination.JOURNAL.exists())
    def test_standard_user_can_lease_but_cannot_mutate_or_read_private_state(self):
        coordination.JOURNAL.write_text('private diagnostic')
        coordination.JOURNAL.chmod(0o600)
        program = (
            'import os,fcntl,sys;from pathlib import Path;'
            'p=Path(sys.argv[1]);f=os.open(p/"sessions.gate",os.O_RDONLY);'
            'fcntl.flock(f,fcntl.LOCK_SH|fcntl.LOCK_NB);os.close(f);'
            '\nfor action in (lambda:(p/"sessions.gate").write_text("unsafe"),'
            'lambda:(p/"sessions.gate").unlink(),'
            'lambda:(p/"new-state").write_text("unsafe"),'
            'lambda:(p/"transaction.json").read_text()):'
            '\n try:action()'
            '\n except PermissionError:continue'
            '\n raise Exception("Standard user changed or read protected state")')
        def unelevated():
            os.setgroups([]); os.setgid(65534); os.setuid(65534)
        result = subprocess.run([sys.executable, '-c', program, str(self.root)], preexec_fn=unelevated, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_root_record_blocks_after_simulated_restart(self):
        coordination.JOURNAL.write_text('malformed stale state')
        with self.assertRaises(coordination.CoordinationError):
            coordination.run('operation', [sys.executable, '-c', 'raise Exception("must not start")'])
    def test_closed_admission_blocks_new_session_but_retains_existing_session(self):
        session = coordination.admitted_session()
        admission = coordination.gate('admission.gate', False)
        try:
            with self.assertRaises(BlockingIOError):
                coordination.admitted_session()
            inherited = coordination.admitted_session(str(session))
            os.close(inherited)
            with self.assertRaises(BlockingIOError):
                coordination.gate('sessions.gate', False)
        finally:
            os.close(admission)
            os.close(session)
    def test_orphan_scope_blocks_even_session_only_launch(self):
        (self.root / 'installation-scope.json').write_text('unknown')
        with self.assertRaises(coordination.CoordinationError):
            coordination.run('session', [sys.executable, '-c', 'raise Exception("must not start")'])
    def test_unsafe_modes_and_symlinks_rejected(self):
        (self.root / 'operations.gate').chmod(0o644)
        with self.assertRaises(coordination.CoordinationError):
            coordination.gate('operations.gate', False)
        (self.root / 'operations.gate').unlink()
        (self.root / 'operations.gate').symlink_to('sessions.gate')
        with self.assertRaises(OSError):
            coordination.gate('operations.gate', False)

@unittest.skipUnless(sys.platform == 'linux', 'Linux adapter')
class AdmissionOrdering(unittest.TestCase):
    def test_new_session_checks_intent_on_each_side_of_both_gates(self):
        with patch.object(coordination, 'no_interruption') as intent, \
                patch.object(coordination, 'gate', side_effect=[11, 12]) as gate, \
                patch.object(coordination.os, 'close') as close:
            events = unittest.mock.Mock()
            events.attach_mock(intent, 'intent')
            events.attach_mock(gate, 'gate')
            events.attach_mock(close, 'close')
            self.assertEqual(coordination.admitted_session(), 12)
            self.assertEqual(events.mock_calls, [call.intent(), call.gate('admission.gate', True),
                call.intent(), call.gate('sessions.gate', True, None), call.intent(), call.close(11)])

    def test_late_intent_releases_both_acquired_descriptors(self):
        with patch.object(coordination, 'no_interruption',
                          side_effect=[None, None, coordination.CoordinationError('intent')]), \
                patch.object(coordination, 'gate', side_effect=[11, 12]), \
                patch.object(coordination.os, 'close') as close:
            with self.assertRaises(coordination.CoordinationError):
                coordination.admitted_session()
            self.assertEqual(close.call_args_list, [call(12), call(11)])

    def test_existing_session_does_not_reenter_admission(self):
        with patch.object(coordination, 'no_interruption'), \
                patch.object(coordination, 'gate', return_value=12) as gate:
            self.assertEqual(coordination.admitted_session('9'), 12)
            gate.assert_called_once_with('sessions.gate', True, '9')


if __name__ == '__main__':
    if os.environ.get('SDE_REQUIRE_COORDINATION') and (sys.platform != 'linux' or os.geteuid() != 0):
        raise RuntimeError('Required protected coordination tests cannot be skipped')
    unittest.main()
