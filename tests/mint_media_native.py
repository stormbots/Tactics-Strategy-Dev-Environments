"""Explicit native ports for future authorized preparation. No CLI or import I/O.

Tests must mock all OS/process/network operations. Only curl/GPG test processes
can be created. No generic shell, QEMU launcher, package or runner executor.
"""
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import selectors
import stat
import subprocess
import time

from mint_media_console import (BASE, CHUNK, ISO, REPORT_LIMIT, WORKSPACE_LIMIT,
                                Stop, Transfer, canonical_uuid, require, KEY_SHA, METADATA_LIMIT,
                                SIGNATURE_LIMIT, sha)

TOOLS = {'/usr/bin/curl', '/usr/bin/gpg'}
NAMES = {'signing-key.asc', 'sha256sum.txt.partial', 'sha256sum.txt.gpg.partial',
         ISO + '.partial', ISO, 'authenticated-pin.json', 'report.json',
         'ownership.json', 'failure.json'}


def identity(st):
    return (st.st_dev, st.st_ino, st.st_uid, stat.S_IMODE(st.st_mode), st.st_nlink)


def _owned_directory(path, uid):
    """Open every absolute component relative to pinned parent; reject symlinks."""
    path = Path(path)
    require(path.is_absolute() and str(path) == os.path.normpath(str(path)), 'ANCESTRY')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in path.parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd); fd = nxt
            st = os.fstat(fd)
            require(st.st_uid in {0, uid} and not stat.S_IMODE(st.st_mode) & 0o022, 'ANCESTRY')
        return fd
    except BaseException:
        os.close(fd)
        raise


def _tool(path):
    require(path in TOOLS, 'TOOL')
    parent = _owned_directory(Path(path).parent, 0)
    try:
        st = os.stat(Path(path).name, dir_fd=parent, follow_symlinks=False)
        require(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and st.st_nlink == 1
                and not stat.S_IMODE(st.st_mode) & 0o022, 'TOOL')
    finally:
        os.close(parent)


def _names(fd, limit=64):
    names = []
    with os.scandir(fd) as entries:
        for entry in entries:
            require(len(names) < limit, 'INVENTORY_SIZE')
            names.append(entry.name)
    return names


