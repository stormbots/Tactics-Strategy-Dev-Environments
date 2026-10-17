"""W2m only: ancillary-truncation partial-descriptor-delivery diagnostic. No production authority."""
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
spec = importlib.util.spec_from_file_location('w2m_reviewed_w2i_definitions', HELPER)
i = importlib.util.module_from_spec(spec)
spec.loader.exec_module(i)  # Definitions only; no W2i scenario or entrypoint runs.
require = i.require
CASES = ('M1', 'M2')
TIMEOUT = i.TIMEOUT
def partial_capacity():
    # Fixed test-only formula: never scan/tune capacities to obtain a result.
    return socket.CMSG_SPACE(struct.calcsize('3i')) + socket.CMSG_LEN(array.array('i').itemsize)


def fd_info(fd):
    st = os.fstat(fd)
    return dict(fd=fd, dev=st.st_dev, ino=st.st_ino, mode=st.st_mode,
                fdflags=fcntl.fcntl(fd, fcntl.F_GETFD), flags=fcntl.fcntl(fd, fcntl.F_GETFL))


def fd_inventory():
    """Keep the scan handle live; exclude only its observed directory identity.

    Single-threaded actors must expose exactly one matching /proc/self/fd handle.
    A vanished baseline descriptor is an error, never an ignored EBADF entry.
    """
    directory = os.stat('/proc/self/fd')
    result, scan_handles = [], []
    with os.scandir('/proc/self/fd') as entries:
        for entry in entries:
            info = fd_info(int(entry.name))
            if (stat.S_ISDIR(info['mode']) and
                    (info['dev'], info['ino']) == (directory.st_dev, directory.st_ino)):
                scan_handles.append(info['fd'])
            else:
                result.append(info)
    require(len(scan_handles) == 1, 'Blocked: ambiguous/missing live inventory handle')
    return sorted(result, key=lambda fd: fd['fd'])


def rights_from(ancillary):
    result = []
    for level, kind, raw in ancillary:
        if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
            ints = array.array('i')
            # Inventory all delivered integers; unsupported partial delivery is
            # rejected, not injected or interpreted as a passing W2m schedule.
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
    payload_capacity = i.MAX_RECORD
    ancillary_capacity = partial_capacity() if attempt == 'M2' else i.ANCILLARY
    data, anc, flags, _ = conn.recvmsg(payload_capacity, ancillary_capacity, socket.MSG_CMSG_CLOEXEC)
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
    expected_data = i.frame('action', attempt, enrolled['pid'])
    return dict(decision=decision, recvmsg_flags_argument=socket.MSG_CMSG_CLOEXEC,
                payload_capacity=payload_capacity, ancillary_capacity=ancillary_capacity, received_bytes=len(data),
                declared_json_bytes=struct.unpack('!I',data[:4])[0] if len(data) >= 4 else None,
                expected_record_bytes=len(expected_data),
                received_flags=flags, before=before, installed=installed, immediately_closed=closed,
                after=after, observation_errors=observation_errors, raw_credentials=raw_creds,
                ancillary=[dict(level=l, type=t, bytes=len(raw)) for l,t,raw in anc],
                raw_ancillary=[dict(level=l,type=t,hex=raw.hex()) for l,t,raw in anc],
                fixture_payload_matches=data == i.frame('action', attempt, enrolled['pid']),
                payload_sha256=hashlib.sha256(data).hexdigest(), retained_pidfd=retained,
                pidfd_live=i.live(retained), descriptor=i.descriptor(conn))


def sender_send(conn, attempt, pipe):
    """One complete record; only M2 attaches both run-owned pipe ends."""
    original = i.identity()
    explicit = [original['pid'], original['uids'][0], original['gids'][0]]
    data = i.frame('action', attempt, original['pid'])
    anc = [(socket.SOL_SOCKET, socket.SCM_CREDENTIALS, struct.pack('3i', *explicit))]
    if attempt == 'M2':
        require(len(pipe) == 2, 'two owned pipe ends required')
        anc.append((socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', pipe).tobytes()))
    else:
        require(attempt == 'M1' and pipe == [], 'invalid healthy attachment')
    result = dict(identity=original, requested_credentials=explicit, attached_fds=list(pipe), sent_pipe=[fd_info(fd) for fd in pipe],
                  record_bytes=len(data), payload_sha256=hashlib.sha256(data).hexdigest(), descriptor=i.descriptor(conn))
    require(result['descriptor']['passcred'] == 1, 'Blocked: pre-send credential option disabled')
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
        require(role in ('server', 'client'), 'unknown W2m actor')
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
                require(role == 'client' and attempt == 'M2' and not pipe, 'invalid pipe creation')
                pipe = list(os.pipe())
                i.write_control(1, dict(identity=i.identity(), pipe=[fd_info(fd) for fd in pipe]))
            elif op == 'send-action':
                require(role == 'client' and sent == 0, 'invalid send/count')
                require(set(c) == {'op'}, 'no attachment/control override allowed')
                result = sender_send(conn, attempt, pipe)
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
                                        pipe=[fd_info(fd) for fd in pipe]))
                return
            else:
                raise RuntimeError('unknown W2m operation')
    finally:
        for fd in pipe: os.close(fd)
        if retained is not None: os.close(retained)
        if conn is not None: conn.close()
        if listener is not None: listener.close()


