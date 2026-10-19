#!/usr/bin/python3 -I
"""Fixed polkit entry point; installation/registration is a separate native gate.

Installed executable path: /usr/local/libexec/skyview-app-update-request.
No caller arguments. PKEXEC_UID is trusted only at that polkit-owned boundary;
root already has arbitrary authority. Never invoke this through a general sudo
rule or a policy granting authorization for /usr/bin/python3.
"""
import fcntl
import json
import itertools
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import time
import uuid

ROOT = Path('/var/lib/skyview-robotics/self-update')
ENTRY = Path('/usr/local/libexec/skyview-app-update-request')
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'HOME': '/root', 'LC_ALL': 'C'}
EXECUTION_ENABLED = False  # Source gate: no flag, environment or receipt enables execution.
MAX_RUNS = 8
MAX_SNAPSHOT = 64 * 1024 * 1024


def trusted(path):
    for item in (path, *path.parents):
        m = item.lstat()
        if m.st_uid != 0 or m.st_mode & 0o022 or not (stat.S_ISDIR(m.st_mode) or stat.S_ISREG(m.st_mode)):
            raise RuntimeError('Untrusted app-only path')
        if stat.S_ISREG(m.st_mode) and m.st_nlink != 1:
            raise RuntimeError('Linked app-only file')


def bounded_json(path, limit=16384):
    trusted(path)
    if not stat.S_ISREG(path.lstat().st_mode):
        raise RuntimeError('Expected regular receipt')
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise RuntimeError('Receipt exceeds bound')
    return json.loads(data)


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_new(path, data, mode=0o600):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def validate_invocation(argv, env, uid, executable):
    value = env.get('PKEXEC_UID', '')
    if uid != 0 or len(argv) != 1 or executable != ENTRY or not value.isascii() or not value.isdecimal():
        raise RuntimeError('Fixed OS-authorized request required')
    requester = int(value)
    if not 0 < requester < 4294967295 or str(requester) != value:
        raise RuntimeError('Invalid requesting identity')
    return requester


def snapshot(source, destination, limit):
    trusted(source)
    if not stat.S_ISREG(source.lstat().st_mode) or source.stat().st_size > limit:
        raise RuntimeError('Invalid snapshot source')
    with source.open('rb') as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise RuntimeError('Snapshot exceeds bound')
    write_new(destination, data, 0o700 if destination.name == 'sde-update-trust' else 0o600)


def reader_acl(fd, uid):
    # Root writes; exactly the original requesting UID reads. No primary-group grant.
    acl = struct.pack('<I', 2)
    for tag, permission, identity in [(1, 6, 0xffffffff), (2, 4, uid),
                                      (4, 0, 0xffffffff), (16, 4, 0xffffffff), (32, 0, 0xffffffff)]:
        acl += struct.pack('<HHI', tag, permission, identity)
    os.setxattr(fd, 'system.posix_acl_access', acl)


