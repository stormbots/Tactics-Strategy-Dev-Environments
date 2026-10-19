#!/usr/bin/python3 -I
"""Isolated Mint validation control tool. Import/plan never executes native work.

No installer, downloader, package operation, service registration or enablement
receipt is implemented here. Native execution requires an approved disposable VM.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
import pwd
from pathlib import Path
import re
import select
import signal
import stat
import struct
import subprocess
import sys
import time
import uuid

SCHEMA = 1
PRODUCTION_COMMIT = 'a2a518684a77a5fc86287144f932c1510f1971e8'
FINGERPRINT = '27DEB15644C6B3CF3BD7D291300F846BA25BAE09'
ISO = 'linuxmint-22.3-cinnamon-64bit.iso'
ROOT = Path('/var/lib/skyview-robotics/self-update')
TOOLS = Path('/opt/sde-phase3-validation')
ENTRY = Path('/usr/local/libexec/skyview-app-update-request')
POLICY = Path('/usr/share/polkit-1/actions/org.skyviewrobotics.sde.app-update.policy')
COORDINATION = Path('/var/lib/skyview-robotics-coordination')
ASSETS = {'broker': 'app_request.py', 'policy': 'org.skyviewrobotics.sde.app-update.policy',
          'verifier': 'sde-update-trust', 'sentinel': 'sentinel.py', 'driver': 'driver.py'}
ACTIONS = ['root-fixtures', 'temporary-polkit', 'desktop-authorization',
           'owned-sentinel-signals', 'owned-cleanup']
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'HOME': '/root', 'LC_ALL': 'C'}
MAX_RECORD = 65536
MAX_TOTAL = 1024 * 1024


class Stop(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise Stop(message)


def canonical_uuid(value):
    try:
        return isinstance(value, str) and str(uuid.UUID(value)) == value
    except (ValueError, TypeError, AttributeError):
        return False


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    data = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    require(len(data) <= MAX_RECORD, 'Evidence record limit exceeded')
    return data


def strict_json(data):
    require(len(data) <= MAX_RECORD, 'Input limit exceeded')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON field')
            result[key] = value
        return result
    try:
        return json.loads(data, object_pairs_hook=pairs)
    except (ValueError, UnicodeError):
        raise Stop('Invalid JSON') from None


def host_check(facts):
    """Pure assessment; accepts only collected facts, never provisions a host."""
    reasons = []
    expected = {'os': 'ubuntu', 'version': '24.04', 'arch': 'x86_64',
                'disposable': True, 'kvm_api': 12, 'tools_trusted': True,
                'loopback_console': True, 'no_host_mounts': True}
    for field, value in expected.items():
        if type(facts.get(field)) is not type(value) or facts.get(field) != value:
            reasons.append(field)
    for field, minimum in [('cpus', 2), ('available_memory', 6 * 1024**3),
                           ('available_disk', 36 * 1024**3)]:
        if type(facts.get(field)) is not int or facts[field] < minimum:
            reasons.append(field)
    return {'schemaVersion': 1, 'ready': not reasons, 'blockers': reasons,
            'guest': {'os': 'Mint 22.3 Cinnamon', 'cpus': 2, 'memoryGiB': 4,
                      'diskGiB': 30, 'filesystem': 'ext4'},
            'nativeGuestTestsExecuted': False, 'fallbackAllowed': False}


def media_check(checksums, gpg_status, returncode, actual_digest, pinned_digest):
    require(len(checksums) <= MAX_RECORD and len(gpg_status) <= 8192, 'Media metadata limit')
    require(type(returncode) is int and returncode == 0, 'ISO signature verification failed')
    # GnuPG status-fd primary/subkey attribution, not human-readable "Good signature".
    signatures = [line.split() for line in gpg_status.splitlines()
                  if line.startswith('[GNUPG:] VALIDSIG ')]
    require(len(signatures) == 1 and len(signatures[0]) >= 12, 'Missing unique VALIDSIG')
    require(signatures[0][2] == FINGERPRINT or signatures[0][-1] == FINGERPRINT,
            'Wrong Mint signing key')
    entries = re.findall(r'^([a-f0-9]{64}) [ *]' + re.escape(ISO) + r'$', checksums, re.M)
    require(len(entries) == 1, 'Missing/duplicate Cinnamon checksum')
    require(re.fullmatch('[a-f0-9]{64}', pinned_digest or '') is not None,
            'Authenticated Cinnamon digest must be pinned before execution approval')
    require(entries[0] == actual_digest == pinned_digest, 'ISO digest mismatch')
    return {'schemaVersion': 1, 'filename': ISO, 'sha256': actual_digest,
            'signingFingerprint': FINGERPRINT, 'authenticated': True}


def approval_check(a, facts, hashes):
    require(set(a) == {'schemaVersion', 'runId', 'vmId', 'bootId', 'purpose',
                       'productionCommit', 'artifactSha256', 'actions', 'uids',
                       'mediaSha256', 'expiresBootMs'}, 'Approval fields mismatch')
    require(type(a['schemaVersion']) is int and a['schemaVersion'] == 1,
            'Approval schema mismatch')
    require(a['purpose'] == 'mint-phase3-negative-and-sentinel-only', 'Wrong approval scope')
    require(a['productionCommit'] == PRODUCTION_COMMIT, 'Production revision mismatch')
    require(all(canonical_uuid(a[k]) for k in ['runId', 'vmId', 'bootId']), 'Invalid identity')
    require(a['vmId'] == facts['vmId'] and a['bootId'] == facts['bootId'], 'VM/boot mismatch')
    require(facts['euid'] == 0 and facts.get('ruid') == 0 and facts.get('egid') == 0
            and facts.get('container') == 'none' and facts.get('pid1') == 'systemd' and facts['mint'] == '22.3' and facts['virtualization'] == 'QEMU',
            'Requires root on the approved disposable Mint VM')
    require(type(a['expiresBootMs']) is int and facts['bootMs'] < a['expiresBootMs']
            <= facts['bootMs'] + 30 * 60 * 1000, 'Approval expired or unbounded')
    require(a['actions'] == ACTIONS, 'Approval action set mismatch')
    require(a['artifactSha256'] == hashes and set(hashes) == set(ASSETS), 'Artifact mismatch')
    require(set(a['uids']) == {'sde-student', 'sde-other', 'sde-mentor'}
            and all(type(v) is int and 1000 <= v < 2**32 - 1 for v in a['uids'].values())
            and len(set(a['uids'].values())) == 3, 'Test account identity mismatch')
    require(re.fullmatch('[a-f0-9]{64}', a['mediaSha256']) is not None, 'Missing media pin')
    return a


def fixture_plan(a, assets, kind):
    require(kind in ['production', 'sentinel'], 'Unknown worker kind')
    generation = a['runId']
    worker = assets['verifier' if kind == 'production' else 'sentinel']
    require(0 < len(worker) <= 64 * 1024**2, 'Worker snapshot size')
    engine = ROOT / 'engines' / generation
    # No valid capability receipt, coordination state, scheduler or installed bundle.
    return [('dir', ROOT.parent, 0o755, None), ('dir', ROOT, 0o755, None),
            ('dir', ROOT / 'engines', 0o700, None), ('dir', engine, 0o700, None),
            ('dir', ROOT / 'app-only', 0o711, None),
            ('dir', ROOT / 'app-only/runs', 0o711, None),
            ('file', ROOT / 'app-only/request.gate', 0o600, b''),
            ('file', engine / 'sde-update-trust', 0o700, worker),
            ('file', engine / 'version.json', 0o600, encode({'schemaVersion': 1, 'version': '1.2.9'})),
            ('file', ROOT / 'active.json', 0o600, encode({'schemaVersion': 1, 'version': '1.2.9', 'generation': generation})),
            ('file', ROOT / 'app-only-capabilities.json', 0o600, b'{}'),
            ('file', ENTRY, 0o755, assets['broker']), ('file', POLICY, 0o644, assets['policy']),
            ('dir', TOOLS, 0o755, None),
            ('file', TOOLS / 'driver.py', 0o755, assets['driver']),
            ('file', TOOLS / 'sde-update-trust', 0o755, assets['verifier']),
            ('file', TOOLS / 'case.json', 0o644, encode({'schemaVersion': 1, 'runId': a['runId'],
                                                      'kind': kind, 'uid': a['uids']['sde-student'], 'otherUid': a['uids']['sde-other']}))]


def process_check(p, expected, sentinel=False):
    require(all(p.get(k) == expected[k] for k in ['pid', 'startTicks', 'bootId', 'uid']),
            'Process instance/ownership mismatch')
    require(p.get('pidfdLive') is True, 'Enrolled process no longer live')
    if sentinel:
        require(p['uid'] == 0 and p['sid'] == p['pid'] and p['pgid'] == p['pid'],
                'Sentinel not in its own root session/process group')
        require(p['fds'] == {'0': '/dev/null', '1': '/dev/null', '2': '/dev/null'},
                'Sentinel inherited an unexpected descriptor')
    return p


def deferred_check(request, claim, progress, uid, boot):
    require(set(request) == {'schemaVersion', 'requestId', 'uid', 'bootId', 'createdMs', 'deadlineMs'}
            and set(claim) == {'schemaVersion', 'requestId', 'bootId', 'workerPid'}
            and set(progress) == {'schemaVersion', 'requestId', 'uid', 'bootId', 'sequence', 'observedMs',
                                 'deadlineMs', 'readyDeadlineMs', 'state', 'candidate', 'nativeExit', 'detail'}
            and all(type(v.get('schemaVersion')) is int and v['schemaVersion'] == 1 for v in [request, claim, progress]), 'Protected schema drift')
    require(request.get('uid') == uid and request.get('bootId') == boot
            and canonical_uuid(request.get('requestId')), 'Request identity mismatch')
    require(type(request.get('createdMs')) is int and type(request.get('deadlineMs')) is int
            and request['deadlineMs'] - request['createdMs'] == 900000, 'Request lifetime changed')
    rid = request['requestId']
    require(claim.get('requestId') == rid and claim.get('bootId') == boot
            and type(claim.get('workerPid')) is int and claim['workerPid'] > 1, 'Invalid claim')
    require(progress.get('requestId') == rid and progress.get('uid') == uid
            and progress.get('bootId') == boot and progress.get('state') == 'deferred'
            and progress.get('detail') == 'Invalid protected app-only record'
            and progress.get('candidate') is None and progress.get('nativeExit') is None
            and progress.get('readyDeadlineMs') is None
            and type(progress.get('sequence')) is int and progress['sequence'] == 1
            and progress['deadlineMs'] == request['deadlineMs']
            and type(progress['observedMs']) is int and progress['observedMs'] >= request['createdMs'],
            'Worker did not take the expected safe-deferral path')
    return {'requestId': rid, 'outcome': 'Deferred', 'installationValidated': False}


def acl_check(raw, uid):
    expected = struct.pack('<I', 2) + b''.join(struct.pack('<HHI', *e) for e in
        [(1, 6, 2**32-1), (2, 4, uid), (4, 0, 2**32-1), (16, 4, 2**32-1), (32, 0, 2**32-1)])
    require(raw == expected, 'Unexpected root/named-reader ACL')


def authorization_audit(records, subject_pid, case, provider):
    matched = []
    for r in records:
        if r.get('_UID') != str(provider['uid']) or r.get('_PID') != str(provider['pid']) or r.get('_SYSTEMD_UNIT') != 'polkit.service' or r.get('_EXE') not in [
                '/usr/lib/polkit-1/polkitd', '/usr/libexec/polkitd', '/usr/lib/policykit-1/polkitd']:
            continue
        message = r.get('MESSAGE', '')
        subject = re.search(r'for unix-process:(\d+):', message)
        if not subject or int(subject[1]) != subject_pid:
            continue
        action = re.search(r'authorization for action ([A-Za-z0-9_.-]+)', message)
        require(action and action[1] == 'org.skyviewrobotics.sde.app-update', 'Unexpected polkit action attribution')
        matched.append('successfully authenticated' in message)
    if case == 'inactive' and not matched:
        return {'action': 'NotObserved', 'authorization': 'DeniedWithoutAuthenticationEvent',
                'limit': 'Exact action not independently attributed in this negative case'}
    require(matched, 'Expected polkit audit attribution unavailable')
    expected_success = case != 'denied'
    require(sum(matched) == (1 if expected_success else 0), 'Unexpected authorization count')
    return {'action': 'org.skyviewrobotics.sde.app-update',
            'successfulAuthorizations': sum(matched), 'subjectPid': subject_pid}


class Evidence:
    """Only explicit structured fields enter artifacts. No stdout/credentials."""
    def __init__(self, writer):
        self.writer, self.total, self.stopped = writer, 0, False

    def add(self, case, value):
        require(not self.stopped and re.fullmatch('[a-z0-9-]{1,40}', case), 'Evidence stopped/name')
        try:
            data = encode(value)
            require(self.total + len(data) <= MAX_TOTAL, 'Suite evidence limit exceeded')
            self.writer(case, data)  # must be exclusive + durable; failure stops suite
            self.total += len(data)
        except Exception:
            self.stopped = True
            raise


class Native:
    """No constructor I/O. Only explicit CLI execution instantiates operations."""
    def read(self, path, limit=MAX_RECORD, protected=True):
        if protected:
            self.trusted(path)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            m = os.fstat(fd)
            require(stat.S_ISREG(m.st_mode) and m.st_nlink == 1 and m.st_size <= limit,
                    'Expected bounded single-link regular file')
            data = os.read(fd, limit + 1)
            require(len(data) <= limit, 'Read limit exceeded')
            return data
        finally:
            os.close(fd)

    def trusted(self, path):
        for p in (Path(path), *Path(path).parents):
            m = p.lstat()
            require(m.st_uid == 0 and not m.st_mode & 0o022 and
                    (stat.S_ISDIR(m.st_mode) or stat.S_ISREG(m.st_mode)), 'Untrusted fixture path')
            require(not stat.S_ISREG(m.st_mode) or m.st_nlink == 1, 'Linked fixture file')

    def exists(self, path):
        try:
            Path(path).lstat()
            return True
        except FileNotFoundError:
            return False

    def fingerprint(self, path):
        self.trusted(path)
        m = Path(path).lstat()
        return {'dev': m.st_dev, 'ino': m.st_ino, 'uid': m.st_uid, 'gid': m.st_gid,
                'mode': stat.S_IMODE(m.st_mode), 'kind': 'dir' if stat.S_ISDIR(m.st_mode) else 'file',
                'sha256': None if stat.S_ISDIR(m.st_mode) else digest(self.read(path, 64*1024**2))}

    def create(self, op):
        kind, path, mode, data = op
        self.trusted(path.parent)
        require(not self.exists(path), 'Fixture collision')
        if kind == 'dir':
            path.mkdir(mode=mode)
            path.chmod(mode)
        else:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
            with os.fdopen(fd, 'wb') as f:
                f.write(data)
                os.fchmod(f.fileno(), mode)
                f.flush()
                os.fsync(f.fileno())
        self.sync(path.parent)
        return self.fingerprint(path)

    def sync(self, path):
        fd = os.open(path, os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def atomic(self, path, value):
        self.trusted(path.parent)
        if self.exists(path):
            self.trusted(path)
        temp = path.parent / (str(uuid.uuid4()) + '.tmp')
        self.create(('file', temp, 0o600, encode(value)))
        os.replace(temp, path)
        self.sync(path.parent)

    def remove(self, path, kind):
        if kind == 'dir':
            path.rmdir()
        else:
            path.unlink()
        self.sync(path.parent)

    def children(self, path):
        names = []
        with os.scandir(path) as entries:
            for item in entries:
                require(len(names) < 256, 'Directory inventory limit')
                names.append(item.name)
        return sorted(names)

    @contextmanager
    def cleanup_gate(self):
        import fcntl
        gate = ROOT/'app-only/request.gate'
        self.trusted(gate)
        fd = os.open(gate, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(fd)

    def accounts(self, expected):
        import grp
        for name, uid in expected.items():
            account = pwd.getpwnam(name)
            require(account.pw_uid == uid and account.pw_dir == '/home/' + name,
                    'Guest account mapping changed')
            sudo = grp.getgrnam('sudo').gr_gid in os.getgrouplist(name, account.pw_gid)
            require(sudo == (name == 'sde-mentor'), 'Guest admin membership changed')

    def process(self, pid, handle):
        require(not select.select([handle], [], [], 0)[0], 'Process exited during observation')
        base = Path('/proc') / str(pid)
        status = (base / 'stat').read_text().rsplit(')', 1)[1].split()
        ids = next(line.split()[1:] for line in (base / 'status').read_text().splitlines() if line.startswith('Uid:'))
        require(len(set(ids)) == 1, 'Mixed process credentials')
        cmd = self.read(base/'cmdline', 8192, protected=False).split(b'\0')
        fds = {}
        with os.scandir(base/'fd') as entries:
            for entry in entries:
                require(len(fds) < 32, 'Process descriptor inventory bound')
                fds[entry.name] = os.readlink(entry.path)
        result = {'pid': pid, 'startTicks': int(status[19]),
                  'bootId': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  'uid': int(ids[0]), 'ppid': int(status[1]), 'pgid': int(status[2]),
                  'sid': int(status[3]), 'cgroup': (base / 'cgroup').read_text()[:4096],
                  'fds': fds, 'pidfdLive': True,
                  'cmd': [part.decode() for part in cmd if part]}
        require(not select.select([handle], [], [], 0)[0], 'Process lost while observing')
        return result

    def wait_json(self, path, seconds=5):
        until = time.clock_gettime(time.CLOCK_BOOTTIME) + seconds
        while not self.exists(path):
            require(time.clock_gettime(time.CLOCK_BOOTTIME) < until, 'Required worker evidence missing')
            time.sleep(0.02)
        return strict_json(self.read(path, 4096))

    def ready_sentinel(self, pid, handle, expected):
        until = time.clock_gettime(time.CLOCK_BOOTTIME) + 2
        while True:
            snapshot = self.process(pid, handle)
            process_check(snapshot, expected)
            require(snapshot['uid'] == 0 and snapshot['sid'] == pid and snapshot['pgid'] == pid,
                    'Unexpected sentinel ownership/group')
            if snapshot['fds'] == {'0':'/dev/null', '1':'/dev/null', '2':'/dev/null'}:
                return snapshot
            require(time.clock_gettime(time.CLOCK_BOOTTIME) < until,
                    'Sentinel descriptors did not reach the fixed barrier inventory')
            time.sleep(0.02)

    def pidfd(self, pid):
        return os.pidfd_open(pid, 0)

    def closed(self, handle, timeout):
        return bool(select.select([handle], [], [], timeout)[0])

    def session(self, pid):
        bus = '/usr/bin/busctl'
        prefix = [bus, '--system', '--json=short']
        code, output = self.command(prefix + ['call', 'org.freedesktop.login1',
             '/org/freedesktop/login1', 'org.freedesktop.login1.Manager', 'GetSessionByPID', 'u', str(pid)])
        require(code == 0, 'Cannot attribute subject to a real logind session')
        result = strict_json(output)
        require(result.get('type') == 'o' and len(result.get('data', [])) == 1, 'Invalid logind result')
        obj = result['data'][0]
        require(re.fullmatch('/org/freedesktop/login1/session/[A-Za-z0-9_]+', obj), 'Invalid session object')
        values = {}
        for field in ['Active', 'Remote', 'Type']:
            code, output = self.command(prefix + ['get-property', 'org.freedesktop.login1', obj,
                                                  'org.freedesktop.login1.Session', field])
            data = strict_json(output)
            require(code == 0 and len(data.get('data', [])) == 1, 'Invalid session property')
            values[field] = data['data'][0]
        return values

    def policy_provider(self):
        result = {}
        for method, key in [('GetConnectionUnixUser', 'uid'), ('GetConnectionUnixProcessID', 'pid')]:
            code, data = self.command(['/usr/bin/busctl', '--system', '--json=short', 'call',
                'org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus',
                method, 's', 'org.freedesktop.PolicyKit1'])
            parsed = strict_json(data)
            require(code == 0 and parsed.get('type') == 'u' and len(parsed.get('data', [])) == 1,
                    'Cannot attribute actual polkit bus owner')
            value = parsed['data'][0]
            require(type(value) is int and value >= 0, 'Invalid polkit bus-owner identity')
            result[key] = value
        allowed_uid = {0}
        try:
            allowed_uid.add(pwd.getpwnam('polkitd').pw_uid)
        except KeyError:
            pass
        require(result['uid'] in allowed_uid and result['uid'] < 1000 and result['pid'] > 1,
                'Unexpected PolicyKit provider')
        return result

    def journal_cursor(self):
        code, data = self.command(['/usr/bin/journalctl', '--no-pager', '-n', '1', '-o', 'json'])
        require(code == 0, 'Journal cursor unavailable')
        cursor = strict_json(data)['__CURSOR']
        require(re.fullmatch('[A-Za-z0-9;=:_-]{1,1024}', cursor), 'Invalid journal cursor')
        return cursor

    def journal_events(self, cursor):
        require(re.fullmatch('[A-Za-z0-9;=:_-]{1,1024}', cursor), 'Invalid journal cursor')
        code, data = self.command(['/usr/bin/journalctl', '--no-pager', '--after-cursor', cursor,
                                   '-n', '8', '-o', 'json', '_COMM=polkitd'])
        require(code == 0, 'Polkit audit unavailable')
        return [strict_json(line) for line in data.splitlines() if line]

    def close(self, handle):
        os.close(handle)

    def kill_gui(self, handle):
        signal.pidfd_send_signal(handle, signal.SIGKILL)

    def acl(self, path):
        return os.getxattr(path, 'system.posix_acl_access')

    def replay(self, run):
        require(run.parent == ROOT/'app-only/runs' and canonical_uuid(run.name), 'Invalid replay path')
        require(strict_json(self.read(ROOT/'app-only-capabilities.json')) == {}, 'Capability gate changed')
        before = self.fingerprint(run/'claimed')
        child = subprocess.Popen([str(run/'sde-update-trust'), 'app-only-linux'], stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True,
                                 cwd='/', env=ENV)
        try:
            code = child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            raise Stop('Replay completion unknown; no signal/cleanup authorized') from None
        require(code != 0 and self.fingerprint(run/'claimed') == before, 'Claim replay accepted/changed')

    def command(self, argv, timeout=5):
        # Fixed caller commands only. No shell, privilege wrapper, package action
        # or caller-selected command/URL. Only read-only preflight uses timeout.
        require(argv[0] in ['/usr/bin/dpkg-query', '/usr/bin/loginctl', '/usr/bin/gpg', '/usr/bin/busctl', '/usr/sbin/runuser', '/usr/bin/journalctl', '/usr/bin/systemd-detect-virt'],
                'Command not permitted by validation driver')
        self.trusted(Path(argv[0]))
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, env=ENV, cwd='/',
                                 close_fds=True, start_new_session=True)
        output = bytearray()
        until = time.monotonic() + timeout
        eof = False
        try:
            os.set_blocking(child.stdout.fileno(), False)
            while True:
                code = child.poll()
                require(time.monotonic() < until, 'Read-only probe deadline expired')
                if not eof and select.select([child.stdout], [], [], 0.02)[0]:
                    block = os.read(child.stdout.fileno(), 8193-len(output))
                    eof = not block
                    output.extend(block)
                    require(len(output) <= 8192, 'Read-only probe output limit')
                if eof and code is not None:
                    return code, bytes(output)
                if eof:
                    time.sleep(0.005)
        finally:
            # Only these whitelisted read-only probes are supervised this way.
            # Production worker/replay/installer execution NEVER uses this runner.
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=1)
            child.stdout.close()

    def facts(self):
        os_release = dict(line.split('=', 1) for line in self.read(Path('/etc/os-release').resolve(), 8192).decode().splitlines() if '=' in line)
        # Explicit QEMU DMI+UUID binding, not "GITHUB_ACTIONS" or an environment flag.
        product = Path('/sys/class/dmi/id/product_name').read_text().strip()
        container_code, container_name = self.command(['/usr/bin/systemd-detect-virt', '--container'])
        return {'vmId': Path('/sys/class/dmi/id/product_uuid').read_text().strip().lower(),
                'bootId': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                'bootMs': time.clock_gettime_ns(time.CLOCK_BOOTTIME)//1000000,
                'euid': os.geteuid(), 'ruid': os.getuid(), 'egid': os.getegid(),
                'container': 'none' if container_code == 1 and not container_name.strip() else container_name.decode().strip(),
                'pid1': Path('/proc/1/comm').read_text().strip(),
                'kernel': os.uname().release, 'machine': os.uname().machine, 'python': sys.version.split()[0], 'mint': os_release.get('VERSION_ID', '').strip('"')
                if os_release.get('ID', '').strip('"') == 'linuxmint' else None,
                'virtualization': 'QEMU' if product in ['Standard PC (Q35 + ICH9, 2009)',
                                                       'Standard PC (i440FX + PIIX, 1996)', 'QEMU'] else product}


def prepare(native, approval, assets, kind, ledger):
    """Journal before each mutation. Pending mutation => stop/destroy VM, no undo."""
    require(not native.exists(ledger), 'Approval/run already used')
    for p in [ROOT, ENTRY, POLICY, TOOLS, COORDINATION,
              Path('/usr/bin/skyview-dev-setup'), Path('/usr/local/sbin/skyview-student-dev-update')]:
        require(not native.exists(p), 'Installed SDE or fixture collision; abort')
    code, out = native.command(['/usr/bin/dpkg-query', '-W', '-f=${db:Status-Status}', 'skyview-dev-setup'])
    require(code == 1 and not out, 'Installed SDE or ambiguous package database')
    for p in [Path('/usr/bin/pkexec'), Path('/usr/sbin/runuser'), Path('/usr/bin/busctl')]:
        native.trusted(p)
    entries = []
    state = {'schemaVersion': 1, 'runId': approval['runId'], 'vmId': approval['vmId'],
             'bootId': approval['bootId'], 'kind': kind, 'entries': entries,
             'pending': None, 'sealed': False, 'phase': 'Prepared', 'cleanup': 'NotRun'}
    require(ledger.parent.name == 'sde-mint-validation-' + approval['runId'], 'Staging/run mismatch')
    native.atomic(ledger, state)
    for op in fixture_plan(approval, assets, kind):
        path = op[1]
        if path == ROOT.parent and native.exists(path):
            native.trusted(path)  # existing ancestor is never owned or removed
            continue
        state['pending'] = str(path)
        native.atomic(ledger, state)
        fp = native.create(op)
        entries.append({'path': str(path), 'identity': fp})
        state['pending'] = None
        native.atomic(ledger, state)
    return state


def owned_path(path, run):
    static = {ROOT.parent, ROOT, ROOT/'engines', ROOT/'engines'/run,
              ROOT/'engines'/run/'sde-update-trust', ROOT/'engines'/run/'version.json',
              ROOT/'app-only', ROOT/'app-only/runs', ROOT/'app-only/request.gate',
              ROOT/'active.json', ROOT/'app-only-capabilities.json', ENTRY, POLICY, TOOLS,
              TOOLS/'driver.py', TOOLS/'sde-update-trust', TOOLS/'case.json', TOOLS/'desktop-go'}
    p = Path(path)
    if str(p) != path or '..' in p.parts:
        return False
    if p in static:
        return True
    if p.parent == ROOT/'app-only/runs':
        return canonical_uuid(p.name)
    return (p.parent.parent == ROOT/'app-only/runs' and canonical_uuid(p.parent.name)
            and p.name in ['request.json', 'claimed', 'progress.json', 'version.json',
                           'sde-update-trust', 'sentinel.json', 'sentinel-ended.json', 'gui-close', 'release-sentinel'])


def verify_static(native, state):
    for entry in state['entries']:
        require(owned_path(entry['path'], state['runId']), 'Out-of-scope ownership record')
        require(native.fingerprint(Path(entry['path'])) == entry['identity'], 'Owned file identity changed')


def cleanup(native, state, ledger):
    require(state.get('sealed') is True and state.get('phase') == 'Sealed' and state.get('pending') is None,
            'Cannot clean unsealed/live/uncertain fixture; preserve evidence and discard VM')
    with native.cleanup_gate():
        return cleanup_locked(native, state, ledger)


def cleanup_locked(native, state, ledger):
    require(state.get('sealed') is True and state.get('phase') == 'Sealed' and state.get('pending') is None,
            'Cannot clean unsealed/live/uncertain fixture; preserve evidence and discard VM')
    # Prevalidate ALL identities and complete child sets before ANY deletion.
    require(len(state['entries']) <= 128 and len({e['path'] for e in state['entries']}) == len(state['entries']), 'Ownership count/duplicates')
    verify_static(native, state)
    for entry in state['entries']:
        if entry['identity']['kind'] == 'dir':
            path = Path(entry['path'])
            expected = sorted(Path(e['path']).name for e in state['entries'] if Path(e['path']).parent == path)
            require(native.children(path) == expected, 'Unowned directory content; no deletion')
    state['cleanup'] = 'InProgress'
    native.atomic(ledger, state)
    for entry in reversed(state['entries']):
        path = Path(entry['path'])
        require(native.fingerprint(path) == entry['identity'], 'Cleanup race')
        native.remove(path, entry['identity']['kind'])
    state['cleanup'] = 'Pass'
    state['cleanupScope'] = 'manifest-owned-root-fixture-only'
    state['vmDisposal'] = 'NotRun'
    native.atomic(ledger, state)
    return state


CASES = ['approved', 'denied', 'bad-args', 'inactive', 'normal', 'abrupt']


def desktop_request(case):
    """Run from actual test desktop; no passwords, sudo or arbitrary arguments."""
    require(os.geteuid() != 0 and case in CASES, 'Use an unelevated test desktop')
    n = Native()
    config = strict_json(n.read(TOOLS / 'case.json'))
    uid = config['otherUid'] if case == 'inactive' else config['uid']
    require(os.getuid() == uid, 'Wrong desktop test account')
    require((config['kind'] == 'sentinel') == (case in ['normal', 'abrupt']), 'Case/worker mismatch')
    home = Path('/home/sde-other' if case == 'inactive' else '/home/sde-student')
    receipt = home / 'sde-phase3-request.json'
    require(not n.exists(receipt), 'Desktop receipt collision; fresh fixture required')
    # This unprivileged receipt is a hint only; root later verifies pidfd/kernel
    # ownership/start time, exact command, logind and protected request correlation.
    body = {'schemaVersion': 1, 'runId': config['runId'], 'case': case, 'pid': os.getpid(),
            'status': 'Ready', 'requestId': None, 'exit': None, 'subjectPid': None}
    def write():
        temp = home / ('sde-request-' + str(uuid.uuid4()) + '.tmp')
        fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(encode(body)); f.flush(); os.fsync(f.fileno())
        os.replace(temp, receipt)
    write()
    until = time.clock_gettime(time.CLOCK_BOOTTIME) + 90
    while not n.exists(TOOLS / 'desktop-go'):
        require(time.clock_gettime(time.CLOCK_BOOTTIME) < until, 'Desktop enrollment timed out')
        time.sleep(0.02)
    go = strict_json(n.read(TOOLS / 'desktop-go'))
    require(go == {'runId': config['runId'], 'case': case}, 'Wrong desktop enrollment')
    argv = ['/usr/bin/pkexec', str(ENTRY)] + (['--rejected-test-argument'] if case == 'bad-args' else [])
    # stderr stays off artifacts; the real authentication agent handles consent.
    child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, close_fds=True)
    body['subjectPid'] = child.pid
    write()
    try:
        code = child.wait(timeout=max(0.001, until-time.clock_gettime(time.CLOCK_BOOTTIME)))
    except subprocess.TimeoutExpired:
        # Do not kill pkexec or an unknown privileged descendant. Stop/discard VM.
        body['status'] = 'Unknown'; write(); raise Stop('Authorization completion unknown') from None
    try:
        os.set_blocking(child.stdout.fileno(), False)
        data = child.stdout.read(513)
        require(isinstance(data, bytes) and len(data) <= 512, 'Broker response incomplete/over limit')
    finally:
        child.stdout.close()
    body['status'], body['exit'] = 'Completed', code
    if code == 0:
        parsed = strict_json(data)
        require(set(parsed) == {'schemaVersion', 'requestId'} and parsed['schemaVersion'] == 1
                and canonical_uuid(parsed['requestId']), 'Invalid broker correlation')
        body['requestId'] = parsed['requestId']
    write()
    if case in ['normal', 'abrupt'] and code == 0:
        until = time.clock_gettime(time.CLOCK_BOOTTIME) + 30
        while not n.exists(ROOT / 'app-only/runs' / body['requestId'] / 'gui-close'):
            require(time.clock_gettime(time.CLOCK_BOOTTIME) < until, 'GUI surrogate barrier expired')
            time.sleep(0.02)


def desktop_receipt(n, a, case):
    uid = a['uids']['sde-other' if case == 'inactive' else 'sde-student']
    path = Path('/home/sde-other' if case == 'inactive' else '/home/sde-student') / 'sde-phase3-request.json'
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        m = os.fstat(fd)
        require(m.st_uid == uid and stat.S_ISREG(m.st_mode) and m.st_nlink == 1
                and stat.S_IMODE(m.st_mode) == 0o600, 'Untrusted desktop receipt')
        record = strict_json(os.read(fd, MAX_RECORD+1))
    finally:
        os.close(fd)
    require(record.get('runId') == a['runId'] and record.get('case') == case
            and type(record.get('pid')) is int and record['pid'] > 1, 'Desktop correlation mismatch')
    return record, uid


def arm_desktop(n, a, case, receipt):
    r, uid = receipt
    config = strict_json(n.read(TOOLS/'case.json'))
    require(strict_json(n.read(ROOT/'app-only-capabilities.json')) == {}, 'Capability gate changed')
    require((config['kind'] == 'sentinel') == (case in ['normal', 'abrupt']), 'Case/fixture mismatch')
    handle = n.pidfd(r['pid'])
    try:
        p = n.process(r['pid'], handle)
        require(p['uid'] == uid and p['cmd'] == ['/usr/bin/python3', '-I', str(TOOLS/'driver.py'),
                'desktop-request', '--execute', '--case', case], 'Wrong desktop subject instance')
        session = n.session(r['pid'])
        require(type(session.get('Active')) is bool and type(session.get('Remote')) is bool,
                'Invalid native session attribution')
        if case == 'inactive':
            require(not session['Active'], 'Inactive test subject is active')
        else:
            require(session['Active'] and not session['Remote']
                    and session['Type'] in ['x11', 'wayland'], 'Not an active local graphical session')
        require(r['status'] == 'Ready', 'Subject already sent request')
        require(not n.children(ROOT / 'app-only/runs'), 'Fixture already used')
        provider = n.policy_provider()
        cursor = n.journal_cursor()
        n.create(('file', TOOLS / 'desktop-go', 0o644, encode({'runId': a['runId'], 'case': case})))
        p.pop('cmd')  # never export arbitrary command text
        return {'subject': p, 'session': session, 'case': case, 'journalCursor': cursor, 'policyProvider': provider}
    finally:
        n.close(handle)


def observe_sentinel(n, a, r, enrollment):
    run = ROOT / 'app-only/runs' / r['requestId']
    probe = n.wait_json(run/'sentinel.json')
    require(probe.get('testOnly') is True, 'Not a test sentinel')
    gui = enrollment['subject']
    gh = n.pidfd(gui['pid'])
    try:
        sh = n.pidfd(probe['pid'])
    except Exception:
        n.close(gh)
        raise
    try:
        before_gui = n.process(gui['pid'], gh)
        process_check(before_gui, gui)
        before = n.ready_sentinel(probe['pid'], sh, probe)
        process_check(before, probe, sentinel=True)
        require(before['cmd'] == ['/usr/bin/python3', '-I', str(run/'sde-update-trust'), 'app-only-linux'],
                'Sentinel script identity mismatch')
        if r['case'] == 'normal':
            n.create(('file', run/'gui-close', 0o644, b''))
        else:
            # Retained pidfd; validated kernel owner + exact enrolled test instance.
            n.kill_gui(gh)
        require(n.closed(gh, 5), 'GUI surrogate did not exit')
        after = n.process(probe['pid'], sh)
        process_check(after, probe, sentinel=True)
        n.create(('file', run/'release-sentinel', 0o600, b''))
        require(n.closed(sh, 5), 'Sentinel did not end after release')
        ended = n.wait_json(run/'sentinel-ended.json')
        require(ended.get('outcome') == 'released' and all(ended.get(k) == probe[k]
                for k in ['pid', 'startTicks', 'bootId', 'uid']), 'Sentinel did not acknowledge explicit release')
        for p in [before, after]:
            p.pop('cmd')
        return {'before': before, 'after': after, 'guiEnded': True,
                'sentinelEnded': True, 'scope': 'broker-surrogate-only',
                'authenticationSafety': 'Unproven'}
    finally:
        n.close(gh); n.close(sh)


def seal(n, a, state, case, receipt, enrollment):
    require(state['pending'] is None and not state['sealed'], 'Uncertain/already sealed fixture')
    require(state['runId'] == a['runId'] and state['bootId'] == a['bootId'], 'Ownership record mismatch')
    r, uid = receipt
    require(enrollment['case'] == case and enrollment['subject']['pid'] == r['pid'], 'Enrollment/capture mismatch')
    require((state['kind'] == 'sentinel') == (case in ['normal', 'abrupt']), 'Case/worker mismatch')
    require(r['status'] == 'Completed', 'Unknown request completion')
    names = n.children(ROOT / 'app-only/runs')
    expected = [] if case in ['denied', 'bad-args', 'inactive'] else [r['requestId']]
    require(names == expected and all(canonical_uuid(v) for v in names), 'Unexpected request count/identity')
    require((r['exit'] != 0) == (not expected), 'Unexpected authorization outcome')
    # No native intent, staging, resources or installed-state records may appear.
    require(n.children(ROOT) == ['active.json', 'app-only', 'app-only-capabilities.json', 'engines']
            and not n.exists(COORDINATION), 'Unexpected native/coordination state')
    evidence = {'case': case, 'subject': enrollment, 'diagnosticCompletion': 'Pass',
                'authenticationSafety': 'Unproven', 'cleanupCorrectness': 'NotRun'}
    require(type(r.get('subjectPid')) is int and r['subjectPid'] > 1, 'Missing OS authorization subject')
    require(n.policy_provider() == enrollment['policyProvider'], 'PolicyKit provider changed during case')
    evidence['polkit'] = authorization_audit(n.journal_events(enrollment['journalCursor']), r['subjectPid'], case, enrollment['policyProvider'])
    if expected:
        run = ROOT / 'app-only/runs' / names[0]
        request_identity = n.wait_json(run/'request.json')
        require(request_identity.get('requestId') == r['requestId']
                and request_identity.get('uid') == uid and request_identity.get('bootId') == a['bootId'],
                'Protected request and desktop correlation differ')
        require(digest(n.read(run/'sde-update-trust', 64*1024**2)) ==
                next(e['identity']['sha256'] for e in state['entries'] if e['path'].endswith('/engines/'+a['runId']+'/sde-update-trust')),
                'Snapshot executable mismatch')
        if state['kind'] == 'production':
            n.wait_json(run/'progress.json')
            require(n.children(run) == ['claimed', 'progress.json', 'request.json', 'sde-update-trust', 'version.json'],
                    'Unexpected production run contents')
            progress = n.wait_json(run/'progress.json')
            request, claim = [strict_json(n.read(run/name, 4096)) for name in ['request.json', 'claimed']]
            evidence['worker'] = deferred_check(request, claim, progress, uid, a['bootId'])
            acl_check(n.acl(run/'progress.json'), uid)
            for account, readable in [('sde-student', True), ('sde-other', False)]:
                code, output = n.command(['/usr/sbin/runuser', '-u', account, '--', '/usr/bin/python3',
                     '-I', str(TOOLS/'driver.py'), 'acl-probe', '--execute', '--request', r['requestId']])
                require(code == 0 and strict_json(output) == {'read': readable, 'write': False},
                        'Kernel cross-user access differs from intended ACL')
            for account, readable in [('sde-student', True), ('sde-other', False)]:
                code, output = n.command(['/usr/sbin/runuser', '-u', account, '--',
                     str(TOOLS/'sde-update-trust'), 'app-only-progress', r['requestId']])
                require((code == 0 and strict_json(output) == progress) if readable else
                        (code != 0 and not output), 'Public progress CLI reader isolation failed')
            before_progress = n.fingerprint(run/'progress.json')
            n.replay(run)
            require(n.fingerprint(run/'progress.json') == before_progress, 'Replay published progress')
            evidence['kernelAccess'] = 'Intended read only; other read and both write denied'
            evidence['replay'] = 'Rejected; original claim/progress unchanged'
            try:
                handle = n.pidfd(claim['workerPid'])
            except ProcessLookupError:
                evidence['process'] = 'GoneBeforeEnrollment; source-gated no-fork deferral only'
            else:
                try:
                    p = n.process(claim['workerPid'], handle)
                    require(p['uid'] == 0 and p['cmd'] == [str(run/'sde-update-trust'), 'app-only-linux'],
                            'Worker PID reused/ambiguous')
                    require(n.closed(handle, 5), 'Safe-deferral worker still active')
                    evidence['process'] = 'Observed actual worker exit'
                finally:
                    n.close(handle)
        else:
            evidence['worker'] = observe_sentinel(n, a, r, enrollment)
            require(n.children(run) == sorted(['request.json', 'sde-update-trust', 'version.json',
                    'sentinel.json', 'sentinel-ended.json', 'release-sentinel'] + (['gui-close'] if case == 'normal' else [])),
                    'Unexpected sentinel run contents')
        # All known run processes have ended before dynamic identities are sealed.
        state['entries'].append({'path': str(run), 'identity': n.fingerprint(run)})
        for name in n.children(run):
            state['entries'].append({'path': str(run/name), 'identity': n.fingerprint(run/name)})
    state['entries'].append({'path': str(TOOLS/'desktop-go'), 'identity': n.fingerprint(TOOLS/'desktop-go')})
    state['sealed'] = True
    state['phase'] = 'Sealed'
    return evidence


def acl_probe(request):
    require(canonical_uuid(request) and os.geteuid() != 0, 'Unprivileged fixed ACL probe only')
    n = Native()
    c = strict_json(n.read(TOOLS/'case.json'))
    require(os.getuid() in [c['uid'], c['otherUid']], 'Not a fixture account')
    path = ROOT/'app-only/runs'/request/'progress.json'
    result = {}
    for name, mode in [('read', os.O_RDONLY), ('write', os.O_WRONLY)]:
        try:
            fd = os.open(path, mode | os.O_NOFOLLOW | os.O_CLOEXEC)
        except PermissionError:
            result[name] = False
        else:
            os.close(fd)  # open-only: never truncate/write the progress record
            result[name] = True
    return result


def plan():
    return {'schemaVersion': 1, 'purpose': 'mint-phase3-negative-and-sentinel-only',
            'productionCommit': PRODUCTION_COMMIT, 'approvalRequired': ACTIONS,
            'cases': ['owned-file-acl', 'production-safe-deferral', 'sentinel-normal', 'sentinel-abrupt'],
            'fixedPaths': [str(p) for p in [ROOT, ENTRY, POLICY, TOOLS]],
            'capabilityReceipt': {}, 'nativeExecuted': False,
            'diagnosticCompletion': 'NotRun', 'cleanupCorrectness': 'NotRun',
            'authenticationSafety': 'Unproven', 'productionReady': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'prepare', 'arm-desktop', 'capture', 'cleanup', 'desktop-request', 'acl-probe'])
    parser.add_argument('--request')
    parser.add_argument('--case', choices=CASES, default='approved')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--approval', type=Path)
    parser.add_argument('--kind', choices=['production', 'sentinel'], default='production')
    args = parser.parse_args(argv)
    if args.action == 'plan':
        require(not args.execute, 'Plan never executes')
        print(json.dumps(plan(), indent=2))
        return
    if args.action == 'acl-probe':
        require(args.execute, 'ACL execution is not authorized by default')
        print(json.dumps(acl_probe(args.request)))
        return
    if args.action == 'desktop-request':
        require(args.execute, 'Desktop execution not authorized by default')
        desktop_request(args.case)
        return
    require(args.execute and args.approval is not None, 'Native execution requires explicit approval')
    require(sys.flags.isolated == 1, 'Run privileged control with /usr/bin/python3 -I')
    n = Native()
    require(args.approval.name == 'approval.json' and re.fullmatch('sde-mint-validation-[a-f0-9-]{36}', args.approval.parent.name) and args.approval.parent.parent == Path('/run'), 'Use the fixed private root staging directory')
    n.trusted(args.approval)
    require(args.approval.stat().st_mode & 0o777 == 0o600, 'Approval must be private root-owned')
    a = strict_json(n.read(args.approval))
    stage = args.approval.parent
    require(stat.S_IMODE(stage.stat().st_mode) == 0o700, 'Staging directory must be private')
    n.trusted(Path(__file__).resolve())
    require(Path(__file__).resolve() == stage / 'driver.py', 'Run only immutable root-staged driver')
    assets = {key: n.read(stage / name, 64*1024**2 if key == 'verifier' else MAX_RECORD) for key, name in ASSETS.items()}
    native_facts = n.facts()
    approval_check(a, native_facts, {k: digest(v) for k, v in assets.items()})
    require(stage.name == 'sde-mint-validation-'+a['runId'], 'Staging/run mismatch')
    n.accounts(a['uids'])
    require(set(n.children(stage)) <= set(ASSETS.values()) | {'approval.json', 'ownership.json', 'enrollment.json', 'case-evidence.json', 'failure.json', 'environment.json'}, 'Unknown/pending staging artifact; discard VM')
    require(not n.exists(stage/'failure.json'), 'Prior failure retained; discard VM instead of resuming')
    ledger = stage / 'ownership.json'
    try:
        if args.action == 'prepare':
            n.create(('file', stage/'environment.json', 0o600, encode(native_facts)))
            result = prepare(n, a, assets, args.kind, ledger)
        else:
            result = strict_json(n.read(ledger))
            verify_static(n, result)
            require(result['runId'] == a['runId'] and result['vmId'] == a['vmId'] and result['bootId'] == a['bootId'], 'Ledger VM/run mismatch')
            if args.action == 'cleanup':
                result = cleanup(n, result, ledger)
            elif args.action == 'arm-desktop':
                require(result['phase'] == 'Prepared', 'Fixture cannot re-arm/replay')
                result['phase'] = 'Arming'
                n.atomic(ledger, result)
                evidence = arm_desktop(n, a, args.case, desktop_receipt(n, a, args.case))
                n.atomic(stage/'enrollment.json', evidence)
                result['phase'] = 'Armed'
                n.atomic(ledger, result)
            else:
                require(result['phase'] == 'Armed', 'Capture cannot replay or resume uncertainty')
                result['phase'] = 'Capturing'
                n.atomic(ledger, result)
                evidence = seal(n, a, result, args.case, desktop_receipt(n, a, args.case),
                                strict_json(n.read(stage/'enrollment.json')))
                evidence['environment'] = strict_json(n.read(stage/'environment.json'))
                # Persist bounded evidence before the ledger can authorize cleanup.
                n.create(('file', stage/'case-evidence.json', 0o600, encode(evidence)))
                n.atomic(ledger, result)
    except BaseException as error:
        failure = {'schemaVersion': 1, 'runId': a['runId'], 'vmId': a['vmId'],
                   'bootId': a['bootId'], 'diagnosticCompletion': 'Fail',
                   'cleanupCorrectness': 'NotRun/uncertain', 'authenticationSafety': 'Unproven',
                   'errorType': type(error).__name__, 'reason': str(error)[:256]}
        try:
            n.create(('file', stage/'failure.json', 0o600, encode(failure)))
        except Exception:
            raise Stop('Failure evidence could not persist; preserve fixture and discard VM') from error
        raise
    print(json.dumps({'runId': result['runId'], 'cleanup': result['cleanup'], 'cleanupScope': 'manifest-owned-root-fixture-only',
                      'vmDisposal': result.get('vmDisposal', 'NotRun'),
                      'diagnosticCompletion': 'Pass' if result.get('sealed') else 'NotRun', 'authenticationSafety': 'Unproven'}))


if __name__ == '__main__':
    try:
        main()
    except (Stop, OSError, ValueError, subprocess.SubprocessError) as error:
        # no raw subprocess stdout/stderr or credentials in evidence
        print('Mint validation stopped: ' + str(error), file=sys.stderr)
        sys.exit(1)
