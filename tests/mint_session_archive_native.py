"""Fixed Mint archival ports/controller; no CLI or import-time host operations.

Never call Native.open/execute during mocked CI. Remote controls are owner
attestations supplied by the separately authorized controller, not API proof.
No recursive traversal, delete, chmod/chown, process launch or recovery executor.
"""
import ctypes
import grp
import json
import os
import pwd
import select
import signal
import stat
import sys
import time

import mint_session_archive_plan as plan

SOURCE = plan.SOURCE.rsplit('/', 1)[1]
ARCHIVE = plan.ARCHIVE.rsplit('/', 1)[1]
LEGACY = plan.LEGACY.rsplit('/', 1)[1]
JOURNAL = plan.JOURNAL.rsplit('/', 1)[1]
DEADLINE_SECONDS = 30
PROC_BYTES = 32 * 1024 * 1024
PROC_ENTRIES = 4096


class Stop(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Stop(reason)


def sig(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_gid,
            stat.S_IMODE(info.st_mode), stat.S_IFMT(info.st_mode))


def bind_rename(lib):
    # Exact libc ABI; no guessed syscall number or ordinary-rename fallback.
    fn = lib.renameat2
    fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
                   ctypes.c_uint]
    fn.restype = ctypes.c_int
    return fn


class Native:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.deadline = None
        self.owned = []
        self.home = self.source = self.legacy = self.journal = None
        self.rows = {}
        self.procs = None
        self.pidfds = []
        self.journal_bytes = b''
        self.sequence = 0
        self.read_bytes = 0
        self.stop_requested = False
        self.rename_errno = None

    def check(self):
        need(not self.stop_requested, 'INTERRUPTED')
        need(self.deadline is not None and self.clock() < self.deadline, 'DEADLINE')

    def keep(self, fd):
        self.owned.append(fd)
        return fd

    def close(self, fd):
        self.owned.remove(fd)  # never retry an ambiguously closed descriptor
        os.close(fd)

    def cleanup(self):
        errors = False
        for fd in list(reversed(self.owned)):
            try:
                self.close(fd)
            except (Exception, KeyboardInterrupt):
                errors = True
        need(not errors, 'CLOSE_UNCERTAIN')

    def directory(self, name, parent=None):
        self.check()
        return self.keep(os.open(name, os.O_RDONLY | os.O_DIRECTORY |
                                 os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent))

    def row(self, fd, uid, mode, acl=True):
        self.check()
        info = os.fstat(fd)
        need(stat.S_ISDIR(info.st_mode) and info.st_uid == uid and
             stat.S_IMODE(info.st_mode) == mode, 'DIRECTORY_OWNER')
        default = None
        if acl:
            attrs = os.listxattr(fd)
            need(len(attrs) <= 64 and all(len(a) <= 255 for a in attrs), 'ACL_BOUND')
            default = 'system.posix_acl_default' in attrs
            need(not default, 'DEFAULT_ACL')
        return dict(kind='directory', uid=uid, mode=format(mode, '04o'),
                    device=info.st_dev, inode=info.st_ino, defaultAcl=default)

    def absent(self, parent, name):
        self.check()
        try:
            os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return
        raise Stop('PATH_EXISTS')

    def local_registration_absent(self):
        for name in ('.runner', '.credentials', '.credentials_rsaparams', '.service'):
            self.absent(self.source, name)

    def read_proc(self, parent, name, limit):
        self.check()
        fd = self.keep(os.open(name, os.O_RDONLY | os.O_NOFOLLOW |
                               os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=parent))
        try:
            raw = os.read(fd, limit + 1)
            self.read_bytes += len(raw)
            need(0 < len(raw) <= limit and self.read_bytes <= PROC_BYTES, 'PROC_BOUND')
            self.check()
            return raw
        finally:
            self.close(fd)

    def process_scan(self, proc):
        result = {}
        with os.scandir(proc) as entries:
            count = 0
            for entry in entries:
                self.check()
                count += 1
                need(count <= PROC_ENTRIES, 'PROC_COUNT')
                name = entry.name
                if not name.isascii() or not name.isdecimal():
                    continue
                need(0 < len(name) <= 10, 'PROC_PID')
                fd = self.directory(name, proc)
                try:
                    status = self.read_proc(fd, 'status', 16384)
                    lines = [r.split()[1:] for r in status.splitlines() if r.startswith(b'Uid:')]
                    need(len(lines) == 1 and len(lines[0]) == 4, 'PROC_UID')
                    uids = tuple(int(x) for x in lines[0])
                    if 1001 not in uids:
                        continue
                    need(uids == (1001,) * 4, 'PROC_UID')
                    threads = [r.split()[1:] for r in status.splitlines()
                               if r.startswith(b'Threads:')]
                    need(threads == [[b'1']], 'ACCOUNT_THREADS')
                    for label in (b'CapInh:', b'CapPrm:', b'CapEff:', b'CapAmb:'):
                        values = [r.split()[1:] for r in status.splitlines()
                                  if r.startswith(label)]
                        need(len(values) == 1 and len(values[0]) == 1 and
                             len(values[0][0]) <= 16 and int(values[0][0], 16) == 0,
                             'ACCOUNT_CAPABILITIES')
                    raw = self.read_proc(fd, 'stat', 8192)
                    tail = raw[raw.rfind(b')') + 1:].split()
                    need(b')' in raw and raw.startswith(name.encode() + b' (') and len(tail) >= 20,
                         'PROC_STAT')
                    ppid, started = int(tail[1]), int(tail[19])
                    need(started > 0, 'PROC_STAT')
                    result[int(name)] = (ppid, started)
                    need(len(result) <= 16, 'ACCOUNT_PROCESS_BOUND')
                finally:
                    self.close(fd)
        return result

    def quiescence(self):
        self.check()
        proc = self.directory('/proc')
        try:
            first = self.process_scan(proc)
            need(first == self.process_scan(proc), 'PROCESS_CHANGED')
            # Only the inspector and its identified controller ancestors may exist.
            current = os.getpid()
            allowed = set()
            while current in first and current not in allowed:
                allowed.add(current)
                current = first[current][0]
            need(os.getpid() in first and set(first) == allowed, 'ACCOUNT_NOT_QUIESCENT')
            if self.procs is None:
                for pid in sorted(first):
                    fd = self.keep(os.pidfd_open(pid, 0))
                    self.pidfds.append(fd)
                # Recheck after pidfd acquisition; PID reuse is not enrollment.
                need(first == self.process_scan(proc), 'PROCESS_CHANGED')
                self.procs = first
            need(first == self.procs, 'CONTROLLER_CHANGED')
            for fd in self.pidfds:
                poll = select.poll()
                poll.register(fd, select.POLLIN)
                need(not poll.poll(0), 'CONTROLLER_EXITED')
        finally:
            self.close(proc)

    def open(self):
        need(self.deadline is None and not self.owned, 'INSTANCE_REUSED')
        self.deadline = self.clock() + DEADLINE_SECONDS
        need(os.getuid() == os.geteuid() == 1001, 'ACCOUNT')
        need(sys.platform == 'linux', 'PLATFORM')
        user = pwd.getpwuid(1001)
        need(user.pw_name == 'sde-runner' and user.pw_dir == plan.HOME, 'ACCOUNT')
        groups = sorted({grp.getgrgid(g).gr_name for g in set(os.getgroups()) | {os.getgid()}})
        need(groups == ['kvm', 'sde-runner', 'users'], 'GROUPS')
        # Binding availability is preflight; actual kernel support is proven only
        # by the authorized rename call. ENOSYS/EINVAL/EOPNOTSUPP stops, no probe.
        self.started = self.clock()
        self.rename = bind_rename(ctypes.CDLL(None, use_errno=True))
        root = self.directory('/')
        home_parent = self.directory('home', root)
        self.home = self.directory('sde-runner', home_parent)
        self.source = self.directory(SOURCE, self.home)
        self.legacy = self.directory(LEGACY, self.home)
        self.rows = {'/': self.row(root, 0, 0o755),
                     '/home': self.row(home_parent, 0, 0o755),
                     plan.HOME: self.row(self.home, 1001, 0o750),
                     plan.SOURCE: self.row(self.source, 1001, 0o700),
                     plan.LEGACY: self.row(self.legacy, 1001, 0o700, acl=False)}
        self.pinned = [(None, '/', root), (root, 'home', home_parent),
                       (home_parent, 'sde-runner', self.home),
                       (self.home, SOURCE, self.source), (self.home, LEGACY, self.legacy)]
        self.signatures = {fd: sig(os.fstat(fd)) for _, _, fd in self.pinned}
        self.quiescence()
        self.local_registration_absent()
        self.absent(self.home, ARCHIVE)
        self.absent(self.home, JOURNAL)

    def observation(self, remote):
        self.check()
        need(type(remote) is dict and set(remote) == {
            'activationDisabled', 'remoteRunnerAbsent', 'noQueuedOrActiveJobs'}, 'REMOTE_FIELDS')
        need(all(v is True for v in remote.values()), 'REMOTE_GATES')
        return dict(schema=1, account='sde-runner', uid=1001, euid=1001,
                    home=plan.HOME, groups=['kvm', 'sde-runner', 'users'],
                    **remote, dedicatedAccountQuiescent=True, localRegistrationAbsent=True,
                    scanComplete=True, scanStable=True, scanSeconds=self.clock() - self.started,
                    archiveAbsent=True, journalAbsent=True, noReplaceRenameAvailable=True,
                    sameFilesystem=True, directories=self.rows,
                    controllerProcesses=[dict(pid=pid, parent=value[0], startTimeTicks=value[1])
                                         for pid, value in sorted(self.procs.items())])

    def revalidate(self, archived=False, journal=False):
        self.check()
        self.quiescence()
        for parent, name, fd in self.pinned:
            if fd == self.source and archived:
                name = ARCHIVE
            actual = os.stat(name, dir_fd=parent, follow_symlinks=False)
            need(sig(actual) == self.signatures[fd] == sig(os.fstat(fd)), 'PATH_CHANGED')
            # ACL inheritance can change while modes stay fixed.
            if fd != self.legacy:
                self.row(fd, actual.st_uid, stat.S_IMODE(actual.st_mode))
        self.local_registration_absent()
        if not archived:
            self.absent(self.home, ARCHIVE)
        if journal:
            self.journal_info()
        else:
            self.absent(self.home, JOURNAL)

    def create_journal(self):
        self.check()
        self.absent(self.home, JOURNAL)
        self.journal = self.keep(os.open(JOURNAL, os.O_RDWR | os.O_APPEND |
            os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=self.home))
        self.journal_signature = sig(os.fstat(self.journal))
        self.journal_info()
        os.fsync(self.home)

    def journal_info(self):
        self.check()
        info = os.fstat(self.journal)
        linked = os.stat(JOURNAL, dir_fd=self.home, follow_symlinks=False)
        need(stat.S_ISREG(info.st_mode) and info.st_uid == 1001 and
             stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1 and
             linked.st_nlink == 1 and sig(info) == sig(linked) == self.journal_signature and
             info.st_size == len(self.journal_bytes), 'JOURNAL_CHANGED')
        need(os.pread(self.journal, plan.RECORD_LIMIT + 1, 0) == self.journal_bytes,
             'JOURNAL_READBACK')

    def record(self, phase, data):
        self.journal_info()
        record = dict(sequence=self.sequence, phase=phase, runId='39132131036',
                      sourceIdentity=list(plan.IDENTITY), data=data)
        raw = json.dumps(record, sort_keys=True, ensure_ascii=True).encode('ascii') + b'\n'
        need(len(self.journal_bytes) + len(raw) <= plan.RECORD_LIMIT, 'JOURNAL_BOUND')
        need(os.write(self.journal, raw) == len(raw), 'JOURNAL_SHORT_WRITE')
        self.journal_bytes += raw
        os.fsync(self.journal)
        self.journal_info()
        need(os.pread(self.journal, plan.RECORD_LIMIT + 1, 0) == self.journal_bytes,
             'JOURNAL_READBACK')
        self.sequence += 1
        self.check()

    def rename_source(self):
        self.check()
        ctypes.set_errno(0)
        result = self.rename(self.home, SOURCE.encode('ascii'), self.home,
                             ARCHIVE.encode('ascii'), 1)  # RENAME_NOREPLACE
        self.rename_errno = ctypes.get_errno()
        need(result == 0, 'RENAME_STOP')  # no retry/fallback regardless of errno
        os.fsync(self.home)

    def verify_archive(self):
        self.revalidate(archived=True, journal=True)
        self.absent(self.home, SOURCE)

    def create_directory(self, name, parent):
        self.check()
        os.mkdir(name, 0o700, dir_fd=parent)  # exclusive; never exist_ok
        fd = self.directory(name, parent)
        self.row(fd, 1001, 0o700)
        os.fsync(fd)
        os.fsync(parent)
        return fd

    def create_source(self):
        self.verify_archive()
        self.fresh = self.create_directory(SOURCE, self.home)
        need(sig(os.fstat(self.fresh))[:2] != plan.IDENTITY, 'FRESH_IDENTITY')
        return list(sig(os.fstat(self.fresh))[:2])

    def create_work(self):
        self.revalidate(archived=True, journal=True)
        need(sig(os.stat(SOURCE, dir_fd=self.home, follow_symlinks=False)) ==
             sig(os.fstat(self.fresh)), 'FRESH_PATH_CHANGED')
        self.work = self.create_directory('_work-private', self.fresh)
        return list(sig(os.fstat(self.work))[:2])

    def verify_fresh(self):
        self.revalidate(archived=True, journal=True)
        self.row(self.fresh, 1001, 0o700)
        self.row(self.work, 1001, 0o700)
        for parent, name, fd in ((self.home, SOURCE, self.fresh),
                                 (self.fresh, '_work-private', self.work)):
            need(sig(os.stat(name, dir_fd=parent, follow_symlinks=False)) == sig(os.fstat(fd)),
                 'FRESH_PATH_CHANGED')
        with os.scandir(self.fresh) as entries:
            first = next(entries, None)
            need(first is not None and first.name == '_work-private' and
                 next(entries, None) is None, 'FRESH_NOT_EMPTY')
        with os.scandir(self.work) as entries:
            need(next(entries, None) is None, 'WORK_NOT_EMPTY')


