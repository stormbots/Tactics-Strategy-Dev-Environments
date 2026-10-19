"""Reviewed two-file gate on the installed spare; never invokes authorization.

prepare/cleanup require root. The separate operator packet owns the two manual
pkexec calls. All native commands here are read-only. No bootstrap or worker.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import socket
import stat
import subprocess
import sys
import time
import uuid

ROOT_UID = ROOT_GID = 0
REQUESTER_UID = 1000
ACTION = 'org.skyviewrobotics.sde.app-update'
JOURNAL_PARENT = Path('/var/tmp')
PREFIX = 'sde-mint-disabled-broker-'
TARGETS = {
    'app_request.py': (Path('/usr/local/libexec/skyview-app-update-request'), 0o755,
                       '122bef3156eb03e258c1693af3eb177e082a0c84db9fe2d927ed8b039d581b10'),
    'app-update.policy': (Path('/usr/share/polkit-1/actions/org.skyviewrobotics.sde.app-update.policy'), 0o644,
                         '50900fa7d3f8f92c8646c8ae821b6ed6ac9356639abed17c9091b7ee17b25187'),
}
NAMESPACE = Path('/var/lib/skyview-robotics/self-update/app-only')
BARRIERS = [Path('/var/lib/skyview-robotics-coordination') / name
            for name in ['transaction.json', 'installation-scope.json']]
PRESERVE = [Path(name) for name in [
    '/usr/bin/skyview-dev-setup',
    '/usr/local/sbin/skyview-student-dev-update',
    '/usr/local/lib/skyview-student-dev/coordination.py',
    '/usr/local/libexec/skyview-self-update.py',
    '/var/lib/skyview-robotics/student-dev/version',
    '/etc/systemd/system/skyview-student-dev-update.service',
    '/etc/systemd/system/skyview-student-dev-update.timer',
    '/etc/systemd/system/skyview-student-dev-update.service.d/sde-self-update.conf',
    '/var/lib/skyview-robotics/self-update/active.json',
    '/var/lib/skyview-robotics/self-update/previous-engine.json',
    '/var/lib/skyview-robotics/self-update/policy.json',
    '/var/lib/skyview-robotics/self-update/installation.json',
    '/var/lib/skyview-robotics/self-update/recovery.json',
    '/var/lib/skyview-robotics/self-update/previous-recovery.json',
    '/var/lib/skyview-robotics/self-update/app-only-capabilities.json',
    '/var/lib/skyview-robotics/self-update/app-only-deployment.json',
]]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def present(path):
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False


def trusted_parent(path, allow_missing=False):
    # Walk from root: a missing nested path must not conceal a linked ancestor.
    for parent in reversed((path.parent, *path.parent.parents)):
        if allow_missing and not present(parent):
            continue
        m = parent.lstat()
        if not stat.S_ISDIR(m.st_mode) or m.st_uid != ROOT_UID or m.st_mode & 0o022:
            raise ValueError('Untrusted installed parent; no permission repair')


def read_file(path, owner=0, limit=64 * 1024 * 1024):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != owner
                or before.st_mode & 0o022 or before.st_nlink != 1 or before.st_size > limit):
            raise ValueError('Unexpected file identity, permissions, links or size')
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    keys = ('st_dev', 'st_ino', 'st_uid', 'st_gid', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if len(data) != before.st_size or any(getattr(before, k) != getattr(after, k) for k in keys):
        raise ValueError('File changed while being read')
    identity = {key: getattr(before, key) for key in keys}
    identity['sha256'] = digest(data)
    return data, identity


def snapshot():
    result = {}
    for path in [*PRESERVE, *BARRIERS]:
        trusted_parent(path, allow_missing=True)
        result[str(path)] = read_file(path, ROOT_UID)[1] if present(path) else None
    # No request/progress namespace may appear during this disabled-only gate.
    trusted_parent(NAMESPACE, allow_missing=True)
    result['appOnlyNamespacePresent'] = present(NAMESPACE)
    return result


def command(*arguments):
    allowed = ['/usr/bin/loginctl', '/usr/bin/dpkg-query', '/usr/bin/pkaction']
    if arguments[0] not in allowed:
        raise ValueError('Not a read-only gate probe')
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=10,
                            env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'HOME': '/root', 'LC_ALL': 'C'})
    if len(result.stdout.encode()) + len(result.stderr.encode()) > 16384:
        raise ValueError('Probe output exceeds bound')
    return result


def action_present():
    p = command('/usr/bin/pkaction', '--action-id', ACTION, '--verbose')
    if p.returncode == 0:
        normalized = ' '.join(p.stdout.split())
        required = ['implicit any: no', 'implicit inactive: no', 'implicit active: auth_admin',
                    'org.freedesktop.policykit.exec.path -> ' + str(TARGETS['app_request.py'][0])]
        if not all(value in normalized for value in required):
            raise ValueError('Unexpected registered action; stop without changing it')
        return True
    if p.returncode == 1 and 'No action with action id ' + ACTION in p.stderr:
        return False
    raise ValueError('Cannot establish the fixed action state')


def wait_action(expected):
    deadline = time.monotonic() + 5
    while True:
        if action_present() == expected:
            return
        if time.monotonic() >= deadline:
            raise ValueError('Policy registry did not reach the expected state; stop')
        time.sleep(0.2)  # Read-only registry observation, never an auth retry.


def host_preflight(session):
    if socket.gethostname() != 'ryan-ThinkCentre-M910q' or pwd.getpwuid(REQUESTER_UID).pw_name != 'ryan':
        raise ValueError('Only the reviewed spare and original UID are permitted')
    os_release = Path('/etc/os-release').read_text()
    if not re.search(r'^ID="?linuxmint"?$', os_release, re.M) or not re.search(r'^VERSION_ID="?22\.3"?$', os_release, re.M):
        raise ValueError('Reviewed Mint 22.3 host required')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', session):
        raise ValueError('Invalid session identity')
    p = command('/usr/bin/loginctl', 'show-session', session, '-p', 'User', '-p', 'Seat',
                '-p', 'Service', '-p', 'Type', '-p', 'Active', '-p', 'Remote', '-p', 'Display')
    fields = dict(line.split('=', 1) for line in p.stdout.splitlines() if '=' in line)
    expected = {'User': '1000', 'Seat': 'seat0', 'Service': 'lightdm',
                'Type': 'x11', 'Active': 'yes', 'Remote': 'no', 'Display': ':0'}
    if p.returncode or fields != expected:
        raise ValueError('Use the verified active physical Cinnamon console, not XRDP/SSH')
    p = command('/usr/bin/dpkg-query', '-W', '-f=${Version}', 'skyview-dev-setup')
    if p.returncode or p.stdout != '1.2.9':
        raise ValueError('Installed 1.2.9 baseline changed; no package repair')
    if present(NAMESPACE) or any(present(path) for path in BARRIERS):
        raise ValueError('Existing app-only namespace or recovery barrier; preserve and stop')
    return fields


def sync_dir(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def create(path, data, mode):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    with os.fdopen(fd, 'wb') as stream:
        os.fchown(stream.fileno(), ROOT_UID, ROOT_GID)
        os.fchmod(stream.fileno(), mode)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    sync_dir(path.parent)
    return read_file(path, ROOT_UID)[1]


def save(directory, record):
    data = (json.dumps(record, indent=2) + '\n').encode()
    if len(data) > 128 * 1024:
        raise ValueError('Journal bound exceeded')
    temporary = directory / 'record.tmp'
    create(temporary, data, 0o600)
    os.replace(temporary, directory / 'record.json')
    sync_dir(directory)


def prepare(sources, session, verified_source):
    # The hash-verifying stdin loader passes the same bytes it compiled. Never
    # reread an unelevated writable helper after checking its hash.
    if not isinstance(verified_source, bytes) or not 0 < len(verified_source) <= 65536:
        raise ValueError('Use the reviewed hash-verifying loader')
    facts = host_preflight(session)
    payloads = {}
    for name, (target, mode, expected_hash) in TARGETS.items():
        trusted_parent(target)
        if present(target):
            raise ValueError('Existing fixed file; no overwrite or adoption')
        data, _ = read_file(sources / name, REQUESTER_UID, 65536)
        if digest(data) != expected_hash:
            raise ValueError('Source hash mismatch')
        payloads[name] = data
    if payloads['app_request.py'].count(b'EXECUTION_ENABLED = False') != 1:
        raise ValueError('Only the pinned disabled broker is permitted')
    if action_present():
        raise ValueError('Existing action; no registration overwrite')
    before = snapshot()
    directory = JOURNAL_PARENT / (PREFIX + str(uuid.uuid4()))
    directory.mkdir(mode=0o700)
    directory.chmod(0o700)
    print('Retained root journal: ' + str(directory), file=sys.stderr, flush=True)
    helper = create(directory / 'gate.py', verified_source, 0o700)
    for name, data in payloads.items():
        create(directory / name, data, 0o600)
    record = {'schemaVersion': 1, 'phase': 'preparing', 'session': session, 'sessionFacts': facts,
              'bootId': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              'preparedBootMs': int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000),
              'before': before, 'helper': helper, 'created': {}}
    save(directory, record)
    for name, (target, mode, _) in TARGETS.items():
        record['created'][name] = create(target, payloads[name], mode)
        save(directory, record)
    wait_action(True)
    if snapshot() != before:
        raise ValueError('Protected baseline changed; retain journal and stop')
    record['phase'] = 'prepared'
    save(directory, record)
    return {'status': 'prepared', 'journal': str(directory), 'uid': REQUESTER_UID,
            'bootId': record['bootId'], 'preparedBootMs': record['preparedBootMs']}


def cleanup(directory):
    if (directory.parent != JOURNAL_PARENT or not directory.name.startswith(PREFIX)
            or str(uuid.UUID(directory.name[len(PREFIX):])) != directory.name[len(PREFIX):]):
        raise ValueError('Not this gate journal namespace')
    m = directory.lstat()
    if not stat.S_ISDIR(m.st_mode) or m.st_uid != ROOT_UID or stat.S_IMODE(m.st_mode) != 0o700:
        raise ValueError('Untrusted journal directory')
    raw, _ = read_file(directory / 'record.json', ROOT_UID, 131072)
    record = json.loads(raw)
    if record.get('schemaVersion') != 1 or record.get('phase') != 'prepared' or set(record.get('created', {})) != set(TARGETS):
        raise ValueError('Partial or unknown journal; preserve for review')
    if read_file(directory / 'gate.py', ROOT_UID, 65536)[1] != record['helper']:
        raise ValueError('Journal helper changed')
    # Validate the entire pair before removing anything; targets are constants,
    # never paths selected by journal JSON. Unknown or missing bytes stop.
    for name, (target, _, _) in TARGETS.items():
        trusted_parent(target)
        if read_file(target, ROOT_UID)[1] != record['created'][name]:
            raise ValueError('Fixed file changed; refusing cleanup')
    record['phase'] = 'removing'
    save(directory, record)
    for name in ['app-update.policy', 'app_request.py']:
        target = TARGETS[name][0]
        target.unlink()
        sync_dir(target.parent)
    record['phase'] = 'files-removed'
    save(directory, record)
    wait_action(False)
    record['preservationUnchanged'] = snapshot() == record['before']
    record['phase'] = 'cleaned'
    save(directory, record)
    if not record['preservationUnchanged']:
        raise ValueError('Owned files removed, but protected baseline changed; preserve and stop')
    return {'status': 'cleaned', 'journalRetained': str(directory),
            'installedFilesRemoved': 2, 'preservationUnchanged': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('sources', type=Path)
    p.add_argument('session')
    p = sub.add_parser('cleanup')
    p.add_argument('journal', type=Path)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise ValueError('Reviewed root operation required; never use this for GUI requests')
    os.umask(0o077)
    result = (prepare(args.sources, args.session, globals().get('_VERIFIED_SOURCE'))
              if args.mode == 'prepare' else cleanup(args.journal))
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('STOP: ' + str(error) + '; do not retry or repair automatically.', file=sys.stderr)
        sys.exit(1)
