"""W2g ONLY: enrolled-client exit with a surviving connected-socket holder."""
from datetime import datetime, timezone
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
import struct
import subprocess
import sys
import tempfile
import time

SCRIPT = Path(__file__).resolve()
PEER_HELPER = SCRIPT.parent.parent / 'manual-update-w2f/run_experiment.py'
spec = importlib.util.spec_from_file_location('w2g_peer_helpers', PEER_HELPER)
peer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(peer)  # definitions only; no earlier experiments execute
support = peer.support
ensure = support.ensure
TIMEOUT = 5  # test diagnostic only, not a production timeout
CASES = ('healthy', 'client-exit', 'TEST-ONLY-omitted-liveness')


def credentials(conn):
    raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i'))
    ensure(len(raw) == struct.calcsize('3i'), 'short kernel credential record')
    pid, uid, gid = struct.unpack('3i', raw)
    return dict(pid=pid, uid=uid, gid=gid)


def descriptor(conn):
    info = os.fstat(conn.fileno())
    ensure(stat.S_ISSOCK(info.st_mode), 'not a socket descriptor')
    return dict(fd=conn.fileno(), device=info.st_dev, inode=info.st_ino,
                uid=info.st_uid, gid=info.st_gid, socket=True,
                inheritable=os.get_inheritable(conn.fileno()),
                type=conn.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE))


def same_socket(first, second):
    return all(first[k] == second[k] for k in ('device', 'inode', 'uid', 'gid', 'socket', 'type'))


def live(fd):
    return not bool(select.select([fd], [], [], 0)[0])


def bind_process(expected):
    """Bind only an independently enrolled creation identity, retaining the handle."""
    ensure(peer.identity(expected['pid']) == expected, 'process identity mismatch before binding')
    fd = os.pidfd_open(expected['pid'], 0)
    try:
        ensure(peer.identity(expected['pid']) == expected and live(fd), 'process identity/liveness changed during binding')
        return fd
    except BaseException:
        os.close(fd)
        raise


def ready(event='ready', **extra):
    return dict(event=event, identity=peer.identity(os.getpid()), privilege=support.privilege(), **extra)


def fixed_request(pid):
    return dict(test_only='W2g-precommit', claimed_pid=pid, request='one-fixed-action')


def evaluate(conn, enrolled, retained_pidfd, variant):
    """Only this server-side guard decides; no parent allow/deny input."""
    ensure(variant in ('guarded', 'TEST-ONLY-omitted-liveness'), 'unknown guard variant')
    raw = peer.data_receive(conn)
    ensure(raw is not None, 'missing test request')
    request = json.loads(raw)
    ensure(request == fixed_request(enrolled['pid']), 'not the fixed test request')
    observed = credentials(conn)
    original_live = live(retained_pidfd)
    identity_matches = observed == {k: enrolled[k] for k in ('pid', 'uid', 'gid')}
    authorized = identity_matches and (original_live or variant == 'TEST-ONLY-omitted-liveness')
    reason = ('kernel-credentials-mismatch' if not identity_matches else
              'original-client-exited' if not authorized else
              'enrolled-client-live' if original_live else 'TEST-ONLY-stale-peer-authorized')
    return dict(event='evaluation', variant=variant, request=request, requests_received=1,
                kernel=observed, original_client_live=original_live,
                retained_pidfd=retained_pidfd, retained_pidfd_inheritable=os.get_inheritable(retained_pidfd),
                authorized_actions=int(authorized), reason=reason, evaluated_at=time.monotonic())


def server(endpoint):
    retained = None
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
        listener.settimeout(TIMEOUT)
        listener.bind(endpoint)
        os.chmod(endpoint, 0o600)
        listener.listen(1)
        support.write_message(1, ready())
        command = support.read_message(0)
        ensure(command['op'] == 'connect', 'invalid server setup')
        conn, _ = listener.accept()
        try:
            with conn:
                enrolled = command['enrolled']
                verification = peer.verify(conn, enrolled)
                ensure(verification['accepted'], 'initial enrolled-client verification failed')
                retained = bind_process(enrolled)
                support.write_message(1, ready('authenticated', verification=verification,
                                              retained_pidfd=retained, pidfd_live=live(retained),
                                              pidfd_inheritable=os.get_inheritable(retained),
                                              descriptor=descriptor(conn)))
                ensure(support.read_message(0) == {'op': 'evaluate'}, 'invalid evaluation barrier')
                support.write_message(1, evaluate(conn, enrolled, retained, command['variant']))
                ensure(support.read_message(0) == {'op': 'stop'}, 'invalid server shutdown')
        finally:
            if retained is not None:
                os.close(retained)


