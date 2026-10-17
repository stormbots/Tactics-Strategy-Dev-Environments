"""W2i only: unprivileged record-credential primitive; NOT production authentication."""
import array
import ctypes
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import select
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time

SCRIPT = Path(__file__).resolve()
TIMEOUT = 5  # test-only per-operation watchdog, not production timing
MAX_RECORD = 16384
MAX_CONTROL = 4096
ANCILLARY = 256  # bounded recvmsg control storage, not a native hostile-input proof
CASES = ('I1', 'I2', 'I3')


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def identity(pid=None):
    pid = pid or os.getpid()
    status = dict(line.split(':', 1) for line in Path(f'/proc/{pid}/status').read_text().splitlines() if ':' in line)
    stat = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    return dict(pid=pid, ppid=int(stat[1]), start_ticks=int(stat[19]),
                uids=list(map(int, status['Uid'].split())), gids=list(map(int, status['Gid'].split())),
                caps={k: status[k].strip() for k in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')},
                threads=int(status['Threads']), namespaces={k: os.readlink(f'/proc/{pid}/ns/{k}') for k in ('pid', 'user')})


def unprivileged(info):
    require(all(x != 0 for x in info['uids']), 'Blocked: root actor')
    require(int(info['caps']['CapEff'], 16) == 0, 'Blocked: effective capabilities')
    require(info['threads'] == 1, 'Blocked: threaded actor')


def live(fd):
    return not bool(select.select([fd], [], [], 0)[0])


def bind(info):
    fd = os.pidfd_open(info['pid'])
    try:
        require(identity(info['pid']) == info and live(fd), 'process instance changed during enrollment')
        return fd
    except BaseException:
        os.close(fd)
        raise


def descriptor(s):
    st = os.fstat(s.fileno())
    return dict(fd=s.fileno(), device=st.st_dev, inode=st.st_ino,
                inheritable=os.get_inheritable(s.fileno()), type=s.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE),
                passcred=s.getsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED))


def write_control(fd, msg):
    raw = json.dumps(msg, separators=(',', ':')).encode() + b'\n'
    require(len(raw) <= MAX_CONTROL, 'control output bound')
    require(bool(select.select([], [fd], [], TIMEOUT)[1]), 'control write watchdog')
    require(os.write(fd, raw) == len(raw), 'short control write')


def read_control(fd):
    data = bytearray()
    deadline = time.monotonic() + TIMEOUT
    while True:
        require(bool(select.select([fd], [], [], max(0, deadline-time.monotonic()))[0]), 'control read watchdog')
        byte = os.read(fd, 1)
        require(bool(byte), 'control EOF')
        if byte == b'\n':
            return json.loads(data)
        data.extend(byte)
        require(len(data) < MAX_CONTROL, 'control input bound')


def frame(tag, attempt, claimed):
    data = json.dumps(dict(tag=tag, attempt=attempt, claim_pid=claimed), separators=(',', ':')).encode()
    return struct.pack('!I', len(data)) + data


def no_duplicates(pairs):
    result = {}
    for k, v in pairs:
        require(k not in result, 'duplicate JSON key')
        result[k] = v
    return result


def validate(data, ancillary, flags, expected, expected_frame, alive):
    """Pure rejection logic plus owned delivered-SCM_RIGHTS cleanup. Synthetic tests labeled."""
    delivered = []
    parsed_creds = []
    reason = None
    body = None
    try:
        # Inventory *all* delivered rights before any rejection, including truncation.
        for level, kind, raw in ancillary:
            if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                ints = array.array('i')
                ints.frombytes(raw[:len(raw) - len(raw) % ints.itemsize])
                delivered.extend(ints)
        require(len(data) <= MAX_RECORD, 'record size')
        require(not flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC), 'truncated record/control')
        for level, kind, raw in ancillary:
            require(level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS, 'unexpected ancillary/descriptor')
            require(len(raw) == struct.calcsize('3i'), 'credential size')
            parsed_creds.append(struct.unpack('3i', raw))
        require(len(parsed_creds) == 1, 'missing/duplicate credentials')
        require(parsed_creds[0] == (expected['pid'], expected['uids'][0], expected['gids'][0]), 'sender mismatch')
        require(alive, 'enrolled peer exited')
        require(len(data) >= 5 and struct.unpack('!I', data[:4])[0] == len(data)-4, 'envelope length')
        body = json.loads(data[4:].decode('utf-8'), object_pairs_hook=no_duplicates)
        # Fixed schema gives depth/field/integer bounds; no extensible command executor.
        require(type(body) is dict and set(body) == {'tag', 'attempt', 'claim_pid'}, 'schema')
        require(type(body['claim_pid']) is int and 0 < body['claim_pid'] <= 2147483647, 'PID bound')
        require(body == expected_frame, 'fixed envelope mismatch')
    except (RuntimeError, ValueError, UnicodeError, RecursionError) as exc:
        reason = str(exc)
    finally:
        # Only descriptors delivered out-of-band; never numeric payload fields.
        for fd in set(delivered):
            os.close(fd)
    return dict(accepted=reason is None, reason=reason, credentials=[list(c) for c in parsed_creds],
                flags=flags, record_bytes=len(data), delivered_fds_closed=len(set(delivered)))


