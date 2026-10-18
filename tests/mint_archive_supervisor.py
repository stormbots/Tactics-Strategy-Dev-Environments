"""Fixed archival delivery/report/supervision ports. No CLI or import-time I/O.

Never invoke native methods in mocked CI. No downloader, generic command runner,
runner management, recovery or activation writer. Same-UID/root tampering is
outside this local delivery boundary; verify this controller externally first.
"""
import ctypes
import hashlib
import json
import os
import pwd
import select
import signal
import stat
import sys
import time
import types

SOURCE_SHA = '887ebc9485ec2b18064cb9f3515929dd37436e61'
HOME = '/home/sde-runner'
CONTROL = 'mint-archive-control-39132131036'
REPORT = 'supervisor-report.jsonl'
PINS = {
    'mint_session_archive_plan': 'ae5cbb7766e6aec5fc29d31e4685100cb1a244e214c94e236eef8c4ef266664a',
    'mint_session_archive_native': '5eefa2077f47ee28d035c446b9fc0a4b69af6dd1879df2870228c951c711d292',
}
FILE_LIMIT = 128 * 1024
LIMIT = 16 * 1024
WALL = 35
GRACE = 2


class Stop(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Stop(reason)


SAFE_REASONS = {
    'ACCOUNT',
    'ARM_STOP',
    'BUNDLE_DIGEST',
    'BUNDLE_FILES',
    'CHILD_OUTPUT_DEADLINE',
    'CHILD_OUTPUT_STOP',
    'CHILD_UNCONFIRMED',
    'DELIVERY_ACL',
    'DELIVERY_CHANGED',
    'DELIVERY_CLOSE',
    'DELIVERY_FILE',
    'DELIVERY_OWNER',
    'DELIVERY_PATH_CHANGED',
    'EXPORT_BOUND',
    'HELPER_PRELOADED',
    'IDENTITY_OUTCOME',
    'IDENTITY_SCHEMA',
    'INTERRUPTED',
    'NOT_ARMED',
    'NOT_AUTHORIZED',
    'NOT_STARTED',
    'OUTPUT_BOUND',
    'PARENT_CHANGED',
    'PIDFD_UNSUPPORTED',
    'PROCESS_CLOSE',
    'REPORT_BOUND',
    'REPORT_CHANGED',
    'REPORT_READBACK',
    'REPORT_SHORT_WRITE',
    'RESULT_BOUND',
    'RESULT_CLEANUP',
    'RESULT_DUPLICATE',
    'RESULT_ERRNO',
    'RESULT_PASS',
    'RESULT_SCHEMA',
    'RESULT_TEXT',
    'SIGCHLD_POLICY',
    'START_STOP',
    'TERMINATION_SCHEMA',
    'WAIT_IDENTITY',
    'WORKER_EXIT',
    'WORKER_TIMEOUT',
}


def safe_reason(error):
    args = error.args
    if (type(error) is Stop and len(args) == 1 and type(args[0]) is str and
            args[0] in SAFE_REASONS):
        return args[0]
    return 'SUPERVISOR_STOPPED'


def signature(s):
    return (s.st_dev, s.st_ino, s.st_uid, s.st_mode, s.st_nlink,
            s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def verify_bundle(snapshots):
    need(type(snapshots) is dict and set(snapshots) == set(PINS), 'BUNDLE_FILES')
    for name, digest in PINS.items():
        raw = snapshots[name]
        need(type(raw) is bytes and 0 < len(raw) <= FILE_LIMIT and
             hashlib.sha256(raw).hexdigest() == digest, 'BUNDLE_DIGEST')


def validate_result(raw):
    need(type(raw) is bytes and 0 < len(raw) <= LIMIT, 'RESULT_BOUND')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, 'RESULT_DUPLICATE')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    keys = {'renameErrno', 'passed', 'reason', 'lastKnownPhase', 'cleanupStatus',
            'nativeValidated', 'authenticationSafety', 'wholeHostCleanupPerformed', 'retryAuthorized'}
    need(type(value) is dict and set(value) == keys and
         type(value['passed']) is bool and value['nativeValidated'] is False and
         value['authenticationSafety'] == 'NotValidated' and
         value['wholeHostCleanupPerformed'] is False and value['retryAuthorized'] is False,
         'RESULT_SCHEMA')
    for key in ('reason', 'lastKnownPhase'):
        need(type(value[key]) is str and 0 < len(value[key]) <= 64 and
             value[key].isascii() and all(c.isalnum() or c in '_-' for c in value[key]), 'RESULT_TEXT')
    status = value['cleanupStatus']
    need(type(status) is dict and set(status) == {'descriptors','umask','signals'}, 'RESULT_CLEANUP')
    need(status['descriptors'] in ('NotAttempted','ClosedAsReported','Uncertain') and
         status['umask'] in ('Unchanged','Restored','Uncertain') and
         status['signals'] in ('Unchanged','Restored','Uncertain'), 'RESULT_CLEANUP')
    error = value['renameErrno']
    need(error is None or type(error) is int and 0 <= error <= 4095, 'RESULT_ERRNO')
    if value['passed']:
        need(value['reason'] == 'SETUP_RECORDED' and value['lastKnownPhase'] == 'complete' and
             status == dict(descriptors='ClosedAsReported', umask='Restored', signals='Restored') and
             error == 0, 'RESULT_PASS')
    return value


def arm_parent_death(parent_pid):
    # Fixed Linux prctl ABI, applied only in the child before its arm barrier.
    prctl=ctypes.CDLL(None,use_errno=True).prctl
    prctl.argtypes=[ctypes.c_int]+[ctypes.c_ulong]*4
    prctl.restype=ctypes.c_int
    need(prctl(1,signal.SIGKILL,0,0,0) == 0 and
         os.getppid() == parent_pid,'PARENT_CHANGED')


def worker(snapshots, gates):
    """Run only in the supervised child; execute exactly verified immutable bytes."""
    verify_bundle(snapshots)
    need(not set(PINS) & set(sys.modules), 'HELPER_PRELOADED')
    loaded = []
    try:
        for name in PINS:
            module = types.ModuleType(name)
            module.__file__ = '<verified-archive/' + name + '.py>'
            sys.modules[name] = module
            loaded.append(name)
            exec(compile(snapshots[name], module.__file__, 'exec'), module.__dict__)
        native = sys.modules['mint_session_archive_native']
        result = native.execute(native.Native(), gates, authorized=True)
        raw = json.dumps(result, sort_keys=True, ensure_ascii=True).encode('ascii')
        validate_result(raw)
        return raw
    finally:
        for name in reversed(loaded):
            del sys.modules[name]


class Delivery:
    def __init__(self):
        self.owned = []
        self.content = b''
        self.close_uncertain = False
        self.pinned = []

    def keep(self, fd):
        self.owned.append(fd)
        return fd

    def close(self, fd):
        self.owned.remove(fd)
        try:
            os.close(fd)
        except Exception:
            self.close_uncertain = True
            raise

    def cleanup(self):
        failed = self.close_uncertain
        for fd in reversed(self.owned[:]):
            try:
                self.close(fd)
            except Exception:
                failed = True
        need(not failed, 'DELIVERY_CLOSE')

    def open(self):
        need(sys.platform == 'linux' and os.getuid() == os.geteuid() == 1001, 'ACCOUNT')
        who = pwd.getpwuid(1001)
        need(who.pw_name == 'sde-runner' and who.pw_dir == HOME, 'ACCOUNT')
        parent = None
        for name, uid, mode in (('/',0,0o755), ('home',0,0o755),
                                ('sde-runner',1001,0o750), (CONTROL,1001,0o700)):
            previous = parent
            parent = self.keep(os.open(name, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,
                                       dir_fd=parent))
            s = os.fstat(parent)
            need(stat.S_ISDIR(s.st_mode) and s.st_uid == uid and
                 stat.S_IMODE(s.st_mode) == mode, 'DELIVERY_OWNER')
            self.pinned.append((previous,name,parent,(s.st_dev,s.st_ino,s.st_uid,s.st_mode)))
        self.control = parent
        need('system.posix_acl_default' not in os.listxattr(parent), 'DELIVERY_ACL')
        self.control_identity = os.fstat(parent)

    def validate_paths(self):
        for parent,name,fd,expected in self.pinned:
            linked=os.stat(name,dir_fd=parent,follow_symlinks=False)
            actual=os.fstat(fd)
            need((linked.st_dev,linked.st_ino,linked.st_uid,linked.st_mode) == expected ==
                 (actual.st_dev,actual.st_ino,actual.st_uid,actual.st_mode),'DELIVERY_PATH_CHANGED')

    def snapshots(self):
        self.validate_paths()
        result = {}
        for name in PINS:
            fd = self.keep(os.open(name+'.py', os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_NOCTTY|os.O_CLOEXEC,
                                   dir_fd=self.control))
            try:
                before = os.fstat(fd)
                need(stat.S_ISREG(before.st_mode) and before.st_uid == 1001 and
                     stat.S_IMODE(before.st_mode) == 0o600 and before.st_nlink == 1 and
                     0 < before.st_size <= FILE_LIMIT, 'DELIVERY_FILE')
                raw = bytearray()
                while len(raw) <= FILE_LIMIT:
                    part = os.read(fd, min(65536, FILE_LIMIT+1-len(raw)))
                    if not part:
                        break
                    raw.extend(part)
                need(len(raw) == before.st_size and signature(os.fstat(fd)) == signature(before),
                     'DELIVERY_CHANGED')
                result[name] = bytes(raw)
            finally:
                self.close(fd)
        verify_bundle(result)
        return result

    def create_report(self):
        self.validate_paths()
        self.report = self.keep(os.open(REPORT, os.O_RDWR|os.O_APPEND|os.O_CREAT|os.O_EXCL|
                                        os.O_NOFOLLOW|os.O_CLOEXEC, 0o600, dir_fd=self.control))
        self.report_identity = os.fstat(self.report)
        os.fsync(self.control)

    def persist(self, value):
        self.validate_paths()
        raw = json.dumps(value, sort_keys=True, ensure_ascii=True).encode('ascii') + b'\n'
        need(len(self.content)+len(raw) <= LIMIT, 'REPORT_BOUND')
        s = os.fstat(self.report)
        linked = os.stat(REPORT, dir_fd=self.control, follow_symlinks=False)
        need(stat.S_ISREG(s.st_mode) and s.st_uid == 1001 and stat.S_IMODE(s.st_mode) == 0o600 and
             stat.S_ISREG(linked.st_mode) and linked.st_uid == 1001 and
             stat.S_IMODE(linked.st_mode) == 0o600 and s.st_nlink == linked.st_nlink == 1 and
             (s.st_dev,s.st_ino) == (linked.st_dev,linked.st_ino) ==
             (self.report_identity.st_dev,self.report_identity.st_ino) and
             s.st_size == len(self.content) and
             os.pread(self.report,LIMIT+1,0) == self.content, 'REPORT_CHANGED')
        need(os.write(self.report,raw) == len(raw), 'REPORT_SHORT_WRITE')
        self.content += raw
        os.fsync(self.report)
        need(os.pread(self.report,LIMIT+1,0) == self.content, 'REPORT_READBACK')


class Process:
    """One fork, fixed verified worker, pidfd-only signaling; no generic command."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.owned = []
        self.pid = self.pidfd = self.barrier = self.result = None
        self.status = None
        self.armed = False
        self.stop_requested = False
        self.deadline = None
        self.close_uncertain = False

    def keep(self, fd):
        self.owned.append(fd)
        return fd

    def close(self, fd):
        self.owned.remove(fd)
        try:
            os.close(fd)
        except Exception:
            self.close_uncertain = True
            raise

    def start(self, snapshots, gates, inherited):
        need(self.pid is None and hasattr(os,'pidfd_open') and
             hasattr(signal,'pidfd_send_signal'), 'PIDFD_UNSUPPORTED')
        need(signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL,'SIGCHLD_POLICY')
        verify_bundle(snapshots)
        self.deadline = self.clock()+WALL
        parent_pid = os.getpid()
        read, write = os.pipe2(os.O_CLOEXEC)
        self.keep(read);self.keep(write)
        out, send = os.pipe2(os.O_CLOEXEC|os.O_NONBLOCK)
        self.keep(out);self.keep(send)
        self.pid = os.fork()
        if self.pid == 0:
            # Parent barrier EOF means no execution. No native helper before arm.
            try:
                signal.signal(signal.SIGTERM,signal.SIG_DFL)
                signal.signal(signal.SIGINT,signal.SIG_DFL)
                arm_parent_death(parent_pid)
                for fd in (write,out,*inherited):
                    os.close(fd)
                need(os.read(read,1) == b'A', 'NOT_ARMED')
                os.close(read)
                raw = worker(snapshots,gates)
                deadline = self.clock()+GRACE
                while raw:
                    need(self.clock() < deadline, 'CHILD_OUTPUT_DEADLINE')
                    poll = select.poll();poll.register(send,select.POLLOUT)
                    if not poll.poll(50):
                        continue
                    try:
                        size = os.write(send,raw)
                    except BlockingIOError:
                        continue
                    need(size > 0, 'CHILD_OUTPUT_STOP')
                    raw = raw[size:]
                os.close(send)
                os._exit(0)
            except BaseException:
                os._exit(1)  # no raw exception/tool output on any channel
        self.barrier = write;self.result = out
        self.close(read);self.close(send)
        self.pidfd = self.keep(os.pidfd_open(self.pid,0))
        # Child may exit early, but cannot start native work before arm. Default
        # SIGCHLD policy keeps an exited child unreaped until our own waitpid.
        need(not self.stop_requested and self.clock() < self.deadline,'START_STOP')
        need(os.write(write,b'A') == 1, 'ARM_STOP')
        self.armed = True
        self.barrier = None
        self.close(write)

    def exited(self):
        if self.status is None:
            pid, status = os.waitpid(self.pid,os.WNOHANG)
            if pid:
                need(pid == self.pid,'WAIT_IDENTITY')
                self.status = status
        return self.status is not None

    def collect(self):
        need(self.deadline is not None,'NOT_STARTED')
        data = bytearray();eof = False
        while self.clock() < self.deadline:
            need(not self.stop_requested,'INTERRUPTED')
            if not eof:
                try:
                    part = os.read(self.result,LIMIT+1-len(data))
                    if part:
                        data.extend(part);need(len(data) <= LIMIT,'OUTPUT_BOUND')
                    else:
                        eof = True
                except BlockingIOError:
                    pass
            if self.exited() and eof:
                need(os.WIFEXITED(self.status) and os.WEXITSTATUS(self.status) == 0,'WORKER_EXIT')
                return validate_result(bytes(data))
            poll=select.poll();poll.register(self.pidfd if eof else self.result,
                                             select.POLLIN|select.POLLHUP)
            poll.poll(50)
        raise Stop('WORKER_TIMEOUT')

    def stop(self):
        # Closing an unarmed barrier prevents work even if pidfd acquisition failed.
        if self.barrier is not None:
            fd=self.barrier;self.barrier=None
            try:
                self.close(fd)
            except Exception:
                # Preserve close uncertainty, but still terminate by retained pidfd.
                self.close_uncertain=True
        if self.pid is None:
            return 'NotStarted'
        if self.exited():
            return 'ReapedAsReported'
        need(self.pidfd is not None,'CHILD_UNCONFIRMED')
        for signum in (signal.SIGTERM,signal.SIGKILL):
            try:
                signal.pidfd_send_signal(self.pidfd,signum,None,0)
            except ProcessLookupError:
                pass
            deadline=self.clock()+GRACE
            while self.clock() < deadline:
                if self.exited():
                    return 'ReapedAsReported'
                poll=select.poll();poll.register(self.pidfd,select.POLLIN);poll.poll(50)
        raise Stop('CHILD_UNCONFIRMED')

    def evidence(self):
        return dict(pid=self.pid,armed=self.armed,pidfdRetained=self.pidfd in self.owned,
                    reaped=self.status is not None)

    def cleanup(self):
        failed=self.close_uncertain
        for fd in reversed(self.owned[:]):
            try:
                self.close(fd)
            except Exception:
                failed=True
        need(not failed,'PROCESS_CLOSE')


def supervise(delivery, process, gates, *, authorized=False):
    """Explicit injected entrypoint only. Native execution remains unauthorized."""
    report = dict(kind='archive-supervision',passed=False,reason='NOT_AUTHORIZED',
                  helperSourceSha=SOURCE_SHA,helpersSha256=dict(PINS),worker=None,
                  childTermination='NotStarted',childIdentity=None,reportPersistence='NotAttempted',
                  nativeValidated=False,wholeHostCleanupPerformed=False,retryAuthorized=False,
                  returnedAfterCloseout=False,
                  cleanupStatus=dict(processDescriptors='NotAttempted',deliveryDescriptors='NotAttempted',
                                     umask='Unchanged',signals='Unchanged'))
    opened=False;started=False;initial_recorded=False;report_attempted=False;old=None;handlers=[];requested=False
    def interrupted(signum,frame):
        nonlocal requested
        requested=True
        process.stop_requested=True
    def checkpoint():
        need(not requested,'INTERRUPTED')
    try:
        need(authorized is True,'NOT_AUTHORIZED')
        for signum in (signal.SIGTERM,signal.SIGINT):
            previous=signal.getsignal(signum)
            signal.signal(signum,interrupted)
            handlers.append((signum,previous))
        old=os.umask(0o077)
        opened=True;delivery.open()
        checkpoint()
        snapshots=delivery.snapshots()
        verify_bundle(snapshots)
        report_attempted=True
        delivery.create_report()
        delivery.persist(dict(kind='archive-supervision-start',helperSourceSha=SOURCE_SHA,
                              helpersSha256=dict(PINS),nativeExecutionAuthorizedByCaller=True))
        initial_recorded=True
        checkpoint()
        started=True
        process.start(snapshots,gates,tuple(delivery.owned))
        report['worker']=validate_result(json.dumps(process.collect(),ensure_ascii=True).encode('ascii'))
        report['passed']=report['worker']['passed']
        report['reason']='WORKER_REPORTED' if report['passed'] else 'WORKER_FAILED'
    except (Exception,KeyboardInterrupt) as error:
        report['reason']=safe_reason(error)  # never echo exception contents
    finally:
        if started:
            try:
                report['childTermination']=process.stop()
                need(report['childTermination'] in ('NotStarted','ReapedAsReported'),'TERMINATION_SCHEMA')
            except (Exception,KeyboardInterrupt):
                report['passed']=False;report['childTermination']='Unconfirmed'
                report['reason']='CHILD_UNCONFIRMED'
        try:
            if started:
                identity=process.evidence()
                need(type(identity) is dict and set(identity) == {'pid','armed','pidfdRetained','reaped'} and
                     (identity['pid'] is None or type(identity['pid']) is int and
                      0 < identity['pid'] < 2**31) and
                     all(type(identity[k]) is bool for k in ('armed','pidfdRetained','reaped')),
                     'IDENTITY_SCHEMA')
                report['childIdentity']=identity
                if report['passed']:
                    need(report['childTermination'] == 'ReapedAsReported' and
                         identity['pid'] is not None and identity['armed'] and
                         identity['pidfdRetained'] and identity['reaped'],'IDENTITY_OUTCOME')
        except (Exception,KeyboardInterrupt):
            report['passed']=False;report['reason']='IDENTITY_UNCONFIRMED'
        try:
            if started:
                process.cleanup()
                report['cleanupStatus']['processDescriptors']='ClosedAsReported'
        except (Exception,KeyboardInterrupt):
            report['passed']=False;report['reason']='PROCESS_CLOSE'
            report['cleanupStatus']['processDescriptors']='Uncertain'
        if opened:
            if initial_recorded and report['childTermination'] != 'Unconfirmed':
                try:
                    report['reportPersistence']='RecordedPendingCloseout'
                    persisted=dict(report,cleanupStatus=dict(report['cleanupStatus']),
                                   passed=False,workerReportedPass=(report['worker'] is not None and
                                                              report['worker']['passed']),
                                   finalAuthority='returned-report-after-closeout')
                    delivery.persist(persisted)
                except (Exception,KeyboardInterrupt):
                    report['passed']=False;report['reason']='REPORT_UNCONFIRMED'
                    report['reportPersistence']='Unconfirmed'
            else:
                report['reportPersistence']='Unconfirmed' if report_attempted else 'NotAttempted'
            try:
                delivery.cleanup()
                report['cleanupStatus']['deliveryDescriptors']='ClosedAsReported'
            except (Exception,KeyboardInterrupt):
                report['passed']=False;report['reason']='DELIVERY_CLOSE'
                report['cleanupStatus']['deliveryDescriptors']='Uncertain'
        if old is not None:
            try:
                os.umask(old)
                report['cleanupStatus']['umask']='Restored'
            except (Exception,KeyboardInterrupt):
                report['passed']=False;report['reason']='UMASK_RESTORE_UNCERTAIN'
                report['cleanupStatus']['umask']='Uncertain'
        if handlers:
            report['cleanupStatus']['signals']='Restored'
        for signum,previous in reversed(handlers):
            try:
                signal.signal(signum,previous)
            except (Exception,KeyboardInterrupt):
                report['passed']=False;report['reason']='SIGNAL_RESTORE_UNCERTAIN'
                report['cleanupStatus']['signals']='Uncertain'
        if requested:
            report['passed']=False;report['reason']='INTERRUPTED'
    report['returnedAfterCloseout']=True
    need(len(json.dumps(report,ensure_ascii=True).encode('ascii')) <= LIMIT,'EXPORT_BOUND')
    return report