class Workspace:
    """Exclusive run-owned directory. Failure preserves files; there is no resume/delete API."""
    def __init__(self, run_id):
        self.run_id = canonical_uuid(run_id)
        self.uid = os.getuid()
        who = pwd.getpwuid(self.uid)
        require(self.uid >= 1000 and os.geteuid() == self.uid and who.pw_name == 'sde-runner', 'ACCOUNT')
        groups = [grp.getgrgid(g).gr_name for g in set(os.getgroups()) | {os.getgid()}]
        require(not set(groups) & {'sudo', 'admin', 'root', 'docker', 'libvirt', 'lxd'}, 'ACCOUNT_GROUPS')
        home = Path(who.pw_dir)
        self.path = str(home/'mint-validation'/run_id)
        hfd = _owned_directory(home, self.uid)
        bfd = None
        runfd = None
        try:
            try:
                os.mkdir('mint-validation', 0o700, dir_fd=hfd)
                os.fsync(hfd)
            except FileExistsError:
                pass
            bfd = os.open('mint-validation', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=hfd)
            st = os.fstat(bfd)
            require(st.st_uid == self.uid and stat.S_IMODE(st.st_mode) == 0o700, 'WORKSPACE_PARENT')
            os.mkdir(run_id, 0o700, dir_fd=bfd)  # collision is always a stop, never reuse
            os.fsync(bfd)
            runfd = os.open(run_id, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=bfd)
            st = os.fstat(runfd)
            require(st.st_uid == self.uid and stat.S_IMODE(st.st_mode) == 0o700, 'WORKSPACE')
            self.root_identity = identity(st)[:4]
            self.fd = runfd
        except BaseException:
            if runfd is not None:
                os.close(runfd)
            raise
        finally:
            os.close(hfd)
            if bfd is not None:
                os.close(bfd)
        self.files = {}
        self.written = 0
        self.finished = False
        self.closed = False
        self.failed = False
        self.gpg_created = False
        self.gpg_identity = None

    def check(self):
        require(not self.finished and not self.failed and not self.closed, 'WORKSPACE_STOPPED')
        fd = _owned_directory(self.path, self.uid)
        try:
            require(identity(os.fstat(fd))[:4] == self.root_identity
                    and identity(os.fstat(self.fd))[:4] == self.root_identity, 'WORKSPACE_REPLACED')
        finally:
            os.close(fd)

    def _file(self, name):
        require(name in self.files, 'FILE_UNKNOWN')
        fd, expected = self.files[name]
        a = os.fstat(fd)
        b = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
        require(identity(a) == expected == identity(b)
                and stat.S_ISREG(a.st_mode) and a.st_nlink == 1, 'FILE_REPLACED')
        return fd

    def create(self, name):
        self.check()
        require(name in NAMES and name not in self.files, 'FILE_NAME')
        fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=self.fd)
        try:
            st = os.fstat(fd)
            require(st.st_uid == self.uid and st.st_nlink == 1 and stat.S_ISREG(st.st_mode), 'FILE_OWNER')
            self.files[name] = (fd, identity(st))
        except BaseException:
            # No descriptor may escape before it enters the tracked inventory.
            # Preserve the path for investigation; never retry an uncertain close.
            try:
                os.close(fd)
            except OSError:
                raise Stop('DESCRIPTOR_CLEANUP_UNCERTAIN') from None
            raise

    def write(self, name, data):
        self.check()
        require(type(data) is bytes and len(data) <= CHUNK, 'WRITE_CHUNK')
        require(self.written + len(data) <= WORKSPACE_LIMIT, 'WORKSPACE_BUDGET')
        fd = self._file(name)
        require(self.files[name][1][3] == 0o600, 'FILE_SEALED')
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            require(n > 0, 'SHORT_WRITE')
            self.written += n
            view = view[n:]

    def seal(self, name):
        self.check(); fd = self._file(name)
        os.fsync(fd)
        os.fchmod(fd, 0o400)
        self.files[name] = (fd, identity(os.fstat(fd)))
        os.fsync(fd); os.fsync(self.fd)

    def verify(self, name, size, digest, clock, deadline):
        self.check(); fd = self._file(name)
        require(os.fstat(fd).st_size == size, 'FILE_SIZE')
        observed = hashlib.sha256()
        offset = 0
        while offset < size:
            require(clock() < deadline, 'VERIFY_DEADLINE')
            self._file(name)
            block = os.pread(fd, min(CHUNK, size-offset), offset)
            require(0 < len(block) <= min(CHUNK, size-offset), 'FILE_SHORT_READ')
            observed.update(block); offset += len(block)
        require(clock() < deadline and os.fstat(fd).st_size == size
                and observed.hexdigest() == digest, 'FILE_DIGEST')
        self._file(name)

    def store(self, name, value):
        require(type(value) is bytes and len(value) <= REPORT_LIMIT, 'RECORD_SIZE')
        self.create(name)
        for start in range(0, len(value), CHUNK):
            self.write(name, value[start:start+CHUNK])
        self.seal(name)

    def promote(self, old, new):
        self.check(); original = self._file(old)
        require(old == ISO+'.partial' and new == ISO and new not in self.files, 'PROMOTE')
        # Hard-link publication never overwrites a collision. Interrupted link/unlink
        # is unknown state, not a cleanup success; exclusive run may never resume.
        os.link(old, new, src_dir_fd=self.fd, dst_dir_fd=self.fd, follow_symlinks=False)
        require(os.stat(new, dir_fd=self.fd, follow_symlinks=False).st_ino == os.fstat(original).st_ino, 'PROMOTE_IDENTITY')
        os.unlink(old, dir_fd=self.fd)
        self.files[new] = self.files.pop(old)
        require(self._file(new) == original, 'PROMOTE_IDENTITY')
        os.fsync(self.fd)

    def require_absent(self, names):
        self.check()
        for name in names:
            require(name in {'guest.qcow2', 'console.sock', 'control.sock'}, 'PLAN_NAME')
            try:
                os.stat(name, dir_fd=self.fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            raise Stop('PLAN_COLLISION')

    def gpg_home(self):
        self.check(); require(not self.gpg_created, 'VERIFIER_REPLAY')
        os.mkdir('gnupg', 0o700, dir_fd=self.fd)
        os.fsync(self.fd)
        fd = os.open('gnupg', os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC, dir_fd=self.fd)
        try:
            self.gpg_identity = identity(os.fstat(fd))[:4]
        finally:
            os.close(fd)
        self.gpg_created = True
        return str(Path(self.path)/'gnupg')

    def audit(self):
        self.check()
        require(set(_names(self.fd)) == set(self.files) | ({'gnupg'} if self.gpg_created else set()), 'UNKNOWN_FILE')
        records = []
        for name in sorted(self.files):
            fd = self._file(name)
            size = os.fstat(fd).st_size
            require(size <= WORKSPACE_LIMIT, 'FILE_SIZE')
            records.append({'name': name, 'identity': list(identity(os.fstat(fd))), 'size': size})
        gpg = Path(self.path)/'gnupg'
        gpg_bytes = 0
        if self.gpg_created:
            # Pinned public key only; never export keyring bytes. Unknown objects stop.
            allowed = {'key.asc', 'sums', 'signature', 'pubring.kbx', 'pubring.kbx~', 'trustdb.gpg',
                       'private-keys-v1.d', 'openpgp-revocs.d'}
            fd = _owned_directory(gpg, self.uid)
            try:
                require(identity(os.fstat(fd))[:4] == self.gpg_identity
                        and os.fstat(fd).st_uid == self.uid
                        and stat.S_IMODE(os.fstat(fd).st_mode) == 0o700, 'GPG_OWNER')
                names = _names(fd)
                require(len(names) <= 64 and set(names) <= allowed, 'GPG_CONTENTS')
                for name in names:
                    st = os.stat(name, dir_fd=fd, follow_symlinks=False)
                    require(st.st_uid == self.uid and not stat.S_IMODE(st.st_mode) & 0o077, 'GPG_OWNER')
                    if stat.S_ISDIR(st.st_mode):
                        require(name in {'private-keys-v1.d', 'openpgp-revocs.d'}, 'GPG_CONTENTS')
                        child = os.open(name, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC, dir_fd=fd)
                        try:
                            require(not _names(child), 'GPG_CONTENTS')
                        finally:
                            os.close(child)
                    else:
                        require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, 'GPG_CONTENTS')
                        gpg_bytes += st.st_size
                require(gpg_bytes <= 1024**2, 'GPG_SIZE')
            finally:
                os.close(fd)
        require(self.written + gpg_bytes <= WORKSPACE_LIMIT, 'WORKSPACE_BUDGET')
        return records

    def finish(self, report):
        self.audit()
        raw = json.dumps(report, sort_keys=True).encode('ascii')
        self.store('report.json', raw)
        records = self.audit()
        self.store('ownership.json', json.dumps({'runId': self.run_id, 'rootIdentity': self.root_identity,
                   'files': records, 'excludesSelf': True, 'keyringContentsExported': False,
                   'cleanupPerformed': False}).encode('ascii'))
        self.audit()
        self.finished = True

    def fail(self, code):
        # Do not delete/quarantine by pathname. Partial files remain private and
        # unpromoted. Evidence I/O failure is surfaced as unknown, never Pass.
        require(not self.failed and not self.finished, 'WORKSPACE_STOPPED')
        self.store('failure.json', json.dumps({'reason': code, 'pass': False,
                   'partialFilesRetained': True, 'cleanupPerformed': False}).encode('ascii'))
        self.failed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        if self.closed:
            return
        self.closed = True
        uncertain = False
        for fd in [value[0] for value in self.files.values()] + [self.fd]:
            try:
                os.close(fd)
            except OSError:
                uncertain = True  # never retry an ambiguously closed/reused fd
        require(not uncertain, 'DESCRIPTOR_CLEANUP_UNCERTAIN')


