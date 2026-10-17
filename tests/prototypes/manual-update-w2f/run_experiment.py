"""W2f ONLY: same-UID AF_UNIX credential and enrolled process-instance experiment."""
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
SUPPORT = SCRIPT.parent.parent / 'manual-update-w2b/run_experiment.py'
spec = importlib.util.spec_from_file_location('w2f_support', SUPPORT)
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)
TIMEOUT = 5  # test watchdog only


def identity(pid):
    result = support.process_identity(pid)
    result['gid'] = Path(f'/proc/{pid}').stat().st_gid
    return result


def verify(sock, enrolled):
    """Kernel credentials first; bind a live pidfd to enrolled creation identity."""
    result = dict(accepted=False, reason='verification-error', enrolled=enrolled, checked_at=time.monotonic())
    fd = None
    try:
        fields = {'pid', 'uid', 'gid', 'ppid', 'start_ticks'}
        if not isinstance(enrolled, dict) or set(enrolled) != fields or any(type(v) is not int or v < 0 for v in enrolled.values()) or enrolled['pid'] == 0 or enrolled['start_ticks'] == 0:
            raise ValueError('invalid process-instance enrollment')
        raw = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i'))
        if len(raw) != struct.calcsize('3i'):
            raise RuntimeError('short kernel credential record')
        pid, uid, gid = struct.unpack('3i', raw)
        result['kernel'] = dict(pid=pid, uid=uid, gid=gid)
        for key, actual in [('uid', uid), ('gid', gid), ('pid', pid)]:
            if actual != enrolled[key]:
                result['reason'] = f'{key}-mismatch'
                return result
        before = identity(pid)
        fd = os.pidfd_open(pid, 0)
        after = identity(pid)
        result.update(before=before, after=after, pidfd_live=not bool(select.select([fd], [], [], 0)[0]))
        if before != enrolled or after != enrolled:
            result['reason'] = 'process-instance-mismatch'
        elif not result['pidfd_live']:
            result['reason'] = 'process-exited'
        else:
            result.update(accepted=True, reason='enrolled-live-process-instance')
    except (OSError, RuntimeError, KeyError, ValueError, TypeError) as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if fd is not None:
            os.close(fd)
        result['verified_at'] = time.monotonic()
    return result


def send(fd, obj):
    support.write_message(fd, obj)


def receive(fd):
    return support.read_message(fd)


def data_receive(conn):
    """Bounded fixed test frame; None is clean EOF before any payload."""
    deadline, data = time.monotonic() + TIMEOUT, bytearray()
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError('test data deadline expired')
        conn.settimeout(remaining)
        chunk = conn.recv(1)
        if not chunk:
            if data:
                raise RuntimeError('truncated test data frame')
            return None
        if chunk == b'\n':
            return bytes(data)
        data.extend(chunk)
        if len(data) > 8192:
            raise RuntimeError('test data frame too large')


def data_send(conn, payload):
    wire = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode() + b'\n'
    if len(wire) > 8192:
        raise RuntimeError('test data frame too large')
    conn.settimeout(TIMEOUT)
    conn.sendall(wire)
    return len(wire) - 1


