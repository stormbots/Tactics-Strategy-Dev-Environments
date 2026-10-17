"""Local broker/transport-contract checks; no polkit, root worker or packages."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('app_request', REPO / 'linux/self-update/app_request.py')
broker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(broker)


class RequestTests(unittest.TestCase):
    def test_fixed_invocation_and_requester(self):
        self.assertEqual(broker.validate_invocation(['fixed'], {'PKEXEC_UID': '1000'}, 0, broker.ENTRY), 1000)
        for argv, env, uid, path in [(['x', 'install'], {'PKEXEC_UID': '1000'}, 0, broker.ENTRY),
                                    (['x'], {}, 0, broker.ENTRY),
                                    (['x'], {'PKEXEC_UID': '0'}, 0, broker.ENTRY),
                                    (['x'], {'PKEXEC_UID': '01000'}, 0, broker.ENTRY),
                                    (['x'], {'PKEXEC_UID': '4294967295'}, 0, broker.ENTRY),
                                    (['x'], {'PKEXEC_UID': '１０００'}, 0, broker.ENTRY),
                                    (['x'], {'PKEXEC_UID': '1000'}, 1000, broker.ENTRY),
                                    (['x'], {'PKEXEC_UID': '1000'}, 0, Path('/tmp/fake'))]:
            with self.subTest(argv=argv, env=env, uid=uid, path=path):
                with self.assertRaises(RuntimeError):
                    broker.validate_invocation(argv, env, uid, path)

    def test_policy_has_fixed_action_no_cached_or_inactive_authority(self):
        policy = ET.parse(REPO / 'linux/polkit/org.skyviewrobotics.sde.app-update.policy').getroot()
        actions = policy.findall('action')
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action.attrib['id'], 'org.skyviewrobotics.sde.app-update')
        self.assertEqual(action.findtext('defaults/allow_active'), 'auth_admin')
        self.assertEqual(action.findtext('defaults/allow_inactive'), 'no')
        self.assertEqual(action.findtext('defaults/allow_any'), 'no')
        self.assertEqual([(a.attrib['key'], a.text) for a in action.findall('annotate')],
                         [('org.freedesktop.policykit.exec.path', str(broker.ENTRY))])
        self.assertTrue((REPO / 'linux/self-update/app_request.py').read_text().startswith('#!/usr/bin/python3 -I\n'))

    def test_exclusive_receipt_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'request.json'
            broker.write_new(path, b'original')
            with self.assertRaises(FileExistsError):
                broker.write_new(path, b'replay')
            self.assertEqual(path.read_bytes(), b'original')

    def test_snapshot_is_bounded_and_receipt_reader_is_bounded(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(broker, 'trusted'):
            source, destination = Path(temp) / 'source', Path(temp) / 'copy'
            source.write_bytes(b'x' * 10)
            with self.assertRaises(RuntimeError):
                broker.snapshot(source, destination, 9)
            self.assertFalse(destination.exists())
            broker.snapshot(source, destination, 10)
            self.assertEqual(destination.read_bytes(), b'x' * 10)
            with self.assertRaises(RuntimeError):
                broker.bounded_json(source, 9)

    def fixture(self, root):
        (root / 'app-only/runs').mkdir(parents=True)
        (root / 'app-only/request.gate').touch()
        (root / 'app-only-capabilities.json').write_text('{}')
        generation = '00000000-0000-4000-8000-000000000001'
        engine = root / 'engines' / generation
        engine.mkdir(parents=True)
        (engine / 'sde-update-trust').write_bytes(b'mock-only-never-executable')
        version = dict(schemaVersion=1, version='1.2.9')
        (engine / 'version.json').write_text(json.dumps(version))
        (root / 'active.json').write_text(json.dumps(dict(version, generation=generation)))

    def test_mocked_launch_detaches_and_sanitizes_without_native_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            with patch.object(broker, 'ROOT', root), patch.object(broker, 'trusted'), patch.object(broker.subprocess, 'Popen') as spawn:
                identifier = broker.create(1000)
            args, kw = spawn.call_args
            run = root / 'app-only/runs' / identifier
            self.assertEqual(args[0], [str(run / 'sde-update-trust'), 'app-only-linux'])
            self.assertTrue(kw['close_fds'])
            self.assertTrue(kw['start_new_session'])
            self.assertEqual(kw['env'], broker.ENV)
            self.assertEqual(kw['cwd'], '/')
            self.assertEqual(kw['stdin'], broker.subprocess.DEVNULL)
            request = json.loads((run / 'request.json').read_text())
            self.assertEqual(request['uid'], 1000)
            self.assertEqual(request['requestId'], identifier)
            self.assertEqual(request['deadlineMs'] - request['createdMs'], 900000)
            self.assertEqual((run / 'request.json').stat().st_mode & 0o777, 0o600)
            self.assertFalse((run / 'worker.log').exists())

    def test_capacity_stops_without_pruning_or_launching(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            for i in range(broker.MAX_RUNS):
                (root / 'app-only/runs' / str(i)).mkdir()
            with patch.object(broker, 'ROOT', root), patch.object(broker, 'trusted'), patch.object(broker.subprocess, 'Popen') as spawn:
                with self.assertRaises(RuntimeError):
                    broker.create(1000)
                spawn.assert_not_called()
            self.assertEqual(len(list((root / 'app-only/runs').iterdir())), broker.MAX_RUNS)

    def test_failed_spawn_preserves_request_and_snapshot_no_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            with patch.object(broker, 'ROOT', root), patch.object(broker, 'trusted'), patch.object(broker.subprocess, 'Popen', side_effect=OSError('mock failure')) as spawn:
                with self.assertRaises(OSError):
                    broker.create(1000)
                self.assertEqual(spawn.call_count, 1)
            runs = list((root / 'app-only/runs').iterdir())
            self.assertEqual(len(runs), 1)
            self.assertTrue((runs[0] / 'request.json').is_file())
            self.assertTrue((runs[0] / 'sde-update-trust').is_file())


if __name__ == '__main__':
    unittest.main()