class Actor(i.Actor):
    """Reuse reviewed command/wait cleanup; launch only this W2m script."""
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
    """Evidence only: partial ancillary delivery must never authorize a record."""
    require(case in CASES, 'unknown W2m case')
    for field in ('received_flags','recvmsg_flags_argument','payload_capacity','ancillary_capacity',
                  'received_bytes','expected_record_bytes','declared_json_bytes'):
        i.check_count(evaluation[field], 'invalid integer receive evidence: '+field)
    for field in ('record_bytes','return_value','requests_sent'):
        i.check_count(sender[field], 'invalid integer sender evidence: '+field)
    i.check_count(evaluation['authorized_actions'], 'invalid action count')
    i.check_count(evaluation['requests_received'], 'invalid request count')
    require(evaluation['requests_received'] == sender['requests_sent'] == 1, 'wrong request/send count')
    require(not evaluation['observation_errors'], 'unexpected FD observation failure')
    require(evaluation['received_flags'] & socket.MSG_TRUNC == 0, 'unexpected payload truncation')
    require(evaluation['payload_capacity'] == i.MAX_RECORD, 'changed payload capacity')
    require(evaluation['recvmsg_flags_argument'] == socket.MSG_CMSG_CLOEXEC, 'changed recvmsg flags argument')
    expected = sender['identity']
    complete = i.frame('action',case,expected['pid'])
    require(sender['record_bytes'] == sender['return_value'] == len(complete) and sender['errno'] is None, 'incomplete/failed send')
    require(sender['payload_sha256'] == hashlib.sha256(complete).hexdigest(), 'sender fixture mismatch')
    require(evaluation['received_bytes'] == evaluation['expected_record_bytes'] == len(complete), 'incomplete payload evidence')
    require(evaluation['declared_json_bytes'] + 4 == len(complete), 'invalid complete length prefix')
    require(evaluation['fixture_payload_matches'] is True and evaluation['payload_sha256'] == sender['payload_sha256'], 'payload fixture/hash mismatch')
    require(evaluation['pidfd_live'] is True, 'enrolled peer no longer live')
    for inventory in (evaluation['before'], evaluation['after']):
        numbers = [fd['fd'] for fd in inventory]
        require(all(type(n) is int and n >= 0 for n in numbers) and len(numbers) == len(set(numbers)), 'invalid/duplicate inventory FD')
    require(evaluation['before'] == evaluation['after'], 'receiver FD inventory changed')
    d = evaluation['decision']
    for field in ('flags','record_bytes','delivered_fds_closed'):
        i.check_count(d[field], 'invalid validator integer evidence')
    require(d['flags'] == evaluation['received_flags'] and d['record_bytes'] == evaluation['received_bytes'], 'validator flags/length mismatch')
    if case == 'M1':
        require(evaluation['ancillary_capacity'] == i.ANCILLARY and not evaluation['received_flags'] & socket.MSG_CTRUNC, 'healthy ancillary truncation/capacity')
        require(evaluation['raw_credentials'] == [[expected['pid'],expected['uids'][0],expected['gids'][0]]], 'healthy kernel credentials')
        require(evaluation['ancillary'] == [dict(level=socket.SOL_SOCKET,type=socket.SCM_CREDENTIALS,bytes=struct.calcsize('3i'))], 'healthy ancillary shape')
        require(d['credentials'] == evaluation['raw_credentials'], 'healthy validator/kernel credential mismatch')
        require(sender['attached_fds'] == [] and sender['sent_pipe'] == [] and not evaluation['installed'] and not evaluation['immediately_closed'] and d['delivered_fds_closed'] == 0, 'unexpected healthy descriptor')
        require(evaluation['authorized_actions'] == 1 and d['accepted'] is True and d['reason'] is None, 'failed healthy control')
    else:
        require(evaluation['ancillary_capacity'] == partial_capacity(), 'wrong fixed partial-delivery capacity')
        require(evaluation['received_flags'] & socket.MSG_CTRUNC != 0, 'missing actual MSG_CTRUNC')
        require(evaluation['raw_credentials'] == [[expected['pid'], expected['uids'][0], expected['gids'][0]]], 'unexpected partial-delivery kernel credentials')
        wanted = [dict(level=socket.SOL_SOCKET,type=socket.SCM_CREDENTIALS,bytes=struct.calcsize('3i')),
                  dict(level=socket.SOL_SOCKET,type=socket.SCM_RIGHTS,bytes=array.array('i').itemsize)]
        key = lambda c: (c['level'],c['type'],c['bytes'])
        require(sorted(evaluation['ancillary'],key=key) == sorted(wanted,key=key), 'unexpected ancillary delivery shape')
        if evaluation['authorized_actions'] > 0 or d['accepted'] is True:
            return 'CounterexampleDetected'
        require(evaluation['authorized_actions'] == 0 and d['accepted'] is False and d['reason'] == 'truncated record/control', 'missing truncation-specific rejection')
        require(d['credentials'] == [], 'truncated record acquired credential authority')
        require(d['delivered_fds_closed'] == 1 and len(evaluation['installed']) == len(evaluation['immediately_closed']) == 1, 'not exactly one installed/closed FD')
        installed, closed = evaluation['installed'][0], evaluation['immediately_closed'][0]
        i.check_count(installed['fd'], 'invalid installed FD')
        i.check_count(installed['fdflags'], 'invalid FD flags')
        require(installed['fdflags'] & fcntl.FD_CLOEXEC != 0, 'installed FD lacks CLOEXEC')
        require(closed['fd'] == installed['fd'] and installed['fd'] not in [fd['fd'] for fd in evaluation['before']], 'installed/closed identity mismatch')
        require(closed['fstat_errno'] == errno.EBADF and closed['getfd_errno'] == errno.EBADF, 'received FD not immediately closed')
        originals = sender['sent_pipe']
        require(len(originals) == 2 and len(set(sender['attached_fds'])) == 2 and sender['attached_fds'] == [fd['fd'] for fd in originals], 'not both owned pipe ends')
        matches = [fd for fd in originals if all(installed[k] == fd[k] for k in ('dev','ino','mode','flags'))]
        require(stat.S_ISFIFO(installed['mode']) and len(matches) == 1, 'received FD not a distinct sent pipe end')
    return 'Expected'


