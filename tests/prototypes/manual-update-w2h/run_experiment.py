"""W2h only: live-client socket delegation diagnostic, not an authentication fix."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import signal
import socket
import subprocess
import sys
import tempfile
import time

SCRIPT = Path(__file__).resolve()
HELPER = SCRIPT.parent.parent / 'manual-update-w2g/run_experiment.py'
spec = importlib.util.spec_from_file_location('w2h_reviewed_helpers', HELPER)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)  # definitions only; previous experiment entrypoints never run
peer, support, ensure = g.peer, g.support, g.ensure
TIMEOUT = g.TIMEOUT
CASES = ('healthy-original-client', 'live-client-delegation')


def server(endpoint):
    retained = None
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
        listener.settimeout(TIMEOUT)
        listener.bind(endpoint)
        os.chmod(endpoint, 0o600)
        listener.listen(1)
        support.write_message(1, g.ready())
        command = support.read_message(0)
        ensure(set(command) == {'op', 'enrolled'} and command['op'] == 'connect', 'invalid fixed server setup')
        conn, _ = listener.accept()
        try:
            with conn:
                enrolled = command['enrolled']
                verification = peer.verify(conn, enrolled)
                ensure(verification['accepted'], 'initial client verification failed')
                retained = g.bind_process(enrolled)
                support.write_message(1, g.ready('authenticated', verification=verification,
                    retained_pidfd=retained, pidfd_live=g.live(retained),
                    pidfd_inheritable=os.get_inheritable(retained), descriptor=g.descriptor(conn)))
                ensure(support.read_message(0) == {'op': 'evaluate'}, 'invalid evaluation barrier')
                # Exact reviewed guard and fixed request; no mutant/disable input.
                result = g.evaluate(conn, enrolled, retained, 'guarded')
                result.update(credential_guard_enabled=True, liveness_guard_enabled=True)
                support.write_message(1, result)
                ensure(support.read_message(0) == {'op': 'stop'}, 'invalid server shutdown')
        finally:
            if retained is not None:
                os.close(retained)


def holder(data_fd, control_fd):
    sent = 0
    with socket.socket(fileno=data_fd) as conn, socket.socket(fileno=control_fd) as control:
        support.write_message(control.fileno(), g.ready('holder-ready', descriptor=g.descriptor(conn),
            kernel_server=g.credentials(conn), requests_sent_total=sent))
        while True:
            command = support.read_message(control.fileno())
            if command['op'] == 'ping':
                support.write_message(control.fileno(), g.ready('holder-alive', descriptor=g.descriptor(conn), requests_sent_total=sent))
            elif command['op'] == 'send':
                ensure(sent == 0, 'holder already sent its fixed request')
                peer.data_send(conn, g.fixed_request(command['claim_pid']))
                sent += 1
                support.write_message(control.fileno(), g.ready('request-sent', descriptor=g.descriptor(conn),
                    requests_sent=1, requests_sent_total=sent, sent_at=time.monotonic()))
            elif command['op'] == 'stop':
                support.write_message(control.fileno(), g.ready('holder-exiting', requests_sent_total=sent))
                return
            else:
                raise RuntimeError('unknown fixed holder operation')


def client(endpoint, control_fd):
    sent, reaped = 0, False
    support.write_message(1, g.ready())
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(TIMEOUT)
        command = support.read_message(0)
        ensure(set(command) == {'op', 'enrolled'} and command['op'] == 'connect', 'invalid client setup')
        conn.connect(endpoint)
        verification = peer.verify(conn, command['enrolled'])
        ensure(verification['accepted'], 'initial server verification failed')
        support.write_message(1, g.ready('authenticated', verification=verification, descriptor=g.descriptor(conn)))
        ensure(support.read_message(0) == {'op': 'spawn-holder'}, 'invalid holder barrier')
        passed = (conn.fileno(), control_fd)
        child = subprocess.Popen([sys.executable, '-I', str(SCRIPT), '--holder', str(conn.fileno()), str(control_fd)],
            pass_fds=passed, close_fds=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.close(control_fd)
        support.write_message(1, g.ready('holder-spawned', child_identity=peer.identity(child.pid),
            descriptor=g.descriptor(conn), holder_control_fd=control_fd, pass_fds=list(passed), close_fds=True))
        while True:
            command = support.read_message(0)
            if command['op'] == 'status':
                support.write_message(1, g.ready('client-alive', requests_sent_total=sent, descriptor=g.descriptor(conn)))
            elif command['op'] == 'send':
                ensure(sent == 0, 'client already sent its fixed request')
                peer.data_send(conn, g.fixed_request(os.getpid()))
                sent += 1
                support.write_message(1, g.ready('request-sent', requests_sent=1, requests_sent_total=sent,
                    descriptor=g.descriptor(conn), sent_at=time.monotonic()))
            elif command['op'] == 'reap-holder':
                code = child.wait(timeout=TIMEOUT)
                ensure(code == 0, 'holder did not exit zero')
                reaped = True
                support.write_message(1, g.ready('holder-reaped', child_pid=child.pid, exit_code=code))
            elif command['op'] == 'stop':
                ensure(reaped, 'normal client shutdown requires reaped holder')
                support.write_message(1, g.ready('client-exiting', requests_sent_total=sent))
                return
            else:
                raise RuntimeError('unknown fixed client operation')


class Actor(g.Actor):
    """Use reviewed cleanup utilities; launch only this W2h fixed actor script."""
    def __init__(self, role, endpoint, passed=()):
        ensure(role in ('server', 'client'), 'unknown direct actor')
        self.proc, self.pidfd = None, None
        args = [sys.executable, '-I', str(SCRIPT), '--' + role, str(endpoint)]
        if role == 'client':
            args.append(str(passed[0]))
        self.proc = subprocess.Popen(args, pass_fds=passed, close_fds=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.initial = peer.identity(self.proc.pid)
        ensure(self.initial['ppid'] == os.getpid(), 'not an owned direct child')
        self.pidfd = g.bind_process(self.initial)


class Case(g.Case):
    def __init__(self, name):
        ensure(name in CASES, 'unknown W2h case')
        super().__init__('healthy')  # bookkeeping only; never calls a W2g scenario
        self.name = name
        self.report.update(case=name, counterexample=None)

    def start(self, role, passed=()):
        actor = Actor.__new__(Actor)
        self.actors.append(actor)
        actor.__init__(role, self.root / 'peer.sock', passed)
        msg = actor.read()
        self.event(role + '-ready', reply=msg)
        g.validate_actor_snapshot(msg, actor.initial, 'ready')
        return actor

    def client_observation(self, actor):
        msg = self.command(actor, 'status')
        g.validate_actor_snapshot(msg, actor.initial, 'client-alive')
        observed = dict(identity=peer.identity(actor.proc.pid), pidfd_live=g.live(actor.pidfd),
                        observed_at=time.monotonic(), exit_code=actor.proc.poll())
        ensure(observed['identity'] == actor.initial and observed['pidfd_live'] and observed['exit_code'] is None,
               'original client no longer alive at barrier')
        msg['runner_observed'] = observed
        return msg

    def run(self):
        self.root = Path(tempfile.mkdtemp(prefix='PROTOTYPE-W2h-'))
        self.report['root'] = str(self.root)
        self.root_before = peer.metadata(self.root)
        self.report['root_identity'] = self.root_before
        ensure(self.root_before['directory'] and self.root_before['uid'] == os.geteuid() and self.root_before['mode'] == '0o700', 'unsafe root')
        srv = self.start('server')
        path = self.root / 'peer.sock'
        self.sockets[path] = peer.metadata(path)
        ensure(self.sockets[path]['socket'] and self.sockets[path]['uid'] == os.geteuid() and self.sockets[path]['mode'] == '0o600', 'unsafe socket')
        self.report['socket_path_identity'] = self.sockets[path]
        self.parent_control, self.child_control = socket.socketpair()  # separate trusted control plumbing only
        cli = self.start('client', (self.child_control.fileno(),))
        self.child_control.close()
        self.event('connect-barrier', enrolled_client=cli.initial, enrolled_server=srv.initial)
        srv.send(dict(op='connect', enrolled=cli.initial))
        cli.send(dict(op='connect', enrolled=srv.initial))
        sa, ca = srv.read(), cli.read()
        self.event('mutual-authentication', server=sa, client=ca)
        self.report.update(server_auth=sa, client_auth=ca, enrolled_server=srv.initial,
                           enrolled_client=cli.initial, client_socket=ca['descriptor'])
        g.validate_actor_snapshot(sa, srv.initial, 'authenticated')
        g.validate_actor_snapshot(ca, cli.initial, 'authenticated')
        ensure(sa['verification']['accepted'] is True and ca['verification']['accepted'] is True and
               sa['pidfd_live'] is True and sa['pidfd_inheritable'] is False, 'initial authentication/retained pidfd failed')
        spawned = self.command(cli, 'spawn-holder')
        self.holder_identity = spawned['child_identity']
        ensure(self.holder_identity['ppid'] == cli.proc.pid, 'holder not owned by original client')
        self.holder_fd = g.bind_process(self.holder_identity)
        hr = self.holder_message()
        self.report['inheritance'] = dict(spawned=spawned, holder_ready=hr)
        self.validate_holder(hr, cli, False, 'holder-ready')
        self.report['client_before'] = self.client_observation(cli)
        hb = self.holder_message('ping')
        self.validate_holder(hb, cli, False)
        self.report['holder_before'] = hb
        delegated = self.name == CASES[1]
        sent = self.holder_message('send', claim_pid=cli.proc.pid) if delegated else self.command(cli, 'send')
        self.report['request_sender'] = sent
        self.report['evaluation'] = self.command(srv, 'evaluate')
        ha = self.holder_message('ping')
        self.validate_holder(ha, cli, False)
        self.report['holder_after'] = ha
        self.report['client_after'] = self.client_observation(cli)
        outcome = validate_result(self.report)
        self.report.update(outcome)
        stopped = self.holder_message('stop')
        ensure(stopped['event'] == 'holder-exiting', 'holder shutdown missing')
        reaped = self.command(cli, 'reap-holder')
        ensure(reaped['event'] == 'holder-reaped' and reaped['child_pid'] == self.holder_identity['pid'] and
               reaped['exit_code'] == 0 and not g.live(self.holder_fd), 'holder reap missing')
        self.holder_reaped = True
        self.report['holder_reap'] = dict(pid=reaped['child_pid'], exit_code=0, by='original-client', reaped=True)
        self.command(cli, 'stop')
        ensure(cli.proc.wait(timeout=TIMEOUT) == 0, 'client shutdown failed')
        srv.send(dict(op='stop'))
        ensure(srv.proc.wait(timeout=TIMEOUT) == 0, 'server shutdown failed')


def validate_result(report):
    """An observed delegated action is a counterexample, never authentication Pass."""
    name, evaluation = report['case'], report['evaluation']
    ensure(name in CASES and evaluation['event'] == 'evaluation', 'wrong diagnostic case/result')
    delegated = name == CASES[1]
    client_id, server_id = report['enrolled_client'], report['enrolled_server']
    runner = report['runner_identity']
    ensure(client_id['ppid'] == server_id['ppid'] == runner['pid'] and client_id['pid'] != server_id['pid'], 'direct actor ownership mismatch')
    ensure(client_id['uid'] == server_id['uid'] == runner['uid'] != 0 and client_id['gid'] == server_id['gid'], 'account scope mismatch')
    for key, actor_id, peer_id in [('server_auth', server_id, client_id), ('client_auth', client_id, server_id)]:
        auth = report[key]
        g.validate_actor_snapshot(auth, actor_id, 'authenticated')
        g.validate_socket_snapshot(auth['descriptor'])
        proof = auth['verification']
        ensure(proof['accepted'] is True and proof['reason'] == 'enrolled-live-process-instance' and 'error' not in proof,
               'missing initial authentication')
        ensure(proof['enrolled'] == proof['before'] == proof['after'] == peer_id and proof['pidfd_live'] is True, 'missing initial process proof')
        ensure(proof['kernel'] == {k: peer_id[k] for k in ('pid', 'uid', 'gid')}, 'wrong initial kernel credentials')
    sa = report['server_auth']
    ensure(sa['pidfd_live'] is True and sa['pidfd_inheritable'] is False and
           evaluation['retained_pidfd'] == sa['retained_pidfd'] and evaluation['retained_pidfd_inheritable'] is False, 'retained pidfd changed')
    ensure(evaluation['variant'] == 'guarded' and evaluation['credential_guard_enabled'] is True and
           evaluation['liveness_guard_enabled'] is True and evaluation['original_client_live'] is True, 'guards disabled or client exited')
    ensure(evaluation['kernel'] == {k: client_id[k] for k in ('pid', 'uid', 'gid')}, 'server credentials no longer identify enrolled client')
    ensure(evaluation['request'] == g.fixed_request(client_id['pid']) and type(evaluation['requests_received']) is int and evaluation['requests_received'] == 1, 'wrong request/count')
    ensure(type(evaluation['authorized_actions']) is int and evaluation['authorized_actions'] == 1 and evaluation['reason'] == 'enrolled-client-live', 'unexpected guard outcome; investigate before continuing')
    client_socket = report['client_socket']
    ensure(client_socket == report['client_auth']['descriptor'], 'client socket snapshot diverged')
    spawned, hr = report['inheritance']['spawned'], report['inheritance']['holder_ready']
    holder_id = hr['identity']
    g.validate_actor_snapshot(spawned, client_id, 'holder-spawned')
    g.validate_actor_snapshot(hr, spawned['child_identity'], 'holder-ready')
    ensure(holder_id['ppid'] == client_id['pid'] and holder_id['pid'] not in (client_id['pid'], server_id['pid'], runner['pid']) and
           holder_id['uid'] == client_id['uid'] and holder_id['gid'] == client_id['gid'], 'holder ownership/account mismatch')
    ensure(hr['kernel_server'] == {k: server_id[k] for k in ('pid', 'uid', 'gid')}, 'holder server credentials mismatch')
    passed = spawned['pass_fds']
    ensure(spawned['close_fds'] is True and len(passed) == 2 and len(set(passed)) == 2 and
           all(type(fd) is int and fd >= 0 for fd in passed) and
           set(passed) == {spawned['descriptor']['fd'], spawned['holder_control_fd']}, 'wrong explicit inheritance set')
    ensure(spawned['descriptor']['inheritable'] is False and hr['descriptor']['inheritable'] is True, 'descriptor inheritance flags changed')
    for record in (spawned['descriptor'], hr['descriptor'], client_socket):
        g.validate_socket_snapshot(record)
        ensure(g.same_socket(client_socket, record), 'not the inherited connected endpoint')
    ensure(type(hr['requests_sent_total']) is int and hr['requests_sent_total'] == 0, 'holder sent before readiness')
    cb, ca, hb, ha, sent = (report[k] for k in ('client_before', 'client_after', 'holder_before', 'holder_after', 'request_sender'))
    for msg, expected, event in [(cb, client_id, 'client-alive'), (ca, client_id, 'client-alive'),
                                 (hb, holder_id, 'holder-alive'), (ha, holder_id, 'holder-alive'),
                                 (sent, holder_id if delegated else client_id, 'request-sent')]:
        g.validate_actor_snapshot(msg, expected, event)
        g.validate_socket_snapshot(msg['descriptor'])
        ensure(g.same_socket(client_socket, msg['descriptor']), 'actor socket identity changed')
    for msg, expected in [(cb, client_id), (ca, client_id), (hb, holder_id), (ha, holder_id)]:
        observed = msg['runner_observed']
        ensure(observed['identity'] == expected and observed['pidfd_live'] is True, 'missing independent live-process proof')
    ensure(cb['runner_observed']['exit_code'] is None and ca['runner_observed']['exit_code'] is None, 'original client terminated')
    counts = [(cb, 0), (hb, 0), (ca, int(not delegated)), (ha, int(delegated)), (sent, 1)]
    ensure(all(type(msg['requests_sent_total']) is int and msg['requests_sent_total'] == expected for msg, expected in counts), 'sender/non-sender request accounting mismatch')
    ensure(type(sent['requests_sent']) is int and sent['requests_sent'] == 1, 'missing actual sender request')
    times = (cb['runner_observed']['observed_at'], hb['runner_observed']['observed_at'], sent['sent_at'], evaluation['evaluated_at'],
             ha['runner_observed']['observed_at'], ca['runner_observed']['observed_at'])
    ensure(all(type(t) in (int, float) and 0 < t < float('inf') for t in times) and list(times) == sorted(times), 'barrier ordering invalid')
    if delegated:
        return dict(result='CounterexampleDetected', authentication_safety='CounterexampleDetected',
                    counterexample=dict(kind='live-client-socket-delegation', actual_sender=holder_id,
                                        enrolled_client=client_id, server_permitted_actions=1))
    return dict(result='Pass', authentication_safety='HealthyControlOnly', counterexample=None)


def main():
    paths = [SCRIPT, SCRIPT.with_name('test_checks.py'), HELPER, g.PEER_HELPER, peer.SUPPORT]
    report = dict(scope='W2h only; pre-commit in-memory test authority', started_utc=datetime.now(timezone.utc).isoformat(),
        environment=dict(platform=platform.platform(), python=sys.version, privilege=support.privilege(), gid=os.getgid()),
        timing='Five-second test diagnostic watchdogs only', source_hashes={str(p.relative_to(SCRIPT.parent.parent)):
        hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}, cases=[], failures=[], subreaper={})
    original = None
    try:
        ensure(sys.platform == 'linux' and os.getuid() == os.geteuid() != 0 and not int(support.privilege()['effective_capabilities'], 16), 'Blocked: unprivileged Linux required')
        ensure(not support.direct_children(), 'Blocked: initially child-free runner required')
        ensure(hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal') and hasattr(socket, 'SO_PEERCRED'), 'Blocked: missing primitives')
        original = support.subreaper()
        report['subreaper']['before'] = original
        support.subreaper(1)  # fallback ownership only; healthy clients normally reap their holders
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
            ensure(case.report['result'] == ('Pass' if name == CASES[0] else 'CounterexampleDetected'), 'diagnostic case failed; stopping')
    except Exception as exc:
        report['failures'].append(f'{type(exc).__name__}: {exc}')
    finally:
        if original is not None:
            try:
                support.subreaper(original)
                report['subreaper']['after'] = support.subreaper()
                ensure(report['subreaper']['after'] == original, 'restoration failed')
            except Exception as exc:
                report['failures'].append(f'restoration: {exc}')
        report['remaining_children'] = support.direct_children()
        if report['remaining_children']:
            report['failures'].append('children remain; unknown processes never signaled')
    report['diagnostic_success'] = len(report['cases']) == 2 and not report['failures'] and [c['result'] for c in report['cases']] == ['Pass', 'CounterexampleDetected']
    report['authentication_safety'] = 'CounterexampleDetected' if any(c['counterexample'] for c in report['cases']) else 'Unresolved'
    report['production_readiness'] = False
    print(json.dumps(report, indent=2))
    return 0 if report['diagnostic_success'] else 1


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
        raise RuntimeError('unknown fixed W2h role')
