"""Package unpublished native inputs; inspect DEBs without installing/extracting."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ASSET = 'Skyview-Dev-Setup-LinuxMint-amd64.deb'
BASELINE_FILES = [
    '/usr/bin/skyview-dev-setup',
    '/usr/lib/Skyview Dev Setup/backend/linux/self-update/bootstrap.py',
    '/usr/lib/Skyview Dev Setup/backend/linux/self-update/sde-update-trust',
    '/usr/lib/Skyview Dev Setup/backend/linux/lib/coordination.py',
    '/usr/lib/Skyview Dev Setup/backend/linux/Update-SkyviewStudentDev.sh',
]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def archive_hashes(package, switch, wanted):
    # Stream only named regular files; no package path is extracted or executed.
    process = subprocess.Popen(['/usr/bin/dpkg-deb', switch, str(package)], stdout=subprocess.PIPE)
    hashes = {}
    try:
        with tarfile.open(fileobj=process.stdout, mode='r|') as archive:
            for member in archive:
                name = '/' + member.name.removeprefix('./').lstrip('/')
                if name in wanted:
                    if name in hashes or not member.isfile() or member.size > 512 * 1024**2:
                        raise ValueError('Invalid or duplicated package member')
                    with archive.extractfile(member) as stream:
                        hashes[name] = hashlib.file_digest(stream, 'sha256').hexdigest()
        if process.wait() != 0 or set(hashes) != set(wanted):
            raise ValueError('Missing or unreadable package members')
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate()  # Read-only archive subprocess, never an installer.
        process.wait()
    return hashes


def package(build_log, root):
    binaries = [v['executable'] for line in build_log.read_text().splitlines()
                if (v := json.loads(line)).get('reason') == 'compiler-artifact'
                and v.get('profile', {}).get('test')
                and 'lib' in v.get('target', {}).get('kind', []) and v.get('executable')]
    if len(binaries) != 1:
        raise ValueError('Expected one native updater library test binary')
    expected_hooks = {'/' + name: digest(Path('installer/src-tauri/hooks') / name)
                      for name in ['postinst', 'prerm']}
    for role, version in [('baseline', '1.2.1'), ('candidate', '1.2.2')]:
        deb = root / role / ASSET
        identity = subprocess.check_output(['/usr/bin/dpkg-deb', '-f', str(deb),
                                             'Package', 'Version', 'Architecture'], text=True)
        if identity != f'Package: skyview-dev-setup\nVersion: {version}\nArchitecture: amd64\n':
            raise ValueError('Unexpected fixture package identity')
        if archive_hashes(deb, '--ctrl-tarfile', expected_hooks) != expected_hooks:
            raise ValueError('Fixture hooks differ from reviewed source')
    # Required second platform is an explicit inert placeholder in test metadata.
    # It is never packaged as or claimed to be a Windows artifact.
    (root / 'candidate/Skyview-Dev-Setup-Windows-x64.exe').write_bytes(b'unpublished inert test placeholder\n')
    shutil.copyfile(binaries[0], root / 'native-tests')
    (root / 'native-tests').chmod(0o700)
    files = ['baseline/' + ASSET, 'candidate/' + ASSET,
             'candidate/Skyview-Dev-Setup-Windows-x64.exe', 'native-tests']
    manifest = {'schemaVersion': 1, 'purpose': 'unpublished-linux-app-only-core-fixture',
                'sourceCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                'baselineVersion': '1.2.1', 'candidateVersion': '1.2.2',
                'files': {name: digest(root / name) for name in files},
                'baselineInstalledFiles': archive_hashes(root / ('baseline/' + ASSET),
                                                        '--fsys-tarfile', BASELINE_FILES),
                'packageHooks': expected_hooks}
    (root / 'pins.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'pinsSha256': digest(root / 'pins.json'), **manifest}, indent=2))


if __name__ == '__main__':
    if os.geteuid() == 0:
        raise ValueError('Artifact preparation does not need root')
    package(Path(sys.argv[1]), Path(sys.argv[2]))