def exchange(conn, role, verification, enrolled, claim_pid, impostor):
    """The endpoint decision gates actions; the parent supplies no allow/deny bit."""
    result = dict(event='result', authorized_actions=0, requests_sent=0,
                  trusted_status=0, probe_bytes_discarded=0, spoofed_ack_sent=False,
                  request_claim_pid=None, claimed_ack_pid=None)
    if role == 'client':
        if verification['accepted']:
            data_send(conn, dict(test_request='fixed-ack', claimed_pid=claim_pid))
            result.update(requests_sent=1, request_claim_pid=claim_pid)
            response = data_receive(conn)
            if response is not None:
                if json.loads(response) != dict(test_ack=True, claimed_pid=enrolled['pid']):
                    raise RuntimeError('unexpected fixed acknowledgment')
                result['trusted_status'] = 1
        else:
            # Receive a bounded attack probe solely to record/discard it. Do not
            # parse it as status, send an app request, or authorize anything.
            discarded = data_receive(conn)
            result['probe_bytes_discarded'] = len(discarded or b'')
            result['discarded_probe'] = (discarded or b'').decode('ascii')
    elif impostor:
        # Deliberately pretend to be the enrolled server, despite kernel PID.
        data_send(conn, dict(test_ack=True, claimed_pid=claim_pid))
        result.update(spoofed_ack_sent=True, claimed_ack_pid=claim_pid)
        if data_receive(conn) is not None:
            raise RuntimeError('rejected-server client nevertheless sent a request')
    elif verification['accepted']:
        raw = data_receive(conn)
        if raw is None or json.loads(raw) != dict(test_request='fixed-ack', claimed_pid=enrolled['pid']):
            raise RuntimeError('unexpected fixed request')
        result['authorized_actions'] = 1
        data_send(conn, dict(test_ack=True, claimed_pid=os.getpid()))
    else:
        discarded = data_receive(conn)
        result['probe_bytes_discarded'] = len(discarded or b'')
        result['discarded_probe'] = (discarded or b'').decode('ascii')
    result['completed_at'] = time.monotonic()
    return result


def actor(role, endpoint):
    listener = None
    if role == 'server':
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.settimeout(TIMEOUT)
        listener.bind(endpoint)
        os.chmod(endpoint, 0o600)
        listener.listen(1)
    send(1, dict(event='ready', identity=identity(os.getpid()), privilege=support.privilege()))
    command = receive(0)
    if command['op'] == 'idle':
        send(1, dict(event='idle'))
    elif command['op'] == 'connect':
        enrolled = command['enrolled']
        if role == 'server':
            conn, _ = listener.accept()
        else:
            conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            conn.settimeout(TIMEOUT)
            conn.connect(endpoint)
        with conn:
            verification = verify(conn, enrolled)
            send(1, dict(event='verified', verification=verification))
            if receive(0) != {'op': 'exchange'}:
                raise RuntimeError('invalid exchange barrier')
            result = exchange(conn, role, verification, enrolled, command['claim_pid'], command['impostor'])
        # Close the data channel before reporting, but remain alive until stop.
        send(1, result)
    else:
        raise RuntimeError('unknown actor operation')
    if receive(0) != {'op': 'stop'}:
        raise RuntimeError('invalid shutdown barrier')
    if listener is not None:
        listener.close()


class Actor:
    def __init__(self, role, path):
        self.pidfd = None
        self.proc = None
        self.proc = subprocess.Popen([sys.executable, '-I', str(SCRIPT), '--actor', role, str(path)],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     close_fds=True)
        self.pidfd = os.pidfd_open(self.proc.pid, 0)
        self.ready = receive(self.proc.stdout.fileno())
        if self.ready.get('event') != 'ready' or self.ready['identity'] != identity(self.proc.pid) or self.ready['identity']['ppid'] != os.getpid():
            raise RuntimeError('actor creation identity mismatch')
        if self.ready['privilege']['euid'] == 0 or int(self.ready['privilege']['effective_capabilities'], 16):
            raise RuntimeError('actor is privileged')

    def send(self, obj):
        send(self.proc.stdin.fileno(), obj)

    def read(self):
        return receive(self.proc.stdout.fileno())

    def cleanup(self):
        if self.proc is None:
            return dict(pid=None, exit_code=None, stderr='', reaped=True, not_started=True)
        forced = self.proc.poll() is None
        if forced:
            if self.pidfd is not None:
                try:
                    signal.pidfd_send_signal(self.pidfd, signal.SIGKILL)
                except ProcessLookupError:
                    pass  # raced with our owned child's exit; still reap it below
            else:
                # Popen still owns this unreaped direct child. It cannot have its
                # PID recycled before wait; fallback only for pidfd-open failure.
                self.proc.kill()
        try:
            _, error = self.proc.communicate(timeout=TIMEOUT)
            return dict(pid=self.proc.pid, exit_code=self.proc.returncode,
                        stderr=error.decode(), reaped=True, forced=forced,
                        pidfd_registered=self.pidfd is not None)
        finally:
            for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
                if stream is not None:
                    stream.close()
            if self.pidfd is not None:
                os.close(self.pidfd)


