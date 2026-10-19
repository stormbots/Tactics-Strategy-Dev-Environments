"""Archive/diagnostic preparation only; no native install or authorization."""
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import mint_authorization_diagnosis as diagnosis
import package_app_only_fixtures as artifacts


class Preparation(unittest.TestCase):
    def test_desktop_override_preserves_hidden_and_literal_exec_without_running_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'agent.desktop'
            path.write_text('[Desktop Entry]\nExec=/packaged/polkit-agent %u\nHidden=true\nOnlyShowIn=X-Cinnamon;\n')
            with patch.object(subprocess, 'run', side_effect=AssertionError('must not execute')):
                entry = diagnosis.autostart(path)
            self.assertEqual(entry['Exec'], '/packaged/polkit-agent %u')
            self.assertEqual(entry['Hidden'], 'true')
            path.write_text('[Desktop Entry]\nHidden=true\n')
            self.assertEqual(diagnosis.autostart(path, {'agent.desktop'})['Hidden'], 'true')
            path.write_text('[Desktop Entry]\nExec=/some/other-app\n')
            self.assertIsNone(diagnosis.autostart(path))

    def test_diagnosis_refuses_root_before_reading_or_probing(self):
        with patch.object(diagnosis.os, 'geteuid', return_value=0), \
                patch.object(diagnosis, 'probe', side_effect=AssertionError('must not probe')):
            with self.assertRaises(ValueError):
                diagnosis.report()

    def test_real_deb_pair_records_hooks_and_installed_bytes_without_extraction(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / 'test-binary'
            binary.write_bytes(b'never executable test placeholder')
            log = root / 'build.jsonl'
            log.write_text(json.dumps({'reason': 'compiler-artifact', 'profile': {'test': True},
                                      'target': {'kind': ['lib']}, 'executable': str(binary)}) + '\n')
            for role, version in [('baseline', '1.2.1'), ('candidate', '1.2.2')]:
                directory = root / role
                directory.mkdir()
                build = root / (role + '-build')
                control = build / 'DEBIAN'
                control.mkdir(parents=True)
                control.chmod(0o755)
                (control / 'control').write_text(f'Package: skyview-dev-setup\nVersion: {version}\nArchitecture: amd64\nMaintainer: Fixture <test@example.invalid>\nDescription: unpublished archive-only test\n')
                for name in ['postinst', 'prerm']:
                    (control / name).write_bytes((Path('installer/src-tauri/hooks') / name).read_bytes())
                    (control / name).chmod(0o755)
                for name in artifacts.BASELINE_FILES:
                    path = build / name.lstrip('/')
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(('fixture ' + name).encode())
                subprocess.run(['/usr/bin/dpkg-deb', '--build', str(build), str(directory / artifacts.ASSET)],
                               check=True, capture_output=True)
            with patch('sys.stdout', new=io.StringIO()):
                artifacts.package(log, root)
            pins = json.loads((root / 'pins.json').read_text())
            self.assertEqual(pins['purpose'], 'unpublished-linux-app-only-core-fixture')
            self.assertEqual(set(pins['baselineInstalledFiles']), set(artifacts.BASELINE_FILES))
            self.assertEqual(pins['files']['native-tests'], artifacts.digest(binary))
            self.assertEqual(pins['packageHooks']['/postinst'], artifacts.digest(Path('installer/src-tauri/hooks/postinst')))
            self.assertEqual((root / 'native-tests').read_bytes(), binary.read_bytes())

    def test_archive_rejects_missing_and_linked_members(self):
        for linked in [False, True]:
            with tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / 'fixture.tar'
                with tarfile.open(path, 'w') as archive:
                    if linked:
                        member = tarfile.TarInfo('./postinst')
                        member.type, member.linkname = tarfile.SYMTYPE, '/unrelated'
                        archive.addfile(member)
                # Exercise the streaming reader against a real read-only subprocess.
                real_popen = subprocess.Popen
                with patch.object(artifacts.subprocess, 'Popen',
                                  side_effect=lambda *a, **kw: real_popen(['/bin/cat', str(path)], stdout=subprocess.PIPE)):
                    with self.assertRaises(ValueError):
                        artifacts.archive_hashes(path, '--ctrl-tarfile', ['/postinst'])


if __name__ == '__main__':
    unittest.main()
