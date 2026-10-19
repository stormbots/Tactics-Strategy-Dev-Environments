#!/usr/bin/python3
"""DEB packaging hook: activate engines only, never provision or start tools."""
import hashlib
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
APP_ENTRY = Path('/usr/local/libexec/skyview-app-update-request')
APP_POLICY = Path('/usr/share/polkit-1/actions/org.skyviewrobotics.sde.app-update.policy')
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
        os.fchmod(stream.fileno(), mode)  # Exact declared mode, independent of packaging umask.
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


def app_sources():
    return {APP_ENTRY: (BUNDLE / 'app_request.py', 65536, 0o755),
            APP_POLICY: (BUNDLE.parent / 'polkit' / APP_POLICY.name, 8192, 0o644)}


def read_owned(path, limit):
    trusted(path)
    if not stat.S_ISREG(path.lstat().st_mode):
        raise RuntimeError('Expected deployment file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if len(data) > limit or len(data) != before.st_size or any(getattr(before, k) != getattr(after, k) for k in fields):
        raise RuntimeError('Unstable or oversized deployment file')
    return data


def deployment_record():
    path = ROOT / 'app-only-deployment.json'
    try:
        path.lstat()
    except FileNotFoundError:
        return None
    record = json.loads(read_owned(path, 4096))
    if (not isinstance(record, dict) or set(record) != {'schemaVersion', 'executionEnabled', 'nativeValidation', 'files'}
            or type(record['schemaVersion']) is not int or record['schemaVersion'] != 1
            or record['executionEnabled'] is not False or record['nativeValidation'] != 'pending'
            or not isinstance(record['files'], dict) or set(record['files']) != {str(p) for p in app_sources()}
            or any(not isinstance(h, str) or not re.fullmatch('[0-9a-f]{64}', h) for h in record['files'].values())):
        raise RuntimeError('Unknown app-only deployment; mentor migration required')
    return record


def deployment_plan():
    previous = deployment_record()
    plan = {}
    for target, (source, limit, mode) in app_sources().items():
        data = read_owned(source, limit)
        # No receipt, environment or CLI argument may enable this packaged broker.
        if target == APP_ENTRY and data.count(b'EXECUTION_ENABLED = False') != 1:
            raise RuntimeError('Only disabled app-only deployment is authorized')
        try:
            target.lstat()
        except FileNotFoundError:
            if previous is not None:
                raise RuntimeError('Incomplete previous deployment; mentor repair required')
        else:
            old = read_owned(target, limit)
            expected = previous['files'][str(target)] if previous else hashlib.sha256(data).hexdigest()
            if hashlib.sha256(old).hexdigest() != expected:
                raise RuntimeError('Unknown installed app-only file; no overwrite')
        # Validate all existing ancestors even when part of the tree is absent.
        for ancestor in target.parents:
            try:
                ancestor.lstat()
            except FileNotFoundError:
                continue
            trusted(ancestor)
        plan[target] = (data, mode)
    return plan


def app_directory(path, mode):
    try:
        path.lstat()
    except FileNotFoundError:
        directory(path, mode)
    else:
        trusted(path)
        if not stat.S_ISDIR(path.lstat().st_mode) or stat.S_IMODE(path.lstat().st_mode) != mode:
            raise RuntimeError('Unsupported app-only directory; no permission repair')


def deploy_app_only(plan=None):
    plan = deployment_plan() if plan is None else plan
    # Native-only provisioning. Never writes app-only-capabilities.json, touches
    # a timer/service/tool or starts a worker. Request gate inode is never replaced.
    app_directory(ROOT.parent, 0o755)
    app_directory(ROOT, 0o755)
    app_directory(ROOT / 'app-only', 0o711)
    app_directory(ROOT / 'app-only/runs', 0o711)
    gate = ROOT / 'app-only/request.gate'
    try:
        fd = os.open(gate, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    except FileExistsError:
        trusted(gate)
        m = gate.lstat()
        if not stat.S_ISREG(m.st_mode) or stat.S_IMODE(m.st_mode) != 0o600:
            raise RuntimeError('Invalid existing request gate')
    else:
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        sync = os.open(gate.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            os.fsync(sync)
        finally:
            os.close(sync)
    if deployment_plan() != plan:
        raise RuntimeError('Deployment source changed')
    old_hashes = {}
    for target, (_, limit, _) in app_sources().items():
        try:
            target.lstat()
        except FileNotFoundError:
            old_hashes[target] = None
        else:
            old_hashes[target] = hashlib.sha256(read_owned(target, limit)).hexdigest()
    for target, (data, mode) in plan.items():
        try:
            target.lstat()
        except FileNotFoundError:
            if old_hashes[target] is not None:
                raise RuntimeError('Deployment target disappeared')
        else:
            if hashlib.sha256(read_owned(target, app_sources()[target][1])).hexdigest() != old_hashes[target]:
                raise RuntimeError('Deployment target changed')
        app_directory(target.parent, 0o755)
        atomic(target, data, mode)
    record = dict(schemaVersion=1, executionEnabled=False, nativeValidation='pending',
                  files={str(p): hashlib.sha256(data).hexdigest() for p, (data, _) in plan.items()})
    receipt(ROOT / 'app-only-deployment.json', record)


def remove_app_only():
    previous = deployment_record()
    if previous is None:
        # Never remove a foreign/unrecorded launcher or policy.
        for target in app_sources():
            if target.exists() or target.is_symlink():
                raise RuntimeError('Unrecorded deployment requires mentor review')
        return
    for target, (_, limit, _) in app_sources().items():
        if hashlib.sha256(read_owned(target, limit)).hexdigest() != previous['files'][str(target)]:
            raise RuntimeError('Changed deployment; no removal')
    for target in app_sources():
        target.unlink()
        fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    (ROOT / 'app-only-deployment.json').unlink()
    fd = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    # Keep requests/snapshots/capabilities/recovery/maintenance intact, including
    # partial removal evidence. No recursive cleanup or service registration.


def main():
    if os.geteuid() != 0:
        raise RuntimeError('Root packaging invocation required')
    if len(sys.argv) == 2 and sys.argv[1] in ('--deploy-app-only-disabled', '--remove-app-only-disabled'):
        os.umask(0o077)
        if sys.argv[1] == '--deploy-app-only-disabled':
            deploy_app_only()
        else:
            remove_app_only()
        return
    if len(sys.argv) != 1:
        raise RuntimeError('Fixed packaging invocation required')
    os.umask(0o077)
    app_only = app_only_installation()
    trusted(BUNDLE)
    version = subprocess.check_output(['/usr/bin/dpkg-query', '-W', '-f=${Version}', 'skyview-dev-setup'], env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}, text=True)
    if not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', version):
        raise RuntimeError('Invalid installed version')
    app_plan = deployment_plan()  # Fail before changing maintenance activation.
    directory(ROOT.parent, 0o755)
    directory(ROOT, 0o755)
    deploy_app_only(app_plan)
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