def metadata(path):
    info = path.lstat()
    return dict(device=info.st_dev, inode=info.st_ino, uid=info.st_uid,
                gid=info.st_gid, mode=oct(stat.S_IMODE(info.st_mode)), socket=stat.S_ISSOCK(info.st_mode),
                directory=stat.S_ISDIR(info.st_mode))


def cleanup_root(root, original_root, sockets):
    if metadata(root) != original_root or not original_root['directory']:
        raise RuntimeError('root identity changed; preserving root')
    if set(root.iterdir()) != set(sockets):
        raise RuntimeError('unexpected or unregistered directory entry; preserving root')
    for path, original in sockets.items():
        if metadata(path) != original:
            raise RuntimeError('socket identity changed; preserving root')
    for path in sockets:
        path.unlink()
    root.rmdir()
    return not root.exists()


def validate_case(result):
    """Independent result oracle; do not accept decision bits or zero counts alone."""
    ensure = support.ensure
    name = result['case']
    ensure(name in {'intended', 'unexpected-client', 'unexpected-server'}, 'unknown case')
    ownership = result['ownership']
    ensure(len(ownership) == (2 if name == 'intended' else 3), 'wrong actor count')
    identities = [a['identity'] for a in ownership]
    ensure(len({i['pid'] for i in identities}) == len(identities), 'duplicate actor PID')
    ensure(len({(i['uid'], i['gid']) for i in identities}) == 1, 'not same-UID/GID peers')
    for a in ownership:
        ensure(a['event'] == 'ready' and a['identity']['ppid'] == os.getpid(), 'not owned direct child')
        ensure(a['privilege']['uid'] == a['identity']['uid'] and a['privilege']['euid'] == a['identity']['uid'] != 0 and int(a['privilege']['effective_capabilities'], 16) == 0, 'privileged/mismatched actor')
    root_metadata = result['root_metadata']
    ensure(root_metadata['directory'] and root_metadata['uid'] == os.getuid() and root_metadata['mode'] == '0o700', 'unsafe root metadata')
    ensure(len(result['sockets']) == (2 if name == 'unexpected-server' else 1), 'wrong socket count')
    for socket_metadata in result['sockets'].values():
        ensure(socket_metadata['socket'] and socket_metadata['uid'] == os.getuid() and socket_metadata['gid'] == os.getgid() and socket_metadata['mode'] == '0o600', 'unsafe socket metadata')
    server, client = identities[:2]
    actual_server = identities[-1] if name == 'unexpected-server' else server
    actual_client = identities[-1] if name == 'unexpected-client' else client
    directions = [('server_verifies_client', actual_client, client, name != 'unexpected-client'),
                  ('client_verifies_server', actual_server, server, name != 'unexpected-server')]
    for key, actual, enrolled, accepted in directions:
        snapshot = result[key]
        v = snapshot['verification']
        ensure(snapshot['event'] == 'verified' and v['enrolled'] == enrolled, 'enrollment mismatch')
        ensure(v['kernel'] == {k: actual[k] for k in ('pid', 'uid', 'gid')}, 'kernel peer identity mismatch')
        ensure(type(v['accepted']) is bool and v['accepted'] is accepted, 'wrong verification decision')
        ensure('error' not in v, 'verification error cannot count as expected rejection')
        ensure(v['reason'] == ('enrolled-live-process-instance' if accepted else 'pid-mismatch'), 'wrong rejection/acceptance reason')
        if accepted:
            ensure(v['before'] == enrolled and v['after'] == enrolled and v['pidfd_live'] is True, 'missing process-instance/liveness proof')
        else:
            ensure(actual['pid'] != enrolled['pid'], 'rejection lacks unexpected process')
    sr, cr = result['server_result'], result['client_result']
    expected_counts = ((1, 0, 0), (0, 1, 1)) if name == 'intended' else ((0, 0, 0), (0, int(name == 'unexpected-client'), 0))
    for r, counts in zip((sr, cr), expected_counts):
        ensure(r['event'] == 'result', 'missing exchange result')
        for key, expected in zip(('authorized_actions', 'requests_sent', 'trusted_status'), counts):
            ensure(type(r[key]) is int and r[key] == expected, 'authorization/request/status count mismatch')
        ensure(type(r['probe_bytes_discarded']) is int and r['probe_bytes_discarded'] >= 0, 'invalid discarded-byte count')
        ensure(type(r['spoofed_ack_sent']) is bool, 'invalid spoof flag')
        for key, *_ in directions:
            v = result[key]['verification']
            times = (v['checked_at'], v['verified_at'], result['exchange_released_at'], r['completed_at'])
            ensure(all(type(t) in (int, float) and 0 < t < float('inf') for t in times) and list(times) == sorted(times), 'invalid exchange/verification ordering')
    ensure(cr['request_claim_pid'] == (client['pid'] if name != 'unexpected-server' else None), 'request claim mismatch')
    ensure(sr['spoofed_ack_sent'] is (name == 'unexpected-server') and not cr['spoofed_ack_sent'], 'wrong spoofed acknowledgment count')
    if name == 'unexpected-client':
        probe = dict(test_request='fixed-ack', claimed_pid=client['pid'])
        rejected = sr
    elif name == 'unexpected-server':
        probe = dict(test_ack=True, claimed_pid=server['pid'])
        rejected = cr
        ensure(sr['claimed_ack_pid'] == server['pid'], 'server did not spoof enrolled PID')
    else:
        ensure(sr['probe_bytes_discarded'] == cr['probe_bytes_discarded'] == 0, 'unexpected discarded probe')
        return
    encoded = json.dumps(probe, sort_keys=True, separators=(',', ':'))
    ensure(rejected['discarded_probe'] == encoded and rejected['probe_bytes_discarded'] == len(encoded), 'spoofed probe not observed/discarded')
    ensure((cr if name == 'unexpected-client' else sr)['probe_bytes_discarded'] == 0, 'wrong endpoint discarded data')