def verify_case_evidence(report, completed=False):
    """Audit trace relationships before Pass; never supplies receiver authority."""
    require(report['case'] in CASES, 'unknown case evidence')
    names = [event['barrier'] for event in report['trace']]
    require(len(names) == len(set(names)), 'duplicate barrier evidence')
    require([t['index'] for t in report['trace']] == list(range(len(names))), 'invalid trace index')
    require([t['at'] for t in report['trace']] == sorted(t['at'] for t in report['trace']), 'nonmonotonic barrier evidence')
    def ev(name):
        require(name in names, 'missing barrier: '+name)
        return report['trace'][names.index(name)]['evidence']
    server = ev('server-ready-before-connect')['identity']
    client = ev('client-ready-before-connect')['identity']
    require(server['pid'] != client['pid'] and server['ppid'] == client['ppid'], 'actor ownership evidence')
    for who in (server, client):
        i.unprivileged(who)
        require(who['namespaces'] == client['namespaces'], 'actor namespace evidence')
        after = ev('runner-instance-after-'+str(who['pid']))
        require(after['identity'] == who and after['pidfd_live'] is True, 'retained actor instance evidence')
    for enrollment, peer in [('trusted-client-enrollment', client), ('trusted-server-enrollment', server)]:
        record = ev(enrollment)
        require(record['enrolled'] == peer and record['pidfd_live'] is True and record['inheritable'] is False, 'enrollment evidence')
    for name, key in [('server-ready-before-connect','listener'), ('client-ready-before-connect','descriptor'), ('accepted-passcred-verified','descriptor')]:
        d = ev(name)[key]
        require(d['passcred'] == 1 and d['type'] == socket.SOCK_SEQPACKET, 'socket readiness evidence')
    for decision, peer in [(ev('client-credentials-and-server-reply')['verification'],client), (ev('server-reply-verified'),server)]:
        require(decision['accepted'] is True and decision['pidfd_live'] is True, 'hello authentication evidence')
        require(decision['credentials'] == [[peer['pid'],peer['uids'][0],peer['gids'][0]]], 'hello sender evidence')
    baseline = ev('receiver-before-send')
    require(baseline['identity'] == server, 'receiver baseline identity')
    for field in ('authorized_actions','requests_received'):
        i.check_count(baseline[field], 'invalid receiver baseline count')
        require(baseline[field] == 0, 'receiver not fresh before action')
    before, after = ev('sender-before'), ev('sender-after')
    sent = ev('action-send-permitted')
    require(before['identity'] == after['identity'] == sent['identity'] == client, 'sender instance evidence')
    for count, wanted in [(before['requests_sent'],0),(after['requests_sent'],1),(sent['requests_sent'],1)]:
        i.check_count(count, 'invalid sender count')
        require(count == wanted, 'sender count evidence')
    require(type(sent['return_value']) is int and sent['return_value'] == sent['record_bytes'] and sent['errno'] is None, 'send result evidence')
    require(sent['requested_credentials'] == [client['pid'],client['uids'][0],client['gids'][0]], 'explicit credential evidence')
    require(i.same_endpoint(before['descriptor'],sent['descriptor']) and i.same_endpoint(sent['descriptor'],after['descriptor']), 'sender endpoint evidence')
    require(before['pipe'] == after['pipe'] == sent['sent_pipe'], 'sender pipe validity/identity changed')
    if report['case'] == 'M2':
        made = ev('owned-pipe-created')
        require(made['identity'] == client and made['pipe'] == before['pipe'] and len(made['pipe']) == 2, 'pipe ownership evidence')
        read, write = made['pipe']
        require(type(read['fd']) is int and type(write['fd']) is int and read['fd'] != write['fd'], 'distinct pipe FDs required')
        require(stat.S_ISFIFO(read['mode']) and all(read[k] == write[k] for k in ('dev','ino','mode')), 'not one owned pipe')
        require(read['flags'] & os.O_ACCMODE == os.O_RDONLY and write['flags'] & os.O_ACCMODE == os.O_WRONLY, 'pipe endpoint access modes')
    else:
        require(before['pipe'] == [], 'unexpected healthy pipe')
    if report['case'] == 'M1':
        reply = ev('healthy-action-reply-verified')
        require(reply['accepted'] is True and reply['credentials'] == [[server['pid'],server['uids'][0],server['gids'][0]]], 'action reply evidence')
    evaluation = ev('kernel-receive-and-truncation-check')
    i.check_count(report['action_count'], 'invalid case action count')
    accepted = ev('accepted-passcred-verified')['descriptor']
    observed = evaluation['descriptor']
    require(i.same_endpoint(accepted,observed) and accepted['fd'] == observed['fd'], 'receiver endpoint evidence changed')
    for inventory in (evaluation['before'],evaluation['after']):
        matches = [fd for fd in inventory if fd['fd'] == accepted['fd']]
        require(len(matches) == 1 and matches[0]['dev'] == accepted['device'] and matches[0]['ino'] == accepted['inode'], 'accepted endpoint absent/replaced in inventory')
    require(report['action_count'] == evaluation['authorized_actions'], 'case/evaluation count mismatch')
    require(verify_evaluation(report['case'],evaluation,sent) == 'Expected', 'unexpected authorization')
    order = ['server-ready-before-connect','client-ready-before-connect','trusted-client-enrollment','trusted-server-enrollment',
             'connect-permitted','accepted-passcred-verified','hello-send-permitted','client-credentials-and-server-reply','server-reply-verified']
    if report['case'] == 'M2': order.append('owned-pipe-created')
    order += ['receiver-before-send','sender-before','action-send-permitted','kernel-receive-and-truncation-check']
    if report['case'] == 'M1': order.append('healthy-action-reply-verified')
    order += ['sender-after','runner-instance-after-'+str(server['pid']),'runner-instance-after-'+str(client['pid'])]
    stops = ['stop-'+str(client['pid']), 'stop-'+str(server['pid'])]
    if completed or any(name.startswith('stop-') for name in names):
        require(set(name for name in names if name.startswith('stop-')) == set(stops), 'missing/unexpected stop evidence')
        for who, actions, sent in [(client, 0, 1), (server, report['action_count'], 0)]:
            stopped = ev('stop-'+str(who['pid']))
            for field in ('exiting_pid', 'actions', 'requests_sent'):
                i.check_count(stopped[field], 'invalid stop integer evidence')
            require(stopped['exiting_pid'] == who['pid'], 'stop actor identity mismatch')
            require(stopped['actions'] == actions and stopped['requests_sent'] == sent and stopped['pipe'] == (before['pipe'] if who == client else []), 'final actor accounting mismatch')
        order += stops
    if completed:
        cleanup = report['cleanup']
        require(cleanup['root_removed'] is True and not report['failures'], 'incomplete fixture cleanup')
        records = cleanup['actors']
        require(len(records) == 2 and {r['pid'] for r in records} == {client['pid'], server['pid']}, 'cleanup actor ownership mismatch')
        for record in records:
            require(type(record['pid']) is int and type(record['exit_code']) is int and record['exit_code'] == 0
                    and record['reaped'] is True and record['forced'] is False, 'abnormal actor cleanup')
    indices = [names.index(name) for name in order]
    require(indices == sorted(indices), 'barrier ordering evidence')
    return True


