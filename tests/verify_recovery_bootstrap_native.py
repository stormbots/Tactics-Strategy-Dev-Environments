"""Installed Debian post-install hook; synthetic state on disposable CI only.

Invoked explicitly by native CI, never by ordinary unittest discovery.
"""
import fcntl
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

ROOT = Path('/var/lib/skyview-robotics-coordination')
APP = '/usr/bin/skyview-dev-setup'
METADATA = ('recovery-incident.json', 'recovery-binding.json',
            'recovery-acknowledgment.json', 'recovery-context.json')
ORIGINAL = b'{"schema":1,"id":"synthetic-bootstrap-ci-only","kind":"system"}'


def main(package):
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.geteuid() != 0:
        raise RuntimeError('Disposable root GitHub runner required.')
    journal = ROOT / 'transaction.json'
    for name in ('transaction.json', 'recovery-archive', 'recovery-disposition.json', *METADATA):
        if (ROOT / name).exists() or (ROOT / name).is_symlink():
            raise RuntimeError('Expected a clean disposable bootstrap fixture.')
    fd = os.open(journal, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(ORIGINAL)
        stream.flush()
        os.fsync(stream.fileno())
    original_identity = journal.stat().st_ino

    def original():
        info = journal.lstat()
        assert stat.S_ISREG(info.st_mode) and info.st_uid == 0
        assert stat.S_IMODE(info.st_mode) == 0o600 and info.st_ino == original_identity
        assert journal.read_bytes() == ORIGINAL, 'Bootstrap changed original evidence'

    # A signed install owns this gate across dpkg hooks. Initialization must
    # succeed without publishing live work or replacing the held gate inode.
    with (ROOT / 'operations.gate').open('rb') as gate:
        fcntl.flock(gate, fcntl.LOCK_EX | fcntl.LOCK_NB)
        subprocess.run([APP, '--coordination-init'], check=True)
        assert all(not (ROOT / name).exists() for name in METADATA)
        assert (ROOT / 'operations.gate').stat().st_ino == os.fstat(gate.fileno()).st_ino
        with (ROOT / 'operations.gate').open('rb') as probe:
            try:
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                raise AssertionError('Bootstrap released the supervisor gate')
    original()
    # Real package hook, not a direct checkout library call. No package timeout,
    # termination or simulated success; a failing package result fails this job.
    subprocess.run(['/usr/bin/dpkg', '-i', str(Path(package).resolve())], check=True)
    original()
    incident = json.loads((ROOT / METADATA[0]).read_bytes())
    import uuid
    assert set(incident) == {'schema', 'incidentId'} and incident['schema'] == 1
    assert str(uuid.UUID(incident['incidentId'])) == incident['incidentId']
    context = (ROOT / 'recovery-context.json').read_bytes()
    slot = ROOT / 'recovery-acknowledgment.json'
    assert slot.stat().st_uid == 0 and stat.S_IMODE(slot.stat().st_mode) == 0o666
    intent = json.dumps(incident).encode()
    slot.write_bytes(intent)
    subprocess.run([APP, '--coordination-init'], check=True)
    original()
    assert json.loads((ROOT / METADATA[0]).read_bytes()) == incident
    assert (ROOT / 'recovery-context.json').read_bytes() == context
    assert slot.read_bytes() == intent
    assert not (ROOT / 'recovery-archive').exists()
    assert not (ROOT / 'recovery-disposition.json').exists()
    assert not Path('/usr/local/sbin/skyview-student-dev-update').exists()
    assert not Path('/var/lib/skyview-robotics/student-dev/version').exists()
    assert not Path('/etc/systemd/system/skyview-student-dev-update.service').exists()
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'installed_coordination', '/usr/lib/Skyview Dev Setup/backend/linux/lib/coordination.py')
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    try:
        engine.run('system', ['this-command-must-never-run'])
    except engine.CoordinationError as error:
        assert 'interrupted' in str(error)
    else:
        raise AssertionError('Bootstrap released the installed script execution gate')
    original()
    # Cleanup is restricted to a completely successful synthetic fixture. On
    # failure preserve it; never clear unexpected or partially published state.
    original()
    journal.unlink()
    for name in METADATA:
        (ROOT / name).unlink()
    print('SDE_RECOVERY_LINUX_INSTALLED_BOOTSTRAP_OK')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Expected the native fixture package path')
    main(sys.argv[1])
