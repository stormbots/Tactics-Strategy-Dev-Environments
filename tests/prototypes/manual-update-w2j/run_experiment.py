"""W2j only: kernel-installed unexpected FD rejection. No production authority."""
import array
from datetime import datetime, timezone
import errno
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import signal
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time

SCRIPT = Path(__file__).resolve()
HELPER = SCRIPT.parent.parent / 'manual-update-w2i/run_experiment.py'
spec = importlib.util.spec_from_file_location('w2j_reviewed_w2i_definitions', HELPER)
i = importlib.util.module_from_spec(spec)
spec.loader.exec_module(i)  # Definitions only; no W2i scenario or entrypoint runs.
require = i.require
CASES = ('J1', 'J2')
TIMEOUT = i.TIMEOUT


def fd_info(fd):
    st = os.fstat(fd)
    return dict(fd=fd, dev=st.st_dev, ino=st.st_ino, mode=st.st_mode,
                fdflags=fcntl.fcntl(fd, fcntl.F_GETFD), flags=fcntl.fcntl(fd, fcntl.F_GETFL))


def fd_inventory():
    """Single-threaded snapshot; exclude only the already-closed listdir handle."""
    result = []
    for name in sorted(os.listdir('/proc/self/fd'), key=int):
        try:
            result.append(fd_info(int(name)))
        except OSError as exc:
            if exc.errno != errno.EBADF:
                raise
    return result


def rights_from(ancillary):
    result = []
    for level, kind, raw in ancillary:
        if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
            ints = array.array('i')
            # Inventory all delivered integers; unsupported partial delivery is
            # rejected, not injected or interpreted as a passing W2j schedule.
            ints.frombytes(raw[:len(raw)-len(raw) % ints.itemsize])
            result.extend(ints)
    return result


def immediately_closed(fd):
    """No open/listdir/recv occurs between validation cleanup and these checks."""
    result = dict(fd=fd)
    for name, check in [('fstat', lambda: os.fstat(fd)), ('getfd', lambda: fcntl.fcntl(fd, fcntl.F_GETFD))]:
        try:
            check()
            result[name+'_errno'] = None
        except OSError as exc:
            result[name+'_errno'] = exc.errno
    return result


def observe_receive(conn, enrolled, retained, attempt):
    before = fd_inventory()
    data, anc, flags, _ = conn.recvmsg(i.MAX_RECORD, i.ANCILLARY, socket.MSG_CMSG_CLOEXEC)
    delivered = rights_from(anc)
    installed, observation_errors = [], []
    # Metadata observations do not dispatch or authorize the payload. Always run
    # the unchanged W2i validator/cleanup, even if observing a delivered FD fails.
    try:
        for fd in delivered:
            installed.append(fd_info(fd))
    except OSError as exc:
        observation_errors.append(str(exc))
    finally:
        decision = i.validate(data, anc, flags, enrolled,
                              dict(tag='action', attempt=attempt, claim_pid=enrolled['pid']), i.live(retained))
    # Crucially, test closure BEFORE fd_inventory allocates its directory handle.
    closed = [immediately_closed(fd) for fd in delivered]
    after = fd_inventory()
    raw_creds = [list(struct.unpack('3i', raw)) for level, kind, raw in anc
                 if level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS and len(raw) == struct.calcsize('3i')]
    return dict(decision=decision, recvmsg_flags_argument=socket.MSG_CMSG_CLOEXEC,
                received_flags=flags, before=before, installed=installed, immediately_closed=closed,
                after=after, observation_errors=observation_errors, raw_credentials=raw_creds,
                ancillary=[dict(level=l, type=t, bytes=len(raw)) for l,t,raw in anc],
                fixture_payload_matches=data == i.frame('action', attempt, enrolled['pid']),
                payload_sha256=hashlib.sha256(data).hexdigest(), retained_pidfd=retained,
                pidfd_live=i.live(retained), descriptor=i.descriptor(conn))


