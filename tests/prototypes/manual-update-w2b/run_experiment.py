"""W2b Linux-only, unprivileged, fixed sentinel/descriptor experiment. No updater."""
from datetime import datetime, timezone
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import select
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time

TIMEOUT = 5
SCRIPT = str(Path(__file__).resolve())


def ensure(condition, message):
    if not condition:
        raise RuntimeError(message)


def inode(st):
    return dict(device=st.st_dev, inode=st.st_ino, uid=st.st_uid,
                mode=oct(stat.S_IMODE(st.st_mode)), regular=stat.S_ISREG(st.st_mode), size=st.st_size)


def privilege():
    caps = next(x.split()[1] for x in Path('/proc/self/status').read_text().splitlines() if x.startswith('CapEff:'))
    return dict(uid=os.getuid(), euid=os.geteuid(), effective_capabilities=caps)


def process_identity(pid):
    text = Path(f'/proc/{pid}/stat').read_text()
    fields = text[text.rindex(')') + 2:].split()
    return dict(pid=pid, ppid=int(fields[1]), start_ticks=int(fields[19]),
                uid=Path(f'/proc/{pid}').stat().st_uid)


def subreaper(value=None):
    libc = ctypes.CDLL(None, use_errno=True)
    if value is None:
        output = ctypes.c_int()
        result = libc.prctl(37, ctypes.byref(output), 0, 0, 0)  # PR_GET_CHILD_SUBREAPER
        ensure(result == 0, f'get subreaper failed errno={ctypes.get_errno()}')
        return output.value
    ensure(libc.prctl(36, int(value), 0, 0, 0) == 0, f'set subreaper failed errno={ctypes.get_errno()}')


def read_message(fd):
    deadline = time.monotonic() + TIMEOUT
    data = bytearray()
    while True:
        remaining = deadline - time.monotonic()
        ensure(remaining > 0 and select.select([fd], [], [], max(0, remaining))[0], 'barrier read timeout')
        chunk = os.read(fd, 1)  # avoid consuming bytes from a subsequent message
        ensure(chunk, 'barrier EOF')
        if chunk == b'\n':
            return json.loads(data)
        data.extend(chunk)
        ensure(len(data) <= 8192, 'barrier message too large')


def write_message(fd, message):
    wire = json.dumps(message, separators=(',', ':')).encode() + b'\n'
    ensure(len(wire) <= 8192, 'barrier message too large')
    # Small trusted fixed messages only; this is not a hardened production IPC adapter.
    os.write(fd, wire)


def regular_descriptors():
    records = []
    for entry in Path('/proc/self/fd').iterdir():
        try:
            st = os.fstat(int(entry.name))
        except OSError:
            continue  # directory enumeration's transient descriptor may be closed
        if stat.S_ISREG(st.st_mode):
            records.append(dict(fd=int(entry.name), identity=inode(st)))
    return records


def direct_children():
    # Some managed /proc implementations omit task/*/children. Read only process
    # identity metadata and select direct children of this single-purpose runner.
    children = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            details = process_identity(int(entry.name))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if details['ppid'] == os.getpid():
            children.append(details['pid'])
    return sorted(children)


def wait_pidfd(fd):
    ensure(select.select([fd], [], [], TIMEOUT)[0], 'process exit timeout')
    status = os.waitid(os.P_PIDFD, fd, os.WEXITED | os.WNOHANG)
    ensure(status is not None, 'pidfd readable but child not reapable')
    return status


def mount_entries(root):
    matches = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        before, after = line.split(' - ', 1)
        fields = before.split()
        mount = fields[4].replace('\\040', ' ')
        if str(root) == mount or str(root).startswith(mount.rstrip('/') + '/'):
            matches.append(dict(mount_point=mount, mount_id=fields[0],
                                options=fields[5], filesystem=after.split()[0]))
    longest = max(len(entry['mount_point']) for entry in matches)
    return [entry for entry in matches if len(entry['mount_point']) == longest]


def sentinel(control_fd, lock_fd):
    try:
        write_message(control_fd, dict(event='sentinel_ready', identity=process_identity(os.getpid()),
                                      privilege=privilege(), lock_fd=lock_fd,
                                      lock_identity=inode(os.fstat(lock_fd)) if lock_fd >= 0 else None,
                                      inheritable=os.get_inheritable(lock_fd) if lock_fd >= 0 else None,
                                      regular_descriptors=regular_descriptors()))
        while True:
            command = read_message(control_fd)['command']
            if command == 'ping':
                write_message(control_fd, dict(event='alive', identity=process_identity(os.getpid()), lock_fd=lock_fd))
            elif command == 'close_descriptor':
                ensure(lock_fd >= 0, 'no inherited descriptor to close')
                os.close(lock_fd)  # deliberately close, do not issue LOCK_UN on the shared description
                lock_fd = -1
                write_message(control_fd, dict(event='descriptor_closed', identity=process_identity(os.getpid())))
            elif command == 'exit':
                write_message(control_fd, dict(event='sentinel_exiting'))
                return
            else:
                raise RuntimeError('unknown fixed sentinel command')
    finally:
        if lock_fd >= 0:
            os.close(lock_fd)
        os.close(control_fd)


