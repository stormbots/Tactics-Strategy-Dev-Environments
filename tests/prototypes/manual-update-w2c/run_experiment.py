"""W2c only: disposable unprivileged Linux unresolved-intent startup guard.

Test fixture and sentinel, not production journal, installer, IPC or recovery.
"""
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
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

SCRIPT = Path(__file__).resolve()
SUPPORT_PATH = SCRIPT.parent.parent / 'manual-update-w2b' / 'run_experiment.py'
spec = importlib.util.spec_from_file_location('w2b_test_support', SUPPORT_PATH)
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)  # definitions only; never runs a W2b scenario
ensure = support.ensure
TIMEOUT = support.TIMEOUT
LOCKS = ('O', 'A', 'S')


def expected_fixture(root):
    return dict(fixture='W2c-only', schema=1, transaction=root.name, state='unresolved')


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        ensure(key not in result, 'duplicate fixture field')
        result[key] = value
    return result


def inspect_intent(root):
    """Absence is the only admission possibility; any unresolved/invalid file blocks."""
    fd = None
    try:
        fd = os.open(root / 'intent.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
        st = os.fstat(fd)
        ensure(stat.S_ISREG(st.st_mode) and st.st_uid == os.geteuid(), 'unexpected fixture type/owner')
        raw = os.read(fd, 4097)
        ensure(len(raw) <= 4096, 'fixture too large')
        body = json.loads(raw, object_pairs_hook=unique_fields)
        ensure(body == expected_fixture(root) and type(body.get('schema')) is int, 'unsupported test fixture')
        return dict(present=True, reason='unresolved_fixture', identity=support.inode(st),
                    sha256=hashlib.sha256(raw).hexdigest(), body=body)
    except FileNotFoundError:
        return dict(present=False, reason='absent')
    except (OSError, ValueError, RuntimeError) as exc:
        return dict(present=True, reason='invalid_or_unreadable_fixture', error=f'{type(exc).__name__}: {exc}')
    finally:
        if fd is not None:
            os.close(fd)


def publish_intent(root):
    raw = json.dumps(expected_fixture(root), sort_keys=True).encode() + b'\n'
    events = []
    ensure(not os.path.lexists(root / 'intent.json'), 'fixture already exists')
    fd = os.open(root / 'intent.tmp', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        events.append('exclusive_create_temporary_0600')
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset:])
            ensure(written > 0, 'zero-byte fixture write')
            offset += written
        events.append('write_complete')
        os.fsync(fd)
        events.append('fsync_temporary_file')
    finally:
        os.close(fd)
    # Atomic no-replace publication: a racing existing intent must survive.
    os.link(root / 'intent.tmp', root / 'intent.json', follow_symlinks=False)
    events.append('link_into_intent_name_without_replacement')
    (root / 'intent.tmp').unlink()
    events.append('remove_temporary_name')
    directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory_fd)
        events.append('fsync_parent_directory')
    finally:
        os.close(directory_fd)
    return dict(operations=events, observed=inspect_intent(root))