def _stream_process(argv, deadline, clock):
    """Bounded owned curl/GPG stdout stream; no generic shell or installer."""
    _tool(argv[0])
    require(argv[0] in TOOLS, 'TOOL')
    env = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}
    for name in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY', 'http_proxy',
                 'https_proxy', 'all_proxy', 'no_proxy', 'SSL_CERT_FILE', 'SSL_CERT_DIR', 'CURL_CA_BUNDLE',
                 'RUNNER_TRACKING_ID'):
        if name in os.environ:
            env[name] = os.environ[name]  # preserve proxy/trust and runner cleanup tracking; never log values
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               stdin=subprocess.DEVNULL, env=env, start_new_session=True,
                               close_fds=True)
    selector = None
    try:
        selector = selectors.DefaultSelector()
        os.set_blocking(process.stdout.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            left = deadline - clock()
            require(left > 0, 'PROCESS_DEADLINE')
            if not selector.select(min(left, 0.1)):
                continue
            chunk = os.read(process.stdout.fileno(), CHUNK)
            if not chunk:
                break
            yield chunk
        left = deadline - clock(); require(left > 0, 'PROCESS_DEADLINE')
        require(process.wait(timeout=left) == 0, 'TOOL_EXIT')
    finally:
        uncertain = False
        if selector is not None:
            try:
                selector.close()
            except OSError:
                uncertain = True
        try:
            process.stdout.close()
        except OSError:
            uncertain = True
        if process.poll() is None:
            try:
                process.kill()  # only this owned curl/GPG child, never QEMU/worker
            except ProcessLookupError:
                pass
            except OSError:
                uncertain = True
            try:
                process.wait(timeout=5)
            except (subprocess.TimeoutExpired, OSError):
                uncertain = True
        require(not uncertain, 'PROCESS_CLEANUP_UNCERTAIN')


def _capture(argv, deadline, clock, limit=8192):
    data = bytearray()
    stream = _stream_process(argv, deadline, clock)
    try:
        for chunk in stream:
            require(len(data) + len(chunk) <= limit, 'TOOL_OUTPUT')
            data.extend(chunk)
    finally:
        stream.close()
    return bytes(data)


class CurlTransport:
    def __init__(self, clock=time.monotonic):
        self.clock = clock

    def fetch(self, url, make_sink, limit, deadline):
        from mint_media_console import redirected_url
        require(url.startswith(BASE), 'URL')
        redirected_url(url, url)
        require(url[len(BASE):] in {'sha256sum.txt', 'sha256sum.txt.gpg', ISO}, 'URL')
        left = deadline - self.clock(); require(left > 0, 'TRANSFER_DEADLINE')
        argv = ['/usr/bin/curl', '--disable', '--silent', '--show-error', '--http1.1', '--globoff',
                '--proto', '=https', '--proto-redir', '=https', '--connect-timeout', '20',
                '--max-time', str(min(left, 900)), '--retry', '0', '--max-redirs', '0',
                '--include', '--suppress-connect-headers', url]
        stream = _stream_process(argv, deadline, self.clock)
        header = bytearray(); sink = None; status = None; interim = 0; expected_length = None
        try:
            for chunk in stream:
                if status is None:
                    header.extend(chunk)
                    while b'\r\n\r\n' in header:
                        prefix, body = bytes(header).split(b'\r\n\r\n', 1)
                        require(len(prefix) <= 16384, 'HTTP_HEADERS')
                        lines = prefix.split(b'\r\n')
                        first = lines.pop(0).split(b' ', 2)
                        require(len(first) >= 2 and first[0] == b'HTTP/1.1'
                                and len(first[1]) == 3 and first[1].isdigit(), 'HTTP_HEADERS')
                        code = int(first[1])
                        if 100 <= code < 200:
                            interim += 1; require(interim <= 3 and code != 101, 'HTTP_HEADERS')
                            header = bytearray(body); continue
                        headers = {}
                        for line in lines:
                            require(b':' in line and not line.startswith((b' ', b'\t')), 'HTTP_HEADERS')
                            key, value = line.split(b':', 1)
                            key = key.lower()
                            if key in {b'location', b'content-length', b'content-encoding'}:
                                require(key not in headers, 'HTTP_HEADERS')
                                headers[key] = value.strip()
                        if code in {301, 302, 303, 307, 308}:
                            return Transfer(code, headers.get(b'location', b'').decode('ascii'), 0)
                        require(code == 200 and headers.get(b'content-encoding', b'identity') == b'identity', 'HTTP_STATUS')
                        if b'content-length' in headers:
                            require(headers[b'content-length'].isdigit()
                                    and 0 < int(headers[b'content-length']) <= limit, 'HTTP_SIZE')
                            expected_length = int(headers[b'content-length'])
                        status = code; sink = make_sink()
                        if body:
                            sink.write(body)
                        header.clear()
                        break
                    if status is None:
                        require(len(header) <= 16384, 'HTTP_HEADERS')
                else:
                    sink.write(chunk)
            require(status == 200 and sink is not None
                    and (expected_length is None or sink.count == expected_length), 'HTTP_INCOMPLETE')
            return Transfer(200, None, sink.count)
        finally:
            stream.close()


class GpgVerifier:
    def __init__(self, clock=time.monotonic):
        self.clock = clock

    def verify(self, key, sums, signature, workspace, deadline):
        # Inputs were pinned/bounded by core. Fresh snapshots avoid verifying one
        # pathname version then interpreting a replacement metadata file.
        require(type(key) is bytes and sha(key) == KEY_SHA and len(key) <= METADATA_LIMIT, 'KEY_BINDING')
        require(type(sums) is bytes and 0 < len(sums) <= METADATA_LIMIT
                and type(signature) is bytes and 0 < len(signature) <= SIGNATURE_LIMIT, 'METADATA_SIZE')
        home = workspace.gpg_home()
        for name, data in [('key.asc', key), ('sums', sums), ('signature', signature)]:
            path = Path(home)/name
            fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC, 0o600)
            try:
                view = memoryview(data)
                while view:
                    n = os.write(fd, view); require(n > 0, 'SHORT_WRITE'); view = view[n:]
                os.fsync(fd); os.fchmod(fd, 0o400)
            finally:
                os.close(fd)
        common = ['/usr/bin/gpg', '--no-options', '--batch', '--homedir', home,
                  '--no-auto-key-retrieve', '--no-autostart', '--status-fd', '1']
        limit = min(deadline, self.clock()+20)
        _capture(common+['--import', str(Path(home)/'key.asc')], limit, self.clock)
        workspace.audit()
        status = _capture(common+['--verify', str(Path(home)/'signature'), str(Path(home)/'sums')],
                          min(deadline, self.clock()+20), self.clock)
        versions = {}
        for path in ['/usr/bin/gpg', '/usr/bin/curl']:
            args = common + ['--version'] if path.endswith('/gpg') else [path, '--disable', '--version']
            data = _capture(args, min(deadline, self.clock()+5), self.clock)
            first = data.decode('ascii').splitlines()[0]
            require(0 < len(first) <= 256 and first.isprintable(), 'TOOL_VERSION')
            versions[Path(path).name] = first
        workspace.audit()
        return 0, status, versions