def scenario(name):
    if name not in {'intended', 'unexpected-client', 'unexpected-server'}:
        raise ValueError('unknown W2f scenario')
    root = Path(tempfile.mkdtemp(prefix='PROTOTYPE-W2f-'))
    original_root = None
    actors, sockets, result = [], {}, dict(case=name, root=str(root), failures=[], root_removed=False)
    try:
        original_root = metadata(root)
        result['root_metadata'] = original_root
        real_path, fake_path = root / 'real.sock', root / 'fake.sock'
        def start(role, path):
            # Register ownership before subsequent protocol operations.
            obj = Actor.__new__(Actor)
            actors.append(obj)
            obj.__init__(role, path)
            if role == 'server':
                sockets[path] = metadata(path)
                if not sockets[path]['socket'] or sockets[path]['uid'] != os.getuid() or sockets[path]['gid'] != os.getgid() or sockets[path]['mode'] != '0o600':
                    raise RuntimeError('socket ownership/type/mode mismatch')
            return obj
        server = start('server', real_path)
        client = start('client', real_path if name != 'unexpected-server' else fake_path)
        actual_server, actual_client = server, client
        if name == 'unexpected-client':
            actual_client = start('client', real_path)
            client.send(dict(op='idle'))
            client.read()
        if name == 'unexpected-server':
            actual_server = start('server', fake_path)
            server.send(dict(op='idle'))
            server.read()
        result['ownership'] = [a.ready for a in actors]
        if root.stat().st_uid != os.getuid() or stat.S_IMODE(root.stat().st_mode) != 0o700:
            raise RuntimeError('private root ownership/mode mismatch')
        result['sockets'] = {str(p): m for p, m in sockets.items()}
        # Enrollment is exclusively from harness-owned process creation records.
        actual_server.send(dict(op='connect', enrolled=client.ready['identity'], claim_pid=server.proc.pid, impostor=name == 'unexpected-server'))
        actual_client.send(dict(op='connect', enrolled=server.ready['identity'], claim_pid=client.proc.pid, impostor=False))
        sv, cv = actual_server.read(), actual_client.read()
        result['server_verifies_client'], result['client_verifies_server'] = sv, cv
        intended = name == 'intended'
        if sv['event'] != 'verified' or cv['event'] != 'verified':
            raise RuntimeError('missing verification barrier')
        expected = (True, True) if intended else ((False, True) if name == 'unexpected-client' else (True, False))
        observed = (sv['verification']['accepted'], cv['verification']['accepted'])
        if observed != expected:
            raise RuntimeError(f'unexpected authentication decision {observed}')
        if not intended:
            rejected = sv if name == 'unexpected-client' else cv
            if rejected['verification']['reason'] != 'pid-mismatch':
                raise RuntimeError('same-UID rejection did not identify unexpected PID')
        result['exchange_released_at'] = time.monotonic()
        actual_server.send(dict(op='exchange'))
        actual_client.send(dict(op='exchange'))
        result['server_result'], result['client_result'] = actual_server.read(), actual_client.read()
        if result['server_result']['authorized_actions'] != int(intended):
            raise RuntimeError('authorized-action count mismatch')
        if result['client_result']['requests_sent'] != int(name != 'unexpected-server') or result['client_result']['trusted_status'] != int(intended):
            raise RuntimeError('client authorization count mismatch')
        validate_case(result)
        for a in actors:
            a.send(dict(op='stop'))
        for a in actors:
            a.proc.wait(timeout=TIMEOUT)
        result['passed'] = True
    except Exception as exc:
        result.update(passed=False)
        result['failures'].append(f'{type(exc).__name__}: {exc}')
    finally:
        result['cleanup'] = []
        for a in actors:
            try:
                if hasattr(a, 'proc'):
                    result['cleanup'].append(a.cleanup())
            except Exception as exc:
                result['failures'].append(f'cleanup: {exc}')
        try:
            if len(result['cleanup']) != len(actors) or not all(c['reaped'] for c in result['cleanup']):
                raise RuntimeError('actor cleanup uncertain; preserving root')
            result['root_removed'] = cleanup_root(root, original_root, sockets)
            if not result['root_removed']:
                raise RuntimeError('root removal not confirmed')
        except Exception as exc:
            result['failures'].append(f'filesystem cleanup: {exc}')
        if len(result['cleanup']) != len(actors) or any(c['exit_code'] != 0 or c['stderr'] or c['forced'] for c in result['cleanup']):
            result['failures'].append('actor failed or required forced cleanup')
        result['passed'] = result.get('passed', False) and not result['failures']
    return result


