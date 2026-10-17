"""W2d only: barrier-controlled Linux startup/legacy intent race. No updater."""
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
import stat
import subprocess
import sys
import tempfile
import time

SCRIPT = Path(__file__).resolve()
FIXTURE_PATH = SCRIPT.parent.parent / 'manual-update-w2c' / 'run_experiment.py'
spec = importlib.util.spec_from_file_location('w2c_test_fixture', FIXTURE_PATH)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)  # definitions only, no earlier scenarios
support = fixture.support
ensure = support.ensure
LOCKS = ('O', 'A', 'S')
TIMEOUT = support.TIMEOUT


def actor(role, variant, root):
    held = {}
    history = []
    first = None
    phase = 'initial'
    def acquire(name, mode):
        ensure(name not in held, 'lock upgrade/reentrant acquisition forbidden')
        fd = os.open(root / name, os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            fcntl.flock(fd, (fcntl.LOCK_SH if mode == 'shared' else fcntl.LOCK_EX) | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            history.append(f'{name}_{mode}_busy')
            return False
        except BaseException:
            os.close(fd)
            raise
        held[name] = fd
        history.append(f'{name}_{mode}_acquired')
        return True
    def release(name):
        os.close(held.pop(name))
        history.append(f'{name}_released')
    def reply(event, **details):
        support.write_message(1, dict(event=event, role=role, variant=variant,
            identity=support.process_identity(os.getpid()), privilege=support.privilege(),
            held=sorted(held), held_identities={name: support.inode(os.fstat(fd)) for name, fd in held.items()},
            history=list(history), **details))
    try:
        reply('ready')
        while True:
            command = support.read_message(0)['command']
            if command == 'exit':
                reply('exiting')
                return
            if role == 'startup' and command == 'precheck':
                ensure(phase == 'initial', 'precheck already performed')
                ensure(acquire('A', 'shared'), 'admission busy')
                first = fixture.inspect_intent(root)
                ensure(not first['present'], 'pre-existing fixture outside race schedule')
                phase = 'prechecked'
                reply('precheck_clear', first=first)
            elif role == 'startup' and command == 'postcheck':
                ensure(phase == 'prechecked', 'postcheck outside startup phase')
                if not acquire('S', 'shared'):
                    reply('session_busy', first=first, entered_normal=False)
                    continue
                second = dict(skipped=True) if variant == 'omit_second_check' else fixture.inspect_intent(root)
                if second.get('present', False):
                    release('S')
                    release('A')
                    phase = 'rejected'
                    reply('decision', decision='RecoveryRequired', entered_normal=False, first=first, second=second)
                else:
                    release('A')
                    phase = 'normal'
                    reply('decision', decision='NormalSession', entered_normal=True, first=first, second=second)
            elif role == 'legacy' and command == 'attempt':
                ensure(phase == 'initial', 'legacy attempt already performed')
                phase = 'attempted'
                if not acquire('O', 'exclusive'):
                    reply('deferred', publication=None, mutation_starts=0)
                    continue
                if not acquire('S', 'exclusive'):
                    release('O')
                    reply('deferred', publication=None, mutation_starts=0)
                    continue
                # Deliberately no A: surrogate for reviewed O/S-only legacy behavior.
                ensure(set(held) == {'O', 'S'}, 'legacy lock contract changed')
                publication = fixture.publish_intent(root)
                reply('published', publication=publication, mutation_starts=0)
            else:
                raise RuntimeError('unknown fixed actor command')
    finally:
        for fd in held.values():
            os.close(fd)


def admission_violation(reply, actual_intent):
    """Independent of actor's second-check claim (the mutant deliberately skips it)."""
    normal_claim = reply.get('entered_normal') is True or reply.get('decision') == 'NormalSession'
    return normal_claim and actual_intent.get('present') is True


class Case:
    def __init__(self, name, root, report):
        self.name, self.root, self.report = name, root, report
        self.actors = []
        self.started = time.monotonic()
        self.root_before = support.inode(root.stat(follow_symlinks=False))
        ensure(stat.S_ISDIR(root.stat(follow_symlinks=False).st_mode) and self.root_before['uid'] == os.geteuid()
               and self.root_before['mode'] == '0o700', 'root not private/run-owned')
        self.baseline = {}
        self.intent = None
        report['root_identity'] = self.root_before
        report['mount_entries'] = support.mount_entries(root)

    def event(self, event, **data):
        self.report['trace'].append(dict(sequence=len(self.report['trace']) + 1,
            elapsed_seconds=time.monotonic() - self.started, event=event, **data))

    def verify(self):
        ensure({name: support.inode((self.root / name).stat(follow_symlinks=False)) for name in LOCKS} == self.baseline,
               'lock inventory changed')
        observed = fixture.inspect_intent(self.root)
        if self.intent is not None:
            ensure(self.intent.get('present') is True and self.intent.get('reason') == 'unresolved_fixture',
                   'recorded fixture not valid unresolved intent; preserve root')
            ensure(observed == self.intent, 'unresolved fixture changed/removed')
        else:
            ensure(not observed['present'], 'unexpected fixture publication')

    def launch(self, role, variant='guarded'):
        process = subprocess.Popen([sys.executable, '-I', str(SCRIPT), '--actor', role, variant, str(self.root)],
            close_fds=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        entry = dict(role=role, variant=variant, process=process, pidfd=None, expected_exit=0)
        self.actors.append(entry)
        identity = support.process_identity(process.pid)
        ensure(identity['ppid'] == os.getpid() and identity['uid'] == os.geteuid(), 'actor not runner-owned')
        entry['identity'] = identity
        entry['pidfd'] = os.pidfd_open(process.pid)
        ensure(support.process_identity(process.pid) == identity, 'identity changed while binding pidfd')
        self.event('pidfd_bound', role=role, identity=identity)
        ensure(self.receive(entry)['event'] == 'ready', 'actor not ready')
        return entry

    def receive(self, entry, exiting=False):
        process = entry['process']
        reply = support.read_message(process.stdout.fileno())
        self.event('barrier_reply', role=entry['role'], reply=reply)
        ensure(reply['identity'] == entry['identity'] and reply['role'] == entry['role'], 'reply identity mismatch')
        ensure(reply.get('variant') == entry['variant'], 'actor variant mismatch')
        ensure(reply['privilege']['euid'] == os.geteuid() and not int(reply['privilege']['effective_capabilities'], 16),
               'actor not unprivileged')
        ensure(reply['held'] == sorted(reply['held_identities']), 'held-lock evidence inconsistent')
        ensure(all(value == self.baseline[name] for name, value in reply['held_identities'].items()),
               'actor opened different lock inode')
        if not exiting:
            ensure(not select.select([entry['pidfd']], [], [], 0)[0], 'actor exited at barrier')
        return reply

    def command(self, entry, command, expected, exiting=False):
        self.event('barrier_request', role=entry['role'], command=command)
        support.write_message(entry['process'].stdin.fileno(), dict(command=command))
        reply = self.receive(entry, exiting=exiting)
        ensure(reply['event'] == expected, f'expected {expected}, got {reply}')
        # Capture publication only after independently inspecting the same fixture.
        if expected == 'published':
            observed = reply['publication']['observed']
            ensure(observed.get('present') is True and observed.get('reason') == 'unresolved_fixture'
                   and fixture.inspect_intent(self.root) == observed, 'fixture publication not independently confirmed')
            self.intent = observed
        self.verify()
        return reply

    def probe(self, expected):
        observed = {}
        for name in LOCKS:
            fd = os.open(self.root / name, os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW)
            try:
                ensure(support.inode(os.fstat(fd)) == self.baseline[name], 'probe wrong inode')
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    observed[name] = 'acquired'
                except BlockingIOError:
                    observed[name] = 'busy'
            finally:
                os.close(fd)
        self.event('independent_probe', pid=os.getpid(), observed=observed, expected=expected)
        ensure(observed == expected, 'unexpected independent lock outcome')
        self.verify()

    def exit_actor(self, entry):
        self.command(entry, 'exit', 'exiting', exiting=True)
        ensure(entry['process'].wait(TIMEOUT) == 0, 'actor failed normal exit')
        self.event('actor_reaped', role=entry['role'], pid=entry['process'].pid, exitcode=0)

    def terminate_publisher(self, entry):
        ensure(self.intent is not None and entry['role'] == 'legacy', 'publisher not established')
        entry['expected_exit'] = -signal.SIGTERM
        signal.pidfd_send_signal(entry['pidfd'], signal.SIGTERM)
        ensure(entry['process'].wait(TIMEOUT) == -signal.SIGTERM, 'publisher termination failed')
        self.event('publisher_reaped', pid=entry['process'].pid, exitcode=entry['process'].returncode)
        self.verify()

    def run(self):
        for name in LOCKS:
            fd = os.open(self.root / name, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            self.baseline[name] = support.inode(os.fstat(fd))
            os.close(fd)
        self.report['locks_before'] = self.baseline
        variant = 'omit_second_check' if self.name == 'negative_omitted_check' else 'guarded'
        startup = self.launch('startup', variant)
        legacy = self.launch('legacy')
        first = self.command(startup, 'precheck', 'precheck_clear')
        ensure(first['held'] == ['A'] and not first['first']['present'], 'startup precheck state incorrect')
        if self.name == 'startup_wins':
            decision = self.command(startup, 'postcheck', 'decision')
            ensure(decision['decision'] == 'NormalSession' and decision['entered_normal'] is True and decision['held'] == ['S'],
                   'healthy startup failed')
            actual = fixture.inspect_intent(self.root)
            ensure(decision.get('first') == first['first'] == {'present': False, 'reason': 'absent'}
                   and decision.get('second') == actual == {'present': False, 'reason': 'absent'},
                   'healthy second check missing/changed')
            attempt = self.command(legacy, 'attempt', 'deferred')
            ensure(attempt['publication'] is None and attempt['mutation_starts'] == 0 and not attempt['held'],
                   'blocked legacy actor published/retained work')
            ensure('S_exclusive_busy' in attempt['history'] and 'A_exclusive_acquired' not in attempt['history'],
                   'legacy did not take intended O/S-only path')
            self.probe(dict(O='acquired', A='acquired', S='busy'))
            ensure(not admission_violation(decision, fixture.inspect_intent(self.root)), 'unsafe normal admission')
        else:
            publication = self.command(legacy, 'attempt', 'published')
            ensure(publication['held'] == ['O', 'S'] and publication['mutation_starts'] == 0, 'wrong legacy ownership')
            self.probe(dict(O='busy', A='busy', S='busy'))
            blocked = self.command(startup, 'postcheck', 'session_busy')
            ensure(blocked['held'] == ['A'] and not blocked['entered_normal'], 'blocked startup changed session')
            self.terminate_publisher(legacy)
            decision = self.command(startup, 'postcheck', 'decision')
            actual = fixture.inspect_intent(self.root)
            ensure(decision.get('first') == first['first'], 'first intent-check evidence changed')
            violation = admission_violation(decision, actual)
            self.report['oracle'] = dict(actual_intent=actual, violation=violation,
                finding='normal_admission_with_unresolved_intent' if violation else None)
            if self.name == 'negative_omitted_check':
                ensure(violation and decision['decision'] == 'NormalSession' and decision['held'] == ['S']
                       and decision['second'] == {'skipped': True}, 'negative control not detected as designed')
                self.probe(dict(O='acquired', A='acquired', S='busy'))
                self.report['result'] = 'Detected'
            else:
                ensure(not violation and decision['decision'] == 'RecoveryRequired' and not decision['entered_normal']
                       and not decision['held'] and decision['second'] == self.intent, 'post-session guard failed')
                self.probe(dict(O='acquired', A='acquired', S='acquired'))
        self.exit_actor(startup)
        if self.name == 'startup_wins':
            self.exit_actor(legacy)
        self.report['intent_after_schedule'] = fixture.inspect_intent(self.root)
        if self.name != 'negative_omitted_check':
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
                process.wait(TIMEOUT)
                ensure(process.returncode == entry['expected_exit'], 'unexpected actor exit')
            except BaseException as exc:
                errors.append(f"{entry['role']}: {type(exc).__name__}: {exc}")
            for pipe in (process.stdin, process.stdout):
                try:
                    if pipe is not None:
                        pipe.close()
                except BaseException as exc:
                    errors.append(f'pipe close: {type(exc).__name__}: {exc}')
            if entry['pidfd'] is not None:
                try:
                    os.close(entry['pidfd'])
                except BaseException as exc:
                    errors.append(f'pidfd close: {type(exc).__name__}: {exc}')
        self.report['cleanup'] = dict(errors=errors, root_removed=False,
            remaining_direct_children=support.direct_children(),
            actors=[dict(role=e['role'], pid=e['process'].pid, exitcode=e['process'].returncode,
                         expected_exitcode=e['expected_exit']) for e in self.actors])
        try:
            ensure(not support.direct_children() and all(e['process'].returncode is not None for e in self.actors),
                   'actor completion uncertain; preserve root')
            current = support.inode(self.root.stat(follow_symlinks=False))
            ensure(all(current[k] == self.root_before[k] for k in ('device', 'inode', 'uid', 'mode')), 'root changed')
            self.verify()
            expected = set(LOCKS) | ({'intent.json'} if self.intent is not None else set())
            ensure({p.name for p in self.root.iterdir()} == expected, 'unknown files; preserve root')
            self.report['locks_after'] = {name: support.inode((self.root / name).stat()) for name in LOCKS}
            self.report['intent_before_teardown'] = fixture.inspect_intent(self.root)
            self.event('teardown_only_removal', actors_exited=True, not_recovery=True)
            for name in expected:
                (self.root / name).unlink()
            self.root.rmdir()
            self.report['cleanup']['root_removed'] = not self.root.exists()
        except BaseException as exc:
            errors.append(f'root: {type(exc).__name__}: {exc}')
        if errors:
            self.report['result'] = 'Fail'


def main():
    paths = [*SCRIPT.parent.glob('*.py'), FIXTURE_PATH, fixture.SUPPORT_PATH]
    report = dict(experiment='W2d post-session intent race', result='Not run', cases=[], failures=[],
        started_at_utc=datetime.now(timezone.utc).isoformat(), evidence_level='L2 Linux test-surrogate schedules',
        source_hashes={str(p.relative_to(SCRIPT.parent.parent)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        environment=dict(system=platform.system(), kernel=platform.release(), python=platform.python_version()),
        limits=['Two directed guarded schedules and one deliberate unsafe mutant; not exhaustive race proof.',
                'Same-UID cooperating surrogates, trusted IPC and reused W2c-only test fixture; no production compatibility/authentication.',
                'No installer, mutation child, durability/power-loss, privileged recovery or desktop validation. B01-B06 remain open.'])
    root = None
    try:
        ensure(sys.platform == 'linux' and hasattr(signal, 'pidfd_send_signal'), 'Linux pidfd support required')
        report['environment']['privilege'] = support.privilege()
        ensure(os.geteuid() != 0 and not int(support.privilege()['effective_capabilities'], 16), 'unprivileged UID required')
        ensure(not support.direct_children(), 'single-purpose runner must initially have no children')
        report['environment']['os_release'] = next(line.split('=', 1)[1].strip('"') for line in Path('/etc/os-release').read_text().splitlines() if line.startswith('PRETTY_NAME='))
        for name in ('legacy_wins', 'startup_wins', 'negative_omitted_check'):
            root = Path(tempfile.mkdtemp(prefix=f'PROTOTYPE-W2d-{name}-'))
            item = dict(name=name, root=str(root), result='Not run', trace=[], failures=[])
            report['cases'].append(item)
            case = None
            try:
                case = Case(name, root, item)
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
                    item['cleanup'] = dict(root_removed=False, root_preserved=True, reason='initialization not completed')
            if item['result'] not in ('Pass', 'Detected'):
                break
        results = [c['result'] for c in report['cases']]
        report['result'] = 'Pass' if results == ['Pass', 'Pass', 'Detected'] else 'Fail'
        report['outcome_summary'] = dict(guarded_passes=sum(c['result'] == 'Pass' for c in report['cases'] if c['name'] != 'negative_omitted_check'),
            negative_control_detected=any(c['name'] == 'negative_omitted_check' and c['result'] == 'Detected' for c in report['cases']))
    except BaseException as exc:
        report['result'] = 'Fail' if root is not None else 'Blocked'
        report['failures'].append(f'{type(exc).__name__}: {exc}')
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['result'] == 'Pass' else 1


if __name__ == '__main__':
    if len(sys.argv) == 5 and sys.argv[1] == '--actor' and sys.argv[2] in ('startup', 'legacy') and sys.argv[3] in ('guarded', 'omit_second_check'):
        actor(sys.argv[2], sys.argv[3], Path(sys.argv[4]))
    elif len(sys.argv) == 1:
        sys.exit(main())
    else:
        raise SystemExit('fixed W2d modes only')
