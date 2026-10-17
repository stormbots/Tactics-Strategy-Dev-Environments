"""W2a only: unprivileged Linux flock experiment on disposable temporary objects.

No production imports, elevation, services, packages, networks or build dispatch.
Pipe messages use trusted local multiprocessing serialization, NOT authenticated IPC.
"""
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import platform
import sys
import tempfile
import time

TIMEOUT = 5
LOCKS = ('O', 'A', 'S')


def identity(path):
    st = path.stat(follow_symlinks=False)
    return dict(device=st.st_dev, inode=st.st_ino, uid=st.st_uid,
                mode=oct(st.st_mode & 0o777), size=st.st_size)


def privilege():
    effective = next(line.split()[1] for line in Path('/proc/self/status').read_text().splitlines()
                     if line.startswith('CapEff:'))
    return dict(uid=os.getuid(), euid=os.geteuid(), gid=os.getgid(), effective_capabilities=effective)


def worker(connection, root):
    import fcntl
    held = {}
    def acquire(name, mode):
        if name not in LOCKS or mode not in ('shared', 'exclusive') or name in held:
            raise ValueError('invalid lock action / upgrade forbidden')
        fd = os.open(Path(root) / name, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            fcntl.flock(fd, (fcntl.LOCK_SH if mode == 'shared' else fcntl.LOCK_EX) | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            return 'busy'
        except BaseException:
            os.close(fd)
            raise
        held[name] = fd
        return 'acquired'
    def release(name):
        fd = held.pop(name)
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    try:
        connection.send(dict(result='ready', pid=os.getpid(), privilege=privilege()))
        while True:
            request = connection.recv()
            action = request['action']
            if action == 'exit':
                connection.send(dict(result='exiting', held=sorted(held)))
                return
            if action == 'acquire':
                result = acquire(request['lock'], request['mode'])
            elif action == 'release':
                release(request['lock'])
                result = 'released'
            elif action == 'admit':
                result = acquire('A', 'shared')
                if result == 'busy':
                    result = 'admission_rejected'
                    attempted_s = False
                else:
                    attempted_s = True
                    result = acquire('S', 'shared')
                    release('A')
                connection.send(dict(result=result, attempted_s=attempted_s, held=sorted(held)))
                continue
            else:
                raise ValueError('unknown fixed test action')
            connection.send(dict(result=result, held=sorted(held)))
    except EOFError:
        pass
    except BaseException as exc:
        connection.send(dict(result='error', error=f'{type(exc).__name__}: {exc}'))
    finally:
        for fd in held.values():
            os.close(fd)
        connection.close()


def filesystem(root):
    candidates = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        before, after = line.split(' - ', 1)
        fields = before.split()
        mount = fields[4].replace('\\040', ' ')
        if root == mount or root.startswith(mount.rstrip('/') + '/'):
            candidates.append((len(mount), dict(mount_point=mount, filesystem=after.split()[0],
                                                 mount_options=fields[5], mount_id=fields[0])))
    longest = max(length for length, _ in candidates)
    matches = [entry for length, entry in candidates if length == longest]
    return dict(matching_mount_entries=matches,
                note='All longest-path mountinfo matches recorded; stacked mounts may differ in flags. Writes were tested directly.')


class Experiment:
    def __init__(self, root, report):
        self.root, self.report = root, report
        self.actors = {}
        self.started = time.monotonic()
        self.baseline = {name: identity(root / name) for name in LOCKS}
        report['initial_files'] = self.baseline

    def record(self, event, **details):
        self.report['trace'].append(dict(sequence=len(self.report['trace']) + 1,
                                        elapsed_seconds=time.monotonic() - self.started,
                                        event=event, **details))

    def receive(self, label):
        process, connection = self.actors[label]
        if not connection.poll(TIMEOUT):
            raise TimeoutError(f'{label}: barrier response timeout')
        reply = connection.recv()
        self.record('barrier_reply', actor=label, pid=process.pid, reply=reply)
        actual = {name: identity(self.root / name) for name in LOCKS}
        if actual != self.baseline:
            raise RuntimeError('lock file identity/metadata changed')
        if reply.get('result') == 'error':
            raise RuntimeError(reply['error'])
        return reply

    def start(self, label):
        context = multiprocessing.get_context('spawn')  # no inherited open lock descriptions
        parent, child = context.Pipe()
        process = context.Process(target=worker, args=(child, str(self.root)), name=f'W2a-{label}')
        process.start()
        child.close()
        self.actors[label] = process, parent
        reply = self.receive(label)
        if reply['result'] != 'ready' or reply['privilege']['euid'] != os.geteuid() or int(reply['privilege']['effective_capabilities'], 16):
            raise RuntimeError('worker not ready/unprivileged')

    def expect(self, label, expected, **request):
        self.record('barrier_request', actor=label, request=request)
        self.actors[label][1].send(request)
        reply = self.receive(label)
        if reply['result'] != expected:
            raise RuntimeError(f'{label}: expected {expected}, got {reply}')
        return reply

    def check(self, name):
        self.report['checks'].append(dict(name=name, result='Pass'))
        self.record('check_pass', name=name)

    def run(self):
        for actor in ('gui', 'updater', 'peer'):
            self.start(actor)
        self.expect('gui', 'acquired', action='acquire', lock='A', mode='shared')
        self.expect('gui', 'acquired', action='acquire', lock='S', mode='shared')
        self.expect('gui', 'released', action='release', lock='A')
        self.expect('updater', 'acquired', action='acquire', lock='O', mode='exclusive')
        self.expect('updater', 'acquired', action='acquire', lock='A', mode='exclusive')
        self.expect('updater', 'busy', action='acquire', lock='S', mode='exclusive')
        self.check('existing_GUI_shared_S_excludes_updater_exclusive_S')
        reply = self.expect('peer', 'admission_rejected', action='admit')
        if reply['attempted_s'] or reply['held']:
            raise RuntimeError('rejected GUI attempted/retained S')
        self.check('reopen_rejected_at_A_without_attempting_S')
        self.expect('gui', 'released', action='release', lock='S')
        reply = self.expect('updater', 'acquired', action='acquire', lock='S', mode='exclusive')
        if reply['held'] != ['A', 'O', 'S']:
            raise RuntimeError('updater lost O/A while acquiring S')
        self.expect('peer', 'busy', action='acquire', lock='O', mode='exclusive')
        self.check('drain_allows_S_with_O_A_retained_and_competitor_excluded')
        process = self.actors['updater'][0]
        process.terminate()  # ONLY this run-owned sentinel; no mutation/journal exists
        process.join(TIMEOUT)
        if process.is_alive() or process.exitcode != -15:
            raise RuntimeError('sentinel termination not observed')
        self.record('sentinel_terminated', actor='updater', pid=process.pid, exitcode=process.exitcode)
        for name in LOCKS:
            self.expect('peer', 'acquired', action='acquire', lock=name, mode='exclusive')
        self.check('process_exit_releases_locks_on_unchanged_files')
        for name in reversed(LOCKS):
            self.expect('peer', 'released', action='release', lock=name)
        # Positive admission control ensures rejection was not an always-deny stub.
        reply = self.expect('peer', 'acquired', action='admit')
        if not reply['attempted_s'] or reply['held'] != ['S']:
            raise RuntimeError('unblocked GUI admission did not retain shared S')
        self.expect('peer', 'released', action='release', lock='S')
        self.check('positive_GUI_admission_after_updater_exit')

    def cleanup(self):
        outcomes = []
        for label, (process, connection) in self.actors.items():
            fallback = False
            if process.is_alive():
                try:
                    self.expect(label, 'exiting', action='exit')
                    process.join(TIMEOUT)
                except (EOFError, BrokenPipeError, OSError, RuntimeError, TimeoutError):
                    fallback = True
                if process.is_alive():
                    fallback = True
                    process.terminate()
                    process.join(TIMEOUT)
                if process.is_alive():
                    process.kill()
                    process.join(TIMEOUT)
            connection.close()
            outcomes.append(dict(actor=label, pid=process.pid, alive=process.is_alive(),
                                 exitcode=process.exitcode, forced_cleanup=fallback))
        self.report['cleanup']['children'] = outcomes
        self.report['final_files_before_cleanup'] = {name: identity(self.root / name) for name in LOCKS}
        if any(x['alive'] or x['forced_cleanup'] for x in outcomes):
            raise RuntimeError('child cleanup failed or needed fallback')
        if self.report['final_files_before_cleanup'] != self.baseline:
            raise RuntimeError('file inventory changed')


def main():
    report = dict(experiment='W2a Linux cross-process flock subset of E20/B06',
                  evidence_level='L2 Linux primitives only', result='Not run', checks=[], trace=[],
                  failures=[], cleanup={}, started_at_utc=datetime.now(timezone.utc).isoformat(), source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  environment=dict(kernel=platform.release(), system=platform.system(), python=platform.python_version()),
                  limits=['No Mint/Windows desktop, privilege, authentication, service or package validation.',
                          'Same-UID cooperating actors; IPC is trusted test plumbing, not production authenticated IPC.',
                          'No native child, intent/journal, durable recovery, close grant or updater implementation.',
                          'One explicit schedule; no universal race/liveness proof; B01-B06 remain open.'])
    temporary = None
    root = None
    experiment = None
    try:
        if sys.platform != 'linux':
            report['result'] = 'Blocked'
            report['failures'].append('Linux host required')
        else:
            report['environment']['privilege'] = privilege()
            if os.geteuid() == 0 or int(report['environment']['privilege']['effective_capabilities'], 16):
                report['result'] = 'Blocked'
                report['failures'].append('Unprivileged UID with zero effective capabilities required')
            else:
                temporary = tempfile.TemporaryDirectory(prefix='PROTOTYPE-W2a-')
                root = Path(temporary.name)
                report['temporary_root'] = str(root)
                report['temporary_root_identity'] = identity(root)
                if identity(root)['mode'] != '0o700' or identity(root)['uid'] != os.geteuid():
                    raise RuntimeError('temporary root not private/run-owned')
                report['environment']['filesystem'] = filesystem(str(root))
                report['environment']['os_release'] = next((line.split('=', 1)[1].strip('"')
                    for line in Path('/etc/os-release').read_text().splitlines() if line.startswith('PRETTY_NAME=')), 'unknown')
                for name in LOCKS:
                    fd = os.open(root / name, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
                    os.close(fd)
                experiment = Experiment(root, report)
                experiment.run()
                report['result'] = 'Pass'
    except BaseException as exc:
        report['result'] = 'Fail'
        report['failures'].append(f'{type(exc).__name__}: {exc}')
    finally:
        if experiment:
            try:
                experiment.cleanup()
            except BaseException as exc:
                report['result'] = 'Fail'
                report['failures'].append(f'cleanup: {type(exc).__name__}: {exc}')
        if temporary:
            try:
                temporary.cleanup()
                report['cleanup']['temporary_root_removed'] = not root.exists()
                if root.exists():
                    raise RuntimeError('temporary root remains')
            except BaseException as exc:
                report['result'] = 'Fail'
                report['failures'].append(f'temporary cleanup: {type(exc).__name__}: {exc}')
        report['cleanup']['parent_pid'] = os.getpid()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['result'] == 'Pass' else 1


if __name__ == '__main__':
    multiprocessing.freeze_support()
    sys.exit(main())
