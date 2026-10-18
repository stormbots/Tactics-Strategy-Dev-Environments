#!/usr/bin/python3
"""DEB packaging hook: activate engines only, never provision or start tools."""
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import uuid

ROOT = Path('/var/lib/skyview-robotics/self-update')
BUNDLE = Path('/usr/lib/Skyview Dev Setup/backend/linux/self-update')
LAUNCHER = Path('/usr/local/libexec/skyview-self-update.py')
HISTORY_HOOK = Path('/usr/local/libexec/skyview-maintenance-history.py')
DROPIN = Path('/etc/systemd/system/skyview-student-dev-update.service.d/sde-self-update.conf')


def trusted(path):
    for item in (path, *path.parents):
        m = item.lstat()
        if m.st_uid != 0 or m.st_mode & 0o022 or not (stat.S_ISDIR(m.st_mode) or stat.S_ISREG(m.st_mode)):
            raise RuntimeError('Untrusted maintenance path')
        if stat.S_ISREG(m.st_mode) and m.st_nlink != 1:
            raise RuntimeError('Linked maintenance file')


def directory(path, mode=0o700):
    trusted(path.parent)
    try:
        path.mkdir(mode=mode)
        path.chmod(mode)
    except FileExistsError:
        pass
    trusted(path)
    path.chmod(mode)
    # Persist the new directory entry before a receipt can select its engine.
    for item in (path, path.parent):
        fd = os.open(item, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def atomic(path, value, mode=0o600):
    trusted(path.parent)
    if path.exists() or path.is_symlink():
        trusted(path)
    temp = path.with_name(str(uuid.uuid4()) + '.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def receipt(path, value):
    atomic(path, json.dumps(value).encode())


def app_only_installation():
    """Protected scope is a preservation hint, never installation authority."""
    journal = Path('/var/lib/skyview-robotics-coordination/installation-scope.json')
    try:
        journal.lstat()
    except FileNotFoundError:
        return False
    trusted(journal)
    if not stat.S_ISREG(journal.lstat().st_mode):
        raise RuntimeError('Invalid installation intent')
    fd = os.open(journal, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        raw = stream.read(4097)
    if len(raw) > 4096:
        raise RuntimeError('Oversized installation intent')
    record = json.loads(raw)
    if not isinstance(record, dict) or type(record.get('schema')) is not int or record['schema'] != 1:
        raise RuntimeError('Unsupported installation intent')
    scope = record.get('scope')
    if scope != 'app_only' or record.get('kind') != 'installation':
        raise RuntimeError('Unsupported installation scope')
    return True


def configure_maintenance(app_only):
    # A fixed drop-in selects the launcher and records its service attempts.
    # Timer settings and unrelated service settings are preserved; app-only
    # installs create no unit. Hooks do not execute tools or launch installers.
    baseline = Path('/usr/local/sbin/skyview-student-dev-update')
    unit = DROPIN.parent.parent / 'skyview-student-dev-update.service'
    if not app_only and baseline.exists() and unit.exists():
        trusted(baseline)
        trusted(unit)
        if '# SDE_COORDINATION_V1' in baseline.read_text():
            directory(DROPIN.parent, 0o755)
            atomic(DROPIN, b'[Service]\nExecStart=\nExecStart=/usr/bin/python3 -I /usr/local/libexec/skyview-self-update.py\nExecStartPre=/usr/bin/python3 -I /usr/local/libexec/skyview-maintenance-history.py start\nExecStopPost=/usr/bin/python3 -I /usr/local/libexec/skyview-maintenance-history.py finish\n', 0o644)
            if Path('/run/systemd/system').is_dir():
                subprocess.run(['/usr/bin/systemctl', 'daemon-reload'], check=True, env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})


def main():
    if os.geteuid() != 0 or len(sys.argv) != 1:
        raise RuntimeError('Root packaging invocation required')
    os.umask(0o077)
    app_only = app_only_installation()
    trusted(BUNDLE)
    version = subprocess.check_output(['/usr/bin/dpkg-query', '-W', '-f=${Version}', 'skyview-dev-setup'], env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}, text=True)
    if not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', version):
        raise RuntimeError('Invalid installed version')
    directory(ROOT.parent, 0o755)
    directory(ROOT, 0o755)
    for name in ('engines', 'runs', 'staging', 'logs'):
        directory(ROOT / name)
    generation = str(uuid.uuid4())
    engine = ROOT / 'engines' / generation
    directory(engine)
    source = BUNDLE / 'sde-update-trust'
    trusted(source)
    atomic(engine / 'sde-update-trust', source.read_bytes(), 0o700)
    receipt(engine / 'version.json', dict(schemaVersion=1, version=version))
    directory(LAUNCHER.parent, 0o755)
    # Stable schema-1 launcher is installed once; incompatible changes need migration.
    if not LAUNCHER.exists():
        trusted(BUNDLE / 'launcher.py')
        atomic(LAUNCHER, (BUNDLE / 'launcher.py').read_bytes(), 0o755)
    trusted(LAUNCHER)
    # Separate hooks preserve the installed schema-1 launcher's compatibility.
    trusted(BUNDLE / 'history.py')
    atomic(HISTORY_HOOK, (BUNDLE / 'history.py').read_bytes(), 0o700)
    policy = ROOT / 'policy.json'
    if not policy.exists():
        receipt(policy, dict(schemaVersion=1, paused=True))
    trusted(policy)
    # Only the non-secret administrator pause boolean is student-readable.
    policy.chmod(0o644)
    previous = None
    active = ROOT / 'active.json'
    if active.exists():
        trusted(active)
        previous = json.loads(active.read_text())
        receipt(ROOT / 'previous-engine.json', previous)
    receipt(active, dict(schemaVersion=1, version=version, generation=generation))
    configure_maintenance(app_only)
    keep = {generation}
    if previous:
        old = previous.get('generation')
        if isinstance(old, str) and str(uuid.UUID(old)) == old:
            keep.add(old)
        else:
            raise RuntimeError('Invalid previous engine receipt')
    for path in (ROOT / 'engines').iterdir():
        if path.name in keep:
            continue
        if str(uuid.UUID(path.name)) != path.name:
            raise RuntimeError('Unknown engine state')
        trusted(path)
        if {p.name for p in path.iterdir()} != {'sde-update-trust', 'version.json'}:
            raise RuntimeError('Unknown engine files')
        for name in ('sde-update-trust', 'version.json'):
            trusted(path / name)
            (path / name).unlink()
        path.rmdir()


if __name__ == '__main__':
    main()