def collect_host():
    """Future read-only native preflight; no downloads/processes/VM creation."""
    import fcntl
    uid, euid = os.getuid(), os.geteuid()
    who = pwd.getpwuid(uid)
    require(uid >= 1000 and euid == uid and who.pw_name == 'sde-runner', 'HOST_ACCOUNT')
    groups = [grp.getgrgid(g).gr_name for g in set(os.getgroups()) | {os.getgid()}]
    require(not set(groups) & {'root', 'sudo', 'admin', 'docker', 'lxd', 'libvirt'}, 'HOST_GROUPS')

    def read_root(path, limit):
        resolved = Path(path).resolve(strict=True)
        allowed = {'/etc/linuxmint/info', '/etc/os-release', '/usr/lib/os-release', '/proc/meminfo'}
        require(str(resolved) in allowed, 'HOST_FILE')
        parent = _owned_directory(resolved.parent, 0)
        try:
            fd = os.open(resolved.name, os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC, dir_fd=parent)
        finally:
            os.close(parent)
        try:
            st = os.fstat(fd)
            require(stat.S_ISREG(st.st_mode) and st.st_uid == 0
                    and not stat.S_IMODE(st.st_mode) & 0o022, 'HOST_FILE')
            data = bytearray()
            while len(data) <= limit:
                block = os.read(fd, min(CHUNK, limit+1-len(data)))
                if not block:
                    break
                data.extend(block)
            require(len(data) <= limit, 'HOST_FILE_SIZE')
            return data.decode('ascii')
        finally:
            os.close(fd)

    def fields(text):
        rows = [line.split('=', 1) for line in text.splitlines() if '=' in line]
        require(len({row[0] for row in rows}) == len(rows), 'HOST_METADATA')
        return {key: value.strip('"') for key, value in rows}

    release = fields(read_root('/etc/linuxmint/info', 8192))
    osr = fields(read_root('/etc/os-release', 8192))
    mem = dict(line.split(':', 1) for line in read_root('/proc/meminfo', 65536).splitlines() if ':' in line)
    require(mem.get('MemAvailable', '').strip().endswith(' kB'), 'HOST_MEMORY')
    available = int(mem['MemAvailable'].split()[0])*1024
    import platform
    for tool in ['/usr/bin/curl', '/usr/bin/gpg', '/usr/bin/qemu-system-x86_64', '/usr/bin/qemu-img']:
        if tool in TOOLS:
            _tool(tool)
        else:
            parent = _owned_directory(Path(tool).parent, 0)
            try:
                st = os.stat(Path(tool).name, dir_fd=parent, follow_symlinks=False)
                require(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and st.st_nlink == 1
                        and not stat.S_IMODE(st.st_mode) & 0o022, 'HOST_TOOLS')
            finally:
                os.close(parent)
    homefd = _owned_directory(who.pw_dir, uid)
    try:
        disk = os.fstatvfs(homefd)
    finally:
        os.close(homefd)
    fd = os.open('/dev/kvm', os.O_RDWR|os.O_CLOEXEC|os.O_NOFOLLOW)
    try:
        api = fcntl.ioctl(fd, 0xAE00, 0)
    finally:
        os.close(fd)
    facts = {'account': who.pw_name, 'uid': uid, 'euid': euid, 'groups': groups,
             'os': osr.get('ID'), 'release': release.get('RELEASE'), 'arch': platform.machine(),
             'kvm_api': api, 'trusted_tools': True, 'available_memory': available,
             'available_disk': disk.f_bavail*disk.f_frsize}
    from mint_media_console import host_gate
    host_gate(facts)
    return facts
