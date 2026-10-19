"""Temporary-filesystem tests; never invoke sudo, polkit or installed SDE."""
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('mint_gate', Path(__file__).with_name('mint_disabled_broker_gate.py'))
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)
REPO = Path(__file__).resolve().parents[1]


class GateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.sources = self.root / 'sources'
        self.sources.mkdir(mode=0o700)
        installed = self.root / 'installed'
        installed.mkdir(mode=0o700)
        self.targets = {}
        for name, original in [('app_request.py', 'linux/self-update/app_request.py'),
                               ('app-update.policy', 'linux/polkit/org.skyviewrobotics.sde.app-update.policy')]:
            data = (REPO / original).read_bytes()
            (self.sources / name).write_bytes(data)
            (self.sources / name).chmod(0o600)
            mode = gate.TARGETS[name][1]
            self.targets[name] = (installed / name, mode, gate.TARGETS[name][2])
        self.preserved = self.root / 'baseline'
        self.preserved.write_bytes(b'old-maintenance-and-pause-bytes')
        self.preserved.chmod(0o600)
        for name, value in {
            'ROOT_UID': os.getuid(), 'ROOT_GID': os.getgid(), 'REQUESTER_UID': os.getuid(),
            'TARGETS': self.targets, 'JOURNAL_PARENT': self.root,
            'PRESERVE': [self.preserved, self.root / 'absent/optional/drop-in'],
            'BARRIERS': [], 'NAMESPACE': self.root / 'absent/app-only',
        }.items():
            p = patch.object(gate, name, value)
            p.start()
            self.addCleanup(p.stop)
        for name, value in [('host_preflight', {'Seat': 'seat0'}), ('action_present', False),
                            ('wait_action', None), ('trusted_parent', None)]:
            p = patch.object(gate, name, return_value=value)
            setattr(self, name, p.start())
            self.addCleanup(p.stop)
        self.helper = b'# reviewed helper bytes\n'

    def prepare(self):
        return Path(gate.prepare(self.sources, 'console', self.helper)['journal'])

    def test_exact_pair_removed_and_journal_retained(self):
        before = gate.read_file(self.preserved, os.getuid())[1]
        journal = self.prepare()
        for target, mode, expected in self.targets.values():
            _, actual = gate.read_file(target, os.getuid())
            self.assertEqual(actual['sha256'], expected)
            self.assertEqual(actual['st_mode'] & 0o777, mode)
        result = gate.cleanup(journal)
        self.assertEqual(result['installedFilesRemoved'], 2)
        self.assertTrue(result['preservationUnchanged'])
        self.assertTrue((journal / 'gate.py').is_file())
        self.assertEqual(gate.read_file(self.preserved, os.getuid())[1], before)
        self.assertTrue(all(not target.exists() for target, _, _ in self.targets.values()))
        self.wait_action.assert_any_call(True)
        self.wait_action.assert_any_call(False)

    def test_existing_target_never_overwritten(self):
        target = self.targets['app_request.py'][0]
        target.write_bytes(b'existing')
        with self.assertRaisesRegex(ValueError, 'Existing fixed file'):
            self.prepare()
        self.assertEqual(target.read_bytes(), b'existing')
        self.assertFalse(self.targets['app-update.policy'][0].exists())

    def test_source_mismatch_before_installed_mutation(self):
        (self.sources / 'app-update.policy').write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError, 'Source hash mismatch'):
            self.prepare()
        self.assertFalse(any(target.exists() for target, _, _ in self.targets.values()))

    def test_source_symlink_rejected(self):
        source = self.sources / 'app_request.py'
        source.unlink()
        source.symlink_to(self.preserved)
        with self.assertRaises(OSError):
            self.prepare()

    def test_second_target_changed_cleanup_removes_neither(self):
        journal = self.prepare()
        self.targets['app-update.policy'][0].write_bytes(b'unknown')
        with self.assertRaisesRegex(ValueError, 'Fixed file changed'):
            gate.cleanup(journal)
        self.assertTrue(all(target.exists() for target, _, _ in self.targets.values()))

    def test_same_bytes_replaced_inode_not_adopted(self):
        journal = self.prepare()
        target, mode, _ = self.targets['app_request.py']
        replacement = target.with_name('replacement')
        replacement.write_bytes(target.read_bytes())
        replacement.chmod(mode)
        replacement.replace(target)
        with self.assertRaisesRegex(ValueError, 'Fixed file changed'):
            gate.cleanup(journal)
        self.assertTrue(all(target.exists() for target, _, _ in self.targets.values()))

    def test_protected_drift_is_reported_after_owned_cleanup(self):
        journal = self.prepare()
        self.preserved.write_bytes(b'changed elsewhere')
        with self.assertRaisesRegex(ValueError, 'Owned files removed, but protected baseline changed'):
            gate.cleanup(journal)
        self.assertFalse(any(target.exists() for target, _, _ in self.targets.values()))
        self.assertFalse(json.loads((journal / 'record.json').read_text())['preservationUnchanged'])

    def test_partial_journal_refused(self):
        journal = self.prepare()
        record = json.loads((journal / 'record.json').read_text())
        record['phase'] = 'preparing'
        (journal / 'record.json').write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, 'Partial or unknown journal'):
            gate.cleanup(journal)
        self.assertTrue(all(target.exists() for target, _, _ in self.targets.values()))

    def test_record_cannot_select_unlink_target(self):
        journal = self.prepare()
        record = json.loads((journal / 'record.json').read_text())
        record['created'] = {str(self.preserved): next(iter(record['created'].values()))}
        (journal / 'record.json').write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, 'Partial or unknown journal'):
            gate.cleanup(journal)
        self.assertTrue(self.preserved.exists())

    def test_unverified_loader_has_no_side_effect(self):
        with self.assertRaisesRegex(ValueError, 'hash-verifying loader'):
            gate.prepare(self.sources, 'console', None)
        self.host_preflight.assert_not_called()


