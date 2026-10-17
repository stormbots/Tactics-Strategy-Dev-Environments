"""W2e only: unprivileged progress backpressure and pre-install deferral surrogate."""
from datetime import datetime, timezone
import array
import errno
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import select
import signal
import stat
import subprocess
import sys
import tempfile
import termios
import time

SCRIPT = Path(__file__).resolve()
SUPPORT_PATH = SCRIPT.parent.parent / 'manual-update-w2b' / 'run_experiment.py'
spec = importlib.util.spec_from_file_location('w2b_test_utilities', SUPPORT_PATH)
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)  # definitions only, never runs W2b scenarios
ensure = support.ensure
LEASE = 2.0  # TEST ONLY, not production drain or admission budgets
WATCHDOG = 5.0
FRAME = 512
MAX_CAPACITY = 1024 * 1024
LOCKS = ('O', 'A', 'S')


def wire(sequence):
    body = json.dumps(dict(test_only=True, event='progress', sequence=sequence), separators=(',', ':')).encode()
    ensure(len(body) < FRAME, 'frame payload overflow')
    return body + b' ' * (FRAME - len(body) - 1) + b'\n'


class Progress:
    """One replaceable pending atomic-size frame; counters, never a frame history."""
    def __init__(self, fd):
        ensure(not os.get_blocking(fd), 'progress writer must be nonblocking')
        ensure(FRAME <= os.fpathconf(fd, 'PC_PIPE_BUF'), 'frame must fit atomic pipe write')
        self.fd, self.pending = fd, None
        self.sequence = self.bytes_written = self.frames_written = self.blocked = self.coalesced = 0
        self.high_entries = self.high_bytes = 0
        self.last_errno = None

    def update(self):
        self.sequence += 1
        if self.pending is not None:
            self.coalesced += 1
        self.pending = wire(self.sequence)
        self.high_entries = max(self.high_entries, 1)
        self.high_bytes = max(self.high_bytes, len(self.pending))
        self.flush()

    def flush(self):
        if self.pending is None:
            return
        try:
            written = os.write(self.fd, self.pending)
        except BlockingIOError as exc:
            ensure(exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK), 'unexpected pipe error')
            self.blocked += 1
            self.last_errno = exc.errno
            return
        ensure(written == len(self.pending), 'unexpected partial atomic-size pipe write')
        self.frames_written += 1
        self.bytes_written += written
        self.pending = None

    def snapshot(self):
        return dict(updates=self.sequence, bytes_written=self.bytes_written, frames_written=self.frames_written,
            backpressure_events=self.blocked, last_errno=self.last_errno, coalesced_updates=self.coalesced,
            pending_entries=int(self.pending is not None), pending_bytes=len(self.pending or b''),
            high_entries=self.high_entries, high_bytes=self.high_bytes, frame_bytes=FRAME)