def holder(data_fd, control_fd):
    with socket.socket(fileno=data_fd) as conn, socket.socket(fileno=control_fd) as control:
        support.write_message(control.fileno(), ready('holder-ready', descriptor=descriptor(conn), kernel_server=credentials(conn)))
        while True:
            command = support.read_message(control.fileno())
            if command['op'] == 'ping':
                support.write_message(control.fileno(), ready('holder-alive', descriptor=descriptor(conn)))
            elif command['op'] == 'send':
                peer.data_send(conn, fixed_request(command['claim_pid']))
                support.write_message(control.fileno(), ready('request-sent', requests_sent=1, descriptor=descriptor(conn), sent_at=time.monotonic()))
            elif command['op'] == 'stop':
                support.write_message(control.fileno(), ready('holder-exiting'))
                return
            else:
                raise RuntimeError('unknown holder operation')


def client(endpoint, holder_control_fd):
    child = None
    support.write_message(1, ready())
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(TIMEOUT)
        command = support.read_message(0)
        ensure(command['op'] == 'connect', 'invalid client setup')
        conn.connect(endpoint)
        verification = peer.verify(conn, command['enrolled'])
        ensure(verification['accepted'], 'initial server verification failed')
        support.write_message(1, ready('authenticated', verification=verification, descriptor=descriptor(conn)))
        ensure(support.read_message(0) == {'op': 'spawn-holder'}, 'invalid holder barrier')
        passed = (conn.fileno(), holder_control_fd)
        child = subprocess.Popen([sys.executable, '-I', str(SCRIPT), '--holder', str(conn.fileno()), str(holder_control_fd)],
                                 pass_fds=passed, close_fds=True, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.close(holder_control_fd)
        support.write_message(1, ready('holder-spawned', child_identity=peer.identity(child.pid),
                                      descriptor=descriptor(conn), holder_control_fd=holder_control_fd, pass_fds=list(passed), close_fds=True))
        while True:
            command = support.read_message(0)
            if command['op'] == 'send':
                peer.data_send(conn, fixed_request(os.getpid()))
                support.write_message(1, ready('request-sent', requests_sent=1, descriptor=descriptor(conn), sent_at=time.monotonic()))
            elif command['op'] == 'reap-holder':
                code = child.wait(timeout=TIMEOUT)
                ensure(code == 0, 'holder failed under original client')
                support.write_message(1, ready('holder-reaped', child_pid=child.pid, exit_code=code))
            elif command['op'] in ('exit', 'stop'):
                support.write_message(1, ready('client-exiting', child_running=child.poll() is None))
                # The loss case deliberately exits without waiting for the holder.
                return
            else:
                raise RuntimeError('unknown client operation')


def close_resources(resources):
    errors = []
    for label, closer in resources:
        try:
            closer()
        except Exception as exc:
            errors.append(f'{label}: {type(exc).__name__}: {exc}')
    return errors


class Actor:
    def __init__(self, role, endpoint, passed=()):
        self.proc = None
        self.pidfd = None
        args = [sys.executable, '-I', str(SCRIPT), '--' + role, str(endpoint)]
        if role == 'client':
            args.append(str(passed[0]))
        self.proc = subprocess.Popen(args, pass_fds=passed, close_fds=True,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.initial = peer.identity(self.proc.pid)
        ensure(self.initial['ppid'] == os.getpid(), 'actor not owned direct child')
        self.pidfd = bind_process(self.initial)

    def send(self, message):
        support.write_message(self.proc.stdin.fileno(), message)

    def read(self):
        return support.read_message(self.proc.stdout.fileno())

    def cleanup(self):
        if self.proc is None:
            return dict(not_started=True, reaped=True, forced=False, exit_code=None, stderr='')
        forced = self.proc.poll() is None
        try:
            if forced:
                if self.pidfd is None:
                    self.proc.kill()  # owned, still-unreaped direct Popen child only
                else:
                    try:
                        signal.pidfd_send_signal(self.pidfd, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            _, error = self.proc.communicate(timeout=TIMEOUT)
            return dict(pid=self.proc.pid, reaped=True, forced=forced,
                        exit_code=self.proc.returncode, stderr=error.decode())
        finally:
            resources = [(f'actor stream {index}', stream.close) for index, stream in enumerate(
                         (self.proc.stdin, self.proc.stdout, self.proc.stderr)) if stream is not None]
            if self.pidfd is not None:
                resources.append(('actor pidfd', lambda: os.close(self.pidfd)))
            active_error = sys.exc_info()[1]
            errors = close_resources(resources)
            self.pidfd = None
            if errors:
                raise RuntimeError(f'actor close failures: {errors}; prior error: {active_error}') from active_error


class Case:
    def __init__(self, name):
        ensure(name in CASES, 'unknown W2g case')
        self.name = name
        self.root = None
        self.root_before = None
        self.sockets = {}
        self.actors = []
        self.holder_fd = None
        self.holder_identity = None
        self.holder_reaped = False
        self.parent_control = self.child_control = None
        self.report = dict(case=name, result='Fail', failures=[], trace=[], root=None, root_removed=False, runner_identity=peer.identity(os.getpid()))
        self.started = time.monotonic()

    def event(self, name, **details):
        self.report['trace'].append(dict(sequence=len(self.report['trace']) + 1,
                                         elapsed=time.monotonic() - self.started, event=name, **details))

    def start(self, role, passed=()):
        actor = Actor.__new__(Actor)
        self.actors.append(actor)  # partial startup remains registered for cleanup
        actor.__init__(role, self.root / 'peer.sock', passed)
        msg = actor.read()
        self.event(role + '-ready', reply=msg)
        ensure(msg['event'] == 'ready' and msg['identity'] == actor.initial, 'actor ready identity mismatch')
        self.check_privilege(msg)
        return actor

    def check_privilege(self, msg):
        privilege = msg['privilege']
        ensure(privilege['uid'] == privilege['euid'] == os.geteuid() != 0 and
               int(privilege['effective_capabilities'], 16) == 0, 'privileged/foreign actor')

    def command(self, actor, op, **details):
        self.event('actor-command', pid=actor.proc.pid, op=op, **details)
        actor.send(dict(op=op, **details))
        reply = actor.read()
        self.event('actor-reply', pid=actor.proc.pid, reply=reply)
        return reply

    def holder_message(self, op=None, **details):
        if op:
            self.event('holder-command', op=op, **details)
            support.write_message(self.parent_control.fileno(), dict(op=op, **details))
        reply = support.read_message(self.parent_control.fileno())
        self.event('holder-reply', reply=reply)
        return reply

    def validate_holder(self, msg, client, adopted, expected_event='holder-alive'):
        ensure(msg['event'] == expected_event, 'unexpected holder reply event')
        expected = dict(self.holder_identity, ppid=os.getpid() if adopted else client.proc.pid)
        observed = dict(identity=peer.identity(expected['pid']), pidfd_live=live(self.holder_fd), observed_at=time.monotonic())
        ensure(msg['identity'] == expected and observed['identity'] == expected and observed['pidfd_live'], 'holder identity/liveness mismatch')
        msg['runner_observed'] = observed
        self.check_privilege(msg)
        ensure(same_socket(self.report['client_socket'], msg['descriptor']), 'holder did not retain original connected socket')

    def run(self):
        self.root = Path(tempfile.mkdtemp(prefix='PROTOTYPE-W2g-'))
        self.report['root'] = str(self.root)
        self.root_before = peer.metadata(self.root)
        self.report['root_identity'] = self.root_before
        ensure(self.root_before['directory'] and self.root_before['uid'] == os.geteuid() and self.root_before['mode'] == '0o700', 'unsafe root')
        server_actor = self.start('server')
        path = self.root / 'peer.sock'
        self.sockets[path] = peer.metadata(path)
        ensure(self.sockets[path]['socket'] and self.sockets[path]['uid'] == os.geteuid() and self.sockets[path]['mode'] == '0o600', 'unsafe socket path')
        self.report['socket_path_identity'] = self.sockets[path]
        self.parent_control, self.child_control = socket.socketpair()  # trusted controls, NOT tested credential endpoint
        client_actor = self.start('client', (self.child_control.fileno(),))
        self.child_control.close()
        variant = 'TEST-ONLY-omitted-liveness' if self.name == CASES[2] else 'guarded'
        self.event('connect-barrier', enrolled_client=client_actor.initial, enrolled_server=server_actor.initial, variant=variant)
        server_actor.send(dict(op='connect', enrolled=client_actor.initial, variant=variant))
        client_actor.send(dict(op='connect', enrolled=server_actor.initial))
        sa, ca = server_actor.read(), client_actor.read()
        self.event('mutual-authentication', server=sa, client=ca)
        ensure(sa['identity'] == server_actor.initial and ca['identity'] == client_actor.initial, 'authenticated actor identity changed')
        self.check_privilege(sa)
        self.check_privilege(ca)
        ensure(sa['event'] == ca['event'] == 'authenticated' and sa['verification']['accepted'] and ca['verification']['accepted'], 'authentication failed')
        ensure(sa['pidfd_live'] and not sa['pidfd_inheritable'], 'server lacks noninheritable live retained pidfd')
        self.report.update(server_auth=sa, client_auth=ca, enrolled_client=client_actor.initial,
                           enrolled_server=server_actor.initial, client_socket=ca['descriptor'])
        spawned = self.command(client_actor, 'spawn-holder')
        ensure(spawned['event'] == 'holder-spawned' and spawned['child_identity']['ppid'] == client_actor.proc.pid, 'holder ownership mismatch')
        self.holder_identity = spawned['child_identity']
        self.holder_fd = bind_process(self.holder_identity)
        hr = self.holder_message()
        self.report['inheritance'] = dict(spawned=spawned, holder_ready=hr)
        self.validate_holder(hr, client_actor, False, 'holder-ready')
        ensure(hr['event'] == 'holder-ready' and same_socket(spawned['descriptor'], ca['descriptor']), 'holder readiness/descriptor mismatch')
        ensure(spawned['close_fds'] and not spawned['descriptor']['inheritable'] and hr['descriptor']['inheritable'] and spawned['descriptor']['fd'] in spawned['pass_fds'], 'explicit descriptor inheritance not established')
        lost = self.name != 'healthy'
        if lost:
            exited = self.command(client_actor, 'exit')
            ensure(exited['event'] == 'client-exiting' and exited['child_running'], 'client did not leave surviving holder')
            code = client_actor.proc.wait(timeout=TIMEOUT)
            ensure(code == 0 and not live(client_actor.pidfd), 'original client exit not observed')
            self.event('original-client-exited', identity=client_actor.initial, exit_code=code, pidfd_live=live(client_actor.pidfd))
        else:
            ensure(live(client_actor.pidfd), 'healthy original client already exited')
        self.report['original_client_before'] = dict(identity=client_actor.initial, pidfd_live=live(client_actor.pidfd), observed_at=time.monotonic(), exit_code=client_actor.proc.returncode)
        before = self.holder_message('ping')
        self.validate_holder(before, client_actor, lost)
        self.report['holder_before'] = before
        if lost:
            sent = self.holder_message('send', claim_pid=client_actor.proc.pid)
        else:
            sent = self.command(client_actor, 'send')
        ensure(sent['event'] == 'request-sent' and sent['requests_sent'] == 1 and same_socket(ca['descriptor'], sent['descriptor']), 'request source/descriptor mismatch')
        self.report['request_sender'] = sent
        evaluation = self.command(server_actor, 'evaluate')
        self.report['evaluation'] = evaluation
        after = self.holder_message('ping')
        self.validate_holder(after, client_actor, lost)
        self.report['holder_after'] = after
        self.report['original_client_after'] = dict(identity=client_actor.initial, pidfd_live=live(client_actor.pidfd), observed_at=time.monotonic(), exit_code=client_actor.proc.returncode)
        validate_result(self.report)
        self.report['result'] = 'Detected' if self.name == CASES[2] else 'Pass'
        stopped = self.holder_message('stop')
        ensure(stopped['event'] == 'holder-exiting', 'holder shutdown missing')
        if lost:
            status = support.wait_pidfd(self.holder_fd)
            ensure(status.si_pid == self.holder_identity['pid'] and status.si_code == os.CLD_EXITED and status.si_status == 0, 'adopted holder failed')
            self.report['holder_reap'] = dict(pid=status.si_pid, exit_code=status.si_status, by='runner', reaped=True)
            self.holder_reaped = True
        else:
            reaped = self.command(client_actor, 'reap-holder')
            ensure(reaped['event'] == 'holder-reaped' and reaped['child_pid'] == self.holder_identity['pid'] and reaped['exit_code'] == 0 and not live(self.holder_fd), 'holder reap not confirmed')
            self.report['holder_reap'] = dict(pid=reaped['child_pid'], exit_code=0, by='original-client', reaped=True)
            self.holder_reaped = True
            self.command(client_actor, 'stop')
            ensure(client_actor.proc.wait(timeout=TIMEOUT) == 0, 'healthy client shutdown failed')
        server_actor.send(dict(op='stop'))
        ensure(server_actor.proc.wait(timeout=TIMEOUT) == 0, 'server shutdown failed')

    def cleanup(self):
        self.report['actor_cleanup'] = []
        for actor in self.actors:
            try:
                if hasattr(actor, 'proc'):
                    self.report['actor_cleanup'].append(actor.cleanup())
            except Exception as exc:
                self.report['failures'].append(f'actor cleanup: {type(exc).__name__}: {exc}')
        try:
            if self.holder_fd is not None and not self.holder_reaped:
                if live(self.holder_fd):
                    signal.pidfd_send_signal(self.holder_fd, signal.SIGKILL)
                status = support.wait_pidfd(self.holder_fd)
                self.holder_reaped = True
                self.report['holder_reap'] = dict(pid=status.si_pid, exit_code=status.si_status, by='runner-fallback', reaped=True)
                self.report['failures'].append('forced/exceptional holder cleanup')
        except Exception as exc:
            self.report['failures'].append(f'holder cleanup: {exc}')
        finally:
            resources = []
            if self.holder_fd is not None:
                resources.append(('holder pidfd', lambda: os.close(self.holder_fd)))
            for index, control in enumerate((self.parent_control, self.child_control)):
                if control is not None:
                    resources.append((f'holder control {index}', control.close))
            close_errors = close_resources(resources)
            self.holder_fd = None
            self.report['close_errors'] = close_errors
            self.report['failures'].extend(close_errors)
        clean = len(self.report['actor_cleanup']) == len(self.actors) and all(c['reaped'] for c in self.report['actor_cleanup'])
        try:
            ensure(not close_errors and clean and not support.direct_children() and (self.holder_identity is None or self.holder_reaped), 'uncertain process cleanup; preserve root')
            if self.root is None:
                self.report['root_not_allocated'] = True
                self.report['root_removed'] = True
            else:
                ensure(self.root_before is not None, 'unknown root identity; preserve root')
                self.report['root_removed'] = peer.cleanup_root(self.root, self.root_before, self.sockets)
            ensure(self.report['root_removed'], 'root removal not confirmed')
        except Exception as exc:
            self.report['failures'].append(f'filesystem cleanup: {exc}')
        if not clean or any(c['forced'] or c['exit_code'] != 0 or c['stderr'] for c in self.report['actor_cleanup']):
            self.report['failures'].append('actor failure or forced cleanup')
        if self.report['failures']:
            self.report['result'] = 'Fail'


def validate_actor_snapshot(snapshot, expected, event):
    ensure(snapshot['event'] == event and snapshot['identity'] == expected, 'actor identity/reply mismatch')
    privilege = snapshot['privilege']
    ensure(type(privilege['uid']) is int and type(privilege['euid']) is int and
           privilege['uid'] == privilege['euid'] == expected['uid'] != 0 and
           isinstance(privilege['effective_capabilities'], str) and
           int(privilege['effective_capabilities'], 16) == 0, 'privileged/mismatched actor snapshot')


def validate_socket_snapshot(record):
    ensure(record['socket'] is True and type(record['type']) is int and record['type'] == socket.SOCK_STREAM,
           'not a stream socket snapshot')
    for key in ('fd', 'device', 'inode', 'uid', 'gid'):
        ensure(type(record[key]) is int and record[key] >= 0, 'invalid socket descriptor metadata')
    ensure(type(record['inheritable']) is bool, 'invalid socket inheritance flag')


def validate_result(report):
    name, r = report['case'], report['evaluation']
    ensure(name in CASES and r['event'] == 'evaluation', 'invalid case/result')
    lost = name != 'healthy'
    mutant = name == CASES[2]
    enrolled = report['enrolled_client']
    runner_pid = report['runner_identity']['pid']
    ensure(enrolled['ppid'] == runner_pid and report['enrolled_server']['ppid'] == runner_pid, 'initial actors not owned direct children')
    ensure(enrolled['uid'] == report['enrolled_server']['uid'] != 0 and enrolled['gid'] == report['enrolled_server']['gid'], 'account scope mismatch')
    for key, expected in [('server_auth', enrolled), ('client_auth', report['enrolled_server'])]:
        auth = report[key]
        actual_actor = report['enrolled_server'] if key == 'server_auth' else enrolled
        validate_actor_snapshot(auth, actual_actor, 'authenticated')
        validate_socket_snapshot(auth['descriptor'])
        v = auth['verification']
        ensure(auth['event'] == 'authenticated' and v['accepted'] is True and v['reason'] == 'enrolled-live-process-instance' and 'error' not in v, 'missing initial authentication')
        ensure(v['enrolled'] == v['before'] == v['after'] == expected and v['pidfd_live'] is True, 'missing initial creation/liveness proof')
        ensure(v['kernel'] == {k: expected[k] for k in ('pid', 'uid', 'gid')}, 'initial kernel identity mismatch')
    ensure(report['server_auth']['pidfd_live'] is True and report['server_auth']['pidfd_inheritable'] is False, 'retained pidfd not initially live/private')
    for key in ('original_client_before', 'original_client_after'):
        sample = report[key]
        ensure(sample['identity'] == enrolled and sample['pidfd_live'] is (not lost) and sample['exit_code'] == (0 if lost else None), 'independent original-client lifetime proof missing')
    inherited = report['inheritance']
    spawned, holder_ready = inherited['spawned'], inherited['holder_ready']
    validate_actor_snapshot(spawned, enrolled, 'holder-spawned')
    validate_actor_snapshot(holder_ready, spawned['child_identity'], 'holder-ready')
    ensure(spawned['child_identity']['pid'] not in (enrolled['pid'], report['enrolled_server']['pid'], runner_pid), 'holder is not a distinct process')
    ensure(holder_ready['identity']['uid'] == enrolled['uid'] and holder_ready['identity']['gid'] == enrolled['gid'], 'holder account changed')
    for record in (spawned['descriptor'], holder_ready['descriptor'], report['client_socket']):
        validate_socket_snapshot(record)
    ensure(report['client_socket'] == report['client_auth']['descriptor'], 'client socket/authentication record diverged')
    ensure(holder_ready['kernel_server'] == {k: report['enrolled_server'][k] for k in ('pid', 'uid', 'gid')}, 'holder server credentials changed')
    passed = spawned['pass_fds']
    ensure(len(passed) == 2 and all(type(fd) is int and fd >= 0 for fd in passed) and len(set(passed)) == 2 and set(passed) == {spawned['descriptor']['fd'], spawned['holder_control_fd']}, 'unexpected inherited descriptor set')
    ensure(spawned['event'] == 'holder-spawned' and spawned['child_identity'] == holder_ready['identity'] and holder_ready['identity']['ppid'] == enrolled['pid'], 'initial holder ownership mismatch')
    ensure(spawned['close_fds'] is True and spawned['descriptor']['fd'] in spawned['pass_fds'] and spawned['descriptor']['inheritable'] is False and holder_ready['descriptor']['inheritable'] is True, 'missing explicit descriptor inheritance')
    ensure(same_socket(spawned['descriptor'], report['client_socket']) and same_socket(holder_ready['descriptor'], report['client_socket']), 'initial inherited socket mismatch')

    ensure(r['variant'] == ('TEST-ONLY-omitted-liveness' if mutant else 'guarded'), 'wrong guard variant')
    ensure(type(r['original_client_live']) is bool and r['original_client_live'] is not lost, 'wrong original-client liveness')
    enrolled = report['enrolled_client']
    ensure(r['kernel'] == {k: enrolled[k] for k in ('pid', 'uid', 'gid')}, 'kernel identity not the original enrolled client')
    ensure(r['retained_pidfd'] == report['server_auth']['retained_pidfd'] and r['retained_pidfd_inheritable'] is False, 'retained pidfd changed')
    ensure(r['request'] == fixed_request(enrolled['pid']) and type(r['requests_received']) is int and r['requests_received'] == 1, 'missing or changed request')
    expected = int(not lost or mutant)
    ensure(type(r['authorized_actions']) is int and r['authorized_actions'] == expected, 'unexpected authorized-action count')
    reason = 'TEST-ONLY-stale-peer-authorized' if mutant else ('original-client-exited' if lost else 'enrolled-client-live')
    ensure(r['reason'] == reason, 'wrong action/rejection reason')
    before, after, sender = report['holder_before'], report['holder_after'], report['request_sender']
    holder_id = report['inheritance']['holder_ready']['identity']
    for msg in (before, after):
        ensure(msg['identity']['pid'] == holder_id['pid'] and msg['identity']['start_ticks'] == holder_id['start_ticks'], 'holder instance changed')
        expected_identity = dict(holder_id, ppid=runner_pid if lost else enrolled['pid'])
        validate_actor_snapshot(msg, expected_identity, 'holder-alive')
        validate_socket_snapshot(msg['descriptor'])
        ensure(msg['identity'] == expected_identity and msg['runner_observed']['identity'] == expected_identity and msg['runner_observed']['pidfd_live'] is True, 'holder survival/adoption proof missing')
        ensure(same_socket(report['client_socket'], msg['descriptor']), 'holder socket changed')
    validate_actor_snapshot(sender, dict(holder_id, ppid=runner_pid) if lost else enrolled, 'request-sent')
    validate_socket_snapshot(sender['descriptor'])
    ensure(same_socket(report['client_socket'], sender['descriptor']), 'request not sent over retained socket')
    times = (report['original_client_before']['observed_at'], before['runner_observed']['observed_at'], sender['sent_at'], r['evaluated_at'], after['runner_observed']['observed_at'], report['original_client_after']['observed_at'])
    ensure(all(type(t) in (int, float) and 0 < t < float('inf') for t in times) and list(times) == sorted(times), 'barrier/request/evaluation ordering inconsistent')
    ensure(type(sender['requests_sent']) is int and sender['requests_sent'] == 1, 'wrong sent count')
    ensure(sender['identity']['pid'] != r['kernel']['pid'] if lost else sender['identity']['pid'] == r['kernel']['pid'], 'sender/kernel credential distinction missing')


def main():
    paths = [SCRIPT, SCRIPT.with_name('test_checks.py'), PEER_HELPER, peer.SUPPORT]
    report = dict(scope='W2g only; pre-commit test authority; no package action',
                  started_utc=datetime.now(timezone.utc).isoformat(),
                  environment=dict(platform=platform.platform(), python=sys.version, privilege=support.privilege(), gid=os.getgid()),
                  timing='Five-second diagnostic watchdogs only',
                  source_hashes={str(p.relative_to(SCRIPT.parent.parent)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                  cases=[], failures=[], subreaper={})
    original = None
    try:
        ensure(sys.platform == 'linux' and os.getuid() == os.geteuid() != 0 and not int(support.privilege()['effective_capabilities'], 16), 'Blocked: unprivileged Linux required')
        ensure(not support.direct_children(), 'Blocked: runner must initially be child-free')
        ensure(hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal') and hasattr(socket, 'SO_PEERCRED'), 'Blocked: missing native primitives')
        original = support.subreaper()
        report['subreaper']['before'] = original
        support.subreaper(1)
        report['subreaper']['during'] = support.subreaper()
        ensure(report['subreaper']['during'] == 1, 'Blocked: child adoption unavailable')
        for name in CASES:
            case = Case(name)
            report['cases'].append(case.report)
            try:
                case.run()
            except Exception as exc:
                case.report['failures'].append(f'{type(exc).__name__}: {exc}')
            finally:
                case.cleanup()
            ensure(case.report['result'] == ('Detected' if name == CASES[2] else 'Pass'), 'case failed; dependent cases stopped')
    except Exception as exc:
        report['failures'].append(f'{type(exc).__name__}: {exc}')
    finally:
        if original is not None:
            try:
                support.subreaper(original)
                report['subreaper']['after'] = support.subreaper()
                ensure(report['subreaper']['after'] == original, 'subreaper restoration failed')
            except Exception as exc:
                report['failures'].append(f'restoration: {exc}')
        report['remaining_children'] = support.direct_children()
        if report['remaining_children']:
            report['failures'].append('children remain; no unknown process signaled')
    report['passed'] = len(report['cases']) == 3 and not report['failures'] and [c['result'] for c in report['cases']] == ['Pass', 'Pass', 'Detected']
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.exit(main())
    elif sys.argv[1] == '--server':
        server(sys.argv[2])
    elif sys.argv[1] == '--client':
        client(sys.argv[2], int(sys.argv[3]))
    elif sys.argv[1] == '--holder':
        holder(int(sys.argv[2]), int(sys.argv[3]))
    else:
        raise RuntimeError('unknown fixed actor role')