def receive(s, enrolled, pidfd, expected_frame):
    require(descriptor(s)['passcred'] == 1, 'credential option disabled')
    data, ancillary, flags, _ = s.recvmsg(MAX_RECORD, ANCILLARY, socket.MSG_CMSG_CLOEXEC)
    decision = validate(data, ancillary, flags, enrolled, expected_frame, live(pidfd))
    decision.update(ancillary=[dict(level=l, type=t, bytes=len(v),
                     credentials=list(struct.unpack('3i', v)) if l == socket.SOL_SOCKET and t == socket.SCM_CREDENTIALS and len(v) == 12 else None)
                     for l, t, v in ancillary], retained_pidfd=pidfd, pidfd_live=live(pidfd), descriptor=descriptor(s))
    return decision


def send(s, tag, attempt, claimed, explicit=None):
    raw = frame(tag, attempt, claimed)
    anc = [] if explicit is None else [(socket.SOL_SOCKET, socket.SCM_CREDENTIALS, struct.pack('3i', *explicit))]
    result = dict(sender=identity(), descriptor=descriptor(s), tag=tag, requested_credentials=explicit,
                  requested_bytes=len(raw), calls=1)
    try:
        n = s.sendmsg([raw], anc)
        result.update(return_value=n, errno=None)
        require(n == len(raw), 'short record send')
    except OSError as exc:
        result.update(return_value=-1, errno=exc.errno)
    return result


def snapshot(s, sent):
    return dict(identity=identity(), descriptor=descriptor(s), requests_sent=sent)


