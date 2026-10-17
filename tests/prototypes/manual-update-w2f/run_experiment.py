"""W2f ONLY: same-UID AF_UNIX credential and enrolled process-instance experiment."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import select
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
    except (OSError, RuntimeError, KeyError, ValueError) as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if fd is not None:
            os.close(fd)
    return result


def send(fd, obj):
    support.write_message(fd, obj)


def receive(fd):
    return support.read_message(fd)


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
    else:
        enrolled = command['enrolled']
        if role == 'server':
            conn, _ = listener.accept()
        else:
            conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            conn.settimeout(TIMEOUT)
            conn.connect(endpoint)
        with conn:
            conn.settimeout(TIMEOUT)
            verification = verify(conn, enrolled)
            # Independent trusted control barrier: neither peer exits while the
            # other performs its process-instance checks. No application action yet.
            send(1, dict(event='verified', verification=verification))
            go = receive(0)
            authorized = requests = trusted_status = 0
            if go['allow'] and verification['accepted']:
                if role == 'client':
                    send(conn.fileno(), dict(test_request='fixed-ack', claimed_pid=enrolled['pid']))
                    requests = 1
                    response = receive(conn.fileno())
                    if response != {'test_ack': True}:
                        raise RuntimeError('unexpected test acknowledgment')
                    trusted_status = 1
                else:
                    request = receive(conn.fileno())
                    if request != {'test_request': 'fixed-ack', 'claimed_pid': os.getpid()}:
                        raise RuntimeError('unexpected fixed request')
                    authorized = 1
                    send(conn.fileno(), dict(test_ack=True))
            # Rejected peers never send requests or accept trusted status.
            send(1, dict(event='result', authorized_actions=authorized,
                         requests_sent=requests, trusted_status=trusted_status, completed_at=time.monotonic()))
    receive(0)  # explicit harness-owned shutdown barrier
    if listener is not None:
        listener.close()


class Actor:
    def __init__(self, role, path):
        self.proc = subprocess.Popen([sys.executable, '-I', str(SCRIPT), '--actor', role, str(path)],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     close_fds=True)
        self.pidfd = os.pidfd_open(self.proc.pid, 0)
        self.ready = receive(self.proc.stdout.fileno())
        if self.ready['identity'] != identity(self.proc.pid):
            raise RuntimeError('actor creation identity mismatch')
        if self.ready['privilege']['euid'] == 0 or int(self.ready['privilege']['effective_capabilities'], 16):
            raise RuntimeError('actor is privileged')

    def send(self, obj):
        send(self.proc.stdin.fileno(), obj)

    def read(self):
        return receive(self.proc.stdout.fileno())

    def cleanup(self):
        if self.proc.poll() is None:
            # Signals address our registered process instance, never a numeric PID.
            import signal
            signal.pidfd_send_signal(self.pidfd, signal.SIGKILL)
        code = self.proc.wait(timeout=TIMEOUT)
        error = self.proc.stderr.read().decode()
        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            stream.close()
        os.close(self.pidfd)
        return dict(pid=self.proc.pid, exit_code=code, stderr=error, reaped=True)


def metadata(path):
    info = path.lstat()
    return dict(device=info.st_dev, inode=info.st_ino, uid=info.st_uid,
                gid=info.st_gid, mode=oct(stat.S_IMODE(info.st_mode)), socket=stat.S_ISSOCK(info.st_mode))


def scenario(name):
    root = Path(tempfile.mkdtemp(prefix='PROTOTYPE-W2f-'))
    actors, sockets, result = [], {}, dict(case=name, root=str(root), failures=[])
    try:
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
        result['root_metadata'] = dict(uid=root.stat().st_uid, mode=oct(stat.S_IMODE(root.stat().st_mode)))
        result['sockets'] = {str(p): m for p, m in sockets.items()}
        # Enrollment is exclusively from harness-owned process creation records.
        actual_server.send(dict(op='connect', enrolled=client.ready['identity']))
        actual_client.send(dict(op='connect', enrolled=server.ready['identity']))
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
        actual_server.send(dict(allow=intended))
        actual_client.send(dict(allow=intended))
        result['server_result'], result['client_result'] = actual_server.read(), actual_client.read()
        if result['server_result']['authorized_actions'] != int(intended):
            raise RuntimeError('authorized-action count mismatch')
        if result['client_result']['requests_sent'] != int(intended) or result['client_result']['trusted_status'] != int(intended):
            raise RuntimeError('client authorization count mismatch')
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
                if hasattr(a, 'pidfd'):
                    result['cleanup'].append(a.cleanup())
            except Exception as exc:
                result['failures'].append(f'cleanup: {exc}')
        try:
            if set(root.iterdir()) != set(sockets):
                raise RuntimeError('unexpected or unregistered directory entry; preserving root')
            for path, original in sockets.items():
                if metadata(path) != original:
                    raise RuntimeError('socket identity changed; preserving root')
            for path in sockets:
                path.unlink()
            root.rmdir()
            result['root_removed'] = not root.exists()
        except Exception as exc:
            result['failures'].append(f'filesystem cleanup: {exc}')
        if any(c['exit_code'] != 0 or c['stderr'] for c in result['cleanup']):
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
        report['remaining_children'] = support.direct_children()
        if report['remaining_children']:
            raise RuntimeError('unreaped children remain')
    except Exception as exc:
        report['failures'].append(str(exc))
    report['passed'] = len(report['cases']) == 3 and not report['failures']
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--actor':
        actor(sys.argv[2], sys.argv[3])
    else:
        sys.exit(main())