def startup(root):
    held = {}
    trace = []
    def acquire(name):
        fd = os.open(root / name, os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BaseException:
            os.close(fd)
            raise
        held[name] = fd
        trace.append(f'{name}_shared_acquired')
    def result(decision, entered, intent, attempted_s):
        support.write_message(1, dict(decision=decision, entered_normal=entered,
            attempted_s=attempted_s, held=sorted(held), trace=trace, intent=intent,
            identity=support.process_identity(os.getpid()), privilege=support.privilege()))
        ensure(support.read_message(0) == {'command': 'exit'}, 'unknown startup control')
    try:
        acquire('A')
        before = inspect_intent(root)
        trace.append('pre_session_intent_check')
        if before['present']:
            os.close(held.pop('A'))
            result('RecoveryRequired', False, before, False)
            return
        acquire('S')
        after = inspect_intent(root)
        trace.append('post_session_intent_check')
        if after['present']:
            os.close(held.pop('S'))
            os.close(held.pop('A'))
            result('RecoveryRequired', False, after, True)
            return
        os.close(held.pop('A'))
        trace.append('A_released_S_retained')
        result('NormalSession', True, after, True)
    finally:
        for fd in held.values():
            os.close(fd)


def supervisor(root, control_fd):
    held = {}
    for name in LOCKS:
        fd = os.open(root / name, os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        held[name] = fd
    publication = publish_intent(root)  # required before the child can exist
    child = subprocess.Popen([sys.executable, '-I', str(SCRIPT), '--sentinel', str(control_fd)],
        pass_fds=(control_fd,), close_fds=True, stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.close(control_fd)
    support.write_message(1, dict(event='supervisor_ready', identity=support.process_identity(os.getpid()),
        privilege=support.privilege(), child_identity=support.process_identity(child.pid),
        publication=publication, locks={name: support.inode(os.fstat(fd)) for name, fd in held.items()},
        close_fds=True, passed_lock_descriptors=False))
    signal.pause()


class Experiment:
    def __init__(self, root, report):
        self.root, self.report = root, report
        self.root_before = support.inode(root.stat(follow_symlinks=False))
        ensure(self.root_before['mode'] == '0o700' and self.root_before['uid'] == os.geteuid(), 'root not private')
        self.expected_locks = {}
        self.fixture = None
        self.actors = []
        self.child_identity = None
        self.child_pidfd = None
        self.child_reaped = False
        self.parent_socket = self.child_socket = None
        self.started = time.monotonic()
        report['root_identity'] = self.root_before
        report['mount_entries'] = support.mount_entries(root)

    def event(self, event, **data):
        self.report['trace'].append(dict(sequence=len(self.report['trace']) + 1,
            elapsed_seconds=time.monotonic() - self.started, event=event, **data))

    def verify_files(self):
        actual = {name: support.inode((self.root / name).stat(follow_symlinks=False)) for name in LOCKS}
        ensure(actual == self.expected_locks, 'lock identities changed')
        if self.fixture is not None:
            ensure(inspect_intent(self.root) == self.fixture, 'unresolved fixture changed or removed')

    def bind(self, identity):
        ensure(support.process_identity(identity['pid']) == identity and identity['uid'] == os.geteuid(), 'unowned process')
        fd = os.pidfd_open(identity['pid'])
        try:
            ensure(support.process_identity(identity['pid']) == identity, 'process changed during pidfd binding')
        except BaseException:
            os.close(fd)
            raise
        self.event('pidfd_bound', identity=identity)
        return fd

    def launch(self, role, args, passed=()):
        process = subprocess.Popen([sys.executable, '-I', str(SCRIPT), *args], pass_fds=passed,
            close_fds=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        actor = dict(role=role, process=process, pidfd=None, expected_exit=0)
        self.actors.append(actor)  # track even if later setup fails
        identity = support.process_identity(process.pid)
        ensure(identity['ppid'] == os.getpid(), 'actor not runner-owned')
        actor['pidfd'] = self.bind(identity)
        actor['identity'] = identity
        return actor

    def admission(self, phase, expected):
        actor = self.launch('startup_' + phase, ['--startup', str(self.root)])
        process = actor['process']
        reply = support.read_message(process.stdout.fileno())
        self.event('startup_decision', phase=phase, reply=reply)
        ensure(reply['identity'] == actor['identity'] and reply['privilege']['euid'] == os.geteuid()
               and not int(reply['privilege']['effective_capabilities'], 16), 'startup identity/privilege mismatch')
        ensure(reply['decision'] == expected, 'wrong startup decision')
        if expected == 'NormalSession':
            ensure(reply['entered_normal'] is True and reply['held'] == ['S'], 'healthy admission did not retain S')
            fd = os.open(self.root / 'S', os.O_RDWR | os.O_NOFOLLOW)
            try:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    self.event('healthy_S_exclusion_observed')
                else:
                    raise RuntimeError('normal session did not actually hold shared S')
            finally:
                os.close(fd)
        else:
            ensure(reply['entered_normal'] is False and not reply['held'] and reply['attempted_s'] is False,
                   'uncertain startup entered/attempted normal session')
            ensure(reply['intent'] == self.fixture, 'startup did not observe original unresolved intent')
            self.probe('acquired_all')  # rejected actor is still alive at its exit barrier
        support.write_message(process.stdin.fileno(), {'command': 'exit'})
        ensure(process.wait(TIMEOUT) == 0, 'startup actor did not exit normally')
        self.event('startup_reaped', phase=phase, pid=process.pid, exitcode=process.returncode)
        self.verify_files()

    def ping(self):
        support.write_message(self.parent_socket.fileno(), {'command': 'ping'})
        reply = support.read_message(self.parent_socket.fileno())
        self.event('sentinel_alive', reply=reply)
        ensure(reply['event'] == 'alive' and reply['identity'] == {**self.child_identity, 'ppid': os.getpid()}, 'sentinel identity changed')
        ensure(reply['lock_fd'] == -1 and not select.select([self.child_pidfd], [], [], 0)[0], 'sentinel exited/inherited lock')
        self.verify_files()

    def probe(self, expected):
        held = []
        outcome = 'acquired_all'
        try:
            for name in LOCKS:
                fd = os.open(self.root / name, os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW)
                held.append(fd)
                ensure(support.inode(os.fstat(fd)) == self.expected_locks[name], 'probe wrong inode')
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    outcome = 'busy_' + name
                    break
            self.event('independent_lock_probe', pid=os.getpid(), outcome=outcome, expected=expected)
            ensure(outcome == expected, 'unexpected lock probe outcome')
        finally:
            for fd in held:
                os.close(fd)
        self.verify_files()

    def stop_child(self):
        support.write_message(self.parent_socket.fileno(), {'command': 'exit'})
        ensure(support.read_message(self.parent_socket.fileno())['event'] == 'sentinel_exiting', 'bad child exit ACK')
        status = support.wait_pidfd(self.child_pidfd)
        self.child_reaped = True
        self.event('sentinel_reaped', pid=status.si_pid, code=status.si_code, status=status.si_status)
        ensure(status.si_code == os.CLD_EXITED and status.si_status == 0, 'sentinel exit was not successful')

    def run(self):
        for name in LOCKS:
            fd = os.open(self.root / name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            self.expected_locks[name] = support.inode(os.fstat(fd))
            os.close(fd)
        self.report['locks_before'] = self.expected_locks
        self.admission('healthy', 'NormalSession')
        self.parent_socket, self.child_socket = socket.socketpair()
        actor = self.launch('supervisor', ['--supervisor', str(self.root), str(self.child_socket.fileno())],
                            passed=(self.child_socket.fileno(),))
        actor['expected_exit'] = -signal.SIGTERM
        self.child_socket.close()
        ready = support.read_message(actor['process'].stdout.fileno())
        self.event('supervisor_ready', reply=ready)
        ensure(ready['event'] == 'supervisor_ready' and ready['identity'] == actor['identity'], 'supervisor identity mismatch')
        ensure(ready['locks'] == self.expected_locks and ready['close_fds'] and not ready['passed_lock_descriptors'], 'supervisor lock mismatch')
        ensure(ready['privilege']['euid'] == os.geteuid() and not int(ready['privilege']['effective_capabilities'], 16), 'supervisor not unprivileged')
        self.fixture = ready['publication']['observed']
        ensure(self.fixture['reason'] == 'unresolved_fixture', 'fixture publication failed')
        self.report['publication'] = ready['publication']
        self.child_identity = ready['child_identity']
        ensure(self.child_identity['ppid'] == actor['process'].pid, 'sentinel not owned by supervisor')
        self.child_pidfd = self.bind(self.child_identity)
        child = support.read_message(self.parent_socket.fileno())
        self.event('sentinel_ready', reply=child)
        ensure(child['identity'] == self.child_identity and child['lock_fd'] == -1, 'wrong sentinel identity/descriptor')
        ensure(child['privilege']['euid'] == os.geteuid() and not int(child['privilege']['effective_capabilities'], 16), 'sentinel not unprivileged')
        for descriptor in child['regular_descriptors']:
            ensure(all((descriptor['identity']['device'], descriptor['identity']['inode']) != (value['device'], value['inode'])
                       for value in self.expected_locks.values()), 'sentinel inherited a lock descriptor')
        self.probe('busy_O')
        signal.pidfd_send_signal(actor['pidfd'], signal.SIGTERM)
        ensure(actor['process'].wait(TIMEOUT) == -signal.SIGTERM, 'supervisor did not terminate as intended')
        self.event('supervisor_reaped', pid=actor['process'].pid, exitcode=actor['process'].returncode)
        self.ping()
        self.probe('acquired_all')
        self.admission('child_survives', 'RecoveryRequired')
        self.ping()
        self.stop_child()
        self.admission('child_exited', 'RecoveryRequired')
        self.report['fixture_after_child_exit'] = inspect_intent(self.root)
        self.report['result'] = 'Pass'

    def cleanup(self):
        errors = []
        for actor in self.actors:
            process = actor['process']
            try:
                if process.poll() is None:
                    ensure(actor['pidfd'] is not None, 'no verified actor pidfd; no signal')
                    errors.append(f"fallback termination: {actor['role']}")
                    signal.pidfd_send_signal(actor['pidfd'], signal.SIGKILL)
                process.wait(TIMEOUT)
                ensure(process.returncode == actor['expected_exit'], 'unexpected actor exit')
            except BaseException as exc:
                errors.append(f"{actor['role']}: {type(exc).__name__}: {exc}")
        if self.child_pidfd is not None and not self.child_reaped:
            errors.append('fallback sentinel cleanup')
            try:
                if not select.select([self.child_pidfd], [], [], 0)[0]:
                    signal.pidfd_send_signal(self.child_pidfd, signal.SIGKILL)
                support.wait_pidfd(self.child_pidfd)
                self.child_reaped = True
            except BaseException as exc:
                errors.append(f'sentinel: {type(exc).__name__}: {exc}')
        resources = [sock for sock in (self.parent_socket, self.child_socket) if sock is not None]
        for actor in self.actors:
            resources.extend(pipe for pipe in (actor['process'].stdin, actor['process'].stdout) if pipe is not None)
        for resource in resources:
            try:
                resource.close()
            except BaseException as exc:
                errors.append(f'close: {type(exc).__name__}: {exc}')
        # Reap adopted startup orphans after control EOF, never signal an unregistered PID.
        for pid in support.direct_children():
            if any(actor['process'].pid == pid for actor in self.actors):
                continue
            fd = None
            try:
                identity = support.process_identity(pid)
                ensure(identity['ppid'] == os.getpid() and identity['uid'] == os.geteuid(), 'unowned orphan')
                fd = self.bind(identity)
                errors.append('fallback adopted-child reap')
                status = support.wait_pidfd(fd)
                self.event('fallback_adopted_child_reaped', pid=status.si_pid, status=status.si_status)
            except BaseException as exc:
                errors.append(f'adopted child: {type(exc).__name__}: {exc}')
            finally:
                if fd is not None:
                    try:
                        os.close(fd)
                    except BaseException as exc:
                        errors.append(f'orphan pidfd close: {type(exc).__name__}: {exc}')
        for fd in [actor['pidfd'] for actor in self.actors] + [self.child_pidfd]:
            if fd is not None:
                try:
                    os.close(fd)
                except BaseException as exc:
                    errors.append(f'pidfd close: {type(exc).__name__}: {exc}')
        self.report['cleanup'] = dict(errors=errors, sentinel_reaped=self.child_reaped,
            actors=[dict(role=a['role'], pid=a['process'].pid, exitcode=a['process'].returncode,
                         expected_exitcode=a['expected_exit']) for a in self.actors],
            remaining_direct_children=support.direct_children(), root_removed=False)
        try:
            ensure(not support.direct_children() and all(a['process'].returncode is not None for a in self.actors)
                   and self.child_reaped, 'termination uncertain; preserve root')
            current = support.inode(self.root.stat(follow_symlinks=False))
            ensure(all(current[k] == self.root_before[k] for k in ('device', 'inode', 'uid', 'mode')), 'root changed')
            ensure(self.fixture is not None and self.fixture.get('reason') == 'unresolved_fixture',
                   'no recorded unresolved fixture identity; preserve root')
            self.verify_files()
            ensure({p.name for p in self.root.iterdir()} == set(LOCKS) | {'intent.json'}, 'unknown root entries')
            self.report['locks_after'] = {name: support.inode((self.root / name).stat()) for name in LOCKS}
            self.report['fixture_before_teardown'] = inspect_intent(self.root)
            self.event('teardown_only_fixture_removal', actors_exited=True, not_recovery=True)
            for name in (*LOCKS, 'intent.json'):
                (self.root / name).unlink()
            self.root.rmdir()
            self.report['cleanup']['root_removed'] = not self.root.exists()
        except BaseException as exc:
            errors.append(f'root: {type(exc).__name__}: {exc}')
        if errors:
            self.report['result'] = 'Fail'


def main():
    report = dict(experiment='W2c unresolved test intent startup guard', result='Not run', trace=[], failures=[],
        started_at_utc=datetime.now(timezone.utc).isoformat(), evidence_level='L2 Linux test-only subset',
        source_hashes={str(path.relative_to(SCRIPT.parent.parent)): hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in [*SCRIPT.parent.glob('*.py'), SUPPORT_PATH]},
        environment=dict(system=platform.system(), kernel=platform.release(), python=platform.python_version()),
        limits=['No production journal/recovery, durability, power-loss, package or installer validation.',
                'Same-UID cooperating actors and trusted IPC; no native privileged authentication.',
                'Single pre-existing-intent schedule; no concurrent journal-publication race. B01-B06 remain open.'])
    original = None
    experiment = None
    root = None
    try:
        ensure(sys.platform == 'linux' and hasattr(signal, 'pidfd_send_signal'), 'Linux pidfds required')
        report['environment']['privilege'] = support.privilege()
        ensure(os.geteuid() != 0 and not int(support.privilege()['effective_capabilities'], 16), 'unprivileged UID required')
        ensure(not support.direct_children(), 'single-purpose child-free runner required')
        report['environment']['os_release'] = next(x.split('=', 1)[1].strip('"') for x in Path('/etc/os-release').read_text().splitlines() if x.startswith('PRETTY_NAME='))
        original = support.subreaper()
        report['subreaper'] = dict(original=original)
        support.subreaper(True)
        report['subreaper']['during'] = support.subreaper()
        root = Path(tempfile.mkdtemp(prefix='PROTOTYPE-W2c-'))
        report['temporary_root'] = str(root)
        experiment = Experiment(root, report)
        experiment.run()
    except BaseException as exc:
        report['result'] = 'Fail' if root is not None else 'Blocked'
        report['failures'].append(f'{type(exc).__name__}: {exc}')
    finally:
        if experiment is not None:
            try:
                experiment.cleanup()
            except BaseException as exc:
                report['result'] = 'Fail'
                report['failures'].append(f'cleanup: {type(exc).__name__}: {exc}')
        if experiment is None and root is not None:
            report['cleanup'] = dict(root_removed=False, root_preserved=True,
                                     reason='initialization failed; ownership/inventory not fully established')
        if original is not None:
            try:
                support.subreaper(original)
                report['subreaper']['restored'] = support.subreaper()
                ensure(report['subreaper']['restored'] == original, 'subreaper restoration failed')
            except BaseException as exc:
                report['result'] = 'Fail'
                report['failures'].append(f'restoration: {type(exc).__name__}: {exc}')
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['result'] == 'Pass' else 1


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--startup':
        startup(Path(sys.argv[2]))
    elif len(sys.argv) == 4 and sys.argv[1] == '--supervisor':
        supervisor(Path(sys.argv[2]), int(sys.argv[3]))
    elif len(sys.argv) == 3 and sys.argv[1] == '--sentinel':
        support.sentinel(int(sys.argv[2]), -1)
    elif len(sys.argv) == 1:
        sys.exit(main())
    else:
        raise SystemExit('fixed W2c modes only')