def acquire(root, name, mode):
    fd = os.open(root / name, os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, mode | fcntl.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    return fd


def actor_reply(event, held=None, **details):
    held = held or {}
    support.write_message(1, dict(event=event, identity=support.process_identity(os.getpid()),
        privilege=support.privilege(), held=sorted(held),
        held_identities={name: support.inode(os.fstat(fd)) for name, fd in held.items()}, **details))


def gui(root):
    fd = acquire(root, 'S', fcntl.LOCK_SH)
    try:
        actor_reply('ready', {'S': fd})
        while True:
            command = support.read_message(0)['command']
            if command == 'exit':
                actor_reply('exiting', {'S': fd})
                return
            ensure(command == 'status', 'unknown GUI command')
            actor_reply('gui_alive', {'S': fd})
    finally:
        os.close(fd)


def reader(mode, fd):
    received = 0
    def snapshot(event):
        queued = array.array('i', [0])
        fcntl.ioctl(fd, termios.FIONREAD, queued, True)
        actor_reply(event, mode=mode, bytes_read=received, queued_bytes=queued[0],
                    endpoint_open=True, pipe_identity=support.inode(os.fstat(fd)))
    def drain():
        nonlocal received
        try:
            chunk = os.read(fd, 4096)
        except BlockingIOError:
            return
        ensure(chunk, 'unexpected progress EOF')
        received += len(chunk)
    try:
        snapshot('ready')
        while True:
            ready, _, _ = select.select([0, fd] if mode == 'responsive' else [0], [], [], WATCHDOG)
            ensure(ready, 'reader control watchdog')
            if fd in ready:
                drain()
            if 0 in ready:
                command = support.read_message(0)['command']
                if command == 'exit':
                    snapshot('exiting')
                    return
                if command == 'await_progress':
                    ensure(mode == 'responsive', 'stalled reader cannot drain')
                    if received == 0:
                        ensure(select.select([fd], [], [], WATCHDOG)[0], 'progress delivery watchdog')
                        drain()
                else:
                    ensure(command == 'status', 'unknown reader command')
                snapshot('reader_status')
    finally:
        os.close(fd)


def supervisor(root, fd):
    held = {}
    progress = None
    try:
        for name in ('O', 'A'):
            held[name] = acquire(root, name, fcntl.LOCK_EX)
        progress = Progress(fd)
        capacity = fcntl.fcntl(fd, fcntl.F_GETPIPE_SZ)
        ensure(0 < capacity <= MAX_CAPACITY, 'unsupported test pipe capacity')
        state = 'Prepared'
        start = deadline = decision_at = None
        waiting_reply = False
        def snapshot(event):
            actor_reply(event, held, state=state, lease_seconds=LEASE, start=start, deadline=deadline,
                decision_at=decision_at, progress=progress.snapshot(), pipe_capacity=capacity,
                pipe_nonblocking=not os.get_blocking(fd), pipe_identity=support.inode(os.fstat(fd)),
                mutation_starts=0, intent_created=False)
        def expire():
            nonlocal state, decision_at
            if state != 'Waiting' or time.monotonic() < deadline:
                return
            decision_at = time.monotonic()
            record = dict(test_only=True, state='Deferred', start=start, deadline=deadline,
                          decision_at=decision_at, mutation_starts=0, intent_created=False)
            out = os.open(root / 'deferred.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            try:
                raw = json.dumps(record, sort_keys=True).encode()
                offset = 0
                while offset < len(raw):
                    count = os.write(out, raw[offset:])
                    ensure(count > 0, 'zero-byte state write')
                    offset += count
            finally:
                os.close(out)
            # This is proven pre-install state. No journal or native child exists.
            progress.pending = None
            for name in ('A', 'O'):
                os.close(held.pop(name))
            state = 'Deferred'
        snapshot('ready')
        while True:
            expire()
            if waiting_reply and state == 'Deferred':
                snapshot('deferred')
                waiting_reply = False
            remaining = max(0, deadline - time.monotonic()) if state == 'Waiting' else WATCHDOG
            ready, writable, _ = select.select([0], [fd] if progress.pending is not None else [], [], remaining)
            expire()  # deadline handling precedes output and control processing
            if writable and state == 'Waiting':
                progress.flush()
            if not ready:
                continue
            command = support.read_message(0)['command']
            expire()
            if command == 'exit':
                ensure(state == 'Deferred', 'cannot finish before safe deferral')
                snapshot('exiting')
                return
            if command == 'begin':
                ensure(state == 'Prepared', 'lease cannot be renewed')
                start = time.monotonic()
                deadline = start + LEASE
                state = 'Waiting'
                snapshot('begun')
            elif command == 'pump':
                ensure(state == 'Waiting', 'progress outside lease')
                # More frames than fit, then bounded extra updates to show coalescing.
                for _ in range(2 * capacity // FRAME + 256):
                    expire()
                    if state != 'Waiting':
                        break
                    progress.update()
                snapshot('pumped')
            elif command in ('status', 'ping'):
                snapshot('status' if command == 'status' else 'pong')
            elif command == 'await_deferred':
                if state == 'Deferred':
                    snapshot('deferred')
                else:
                    ensure(state == 'Waiting', 'no test lease')
                    waiting_reply = True  # fixed deadline remains active in the same event loop
            else:
                raise RuntimeError('unknown supervisor command')
    finally:
        for lock_fd in held.values():
            os.close(lock_fd)
        os.close(fd)


class Case:
    def __init__(self, mode, root, report):
        self.mode, self.root, self.report = mode, root, report
        self.actors = []
        self.started = time.monotonic()
        self.root_before = support.inode(root.stat(follow_symlinks=False))
        ensure(stat.S_ISDIR(root.stat(follow_symlinks=False).st_mode) and self.root_before['uid'] == os.geteuid()
               and self.root_before['mode'] == '0o700', 'root not private')
        self.baseline = {}
        self.pipe_fds = []
        self.state_snapshot = None
        report['root_identity'] = self.root_before
        report['mount_entries'] = support.mount_entries(root)

    def event(self, event, **data):
        self.report['trace'].append(dict(sequence=len(self.report['trace']) + 1,
            elapsed_seconds=time.monotonic() - self.started, event=event, **data))

    def verify(self):
        ensure({name: support.inode((self.root / name).stat(follow_symlinks=False)) for name in LOCKS} == self.baseline,
               'lock identities changed')
        ensure(not os.path.lexists(self.root / 'intent.json'), 'unexpected intent')
        if self.state_snapshot is not None:
            ensure(self.read_state() == self.state_snapshot, 'recorded deferral changed')

    def read_state(self):
        fd = os.open(self.root / 'deferred.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            metadata = os.fstat(fd)
            ensure(stat.S_ISREG(metadata.st_mode) and metadata.st_uid == os.geteuid()
                   and stat.S_IMODE(metadata.st_mode) == 0o600, 'unexpected state fixture type/owner/mode')
            raw = os.read(fd, 4097)
            ensure(len(raw) <= 4096, 'state fixture too large')
            return dict(body=json.loads(raw), identity=support.inode(os.fstat(fd)), sha256=hashlib.sha256(raw).hexdigest())
        finally:
            os.close(fd)

    def launch(self, role, pipe_fd=None):
        arguments = [sys.executable, '-I', str(SCRIPT), '--actor', role, str(self.root), self.mode, str(pipe_fd if pipe_fd is not None else -1)]
        process = subprocess.Popen(arguments, pass_fds=(() if pipe_fd is None else (pipe_fd,)), close_fds=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        entry = dict(role=role, process=process, pidfd=None, expected_exit=0)
        self.actors.append(entry)
        identity = support.process_identity(process.pid)
        ensure(identity['ppid'] == os.getpid() and identity['uid'] == os.geteuid(), 'actor not runner-owned')
        entry['identity'] = identity
        entry['pidfd'] = os.pidfd_open(process.pid)
        ensure(support.process_identity(process.pid) == identity, 'process changed during pidfd binding')
        self.event('pidfd_bound', role=role, identity=identity)
        reply = self.receive(entry)
        ensure(reply['event'] == 'ready', 'actor not ready')
        return entry, reply

    def receive(self, entry, exiting=False):
        reply = support.read_message(entry['process'].stdout.fileno())
        self.event('control_reply', role=entry['role'], reply=reply)
        ensure(reply['identity'] == entry['identity'] and reply['privilege']['euid'] == os.geteuid()
               and not int(reply['privilege']['effective_capabilities'], 16), 'actor identity/privilege mismatch')
        ensure(reply['held'] == sorted(reply['held_identities']) and all(value == self.baseline[name]
               for name, value in reply['held_identities'].items()), 'held lock evidence mismatch')
        if not exiting:
            ensure(not select.select([entry['pidfd']], [], [], 0)[0], 'actor exited at control barrier')
        return reply

    def command(self, entry, command, expected):
        self.event('control_request', role=entry['role'], command=command)
        sent = time.monotonic()
        support.write_message(entry['process'].stdin.fileno(), dict(command=command))
        reply = self.receive(entry, exiting=command == 'exit')
        self.event('control_latency', role=entry['role'], command=command, seconds=time.monotonic() - sent)
        ensure(reply['event'] == expected, 'unexpected control response')
        self.verify()
        return reply

    def probe(self, expected):
        observed = {}
        for name in LOCKS:
            fd = os.open(self.root / name, os.O_RDWR | os.O_NOFOLLOW)
            try:
                ensure(support.inode(os.fstat(fd)) == self.baseline[name], 'probe wrong inode')
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    observed[name] = 'acquired'
                except BlockingIOError:
                    observed[name] = 'busy'
            finally:
                os.close(fd)
        self.event('independent_lock_probe', observed=observed, expected=expected)
        ensure(observed == expected, 'wrong lock release/exclusion')
        self.verify()

    def run(self):
        for name in LOCKS:
            fd = os.open(self.root / name, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            self.baseline[name] = support.inode(os.fstat(fd))
            os.close(fd)
        self.report['locks_before'] = self.baseline
        read_fd, write_fd = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
        self.pipe_fds = [read_fd, write_fd]
        pipe_identity = support.inode(os.fstat(read_fd))
        gui_entry, _ = self.launch('gui')
        reader_entry, reader_ready = self.launch('reader', read_fd)
        os.close(read_fd)
        self.pipe_fds.remove(read_fd)
        supervisor_entry, supervisor_ready = self.launch('supervisor', write_fd)
        os.close(write_fd)
        self.pipe_fds.remove(write_fd)
        ensure(reader_ready['pipe_identity'] == supervisor_ready['pipe_identity'] == pipe_identity, 'progress endpoint mismatch')
        ensure(supervisor_ready['pipe_nonblocking'] and supervisor_ready['held'] == ['A', 'O'], 'bad supervisor preparation')
        self.probe(dict(O='busy', A='busy', S='busy'))
        begin = self.command(supervisor_entry, 'begin', 'begun')
        deadline = begin['deadline']
        ensure(deadline == begin['start'] + LEASE, 'wrong fixed test lease')
        pump = self.command(supervisor_entry, 'pump', 'pumped')
        ensure(pump['state'] == 'Waiting' and pump['deadline'] == deadline, 'pump consumed/renewed test lease')
        progress = pump['progress']
        ensure(progress['high_entries'] <= 1 and progress['high_bytes'] <= FRAME, 'progress queue exceeded bound')
        if self.mode == 'stalled':
            ensure(progress['backpressure_events'] > 0 and progress['last_errno'] in (errno.EAGAIN, errno.EWOULDBLOCK)
                   and progress['coalesced_updates'] > 0 and progress['pending_entries'] == 1, 'kernel backpressure/coalescing not demonstrated')
            status = self.command(reader_entry, 'status', 'reader_status')
            ensure(status['bytes_read'] == 0 and status['queued_bytes'] > 0 and status['endpoint_open'], 'stalled reader drained/closed')
        else:
            status = self.command(reader_entry, 'await_progress', 'reader_status')
            ensure(status['bytes_read'] > 0, 'responsive reader received no progress')
        pong = self.command(supervisor_entry, 'ping', 'pong')
        ensure(pong['state'] == 'Waiting' and pong['deadline'] == deadline, 'control stalled or lease extended')
        again = self.command(supervisor_entry, 'status', 'status')
        ensure(again['deadline'] == deadline and again['state'] == 'Waiting', 'query renewed/consumed lease')
        deferred = self.command(supervisor_entry, 'await_deferred', 'deferred')
        reply_received_at = time.monotonic()
        ensure(reply_received_at < begin['start'] + WATCHDOG, 'deferral reply beyond diagnostic watchdog')
        ensure(deferred['state'] == 'Deferred' and not deferred['held'] and deferred['deadline'] == deadline,
               'safe deferral failed')
        ensure(deadline <= deferred['decision_at'] < begin['start'] + WATCHDOG, 'deferral outside test budget/watchdog')
        ensure(deferred['mutation_starts'] == 0 and deferred['intent_created'] is False, 'unexpected native state')
        observed_state = self.read_state()
        ensure(observed_state['body'] == dict(test_only=True, state='Deferred', start=begin['start'], deadline=deadline,
               decision_at=deferred['decision_at'], mutation_starts=0, intent_created=False), 'state record mismatch')
        self.state_snapshot = observed_state  # adopt only after validating the whole test record
        self.report['deferral_record'] = self.state_snapshot
        self.report['deadline_evidence'] = dict(start=begin['start'], deadline=deadline, decision_at=deferred['decision_at'],
            lease_seconds=LEASE, watchdog_seconds=WATCHDOG)
        self.report['progress_evidence'] = deferred['progress']
        self.probe(dict(O='acquired', A='acquired', S='busy'))
        locks_verified_at = time.monotonic()
        ensure(locks_verified_at < begin['start'] + WATCHDOG, 'lock release beyond diagnostic watchdog')
        self.report['deadline_evidence'].update(reply_received_at=reply_received_at, locks_verified_at=locks_verified_at)
        ensure(self.command(gui_entry, 'status', 'gui_alive')['held'] == ['S'], 'GUI session lost')
        final_reader = self.command(reader_entry, 'status', 'reader_status')
        ensure(final_reader['endpoint_open'], 'reader endpoint closed before proof')
        if self.mode == 'stalled':
            ensure(final_reader['bytes_read'] == 0 and final_reader['queued_bytes'] > 0, 'stalled reader drained to permit deferral')
        self.report['reader_evidence'] = final_reader
        # Stop reader before closing writer, avoiding an unrelated EOF experiment.
        for entry in (reader_entry, supervisor_entry, gui_entry):
            self.command(entry, 'exit', 'exiting')
            ensure(entry['process'].wait(WATCHDOG) == 0, 'actor failed normal exit')
            self.event('actor_reaped', role=entry['role'], pid=entry['process'].pid, exitcode=0)
        self.report['result'] = 'Pass'

    def cleanup(self):
        errors = []
        for entry in self.actors:
            process = entry['process']
            try:
                if process.poll() is None:
                    ensure(entry['pidfd'] is not None, 'no owned pidfd; no signal')
                    errors.append(f"fallback actor termination: {entry['role']}")
                    signal.pidfd_send_signal(entry['pidfd'], signal.SIGKILL)
                process.wait(WATCHDOG)
                ensure(process.returncode == 0, 'unexpected actor exit')
            except BaseException as exc:
                errors.append(f"{entry['role']}: {type(exc).__name__}: {exc}")
            for pipe in (process.stdin, process.stdout):
                try:
                    if pipe is not None:
                        pipe.close()
                except BaseException as exc:
                    errors.append(f'control close: {type(exc).__name__}: {exc}')
        for fd in self.pipe_fds + [e['pidfd'] for e in self.actors if e['pidfd'] is not None]:
            try:
                os.close(fd)
            except BaseException as exc:
                errors.append(f'descriptor close: {type(exc).__name__}: {exc}')
        self.report['cleanup'] = dict(errors=errors, root_removed=False, remaining_direct_children=support.direct_children(),
            actors=[dict(role=e['role'], pid=e['process'].pid, exitcode=e['process'].returncode) for e in self.actors])
        try:
            ensure(not support.direct_children() and all(e['process'].returncode is not None for e in self.actors), 'completion uncertain; preserve root')
            current = support.inode(self.root.stat(follow_symlinks=False))
            ensure(all(current[k] == self.root_before[k] for k in ('device', 'inode', 'uid', 'mode')), 'root changed')
            self.verify()
            ensure(self.state_snapshot is not None and self.state_snapshot['body']['state'] == 'Deferred', 'unrecorded state; preserve root')
            ensure({p.name for p in self.root.iterdir()} == set(LOCKS) | {'deferred.json'}, 'unknown files; preserve root')
            self.report['locks_after'] = {name: support.inode((self.root / name).stat()) for name in LOCKS}
            self.event('teardown_only_removal', actors_exited=True, not_recovery=True)
            for name in (*LOCKS, 'deferred.json'):
                (self.root / name).unlink()
            self.root.rmdir()
            self.report['cleanup']['root_removed'] = not self.root.exists()
        except BaseException as exc:
            errors.append(f'root: {type(exc).__name__}: {exc}')
        if errors:
            self.report['result'] = 'Fail'


def main():
    paths = [*SCRIPT.parent.glob('*.py'), SUPPORT_PATH]
    report = dict(experiment='W2e progress backpressure / safe pre-install deferral', result='Not run', cases=[], failures=[],
        started_at_utc=datetime.now(timezone.utc).isoformat(), evidence_level='L2 Linux surrogate transport/locks',
        source_hashes={str(p.relative_to(SCRIPT.parent.parent)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        environment=dict(system=platform.system(), kernel=platform.release(), python=platform.python_version()),
        limits=['Test-only 2-second lease and 5-second diagnostic watchdog, not production timeout/scheduling proof.',
                'Queue counters bound pending frames, not measured total process RSS.',
                'Same-UID trusted controls; no production authenticated IPC, installer, journal, postcheck or recovery.',
                'No Windows/Mint desktop, service, privilege, durability, package or build validation. B01-B06 remain open.'])
    root = None
    try:
        ensure(sys.platform == 'linux' and hasattr(signal, 'pidfd_send_signal') and hasattr(fcntl, 'F_GETPIPE_SZ'), 'Linux pidfd/pipe primitives required')
        report['environment']['privilege'] = support.privilege()
        ensure(os.geteuid() != 0 and not int(support.privilege()['effective_capabilities'], 16), 'unprivileged UID required')
        ensure(not support.direct_children(), 'single-purpose runner must initially be child-free')
        report['environment']['os_release'] = next(x.split('=', 1)[1].strip('"') for x in Path('/etc/os-release').read_text().splitlines() if x.startswith('PRETTY_NAME='))
        for mode in ('responsive', 'stalled'):
            root = Path(tempfile.mkdtemp(prefix=f'PROTOTYPE-W2e-{mode}-'))
            item = dict(mode=mode, root=str(root), result='Not run', trace=[], failures=[])
            report['cases'].append(item)
            case = None
            try:
                case = Case(mode, root, item)
                case.run()
            except BaseException as exc:
                item['result'] = 'Fail'
                item['failures'].append(f'{type(exc).__name__}: {exc}')
            finally:
                if case is not None:
                    try:
                        case.cleanup()
                    except BaseException as exc:
                        item['result'] = 'Fail'
                        item['failures'].append(f'cleanup: {type(exc).__name__}: {exc}')
                else:
                    item['cleanup'] = dict(root_removed=False, root_preserved=True, reason='initialization incomplete')
            if item['result'] != 'Pass':
                break
        report['result'] = 'Pass' if len(report['cases']) == 2 and all(c['result'] == 'Pass' for c in report['cases']) else 'Fail'
    except BaseException as exc:
        report['result'] = 'Fail' if root is not None else 'Blocked'
        report['failures'].append(f'{type(exc).__name__}: {exc}')
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['result'] == 'Pass' else 1


if __name__ == '__main__':
    if len(sys.argv) == 6 and sys.argv[1] == '--actor' and sys.argv[2] in ('gui', 'reader', 'supervisor') and sys.argv[4] in ('responsive', 'stalled'):
        role, root, mode, fd = sys.argv[2], Path(sys.argv[3]), sys.argv[4], int(sys.argv[5])
        if role == 'gui':
            gui(root)
        elif role == 'reader':
            reader(mode, fd)
        else:
            supervisor(root, fd)
    elif len(sys.argv) == 1:
        sys.exit(main())
    else:
        raise SystemExit('fixed W2e modes only')