def publish_reader_record(path, value, uid):
    trusted(path.parent)
    data = json.dumps(value, separators=(',', ':')).encode()
    if len(data) > 4096:
        raise RuntimeError('Receipt publication bound exceeded')
    if path.exists() or path.is_symlink():
        trusted(path)
    temp = path.with_name(str(uuid.uuid4()) + '.tmp')
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            reader_acl(stream.fileno(), uid)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        sync_dir(path.parent)
    finally:
        # Remove only our exclusive temporary name, never an activated/uncertain record.
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def current_slot(base, requester):
    index = base / ('current-' + str(requester) + '.json')
    try:
        index.lstat()
    except FileNotFoundError:
        return index
    previous = bounded_json(index, 4096)
    if (set(previous) != {'schemaVersion', 'requestId', 'uid', 'bootId'}
            or type(previous['schemaVersion']) is not int or previous['schemaVersion'] != 1
            or type(previous['uid']) is not int or previous['uid'] != requester
            or str(uuid.UUID(previous['requestId'])) != previous['requestId']
            or previous['bootId'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip()):
        raise RuntimeError('Previous request identity requires mentor review')
    run = base / 'runs' / previous['requestId']
    receipt = bounded_json(run / 'receipt.json', 4096)
    progress = bounded_json(run / 'progress.json', 4096)
    for record in (receipt, progress):
        if (type(record.get('schemaVersion')) is not int or record.get('schemaVersion') != 1
                or type(record.get('uid')) is not int or record.get('requestId') != previous['requestId']
                or record.get('uid') != requester or record.get('bootId') != previous['bootId']):
            raise RuntimeError('Previous request correlation requires mentor review')
    if receipt.get('status') != 'accepted' or progress.get('state') not in {'current', 'paused', 'deferred', 'updated'}:
        raise RuntimeError('Previous request is unresolved; no queued retry')
    for name in ('transaction.json', 'installation-scope.json'):
        try:
            Path('/var/lib/skyview-robotics-coordination', name).lstat()
        except FileNotFoundError:
            continue
        raise RuntimeError('Recovery barrier requires mentor review')
    # Root may replace the correlation pointer only; all old run evidence stays.
    return index


def create(requester):
    if not EXECUTION_ENABLED:
        raise RuntimeError('App-only execution is disabled pending native validation')
    if type(requester) is not int or not 0 < requester < 4294967295:
        raise RuntimeError('Invalid requesting identity')
    # Installed bootstrap must provision these trusted directories separately.
    # No scheduler repair, registration, tool provisioning or recursive mkdir.
    base = ROOT / 'app-only'
    runs = base / 'runs'
    for path in (base, runs, ROOT / 'active.json', ROOT / 'app-only-capabilities.json'):
        trusted(path)
    gate = os.open(base / 'request.gate', os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        trusted(base / 'request.gate')
        fcntl.flock(gate, fcntl.LOCK_EX | fcntl.LOCK_NB)
        index = current_slot(base, requester)
        # Bounded retention; no deletion of unknown/uncertain workers or snapshots.
        if len(list(itertools.islice(runs.iterdir(), MAX_RUNS))) >= MAX_RUNS:
            raise RuntimeError('App-only evidence capacity reached; mentor review required')
        active = bounded_json(ROOT / 'active.json', 4096)
        generation = active.get('generation')
        if active.get('schemaVersion') != 1 or str(uuid.UUID(generation)) != generation:
            raise RuntimeError('Invalid engine activation')
        identifier = str(uuid.uuid4())
        run = runs / identifier
        # Traversable by students for their ACL-protected progress only. Request,
        # claim, worker and receipts remain root-only; directory is root-writable.
        run.mkdir(mode=0o711)
        run.chmod(0o711)
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        if str(uuid.UUID(boot)) != boot:
            raise RuntimeError('Invalid boot identity')
        created = time.clock_gettime_ns(time.CLOCK_BOOTTIME) // 1000000
        request = dict(schemaVersion=1, requestId=identifier, uid=requester, bootId=boot,
                       createdMs=created, deadlineMs=created + 900000)
        write_new(run / 'request.json', json.dumps(request).encode())
        source = ROOT / 'engines' / generation
        snapshot(source / 'sde-update-trust', run / 'sde-update-trust', MAX_SNAPSHOT)
        snapshot(source / 'version.json', run / 'version.json', 4096)
        if bounded_json(run / 'version.json', 4096) != dict(schemaVersion=1, version=active['version']):
            raise RuntimeError('Snapshot identity mismatch')
        sync_dir(run)
        sync_dir(runs)
        receipt = dict(request, status='pending')
        publish_reader_record(run / 'receipt.json', receipt, requester)
        publish_reader_record(index, {k: request[k] for k in ('schemaVersion', 'requestId', 'uid', 'bootId')}, requester)
        # No pipe to GUI. setsid + redirected stdio + close_fds isolates GUI exit.
        # Worker owns one-shot claim and all O/A/S leases, not this short broker.
        with open(os.devnull, 'wb') as log:
            subprocess.Popen([str(run / 'sde-update-trust'), 'app-only-linux'],
                             stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                             close_fds=True, start_new_session=True, cwd='/', env=ENV)
        # Accepted means launch initiated, never Ready/installed/liveness. Failure
        # after spawn preserves pending/uncertain state and never kills the worker.
        publish_reader_record(run / 'receipt.json', dict(request, status='accepted'), requester)
        return identifier
    finally:
        os.close(gate)


def main():
    requester = validate_invocation(sys.argv, os.environ, os.geteuid(), Path(__file__).absolute())
    # Validate our fixed installed path and every ancestor before reading state.
    trusted(ENTRY)
    if not EXECUTION_ENABLED:
        print(json.dumps(dict(schemaVersion=1, status='disabled', uid=requester)), file=sys.stderr, flush=True)
        return 78
    os.umask(0o077)
    print(json.dumps(dict(schemaVersion=1, requestId=create(requester))), flush=True)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        # No raw path/network/installer output in the unelevated UI channel.
        print('Unable to start the authorized app-only attempt; mentor review may be required.', file=sys.stderr)
        sys.exit(1)
