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
        for name in ('sessions.gate', 'operations.gate'):
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

    def test_readonly_validation_retains_evidence_and_excludes_mutations(self):
        validator = self.root / 'Validate-SkyviewStudentDev.sh'
        validator.write_text('#!/bin/bash\nexit 1\n')
        validator.chmod(0o644)
        original = b'private interrupted evidence; not a command or consent'
        coordination.JOURNAL.write_bytes(original)
        coordination.JOURNAL.chmod(0o600)
        before = coordination.JOURNAL.stat()
        before_files = {path.name: path.read_bytes() for path in self.root.iterdir()}
        command = ['/bin/bash', str(validator)]
        result = coordination.run('readonly', command)
        self.assertEqual(result, 1, 'Preserve real validation failure, not assumed readiness')
        self.assertEqual(coordination.JOURNAL.read_bytes(), original)
        after = coordination.JOURNAL.stat()
        self.assertEqual((before.st_ino, before.st_mtime_ns), (after.st_ino, after.st_mtime_ns))
        self.assertEqual({path.name: path.read_bytes() for path in self.root.iterdir()}, before_files)
        for invalid in ([sys.executable, '-c', 'raise Exception("must not start")'], ['/bin/bash', str(validator), '--system-only']):
            with self.assertRaises(coordination.CoordinationError):
                coordination.run('readonly', invalid)
        with self.assertRaises(coordination.CoordinationError):
            coordination.run('system', [sys.executable, '-c', 'raise Exception("must not start")'])
        lease = coordination.gate('operations.gate', False)
        try:
            with self.assertRaises(BlockingIOError):
                coordination.run('readonly', command)
        finally:
            os.close(lease)

        validator.chmod(0o666)
        try:
            with self.assertRaises(coordination.CoordinationError):
                coordination.run('readonly', command)
        finally:
            validator.chmod(0o644)
        linked = self.root / 'other-name'
        os.link(validator, linked)
        try:
            with self.assertRaises(coordination.CoordinationError):
                coordination.run('readonly', command)
        finally:
            linked.unlink()

    def test_standard_user_can_diagnose_without_reading_private_journal(self):
        validator = self.root / 'Validate-SkyviewStudentDev.sh'
        validator.write_text('#!/bin/bash\nprintf "123\\n"\n')
        validator.chmod(0o644)
        coordination.JOURNAL.write_bytes(b'private interruption')
        coordination.JOURNAL.chmod(0o600)
        # Supply only this test's source as data; nobody must not depend on
        # traverse access to the privileged runner's checkout or home directory.
        program = ('import sys;from pathlib import Path;'
                   'c={"__name__":"coordination_fixture"};exec(sys.argv[1],c);'
                   'c["ROOT"]=Path(sys.argv[2]);c["JOURNAL"]=c["ROOT"]/"transaction.json";'
                   'sys.exit(c["run"]("readonly",["/bin/bash",str(c["ROOT"]/"Validate-SkyviewStudentDev.sh")]))')
        def student():
            os.setgroups([]); os.setgid(65534); os.setuid(65534)
        result = subprocess.run([sys.executable, '-c', program, ENGINE.read_text(), str(self.root)],
                                preexec_fn=student, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('123', result.stdout)
        self.assertIn('Validation does not acknowledge', result.stdout)
        self.assertEqual(coordination.JOURNAL.read_bytes(), b'private interruption')
    def test_unsafe_modes_and_symlinks_rejected(self):
        (self.root / 'operations.gate').chmod(0o644)
        with self.assertRaises(coordination.CoordinationError):
            coordination.gate('operations.gate', False)
        (self.root / 'operations.gate').unlink()
        (self.root / 'operations.gate').symlink_to('sessions.gate')
        with self.assertRaises(OSError):
            coordination.gate('operations.gate', False)

if __name__ == '__main__':
    if os.environ.get('SDE_REQUIRE_COORDINATION') and (sys.platform != 'linux' or os.geteuid() != 0):
        raise RuntimeError('Required protected coordination tests cannot be skipped')
    unittest.main()