def main():
    report = dict(scope='W2f only; no production authentication claim',
                  enrollment='Trusted parent control pipes; independent child creation identities; not production bootstrap',
                  timing='Five-second per-operation test watchdog; no production deadline claim',
                  environment=dict(platform=platform.platform(), python=sys.version,
                                   privilege=support.privilege(), gid=os.getgid()),
                  source_hashes={str(p.relative_to(SCRIPT.parent.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in [SCRIPT, SCRIPT.parent / 'test_checks.py', SUPPORT]},
                  cases=[], failures=[])
    try:
        if os.geteuid() == 0 or int(support.privilege()['effective_capabilities'], 16):
            raise RuntimeError('unprivileged environment required')
        if support.direct_children():
            raise RuntimeError('runner must initially be child-free')
        if not hasattr(signal, 'pidfd_send_signal'):
            raise RuntimeError('Blocked: missing pidfd signaling')
        for attr in ['pidfd_open']:
            if not hasattr(os, attr):
                raise RuntimeError(f'Blocked: missing {attr}')
        if not hasattr(socket, 'SO_PEERCRED'):
            raise RuntimeError('Blocked: SO_PEERCRED unavailable')
        for name in ['intended', 'unexpected-client', 'unexpected-server']:
            case = scenario(name)
            report['cases'].append(case)
            if not case['passed']:
                raise RuntimeError('case failed; dependent cases stopped')
    except Exception as exc:
        report['failures'].append(str(exc))
    report['remaining_children'] = support.direct_children()
    if report['remaining_children']:
        report['failures'].append('unreaped children remain')
    report['passed'] = len(report['cases']) == 3 and not report['failures']
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--actor':
        actor(sys.argv[2], sys.argv[3])
    else:
        sys.exit(main())