def run_case(case):
    report = dict(case=case, trace=[], failures=[], cleanup={})
    actors = []
    root = Path(tempfile.mkdtemp(prefix='w2m-')); original_root = root.stat()
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
            if role == 'server':
                original_socket = endpoint.stat()
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
        if case == 'M2': command(client,'owned-pipe-created','make-pipe')
        command(server,'receiver-before-send','status')
        before = command(client,'sender-before','status')
        sent = command(client,'action-send-permitted','send-action')
        require(sent['identity'] == client.info, 'changed sender')
        require(sent['return_value'] == sent['record_bytes'] and sent['errno'] is None and sent['requests_sent'] == 1, 'short/failed send')
        require(sent['requested_credentials'] == [client.info['pid'], client.info['uids'][0], client.info['gids'][0]], 'explicit credential control missing')
        evaluation = command(server,'kernel-receive-and-truncation-check','evaluate')
        # Preserve any observed unauthorized acceptance even if another evidence
        # check (for example an FD leak) fails in the same observation.
        i.check_count(evaluation['authorized_actions'], 'invalid observed action count')
        report['action_count'] = evaluation['authorized_actions']
        if case == 'M2' and (evaluation['authorized_actions'] > 0 or evaluation['decision']['accepted'] is True):
            report['counterexample'] = evaluation
        disposition = verify_evaluation(case,evaluation,sent)
        if disposition == 'CounterexampleDetected':
            report['counterexample'] = evaluation
            raise RuntimeError('truncated ancillary record obtained authority')
        report['action_count'] = evaluation['authorized_actions']
        if case == 'M1': command(client,'healthy-action-reply-verified','reply-receive')
        after = command(client,'sender-after','status')
        require(before['pipe'] == after['pipe'] == sent['sent_pipe'], 'sender pipe validity changed')
        require(after['requests_sent'] == 1 and after['identity'] == client.info, 'sender accounting/identity changed')
        require(i.same_endpoint(sent['descriptor'],after['descriptor']), 'sender endpoint changed')
        for a in actors:
            event('runner-instance-after-'+str(a.info['pid']),dict(identity=i.identity(a.info['pid']), pidfd_live=i.live(a.fd)))
            require(i.identity(a.info['pid']) == a.info and i.live(a.fd), 'actor changed/exited')
        verify_case_evidence(report)
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
        if report.get('result') == 'Pass' and not report['failures']:
            try: verify_case_evidence(report, completed=True)
            except BaseException as exc: report['failures'].append('completion audit: '+str(exc))
        if report['failures'] and report.get('result') == 'Pass': report['result'] = 'Fail'
    return report