def sender_send(conn, attempt, attach_fd):
    original = i.identity()
    explicit = [original['pid'], original['uids'][0], original['gids'][0]]
    data = i.frame('action', attempt, original['pid'])
    anc = [(socket.SOL_SOCKET, socket.SCM_CREDENTIALS, struct.pack('3i', *explicit))]
    if attach_fd is not None:
        anc.append((socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', [attach_fd]).tobytes()))
    result = dict(identity=original, requested_credentials=explicit, attached_fds=[] if attach_fd is None else [attach_fd],
                  record_bytes=len(data), payload_sha256=hashlib.sha256(data).hexdigest(), descriptor=i.descriptor(conn))
    try:
        result.update(return_value=conn.sendmsg([data], anc), errno=None)
    except OSError as exc:
        result.update(return_value=-1, errno=exc.errno)
    return result


def actor(role, endpoint):
    conn, listener, retained = None, None, None
    pipe = []
    actions = sent = received = 0
    enrolled, attempt = None, None
    try:
        require(role in ('server', 'client'), 'unknown W2j actor')
        i.unprivileged(i.identity())
        if role == 'server':
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            listener.settimeout(TIMEOUT)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            require(i.descriptor(listener)['passcred'] == 1, 'Blocked: listener options')
            listener.bind(endpoint); os.chmod(endpoint, 0o600); listener.listen(1)
            initial = dict(identity=i.identity(), listener=i.descriptor(listener))
        else:
            conn = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            conn.settimeout(TIMEOUT)
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            require(i.descriptor(conn)['passcred'] == 1, 'Blocked: client options')
            initial = dict(identity=i.identity(), descriptor=i.descriptor(conn))
        i.write_control(1, initial)
        while True:
            c = i.read_control(0); op = c['op']
            if op == 'enroll':
                require(enrolled is None, 're-enrollment forbidden')
                enrolled, attempt = c['identity'], c['attempt']
                retained = i.bind(enrolled)
                require(not os.get_inheritable(retained), 'inheritable pidfd')
                i.write_control(1, dict(enrolled=enrolled, pidfd=retained, pidfd_live=i.live(retained), inheritable=os.get_inheritable(retained)))
            elif op == 'connect':
                require(role == 'client' and enrolled is not None, 'connect before enrollment')
                conn.connect(endpoint)
                i.write_control(1, i.snapshot(conn, sent))
            elif op == 'accept':
                require(role == 'server' and enrolled is not None, 'accept before enrollment')
                conn, _ = listener.accept(); conn.settimeout(TIMEOUT)
                require(i.descriptor(conn)['passcred'] == 1, 'Blocked: accepted credential option')
                i.write_control(1, i.snapshot(conn, sent))
            elif op == 'hello-send':
                require(role == 'client', 'wrong hello role')
                result = i.send(conn, 'hello', attempt, os.getpid())
                require(result['errno'] is None, 'hello send failure')
                i.write_control(1, result)
            elif op == 'hello-receive':
                require(role == 'server', 'wrong hello receive role')
                verify = i.receive(conn, enrolled, retained, dict(tag='hello', attempt=attempt, claim_pid=enrolled['pid']))
                require(verify['accepted'], 'hello rejection')
                reply = i.send(conn, 'reply', attempt, os.getpid())
                require(reply['errno'] is None, 'hello reply failure')
                i.write_control(1, dict(verification=verify, reply=reply))
            elif op == 'reply-receive':
                require(role == 'client', 'wrong reply role')
                verify = i.receive(conn, enrolled, retained, dict(tag='reply', attempt=attempt, claim_pid=enrolled['pid']))
                require(verify['accepted'], 'reply rejection')
                i.write_control(1, verify)
            elif op == 'make-pipe':
                require(role == 'client' and not pipe, 'invalid pipe creation')
                pipe = list(os.pipe())
                i.write_control(1, dict(identity=i.identity(), pipe=[fd_info(fd) for fd in pipe]))
            elif op == 'send-action':
                require(role == 'client' and sent == 0, 'invalid send/count')
                # Only the fixed sender schedule knows the attach selector.
                result = sender_send(conn, attempt, pipe[0] if c['attach'] else None)
                sent += 1
                result['requests_sent'] = sent
                i.write_control(1, result)
            elif op == 'evaluate':
                require(role == 'server' and received == 0, 'invalid evaluation/count')
                result = observe_receive(conn, enrolled, retained, attempt)
                received += 1
                if result['decision']['accepted']:
                    actions += 1
                    reply = i.send(conn, 'reply', attempt, os.getpid())
                    require(reply['errno'] is None, 'action reply failure')
                result.update(authorized_actions=actions, requests_received=received)
                i.write_control(1, result)
            elif op == 'status':
                result = i.snapshot(conn, sent)
                result.update(pipe=[fd_info(fd) for fd in pipe], authorized_actions=actions, requests_received=received)
                i.write_control(1, result)
            elif op == 'stop':
                i.write_control(1, dict(exiting_pid=os.getpid(), actions=actions, requests_sent=sent,
                                        owned_pipe_fds_closing=list(pipe)))
                return
            else:
                raise RuntimeError('unknown W2j operation')
    finally:
        for fd in pipe:
            os.close(fd)
        if retained is not None: os.close(retained)
        if conn is not None: conn.close()
        if listener is not None: listener.close()


class Actor(i.Actor):
    """Reuse reviewed command/wait cleanup; launch only this W2j script."""
    def __init__(self, role, endpoint):
        self.stopping = False
        self.proc, self.fd = None, None
        self.proc = subprocess.Popen([sys.executable, '-I', str(SCRIPT), '--actor', role, str(endpoint)],
                                     close_fds=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.info = i.identity(self.proc.pid)
        require(self.info['ppid'] == os.getpid(), 'not a direct owned child')
        self.fd = i.bind(self.info)
        self.initial = i.read_control(self.proc.stdout.fileno())
        if 'error' in self.initial:
            prefix = 'Blocked: ' if self.initial['error'].startswith('PermissionError:') else ''
            raise RuntimeError(prefix+str(self.initial))
        require(self.initial['identity'] == self.info, 'actor instance changed')


def verify_evaluation(case, evaluation, sender):
    """Pure evidence checks; expected result cannot control receiver authority."""
    i.check_count(evaluation['authorized_actions'], 'invalid action count')
    i.check_count(evaluation['requests_received'], 'invalid request count')
    require(evaluation['requests_received'] == 1, 'wrong request count')
    require(not evaluation['observation_errors'], 'FD observation failed')
    require(evaluation['received_flags'] & (socket.MSG_TRUNC | socket.MSG_CTRUNC) == 0, 'unexpected truncation; stop W2j')
    require(evaluation['recvmsg_flags_argument'] == socket.MSG_CMSG_CLOEXEC, 'missing atomic CLOEXEC receive')
    expected = sender['identity']
    require(evaluation['raw_credentials'] == [[expected['pid'], expected['uids'][0], expected['gids'][0]]], 'wrong kernel sender credentials')
    require(evaluation['pidfd_live'] is True and evaluation['fixture_payload_matches'] is True, 'invalid otherwise-eligible fixture')
    require(evaluation['payload_sha256'] == sender['payload_sha256'], 'different payload')
    require(evaluation['before'] == evaluation['after'], 'receiver FD inventory changed')
    d = evaluation['decision']
    if case == 'J1':
        require(evaluation['authorized_actions'] == 1 and d['accepted'] is True, 'failed healthy control')
        require(not evaluation['installed'] and not evaluation['immediately_closed'] and sender['attached_fds'] == [], 'unexpected healthy descriptor')
    else:
        if evaluation['authorized_actions'] > 0 or d['accepted'] is True:
            return 'CounterexampleDetected'
        require(evaluation['authorized_actions'] == 0 and d['reason'] == 'unexpected ancillary/descriptor', 'wrong descriptor rejection')
        require(d['delivered_fds_closed'] == 1 and len(evaluation['installed']) == len(evaluation['immediately_closed']) == 1, 'missing installed/closed descriptor evidence')
        installed, closed = evaluation['installed'][0], evaluation['immediately_closed'][0]
        require(installed['fd'] == closed['fd'] and installed['fd'] not in [fd['fd'] for fd in evaluation['before']], 'installed descriptor identity')
        require(installed['fdflags'] & fcntl.FD_CLOEXEC != 0, 'received FD lacks CLOEXEC')
        require(closed['fstat_errno'] == errno.EBADF and closed['getfd_errno'] == errno.EBADF, 'received descriptor still open/ambiguous')
        original = sender['sent_pipe']
        require(stat.S_ISFIFO(installed['mode']) and all(installed[k] == original[k] for k in ('dev','ino','mode','flags')), 'received FD differs from sender pipe')
        require(sender['attached_fds'] == [original['fd']], 'not exactly one owned attachment')
    return 'Expected'


def run_case(case):
    report = dict(case=case, trace=[], failures=[], cleanup={})
    actors = []
    root = Path(tempfile.mkdtemp(prefix='w2j-')); original_root = root.stat()
    endpoint = root/'record.sock'; original_socket = None
    report['fixture'] = dict(root=str(root), dev=original_root.st_dev, ino=original_root.st_ino, mode=oct(original_root.st_mode & 0o777))
    def event(name, value):
        report['trace'].append(dict(index=len(report['trace']), barrier=name, at=time.monotonic(), evidence=value))
        return value
    def command(a, name, op, **kwargs):
        return event(name, a.command(op, **kwargs))
    try:
        for role in ('server','client'):
            a = Actor.__new__(Actor); actors.append(a); a.__init__(role, endpoint)
            i.unprivileged(a.info)
            require(a.info['namespaces'] == i.identity()['namespaces'], 'Blocked: namespace mismatch')
            event(role+'-ready-before-connect', a.initial)
        server, client = actors
        original_socket = endpoint.stat()
        report['socket_fixture'] = dict(dev=original_socket.st_dev, ino=original_socket.st_ino, mode=oct(original_socket.st_mode & 0o777))
        require(original_root.st_mode & 0o777 == 0o700 and original_socket.st_mode & 0o777 == 0o600, 'fixture modes')
        command(server,'trusted-client-enrollment','enroll',identity=client.info,attempt=case)
        command(client,'trusted-server-enrollment','enroll',identity=server.info,attempt=case)
        command(client,'connect-permitted','connect')
        command(server,'accepted-passcred-verified','accept')
        command(client,'hello-send-permitted','hello-send')
        command(server,'client-credentials-and-server-reply','hello-receive')
        command(client,'server-reply-verified','reply-receive')
        pipe_before = None
        if case == 'J2':
            pipe_before = command(client,'owned-pipe-created','make-pipe')['pipe']
        command(server,'receiver-before-send','status')
        before = command(client,'sender-before','status')
        sent = command(client,'action-send-permitted','send-action',attach=case == 'J2')
        require(sent['identity'] == client.info, 'changed sender')
        require(sent['return_value'] == sent['record_bytes'] and sent['errno'] is None and sent['requests_sent'] == 1, 'short/failed send')
        require(sent['requested_credentials'] == [client.info['pid'], client.info['uids'][0], client.info['gids'][0]], 'explicit credential control missing')
        if pipe_before is not None:
            sent['sent_pipe'] = pipe_before[0]
        evaluation = command(server,'kernel-receive-validation-and-immediate-close','evaluate')
        # Preserve any observed unauthorized acceptance even if another evidence
        # check (for example an FD leak) fails in the same observation.
        i.check_count(evaluation['authorized_actions'], 'invalid observed action count')
        report['action_count'] = evaluation['authorized_actions']
        if case == 'J2' and (evaluation['authorized_actions'] > 0 or evaluation['decision']['accepted'] is True):
            report['counterexample'] = evaluation
        disposition = verify_evaluation(case,evaluation,sent)
        if disposition == 'CounterexampleDetected':
            report['counterexample'] = evaluation
            raise RuntimeError('unexpected descriptor-authorized action')
        report['action_count'] = evaluation['authorized_actions']
        if case == 'J1': command(client,'healthy-action-reply-verified','reply-receive')
        after = command(client,'sender-after','status')
        require(before['pipe'] == after['pipe'] == (pipe_before or []), 'sender descriptors changed/closed')
        require(after['requests_sent'] == 1 and after['identity'] == client.info, 'sender accounting/identity changed')
        require(i.same_endpoint(sent['descriptor'],after['descriptor']), 'sender endpoint changed')
        for a in actors:
            event('runner-instance-after-'+str(a.info['pid']),dict(identity=i.identity(a.info['pid']), pidfd_live=i.live(a.fd)))
            require(i.identity(a.info['pid']) == a.info and i.live(a.fd), 'actor changed/exited')
        for a in reversed(actors): command(a,'stop-'+str(a.info['pid']),'stop')
        report['result'] = 'Pass'
    except BaseException as exc:
        report['failures'].append(str(exc))
        report['result'] = 'CounterexampleDetected' if report.get('counterexample') else ('Blocked' if str(exc).startswith('Blocked:') else 'Fail')
    finally:
        report['cleanup']['actors'] = []
        report['initializations'] = [getattr(a,'initial',None) for a in actors]
        for a in reversed(actors):
            try: report['cleanup']['actors'].append(a.close())
            except BaseException as exc: report['failures'].append('actor cleanup: '+str(exc))
        try:
            require(len(report['cleanup']['actors']) == len(actors) and all(a['reaped'] for a in report['cleanup']['actors']), 'uncertain actor reaping')
            if report.get('result') == 'Pass':
                require(all(a['exit_code'] == 0 and not a['forced'] for a in report['cleanup']['actors']), 'unexpected cleanup/exit')
            require(not root.is_symlink() and (root.stat().st_dev,root.stat().st_ino) == (original_root.st_dev,original_root.st_ino), 'root replaced')
            if endpoint.exists():
                require(original_socket is not None and not endpoint.is_symlink() and (endpoint.stat().st_dev,endpoint.stat().st_ino) == (original_socket.st_dev,original_socket.st_ino), 'socket replaced')
                endpoint.unlink()
            root.rmdir(); report['cleanup']['root_removed'] = not root.exists()
        except BaseException as exc: report['failures'].append('fixture cleanup: '+str(exc))
        if report['failures'] and report.get('result') == 'Pass': report['result'] = 'Fail'
    return report


def main(output):
    report = dict(started=datetime.now(timezone.utc).isoformat(), environment=dict(platform=platform.platform(), kernel=platform.release(), python=sys.version, runner=i.identity()),
                  source_sha256=hashlib.sha256(SCRIPT.read_bytes()).hexdigest(), helper_sha256=hashlib.sha256(HELPER.read_bytes()).hexdigest(),
                  limits=dict(record=i.MAX_RECORD, ancillary=i.ANCILLARY, control=i.MAX_CONTROL, watchdog_seconds=TIMEOUT), cases=[],
                  authentication_safety='Unproven', production_readiness=False, finalization_failures=[])
    fd_before, sub_before = None, None
    try:
        i.unprivileged(report['environment']['runner'])
        for name in ('SCM_RIGHTS','SCM_CREDENTIALS','SO_PASSCRED','SOCK_SEQPACKET','MSG_CMSG_CLOEXEC'):
            require(hasattr(socket,name),'Blocked: missing '+name)
        require(hasattr(os,'pidfd_open') and hasattr(signal,'pidfd_send_signal'),'Blocked: missing pidfd primitives')
        fd_before = fd_inventory(); sub_before = i.subreaper()
        report['runner_before'] = dict(fds=fd_before, subreaper=sub_before)
        for case in CASES:
            report['cases'].append(run_case(case))
            Path(output).write_text(json.dumps(report,indent=2)+'\n')
            if report['cases'][-1]['result'] != 'Pass': break
    except BaseException as exc: report['failure'] = str(exc)
    finally:
        try:
            after = fd_inventory(); sub_after = i.subreaper()
            report['runner_after'] = dict(fds=after,subreaper=sub_after)
            require(fd_before == after and sub_before == sub_after, 'runner FD/settings mismatch')
        except BaseException as exc: report['finalization_failures'].append(str(exc))
        report['diagnostic_success'] = (len(report['cases']) == 2 and all(c['result'] == 'Pass' and not c['failures'] for c in report['cases'])
                                        and not report.get('failure') and not report['finalization_failures'])
        counterexample = any(c.get('counterexample') for c in report['cases'])
        report['authentication_safety'] = 'CounterexampleDetected' if counterexample else 'Unproven'
        report['primitive_result'] = 'Pass' if report['diagnostic_success'] else ('CounterexampleDetected' if counterexample else 'Incomplete/Fail/Blocked')
        Path(output).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('diagnostic_success','primitive_result','authentication_safety','production_readiness')}))
    return 0 if report['diagnostic_success'] else 1


if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1] == '--actor':
        try: actor(sys.argv[2],sys.argv[3])
        except BaseException as exc:
            i.write_control(1,dict(error=type(exc).__name__+': '+str(exc)))
            sys.exit(1)
    else: sys.exit(main(sys.argv[1]))
