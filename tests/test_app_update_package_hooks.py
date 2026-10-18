"""Local mocked hook checks. No installed paths, services or packages are changed."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('app_update_bootstrap', REPO / 'linux/self-update/bootstrap.py')
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


class PackageHooks(unittest.TestCase):
    def test_disabled_deployment_upgrade_and_removal_preserve_gate_and_evidence(self):
        # All filesystem activity is in a disposable user-owned temp fixture.
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            parent = base / 'state'
            parent.mkdir(mode=0o755)
            parent.chmod(0o755)
            root = parent / 'self-update'
            source = base / 'broker'
            source.write_bytes(b'EXECUTION_ENABLED = False\n# old')
            policy = base / 'policy'
            policy.write_bytes(b'policy fixture')
            targets = base / 'targets'
            targets.mkdir(mode=0o755)
            targets.chmod(0o755)
            entry, action = targets / 'entry', targets / 'action'
            sources = {entry: (source, 65536, 0o755), action: (policy, 8192, 0o644)}
            with patch.object(bootstrap, 'ROOT', root), patch.object(bootstrap, 'APP_ENTRY', entry), \
                    patch.object(bootstrap, 'app_sources', return_value=sources), patch.object(bootstrap, 'trusted'), \
                    patch.object(bootstrap.subprocess, 'run', side_effect=AssertionError('command ran')):
                bootstrap.deploy_app_only()
                gate = root / 'app-only/request.gate'
                inode = gate.stat().st_ino
                evidence = root / 'app-only/runs/retained'
                evidence.mkdir()
                source.write_bytes(b'EXECUTION_ENABLED = False\n# new')
                bootstrap.deploy_app_only()
                self.assertEqual(entry.read_bytes(), source.read_bytes())
                self.assertEqual(gate.stat().st_ino, inode)
                self.assertFalse((root / 'app-only-capabilities.json').exists())
                self.assertFalse(json.loads((root / 'app-only-deployment.json').read_text())['executionEnabled'])
                bootstrap.remove_app_only()
                self.assertFalse(entry.exists())
                self.assertFalse(action.exists())
                self.assertTrue(evidence.exists())
                self.assertEqual(gate.stat().st_ino, inode)

    def test_explicit_disabled_deployment_does_not_enter_maintenance(self):
        for flag, method in [('--deploy-app-only-disabled', 'deploy_app_only'),
                             ('--remove-app-only-disabled', 'remove_app_only')]:
            with self.subTest(flag=flag), patch.object(bootstrap.os, 'geteuid', return_value=0), \
                    patch.object(bootstrap.sys, 'argv', ['bootstrap.py', flag]), \
                    patch.object(bootstrap.os, 'umask'), patch.object(bootstrap, method) as action, \
                    patch.object(bootstrap, 'app_only_installation', side_effect=AssertionError('maintenance entered')), \
                    patch.object(bootstrap.subprocess, 'run', side_effect=AssertionError('command ran')):
                bootstrap.main()
                action.assert_called_once_with()

    def test_atomic_exact_declared_mode_with_private_umask(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(bootstrap, 'trusted'):
            path = Path(temp) / 'file'
            previous = os.umask(0o077)
            try:
                for mode in (0o600, 0o644, 0o755):
                    bootstrap.atomic(path, b'disabled fixture', mode)
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), mode)
            finally:
                os.umask(previous)

    def test_deployment_unknown_file_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, target = root / 'source', root / 'target'
            source.write_bytes(b'EXECUTION_ENABLED = False')
            target.write_bytes(b'foreign')
            with patch.object(bootstrap, 'deployment_record', return_value=None), \
                    patch.object(bootstrap, 'APP_ENTRY', target), patch.object(bootstrap, 'trusted'), \
                    patch.object(bootstrap, 'app_sources', return_value={target: (source, 1024, 0o755)}):
                with self.assertRaisesRegex(RuntimeError, 'Unknown installed'):
                    bootstrap.deployment_plan()
            self.assertEqual(target.read_bytes(), b'foreign')

    def test_removal_unknown_deployment_preserves_files(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'foreign'
            target.write_bytes(b'evidence')
            with patch.object(bootstrap, 'deployment_record', return_value=None), \
                    patch.object(bootstrap, 'app_sources', return_value={target: None}):
                with self.assertRaisesRegex(RuntimeError, 'Unrecorded'):
                    bootstrap.remove_app_only()
            self.assertEqual(target.read_bytes(), b'evidence')

    def read_intent(self, value):
        with tempfile.TemporaryFile() as stream:
            stream.write(value)
            stream.seek(0)
            with patch.object(Path, 'lstat', return_value=SimpleNamespace(st_mode=stat.S_IFREG)), \
                    patch.object(bootstrap, 'trusted') as trust, \
                    patch.object(bootstrap.os, 'open', return_value=os.dup(stream.fileno())) as opened:
                result = bootstrap.app_only_installation()
                trust.assert_called_once_with(Path('/var/lib/skyview-robotics-coordination/installation-scope.json'))
                self.assertEqual(opened.call_args.args[1], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
                return result

    def test_app_only_scope_and_legacy_scheduled_record(self):
        self.assertTrue(self.read_intent(b'{"schema":1,"kind":"installation","scope":"app_only"}'))
        for raw in [b'{"schema":1,"kind":"installation"}', b'{"schema":1,"kind":"system","token":"legacy"}']:
            with self.assertRaises(RuntimeError):
                self.read_intent(raw)

    def test_bad_or_future_scope_never_silently_becomes_scheduled(self):
        for record in [[], None, {'schema': True}, {'schema': 2},
                       {'schema': 1, 'scope': 'future'},
                       {'schema': 1, 'scope': 'app_only', 'kind': 'system'}]:
            with self.subTest(record=record), self.assertRaises((ValueError, RuntimeError)):
                self.read_intent(json.dumps(record).encode())
        for raw in [b'{', b'\xff', b' ' * 4097]:
            with self.subTest(raw_length=len(raw)), self.assertRaises((ValueError, RuntimeError)):
                self.read_intent(raw)

    def test_missing_intent_keeps_existing_install_behavior(self):
        with patch.object(Path, 'lstat', side_effect=FileNotFoundError), \
                patch.object(bootstrap, 'Path', wraps=Path) as paths, \
                patch.object(bootstrap, 'trusted') as trust:
            self.assertFalse(bootstrap.app_only_installation())
            paths.assert_called_once_with('/var/lib/skyview-robotics-coordination/installation-scope.json')
            trust.assert_not_called()

    def test_untrusted_or_nonregular_intent_stops(self):
        with patch.object(Path, 'lstat', return_value=SimpleNamespace(st_mode=stat.S_IFREG)), \
                patch.object(bootstrap, 'trusted', side_effect=RuntimeError('untrusted')):
            with self.assertRaises(RuntimeError):
                bootstrap.app_only_installation()
        with patch.object(Path, 'lstat', return_value=SimpleNamespace(st_mode=stat.S_IFDIR)), \
                patch.object(bootstrap, 'trusted'):
            with self.assertRaises(RuntimeError):
                bootstrap.app_only_installation()

    def test_app_only_does_not_touch_schedule_or_run_commands(self):
        with patch.object(Path, 'exists', side_effect=AssertionError('schedule probed')), \
                patch.object(bootstrap, 'atomic', side_effect=AssertionError('schedule changed')), \
                patch.object(bootstrap.subprocess, 'run', side_effect=AssertionError('command ran')):
            bootstrap.configure_maintenance(True)

    def test_scheduled_mode_preserves_existing_activation(self):
        with patch.object(Path, 'exists', return_value=True), \
                patch.object(Path, 'is_dir', return_value=True), \
                patch.object(Path, 'read_text', return_value='# SDE_COORDINATION_V1'), \
                patch.object(bootstrap, 'trusted'), patch.object(bootstrap, 'directory'), \
                patch.object(bootstrap, 'atomic') as atomic, \
                patch.object(bootstrap.subprocess, 'run') as run:
            bootstrap.configure_maintenance(False)
            self.assertEqual(atomic.call_args.args[0], bootstrap.DROPIN)
            self.assertIn(b'ExecStart=/usr/bin/python3 -I /usr/local/libexec/skyview-self-update.py', atomic.call_args.args[1])
            self.assertEqual(run.call_args.args[0], ['/usr/bin/systemctl', 'daemon-reload'])

    def test_app_only_lookup_precedes_packaging_writes(self):
        # Exercise the real main entry, stopping before any filesystem mutation.
        with patch.object(bootstrap.os, 'geteuid', return_value=0), \
                patch.object(bootstrap.sys, 'argv', ['bootstrap.py']), \
                patch.object(bootstrap.os, 'umask'), \
                patch.object(bootstrap, 'app_only_installation', side_effect=RuntimeError('intent unavailable')), \
                patch.object(bootstrap, 'directory') as directory, \
                patch.object(bootstrap, 'atomic') as atomic:
            with self.assertRaisesRegex(RuntimeError, 'intent unavailable'):
                bootstrap.main()
            directory.assert_not_called()
            atomic.assert_not_called()


if __name__ == '__main__':
    unittest.main()