def main(output):
    report = dict(started=datetime.now(timezone.utc).isoformat(), environment=dict(platform=platform.platform(), kernel=platform.release(), python=sys.version, runner=i.identity()),
                  source_sha256=hashlib.sha256(SCRIPT.read_bytes()).hexdigest(), helper_sha256=hashlib.sha256(HELPER.read_bytes()).hexdigest(),
                  limits=dict(record=i.MAX_RECORD, partial_ancillary_formula='CMSG_SPACE(sizeof(ucred)) + CMSG_LEN(sizeof(int))', ucred_bytes=struct.calcsize('3i'), int_bytes=array.array('i').itemsize, ancillary=i.ANCILLARY, control=i.MAX_CONTROL, watchdog_seconds=TIMEOUT), cases=[],
                  authentication_safety='Unproven', production_readiness=False, finalization_failures=[])
    fd_before, sub_before = None, None
    try:
        i.unprivileged(report['environment']['runner'])
        for name in ('SCM_RIGHTS','SCM_CREDENTIALS','SO_PASSCRED','SOCK_SEQPACKET','MSG_CMSG_CLOEXEC','MSG_TRUNC','MSG_CTRUNC','CMSG_SPACE','CMSG_LEN'):
            require(hasattr(socket,name),'Blocked: missing '+name)
        report['limits']['m2_ancillary_receive'] = partial_capacity()
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