def actor(role, endpoint=None, inherited=None):
    conn, listener, peer_fd, child = None, None, None, None
    sent = 0
    actions = 0
    received = 0
    enrolled = None
    attempt = None
    try:
        unprivileged(identity())
        if role == 'server':
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            listener.settimeout(TIMEOUT)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            listener.bind(endpoint)
            os.chmod(endpoint, 0o600)
            listener.listen(1)
            initial = dict(identity=identity(), listener=descriptor(listener))
        else:
            conn = socket.socket(fileno=inherited) if role == 'holder' else socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            conn.settimeout(TIMEOUT)
            # Record inherited descriptor flag BEFORE altering it in the holder.
            inheritance = descriptor(conn) if role == 'holder' else None
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            initial = dict(identity=identity(), descriptor=descriptor(conn), inherited=inheritance)
        write_control(1, initial)
        while True:
            c = read_control(0)
            op = c['op']
            if op == 'enroll':
                require(role != 'holder' and enrolled is None, 'invalid enrollment')
                enrolled = c['identity']
                peer_fd = bind(enrolled)
                attempt = c['attempt']
                write_control(1, dict(enrolled=enrolled, retained_pidfd=peer_fd, live=live(peer_fd)))
            elif op == 'connect':
                require(role == 'client' and enrolled is not None, 'connect before enrollment')
                conn.connect(endpoint)
                write_control(1, snapshot(conn, sent))
            elif op == 'accept':
                require(role == 'server' and enrolled is not None, 'accept before enrollment')
                conn, _ = listener.accept()
                conn.settimeout(TIMEOUT)
                require(descriptor(conn)['passcred'] == 1, 'Blocked: PASSCRED not inherited')
                write_control(1, snapshot(conn, sent))
            elif op == 'hello-send':
                require(role == 'client', 'only client hello')
                result = send(conn, 'hello', attempt, os.getpid())
                require(result['errno'] is None, 'hello send failed')
                write_control(1, result)
            elif op == 'hello-receive':
                require(role == 'server', 'only server hello receive')
                result = receive(conn, enrolled, peer_fd, dict(tag='hello', attempt=attempt, claim_pid=enrolled['pid']))
                require(result['accepted'], 'hello credentials rejected: '+str(result))
                reply = send(conn, 'reply', attempt, os.getpid())
                require(reply['errno'] is None, 'hello reply failed')
                write_control(1, dict(verification=result, reply=reply))
            elif op == 'reply-receive':
                require(role == 'client', 'only client reply receive')
                result = receive(conn, enrolled, peer_fd, dict(tag='reply', attempt=attempt, claim_pid=enrolled['pid']))
                require(result['accepted'], 'server reply rejected: '+str(result))
                write_control(1, result)
            elif op == 'spawn-holder':
                require(role == 'client' and child is None, 'invalid holder spawn')
                child = subprocess.Popen([sys.executable, '-I', str(SCRIPT), '--actor', 'holder', str(conn.fileno())],
                    pass_fds=(conn.fileno(),), close_fds=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                # Publish ownership before waiting for holder readiness, so cleanup
                # can retain a handle even if holder initialization fails.
                write_control(1, dict(holder_identity=identity(child.pid), pass_fds=[conn.fileno()], close_fds=True))
            elif op == 'holder-ready':
                require(child is not None, 'holder absent')
                write_control(1, read_control(child.stdout.fileno()))
            elif op == 'holder-command':
                require(child is not None, 'holder absent')
                write_control(child.stdin.fileno(), c['command'])
                result = read_control(child.stdout.fileno())
                if c['command']['op'] == 'stop':
                    code = child.wait(timeout=TIMEOUT)
                    result.update(reaped_pid=child.pid, exit_code=code)
                    require(code == 0, 'holder failure')
                write_control(1, result)
            elif op == 'send-action':
                require(role in ('client', 'holder') and sent == 0, 'unexpected action sender/count')
                claim = os.getpid() if role == 'client' else c['claim_pid']
                case = attempt if role == 'client' else c['attempt']
                explicit = [claim, os.getuid(), os.getgid()] if c['explicit'] else None
                result = send(conn, 'action', case, claim, explicit)
                sent += 1
                result['requests_sent'] = sent
                write_control(1, result)
            elif op == 'evaluate':
                require(role == 'server' and received == 0, 'unexpected evaluation')
                result = receive(conn, enrolled, peer_fd, dict(tag='action', attempt=attempt, claim_pid=enrolled['pid']))
                received += 1
                if result['accepted']:
                    actions += 1
                    reply = send(conn, 'reply', attempt, os.getpid())
                    require(reply['errno'] is None, 'action reply send failed')
                result.update(authorized_actions=actions, requests_received=received)
                write_control(1, result)
            elif op == 'status':
                result = snapshot(conn, sent)
                result.update(authorized_actions=actions, requests_received=received,
                              queued_record=bool(select.select([conn], [], [], 0)[0]))
                write_control(1, result)
            elif op == 'stop':
                require(child is None or child.poll() == 0, 'holder not reaped')
                write_control(1, dict(exiting_pid=os.getpid(), requests_sent=sent, authorized_actions=actions))
                return
            else:
                raise RuntimeError('unknown test-only operation')
    finally:
        if child is not None:
            # A hung descendant is handled by runner's retained ownership/pidfd registry.
            for pipe in (child.stdin, child.stdout, child.stderr):
                pipe.close()
        if peer_fd is not None:
            os.close(peer_fd)
        if conn is not None:
            conn.close()
        if listener is not None:
            listener.close()


class Actor:
    def __init__(self, role, endpoint):
        self.stopping = False
        self.proc = subprocess.Popen([sys.executable, '-I', str(SCRIPT), '--actor', role, str(endpoint)],
            close_fds=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.fd = None
        self.info = identity(self.proc.pid)
        self.fd = bind(self.info)
        self.initial = read_control(self.proc.stdout.fileno())
        if 'error' in self.initial:
            prefix = 'Blocked: ' if self.initial['error'].startswith('PermissionError:') else ''
            raise RuntimeError(prefix+'actor initialization: '+str(self.initial))
        require(self.initial['identity'] == self.info, 'actor identity mismatch')

    def command(self, op, **kwargs):
        write_control(self.proc.stdin.fileno(), dict(op=op, **kwargs))
        result = read_control(self.proc.stdout.fileno())
        require('error' not in result, str(result))
        if op == 'stop':
            self.stopping = True
        return result

    def close(self):
        forced = False
        # A stop acknowledgement precedes interpreter teardown. Wait for orderly
        # exit rather than racing it with a signal.
        if self.stopping:
            try:
                self.proc.wait(timeout=TIMEOUT)
            except subprocess.TimeoutExpired:
                pass
        if self.proc.poll() is None:
            forced = True
            if self.fd is not None:
                if live(self.fd):
                    signal.pidfd_send_signal(self.fd, signal.SIGTERM)
            else:
                self.proc.terminate()  # still-unreaped direct child only
        code = self.proc.wait(timeout=TIMEOUT)
        for pipe in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            pipe.close()
        if self.fd is not None:
            os.close(self.fd)
        return dict(pid=self.proc.pid, exit_code=code, reaped=True, forced=forced)


def subreaper(value=None):
    libc = ctypes.CDLL(None, use_errno=True)
    old = ctypes.c_int()
    require(libc.prctl(37, ctypes.byref(old), 0, 0, 0) == 0, 'subreaper query failed')
    if value is not None:
        require(libc.prctl(36, value, 0, 0, 0) == 0, 'subreaper set failed')
    return old.value


def run_case(case):
    result = dict(case=case, trace=[], failures=[], cleanup={})
    actors = []
    holder_fd = None
    holder_info = None
    root = Path(tempfile.mkdtemp(prefix='w2i-'))
    root_stat = root.stat()
    endpoint = root / 'record.sock'
    result['root'] = str(root)
    result['fixture'] = dict(mode=oct(root_stat.st_mode & 0o777), device=root_stat.st_dev, inode=root_stat.st_ino)
    socket_stat = None
    def event(name, value):
        result['trace'].append(dict(index=len(result['trace']), barrier=name, at=time.monotonic(), evidence=value))
        return value
    def command(a, barrier, op, **kw):
        return event(barrier, a.command(op, **kw))
    try:
        server = Actor.__new__(Actor); actors.append(server); server.__init__('server', endpoint)
        event('listener-ready-before-connect', server.initial)
        socket_stat = endpoint.stat()
        result['socket_fixture'] = dict(mode=oct(socket_stat.st_mode & 0o777), device=socket_stat.st_dev, inode=socket_stat.st_ino)
        require(socket_stat.st_mode & 0o777 == 0o600, 'socket mode')
        client = Actor.__new__(Actor); actors.append(client); client.__init__('client', endpoint)
        event('client-passcred-ready', client.initial)
        for a in actors:
            unprivileged(a.info)
            require(a.info['namespaces'] == identity()['namespaces'], 'Blocked: namespace mismatch')
        command(server, 'trusted-client-enrollment', 'enroll', identity=client.info, attempt=case)
        command(client, 'trusted-server-enrollment', 'enroll', identity=server.info, attempt=case)
        command(client, 'connect-permitted', 'connect')
        command(server, 'accepted-options-verified-before-send', 'accept')
        command(client, 'hello-send-permitted', 'hello-send')
        command(server, 'hello-credentials-and-reply', 'hello-receive')
        command(client, 'server-credentials-verified', 'reply-receive')
        before = command(client, 'original-before', 'status')
        event('runner-original-before', dict(identity=identity(client.info['pid']), pidfd_live=live(client.fd)))
        if case != 'I1':
            spawned = command(client, 'holder-inheritance', 'spawn-holder')
            holder_info = spawned['holder_identity']
            holder_fd = bind(holder_info)
            holder_ready = command(client, 'holder-ready-after-handle-retained', 'holder-ready')
            require(holder_ready['identity'] == holder_info, 'holder identity mismatch')
            unprivileged(holder_info)
            require(holder_info['ppid'] == client.info['pid'], 'holder parentage')
            require(holder_info['namespaces'] == client.info['namespaces'], 'holder namespaces')
            require(holder_ready['descriptor']['inode'] == before['descriptor']['inode'], 'inherited endpoint mismatch')
            result['holder'] = holder_info
            event('holder-before', dict(identity=identity(holder_info['pid']), pidfd_live=live(holder_fd)))
            sent = command(client, 'holder-send-permitted', 'holder-command', command=dict(op='send-action', explicit=case == 'I3', claim_pid=client.info['pid'], attempt=case))
        else:
            sent = command(client, 'original-send-permitted', 'send-action', explicit=True)
        if case == 'I3':
            require(sent['return_value'] == -1 and sent['errno'] == errno.EPERM, 'unexpected forgery syscall result')
            decision = command(server, 'independent-receiver-count-after-forgery', 'status')
            require(decision['authorized_actions'] == 0 and decision['requests_received'] == 0 and not decision['queued_record'], 'forged record/effect observed')
        else:
            require(sent['errno'] is None and sent['return_value'] == sent['requested_bytes'], 'send failure')
            decision = command(server, 'record-evaluation', 'evaluate')
            wanted = 1 if case == 'I1' else 0
            if decision['authorized_actions'] != wanted:
                result['counterexample'] = decision
            require(decision['authorized_actions'] == wanted, 'unexpected action outcome')
            require(decision['requests_received'] == 1, 'request accounting')
            if case == 'I1':
                require(decision['accepted'], 'healthy rejection')
                command(client, 'action-reply-verified', 'reply-receive')
            else:
                require(decision['reason'] == 'sender mismatch', 'wrong rejection reason')
                require(decision['credentials'] == [[holder_info['pid'], holder_info['uids'][0], holder_info['gids'][0]]], 'holder kernel attribution absent')
        result['action_count'] = decision['authorized_actions']
        after = command(client, 'original-after', 'status')
        event('runner-original-after', dict(identity=identity(client.info['pid']), pidfd_live=live(client.fd)))
        require(live(client.fd) and identity(client.info['pid']) == client.info, 'original changed/exited')
        require(after['requests_sent'] == (1 if case == 'I1' else 0), 'original sender accounting')
        if holder_fd is not None:
            event('holder-after', dict(identity=identity(holder_info['pid']), pidfd_live=live(holder_fd)))
            require(live(holder_fd) and identity(holder_info['pid']) == holder_info, 'holder changed/exited')
            command(client, 'holder-status', 'holder-command', command=dict(op='status'))
            reaped = command(client, 'holder-stop-and-reap', 'holder-command', command=dict(op='stop'))
            require(reaped['reaped_pid'] == holder_info['pid'] and reaped['exit_code'] == 0 and not live(holder_fd), 'holder reap evidence')
        for a in actors:
            require(identity(a.info['pid']) == a.info and live(a.fd), 'actor identity changed')
        for a in reversed(actors):
            command(a, 'actor-stop-'+str(a.info['pid']), 'stop')
        result['result'] = 'Pass'
    except BaseException as exc:
        result['failures'].append(str(exc))
        result['result'] = 'Blocked' if str(exc).startswith('Blocked:') else ('CounterexampleDetected' if result.get('counterexample') else 'Fail')
    finally:
        # Stop the known holder first. Normal path: its parent already reaped it.
        if holder_fd is not None and live(holder_fd):
            signal.pidfd_send_signal(holder_fd, signal.SIGTERM)
        result['actor_initializations'] = [getattr(a, 'initial', None) for a in actors]
        cleanup = result['cleanup']
        cleanup['direct_children'] = []
        for a in reversed(actors):
            try:
                cleanup['direct_children'].append(a.close())
            except BaseException as exc:
                result['failures'].append('cleanup: '+str(exc))
        if holder_fd is not None:
            if not any(t['barrier'] == 'holder-stop-and-reap' for t in result['trace']):
                try:
                    # After client exit runner is the subreaper. Do not reap unknown children.
                    require(not live(holder_fd) or bool(select.select([holder_fd], [], [], TIMEOUT)[0]), 'holder exit watchdog')
                    waited = os.waitid(os.P_PIDFD, holder_fd, os.WEXITED)
                    require(waited.si_pid == holder_info['pid'], 'holder wait identity')
                    cleanup['adopted_holder'] = dict(pid=waited.si_pid, status=waited.si_status, code=waited.si_code)
                except BaseException as exc:
                    result['failures'].append('holder cleanup: '+str(exc))
            cleanup['holder_pidfd_exited'] = not live(holder_fd)
            os.close(holder_fd)
        try:
            require(all(x['reaped'] for x in cleanup['direct_children']) and len(cleanup['direct_children']) == len(actors), 'unreaped actors')
            require(holder_info is None or (holder_fd is not None and cleanup.get('holder_pidfd_exited')), 'holder ownership/exit uncertain')
            if result.get('result') == 'Pass':
                require(all(x['exit_code'] == 0 and not x['forced'] for x in cleanup['direct_children']), 'unexpected actor exit/forced cleanup')
            require(not root.is_symlink() and (root.stat().st_dev, root.stat().st_ino) == (root_stat.st_dev, root_stat.st_ino), 'root replaced')
            if endpoint.exists():
                require(socket_stat is not None and not endpoint.is_symlink() and (endpoint.stat().st_dev, endpoint.stat().st_ino) == (socket_stat.st_dev, socket_stat.st_ino), 'socket replaced')
                endpoint.unlink()
            root.rmdir()
            cleanup['root_removed'] = not root.exists()
        except BaseException as exc:
            result['failures'].append('filesystem cleanup: '+str(exc))
        if result['failures']:
            if result.get('result') == 'Pass':
                result['result'] = 'Fail'
        result['diagnostic_complete'] = not bool(result['failures'])
    return result


def main(output):
    report = dict(started=datetime.now(timezone.utc).isoformat(), environment=dict(kernel=platform.release(), platform=platform.platform(), python=sys.version, runner=identity()),
                  limits=dict(record_bytes=MAX_RECORD, ancillary_bytes=ANCILLARY, control_bytes=MAX_CONTROL, watchdog_seconds=TIMEOUT),
                  source_sha256=hashlib.sha256(SCRIPT.read_bytes()).hexdigest(), cases=[], authentication_safety='Unproven', production_readiness=False)
    initial_subreaper = subreaper()
    report['subreaper_before'] = initial_subreaper
    fd_before = len(os.listdir('/proc/self/fd'))
    try:
        unprivileged(report['environment']['runner'])
        for name in ('SOCK_SEQPACKET', 'SO_PASSCRED', 'SCM_CREDENTIALS', 'MSG_CMSG_CLOEXEC'):
            require(hasattr(socket, name), 'Blocked: missing '+name)
        require(hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal') and hasattr(os, 'P_PIDFD'), 'Blocked: pidfd primitives')
        subreaper(1)
        report['subreaper_during'] = subreaper()
        for case in CASES:
            result = run_case(case)
            report['cases'].append(result)
            Path(output).write_text(json.dumps(report, indent=2)+'\n')
            if result['result'] != 'Pass':
                break
    except BaseException as exc:
        report['failure'] = str(exc)
    finally:
        subreaper(initial_subreaper)
        report['subreaper_after'] = subreaper()
        report['runner_fds_before_after'] = [fd_before, len(os.listdir('/proc/self/fd'))]
        children_path = Path(f'/proc/self/task/{os.getpid()}/children')
        try:
            report['remaining_direct_children'] = children_path.read_text().strip()
            report['child_enumeration'] = 'Available'
        except FileNotFoundError:
            # Optional kernel audit, not the owned-process reaping mechanism.
            report['remaining_direct_children'] = None
            report['child_enumeration'] = 'Unavailable: proc children file absent'
        report['cleanup_scope'] = 'Registered run-owned actors; no claim about unrelated or unknown processes'
        report['owned_cleanup_complete'] = all(
            c['cleanup'].get('root_removed') and len(c['cleanup'].get('direct_children', [])) == 2
            and all(a['reaped'] and a['exit_code'] == 0 for a in c['cleanup']['direct_children'])
            and (c['case'] == 'I1' or c['cleanup'].get('holder_pidfd_exited'))
            for c in report['cases'])
        report['diagnostic_success'] = (len(report['cases']) == 3 and all(c['result'] == 'Pass' for c in report['cases']) and 'failure' not in report
            and report['subreaper_after'] == initial_subreaper and report['runner_fds_before_after'][0] == report['runner_fds_before_after'][1] and not report['remaining_direct_children'] and report['owned_cleanup_complete'])
        report['primitive_result'] = 'Pass' if report['diagnostic_success'] else 'Incomplete/Fail/Blocked'
        Path(output).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('diagnostic_success', 'primitive_result', 'authentication_safety', 'production_readiness')}))
    return 0 if report['diagnostic_success'] else 1


if __name__ == '__main__':
    if sys.argv[1] == '--actor':
        try:
            role = sys.argv[2]
            actor(role, inherited=int(sys.argv[3])) if role == 'holder' else actor(role, endpoint=sys.argv[3])
        except BaseException as exc:
            write_control(1, dict(error=type(exc).__name__+': '+str(exc)))
            sys.exit(1)
    else:
        sys.exit(main(sys.argv[1]))