def execute(ports, gates, *, authorized=False):
    """Explicit injected entrypoint, no CLI. Never execute for local mocked QA.

    gates must supply newly verified remote-control attestations on each call.
    No GitHub API, activation setter, runner command or process killer exists.
    """
    phase = 'not-started'
    passed = False
    reason = 'NOT_AUTHORIZED'
    old_mask = None
    handlers = []
    cleanup_status = dict(descriptors='NotAttempted', umask='Unchanged', signals='Unchanged')
    opened = False
    ready = False
    requested = False

    def checkpoint():
        need(not requested, 'INTERRUPTED')
        if ready:
            ports.check()

    def perform(method, *args, **kwargs):
        checkpoint()
        result = method(*args, **kwargs)
        checkpoint()
        return result

    try:
        need(authorized is True, 'NOT_AUTHORIZED')
        def interrupted(signum, frame):
            # Do not raise between a successful open and recording its ownership.
            nonlocal requested
            requested = True
            ports.stop_requested = True
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous = signal.getsignal(signum)
            signal.signal(signum, interrupted)
            handlers.append((signum, previous))
        old_mask = os.umask(0o077)
        opened = True
        checkpoint()
        ports.open()
        ready = True
        checkpoint()
        observed = perform(ports.observation, gates())
        prepared = plan.prepare(lambda: observed)
        perform(ports.revalidate)
        phase = 'journal-create-pending'
        perform(ports.create_journal)
        perform(ports.record, 'prepared', {'plan': prepared, 'observation': observed})
        phase = 'prepared'
        perform(ports.record, 'rename-pending', {})
        phase = 'rename-pending'
        perform(ports.revalidate, journal=True)
        # Re-attest after the potentially slow process/path scan, immediately
        # before the only rename. These facts are explicit attestations, not IPC.
        remote = gates()
        need(type(remote) is dict and set(remote) == {
            'activationDisabled', 'remoteRunnerAbsent', 'noQueuedOrActiveJobs'} and
             all(v is True for v in remote.values()), 'REMOTE_GATES')
        perform(ports.rename_source)
        perform(ports.verify_archive)
        perform(ports.record, 'archived', {})
        phase = 'archived'
        perform(ports.record, 'source-create-pending', {})
        phase = 'source-create-pending'
        fresh = perform(ports.create_source)
        perform(ports.record, 'source-created', {'identity': fresh})
        phase = 'source-created'
        perform(ports.record, 'work-create-pending', {})
        phase = 'work-create-pending'
        work = perform(ports.create_work)
        perform(ports.record, 'work-created', {'identity': work})
        phase = 'work-created'
        perform(ports.verify_fresh)
        perform(ports.record, 'complete', {'fresh': fresh, 'work': work})
        phase = 'complete'
        passed = True
        reason = 'SETUP_RECORDED'
    except (Exception, KeyboardInterrupt) as error:
        reason = str(error) if isinstance(error, Stop) else 'ARCHIVE_STOPPED'
    finally:
        try:
            if opened:
                ports.cleanup()
                cleanup_status['descriptors'] = 'ClosedAsReported'
        except (Exception, KeyboardInterrupt):
            passed = False
            reason = 'CLOSE_UNCERTAIN'
            cleanup_status['descriptors'] = 'Uncertain'
        if old_mask is not None:
            try:
                os.umask(old_mask)
                cleanup_status['umask'] = 'Restored'
            except (Exception, KeyboardInterrupt):
                passed = False
                reason = 'UMASK_RESTORE_UNCERTAIN'
                cleanup_status['umask'] = 'Uncertain'
        if handlers:
            cleanup_status['signals'] = 'Restored'
        for signum, previous in reversed(handlers):
            try:
                signal.signal(signum, previous)
            except (Exception, KeyboardInterrupt):
                passed = False
                reason = 'SIGNAL_RESTORE_UNCERTAIN'
                cleanup_status['signals'] = 'Uncertain'
        if passed:
            try:
                ports.check()
            except (Exception, KeyboardInterrupt) as error:
                passed = False
                reason = str(error) if isinstance(error, Stop) else 'POSTCHECK_STOP'
    rename_errno = getattr(ports, 'rename_errno', None)
    if type(rename_errno) is not int or not 0 <= rename_errno <= 4095:
        rename_errno = None
    return dict(renameErrno=rename_errno, passed=passed, reason=reason, lastKnownPhase=phase,
                cleanupStatus=cleanup_status,
                nativeValidated=False, authenticationSafety='NotValidated',
                wholeHostCleanupPerformed=False, retryAuthorized=False)