def supervisor(mode, lock_path, control_fd):
    fd = os.open(lock_path, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    passed = (control_fd, fd) if mode == 'inherit' else (control_fd,)
    child = subprocess.Popen([sys.executable, '-I', SCRIPT, '--sentinel', str(control_fd),
                              str(fd if mode == 'inherit' else -1)],
                             pass_fds=passed, close_fds=True,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.close(control_fd)
    write_message(1, dict(event='supervisor_ready', identity=process_identity(os.getpid()),
                          privilege=privilege(), child_identity=process_identity(child.pid),
                          lock_identity=inode(os.fstat(fd)), supervisor_lock_fd=fd,
                          supervisor_lock_inheritable=os.get_inheritable(fd), pass_fds=list(passed), close_fds=True))
    signal.pause()  # fixed sentinel supervisor: terminated only through its owned pidfd


class Case:
    def __init__(self, mode, root, report):
        self.mode, self.root, self.report = mode, root, report
        self.supervisor = None
        self.supervisor_pidfd = None
        self.child_pidfd = None
        self.child_identity = None
        self.parent_socket = self.child_socket = None
        self.expected_file = None
        self.expected_root = inode(root.stat(follow_symlinks=False))
        ensure(stat.S_ISDIR(root.stat(follow_symlinks=False).st_mode) and self.expected_root["uid"] == os.geteuid()
               and self.expected_root["mode"] == "0o700", "test root not private/run-owned")
        self.report["root_identity"] = self.expected_root
        self.report["mount_entries"] = mount_entries(root)
        self.runner_start_ticks = process_identity(os.getpid())["start_ticks"]
        self.child_reaped = False
        self.cleanup_errors = []
        self.start = time.monotonic()

    def event(self, event, **data):
        self.report['trace'].append(dict(sequence=len(self.report['trace']) + 1,
                                        elapsed_seconds=time.monotonic() - self.start,
                                        event=event, **data))

    def bind_pidfd(self, expected):
        before = process_identity(expected['pid'])
        ensure(before == expected and before['uid'] == os.geteuid(), 'process identity mismatch before pidfd')
        fd = os.pidfd_open(expected['pid'])
        try:
            ensure(process_identity(expected['pid']) == before, 'process identity changed while binding pidfd')
        except BaseException:
            os.close(fd)
            raise
        self.event('pidfd_bound', identity=before)
        return fd

    def child_message(self, command=None):
        if command:
            self.event('barrier_request', command=command)
            write_message(self.parent_socket.fileno(), dict(command=command))
        reply = read_message(self.parent_socket.fileno())
        self.event('barrier_reply', reply=reply)
        if self.expected_file:
            ensure(inode((self.root / 'O').stat(follow_symlinks=False)) == self.expected_file, 'lock file changed')
        return reply

    def probe(self, expected):
        fd = os.open(self.root / 'O', os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            ensure(inode(os.fstat(fd)) == self.expected_file, 'probe opened wrong lock inode')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                result = 'acquired'
            except BlockingIOError:
                result = 'busy'
            self.event('independent_probe', pid=os.getpid(), result=result, expected=expected,
                       identity=inode(os.fstat(fd)))
            ensure(result == expected, f'probe expected {expected}, got {result}')
        finally:
            os.close(fd)

    def run(self):
        fd = os.open(self.root / 'O', os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        self.expected_file = inode(os.fstat(fd))
        os.close(fd)  # parent never retains the supervisor's open file description
        self.report['lock_before'] = self.expected_file
        self.parent_socket, self.child_socket = socket.socketpair()
        self.supervisor = subprocess.Popen([sys.executable, '-I', SCRIPT, '--supervisor', self.mode,
                                           str(self.root / 'O'), str(self.child_socket.fileno())],
                                          pass_fds=(self.child_socket.fileno(),), close_fds=True,
                                          stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.child_socket.close()
        parent_identity = process_identity(self.supervisor.pid)
        self.supervisor_pidfd = self.bind_pidfd(parent_identity)
        ready = read_message(self.supervisor.stdout.fileno())
        self.event('supervisor_ready', reply=ready)
        ensure(ready['identity'] == parent_identity and parent_identity['ppid'] == os.getpid(), 'supervisor ownership mismatch')
        ensure(ready['lock_identity'] == self.expected_file, 'supervisor opened wrong inode')
        ensure(not ready['supervisor_lock_inheritable'] and ready['close_fds'], 'descriptor defaults changed')
        self.child_identity = ready['child_identity']
        ensure(self.child_identity['ppid'] == self.supervisor.pid, 'sentinel not a child of this supervisor')
        self.child_pidfd = self.bind_pidfd(self.child_identity)
        child_ready = self.child_message()
        ensure(child_ready['event'] == 'sentinel_ready' and child_ready['identity'] == self.child_identity, 'sentinel identity mismatch')
        for details in (ready, child_ready):
            ensure(details['privilege']['euid'] == os.geteuid() and not int(details['privilege']['effective_capabilities'], 16), 'actor not unprivileged')
        inherited = self.mode == 'inherit'
        actual = [record for record in child_ready['regular_descriptors']
                  if record['identity']['device'] == self.expected_file['device']
                  and record['identity']['inode'] == self.expected_file['inode']]
        ensure(len(actual) == int(inherited), 'actual sentinel lock-descriptor inventory mismatch')
        ensure((child_ready['lock_fd'] >= 0) == inherited, 'sentinel descriptor setting mismatch')
        ensure((ready['supervisor_lock_fd'] in ready['pass_fds']) == inherited, 'pass_fds setting mismatch')
        if inherited:
            ensure(child_ready['lock_identity'] == self.expected_file, 'inherited descriptor inode mismatch')
        self.probe('busy')  # establish that the supervisor genuinely owns the lock
        signal.pidfd_send_signal(self.supervisor_pidfd, signal.SIGTERM)
        code = self.supervisor.wait(TIMEOUT)
        ensure(code == -signal.SIGTERM, 'supervisor termination not observed')
        self.event('supervisor_terminated', exitcode=code, pid=self.supervisor.pid)
        alive = self.child_message('ping')
        ensure(alive['event'] == 'alive' and alive['identity']['ppid'] == os.getpid(), 'sentinel did not survive/adopt to runner')
        ensure(alive['identity']['start_ticks'] == self.child_identity['start_ticks'], 'sentinel identity changed')
        self.probe('busy' if inherited else 'acquired')
        ensure(self.child_message('ping')['event'] == 'alive', 'sentinel died during probe')
        if inherited:
            ensure(self.child_message('close_descriptor')['event'] == 'descriptor_closed', 'descriptor not closed')
            self.probe('acquired')
            ensure(self.child_message('ping')['event'] == 'alive', 'close killed sentinel')
        self.report['result'] = 'Pass'

    def reap_child(self):
        status = wait_pidfd(self.child_pidfd)
        self.child_reaped = True
        self.event('sentinel_reaped', pid=status.si_pid, code=status.si_code, status=status.si_status)
        ensure(status.si_code == os.CLD_EXITED and status.si_status == 0, 'sentinel did not exit normally')

    def cleanup(self):
        # Every signal uses a previously bound pidfd, never an unverified numeric PID.
        if self.supervisor is not None:
            try:
                if self.supervisor.poll() is None:
                    ensure(self.supervisor_pidfd is not None, 'no owned supervisor pidfd')
                    self.cleanup_errors.append('fallback supervisor termination')
                    signal.pidfd_send_signal(self.supervisor_pidfd, signal.SIGTERM)
                self.supervisor.wait(TIMEOUT)
            except BaseException as exc:
                self.cleanup_errors.append(f'supervisor: {type(exc).__name__}: {exc}')
        if self.child_pidfd is not None:
            try:
                self.child_message('exit')
                self.reap_child()
            except BaseException as exc:
                self.cleanup_errors.append(f'sentinel: {type(exc).__name__}: {exc}')
                try:
                    if not self.child_reaped:
                        if not select.select([self.child_pidfd], [], [], 0)[0]:
                            signal.pidfd_send_signal(self.child_pidfd, signal.SIGKILL)
                        status = wait_pidfd(self.child_pidfd)
                        self.child_reaped = True
                        self.event('fallback_sentinel_reaped', pid=status.si_pid, code=status.si_code, status=status.si_status)
                except BaseException as fallback:
                    self.cleanup_errors.append(f'sentinel fallback: {type(fallback).__name__}: {fallback}')
        for sock in (self.parent_socket, self.child_socket):
            if sock is not None:
                sock.close()
        if self.supervisor is not None and self.supervisor.stdout:
            self.supervisor.stdout.close()
        for pid in direct_children():
            if self.supervisor is not None and pid == self.supervisor.pid:
                continue
            recovery_fd = None
            try:
                candidate = process_identity(pid)
                ensure(candidate['ppid'] == os.getpid() and candidate['uid'] == os.geteuid()
                       and candidate['start_ticks'] >= self.runner_start_ticks, 'unowned process; no signal')
                recovery_fd = self.bind_pidfd(candidate)
                self.cleanup_errors.append('fallback cleanup of adopted startup/sentinel child')
                if not select.select([recovery_fd], [], [], 0)[0]:
                    signal.pidfd_send_signal(recovery_fd, signal.SIGKILL)
                status = wait_pidfd(recovery_fd)
                self.event('adopted_child_fallback_reaped', pid=status.si_pid, code=status.si_code, status=status.si_status)
            except BaseException as exc:
                self.cleanup_errors.append(f'adopted child: {type(exc).__name__}: {exc}')
            finally:
                if recovery_fd is not None:
                    os.close(recovery_fd)
        for fd in (self.supervisor_pidfd, self.child_pidfd):
            if fd is not None:
                os.close(fd)
        self.report['cleanup'] = dict(supervisor_exited=self.supervisor is None or self.supervisor.returncode is not None,
                                      sentinel_reaped=self.child_reaped, errors=self.cleanup_errors,
                                      remaining_direct_children=direct_children())
        try:
            ensure(self.report['cleanup']['supervisor_exited'] and self.child_reaped
                   and not direct_children(), 'actor termination not proven; preserve root')
            current_root = inode(self.root.stat(follow_symlinks=False))
            ensure(all(current_root[k] == self.expected_root[k] for k in ('device', 'inode', 'uid', 'mode')), 'root identity changed')
            self.report['lock_after'] = inode((self.root / 'O').stat(follow_symlinks=False))
            ensure(self.report['lock_after'] == self.expected_file, 'lock inventory changed; preserve root')
            ensure({p.name for p in self.root.iterdir()} == {'O'}, 'unknown entries; preserve root')
            (self.root / 'O').unlink()
            self.root.rmdir()
            self.report['cleanup']['root_removed'] = not self.root.exists()
        except BaseException as exc:
            self.cleanup_errors.append(f'root: {type(exc).__name__}: {exc}')
        if self.cleanup_errors:
            self.report['result'] = 'Fail'


def main():
    report = dict(experiment='W2b surviving sentinel / descriptor lifetime', result='Not run',
                  started_at_utc=datetime.now(timezone.utc).isoformat(), cases=[], failures=[],
                  evidence_level='L2 Linux primitives only',
                  source_hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},
                  environment=dict(system=platform.system(), kernel=platform.release(), python=platform.python_version()),
                  limits=['One lock and two directed schedules; no production compatibility or universal race/liveness proof.',
                          'Same-UID trusted control pipes; no authenticated IPC, journal, real installer or crash recovery.',
                          'No desktop, Windows/Mint, service, privilege, package, build or release validation. B01-B06 remain open.'])
    original_subreaper = None
    try:
        ensure(sys.platform == 'linux' and hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal'), 'Linux pidfd support required')
        report['environment']['privilege'] = privilege()
        ensure(os.geteuid() != 0 and not int(privilege()['effective_capabilities'], 16), 'unprivileged process required')
        ensure(not direct_children(), 'single-purpose runner must start without existing children')
        report['environment']['os_release'] = next((line.split('=', 1)[1].strip(chr(34))
            for line in Path('/etc/os-release').read_text().splitlines() if line.startswith('PRETTY_NAME=')), 'unknown')
        original_subreaper = subreaper()
        subreaper(True)
        report['subreaper'] = dict(original=original_subreaper, during=subreaper())
        for mode in ('exclude', 'inherit'):
            root = Path(tempfile.mkdtemp(prefix=f'PROTOTYPE-W2b-{mode}-'))
            item = dict(mode=mode, root=str(root), result='Not run', trace=[], failures=[])
            report['cases'].append(item)
            case = Case(mode, root, item)
            try:
                case.run()
            except BaseException as exc:
                item['result'] = 'Fail'
                item['failures'].append(f'{type(exc).__name__}: {exc}')
            finally:
                case.cleanup()
            if item['result'] != 'Pass':
                break
        report['result'] = 'Pass' if len(report['cases']) == 2 and all(c['result'] == 'Pass' for c in report['cases']) else 'Fail'
    except BaseException as exc:
        report['result'] = 'Fail' if report['cases'] else 'Blocked'
        report['failures'].append(f'{type(exc).__name__}: {exc}')
    finally:
        if original_subreaper is not None:
            try:
                subreaper(original_subreaper)
                report['subreaper']['restored'] = subreaper()
                ensure(report['subreaper']['restored'] == original_subreaper, 'subreaper not restored')
            except BaseException as exc:
                report['result'] = 'Fail'
                report['failures'].append(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['result'] == 'Pass' else 1


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--sentinel':
        sentinel(int(sys.argv[2]), int(sys.argv[3]))
    elif len(sys.argv) == 5 and sys.argv[1] == '--supervisor' and sys.argv[2] in ('exclude', 'inherit'):
        supervisor(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    elif len(sys.argv) == 1:
        sys.exit(main())
    else:
        raise SystemExit('fixed W2b modes only')
