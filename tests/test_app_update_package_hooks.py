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