class ProbeTests(unittest.TestCase):
    def test_non_readonly_commands_never_run(self):
        with patch.object(gate.subprocess, 'run') as run:
            for executable in ['/usr/bin/pkexec', '/usr/bin/apt', '/bin/sh', 'bootstrap.py']:
                with self.assertRaisesRegex(ValueError, 'Not a read-only'):
                    gate.command(executable)
            run.assert_not_called()

    def test_xrdp_rejected_even_when_remote_no_active_yes(self):
        report = 'User=1000\nSeat=\nService=xrdp-sesman\nType=x11\nActive=yes\nRemote=no\nDisplay=:10\n'
        with patch.object(gate.socket, 'gethostname', return_value='ryan-ThinkCentre-M910q'), \
                patch.object(gate.pwd, 'getpwuid', return_value=SimpleNamespace(pw_name='ryan')), \
                patch.object(Path, 'read_text', return_value='ID=linuxmint\nVERSION_ID="22.3"\n'), \
                patch.object(gate, 'command', return_value=SimpleNamespace(returncode=0, stdout=report)) as command:
            with self.assertRaisesRegex(ValueError, 'physical Cinnamon console'):
                gate.host_preflight('c11')
            self.assertEqual(command.call_count, 1)

    def test_absent_nested_parent_allowed_but_symlink_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Restrict the ancestor sequence to this disposable tree only.
            original = Path.lstat
            def metadata(path):
                if path == root or root in path.parents:
                    return original(path)
                return SimpleNamespace(st_mode=0o40755, st_uid=os.getuid())
            with patch.object(gate, 'ROOT_UID', os.getuid()), patch.object(Path, 'lstat', metadata):
                gate.trusted_parent(root / 'missing/nested/file', allow_missing=True)
                (root / 'linked').symlink_to(root, target_is_directory=True)
                with self.assertRaisesRegex(ValueError, 'Untrusted installed parent'):
                    gate.trusted_parent(root / 'linked/missing/file', allow_missing=True)


if __name__ == '__main__':
    unittest.main()
