"""Mocked/local logic ONLY. No KVM, polkit, pidfd, ACL syscall or guest execution."""
import copy
from contextlib import nullcontext
import io
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import Mock, patch

from mint_validation import driver as d
from mint_validation import host_preflight as h

RUN = '00000000-0000-4000-8000-000000000001'
VM = '00000000-0000-4000-8000-000000000002'
BOOT = '00000000-0000-4000-8000-000000000003'
RID = '00000000-0000-4000-8000-000000000004'
ASSETS = {key: ('mock-' + key).encode() for key in d.ASSETS}


def approval():
    return {'schemaVersion': 1, 'runId': RUN, 'vmId': VM, 'bootId': BOOT,
            'purpose': 'mint-phase3-negative-and-sentinel-only',
            'productionCommit': d.PRODUCTION_COMMIT,
            'artifactSha256': {k: d.digest(v) for k, v in ASSETS.items()},
            'actions': d.ACTIONS.copy(), 'uids': {'sde-student': 1001, 'sde-other': 1002, 'sde-mentor': 1003},
            'mediaSha256': 'a' * 64, 'expiresBootMs': 1_000_000}


def facts():
    return {'vmId': VM, 'bootId': BOOT, 'bootMs': 10_000, 'euid': 0, 'ruid': 0, 'egid': 0,
            'mint': '22.3', 'virtualization': 'QEMU', 'container':'none', 'pid1':'systemd'}


class FakeNative:
    """In-memory ownership journal; paths below are never touched on the host."""
    def __init__(self):
        self.files = {}
        self.states = []
        self.mutations = []
        self.fail_at = None
        self.counter = 0
        self.package = (1, b'')
        self.fail_journal = False

    def cleanup_gate(self):
        return nullcontext()

    def children(self, path):
        return sorted(Path(p).name for p in self.files if Path(p).parent == path)

    def exists(self, path):
        return str(path) in self.files

    def trusted(self, path):
        pass

    def command(self, argv, timeout=5):
        assert argv == ['/usr/bin/dpkg-query', '-W', '-f=${db:Status-Status}', 'skyview-dev-setup']
        return self.package

    def atomic(self, path, value):
        if self.fail_journal:
            raise OSError('mock flush failure')
        self.states.append(copy.deepcopy(value))
        self.files[str(path)] = {'data': copy.deepcopy(value)}

    def create(self, op):
        if self.counter == self.fail_at:
            raise OSError('mock create failure')
        self.counter += 1
        kind, path, mode, data = op
        assert not self.exists(path)
        fp = {'dev': 1, 'ino': self.counter, 'uid': 0, 'mode': mode, 'kind': kind,
              'sha256': None if data is None else d.digest(data)}
        self.files[str(path)] = copy.deepcopy(fp)
        self.mutations.append(str(path))
        return fp

    def fingerprint(self, path):
        return copy.deepcopy(self.files[str(path)])

    def remove(self, path, kind):
        self.mutations.append('remove:' + str(path))
        del self.files[str(path)]


class PreflightTests(unittest.TestCase):
    def host(self):
        return {'os': 'ubuntu', 'version': '24.04', 'arch': 'x86_64', 'disposable': True,
                'kvm_api': 12, 'tools_trusted': True, 'loopback_console': True, 'no_host_mounts': True,
                'cpus': 2, 'available_memory': 6 * 1024**3, 'available_disk': 36 * 1024**3}

    def test_host_preflight_no_fallback_and_each_prerequisite(self):
        self.assertTrue(d.host_check(self.host())['ready'])
        for key, value in self.host().items():
            bad = self.host()
            bad[key] = None
            result = d.host_check(bad)
            self.assertFalse(result['ready'], key)
            self.assertIn(key, result['blockers'])
            self.assertFalse(result['fallbackAllowed'])
        bad = self.host(); bad['disposable'] = 1
        self.assertFalse(d.host_check(bad)['ready'])

    def test_media_requires_unique_authenticated_cinnamon_pin(self):
        pin = 'a' * 64
        text = pin + ' *' + d.ISO + '\n'
        status = '[GNUPG:] VALIDSIG ' + d.FINGERPRINT + ' 2026-01-01 1 0 4 0 1 10 00 ' + d.FINGERPRINT
        self.assertTrue(d.media_check(text, status, 0, pin, pin)['authenticated'])
        for args in [(text, status, 1, pin, pin), (text, status, False, pin, pin),
                     (text, status, 0, pin, None), (text + text, status, 0, pin, pin),
                     (text.replace('cinnamon', 'xfce'), status, 0, pin, pin),
                     (text, status.replace(d.FINGERPRINT, 'B' * 40), 0, pin, pin),
                     (text, status+'\n'+status, 0, pin, pin), (text, status, 0, 'b'*64, pin)]:
            with self.subTest(args=args):
                with self.assertRaises(d.Stop): d.media_check(*args)

    def test_readonly_host_cli_never_collects_without_explicit_flag(self):
        with patch.object(h, 'collect') as collect:
            with self.assertRaises(d.Stop): h.main([])
            collect.assert_not_called()

    def test_mocked_host_cli_does_not_claim_media_or_native_proof(self):
        with patch.object(h, 'collect', return_value=self.host()), patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(h.main(['--execute-read-only', '--workspace', '/mock']), 2)
        result = json.loads(out.getvalue())
        self.assertIn('authenticated-media', result['blockers'])
        self.assertFalse(result['declarationsAreAttestation'])
        self.assertFalse(result['nativeGuestTestsExecuted'])


class ApprovalTests(unittest.TestCase):
    def test_approval_binds_vm_boot_artifacts_scope_expiry_and_accounts(self):
        a = approval()
        self.assertEqual(d.approval_check(a, facts(), a['artifactSha256']), a)
        for field, value in [('schemaVersion', True), ('purpose', 'install'), ('productionCommit', 'main'),
                             ('vmId', RUN), ('bootId', RUN), ('actions', d.ACTIONS+['packages']),
                             ('expiresBootMs', 10_000), ('expiresBootMs', 1_810_001),
                             ('uids', {'sde-student': 0, 'sde-other': 1, 'sde-mentor': 2}),
                             ('artifactSha256', {}), ('mediaSha256', 'xfce-digest')]:
            bad = approval(); bad[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(d.Stop): d.approval_check(bad, facts(), a['artifactSha256'])
        for field, value in [('euid', 1000), ('mint', 'Ubuntu'), ('virtualization', 'Docker'), ('container','docker'), ('pid1','bash')]:
            f = facts(); f[field] = value
            with self.assertRaises(d.Stop): d.approval_check(a, f, a['artifactSha256'])

    def test_default_plan_has_no_native_backend(self):
        with patch.object(d, 'Native') as native, patch('sys.stdout', new_callable=io.StringIO) as out:
            d.main(['plan'])
            native.assert_not_called()
        p = json.loads(out.getvalue())
        self.assertFalse(p['nativeExecuted']); self.assertFalse(p['productionReady'])
        self.assertEqual(p['capabilityReceipt'], {})

    def test_every_native_entry_requires_explicit_execute(self):
        for action in ['prepare', 'arm-desktop', 'capture', 'cleanup', 'desktop-request', 'acl-probe']:
            with self.subTest(action=action), patch.object(d, 'Native') as native:
                with self.assertRaises(d.Stop): d.main([action])
                native.assert_not_called()

    def test_json_rejects_duplicates_bad_encoding_and_bounds(self):
        for data in [b'{"runId":1,"runId":2}', b'\xff', b'x'*65537]:
            with self.assertRaises(d.Stop): d.strict_json(data)


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.n = FakeNative()
        self.ledger = Path('/run/sde-mint-validation-'+RUN+'/ownership.json')

    def prepare(self, kind='production'):
        return d.prepare(self.n, approval(), ASSETS, kind, self.ledger)

    def test_plan_only_fixed_paths_invalid_capability_and_no_coordination(self):
        plan = d.fixture_plan(approval(), ASSETS, 'production')
        files = {str(path): (mode, data) for kind, path, mode, data in plan if kind == 'file'}
        self.assertEqual(files[str(d.ROOT/'app-only-capabilities.json')], (0o600, b'{}'))
        self.assertEqual(files[str(d.ENTRY)], (0o755, ASSETS['broker']))
        self.assertFalse(any(str(d.COORDINATION) in str(op[1]) for op in plan))
        sentinel = d.fixture_plan(approval(), ASSETS, 'sentinel')
        worker = next(op[3] for op in sentinel if str(op[1]).endswith('/engines/'+RUN+'/sde-update-trust'))
        self.assertEqual(worker, ASSETS['sentinel'])

    def test_prepare_journals_before_every_mutation_and_consumes_run(self):
        state = self.prepare()
        self.assertFalse(state['sealed'])
        self.assertEqual(state['pending'], None)
        self.assertEqual(len(state['entries']), len(self.n.mutations))
        for path in self.n.mutations:
            self.assertTrue(any(s['pending'] == path for s in self.n.states))
        with self.assertRaises(d.Stop): self.prepare()

    def test_collision_and_ambiguous_package_state_never_mutate(self):
        for path in [d.ROOT, d.ENTRY, d.POLICY, d.TOOLS, d.COORDINATION]:
            n = FakeNative(); n.files[str(path)] = {}
            with self.assertRaises(d.Stop): d.prepare(n, approval(), ASSETS, 'production', self.ledger)
            self.assertEqual(n.mutations, [])
        self.n.package = (2, b'')
        with self.assertRaises(d.Stop): self.prepare()
        self.assertEqual(self.n.mutations, [])

    def test_journal_failure_stops_before_first_mutation(self):
        self.n.fail_journal = True
        with self.assertRaises(OSError): self.prepare()
        self.assertEqual(self.n.mutations, [])

    def test_each_partial_prepare_failure_keeps_pending_no_rollback(self):
        for index in range(len(d.fixture_plan(approval(), ASSETS, 'production'))):
            n = FakeNative(); n.fail_at = index
            with self.assertRaises(OSError): d.prepare(n, approval(), ASSETS, 'production', self.ledger)
            self.assertIsNotNone(n.states[-1]['pending'])
            self.assertFalse(any(v.startswith('remove:') for v in n.mutations))

    def test_cleanup_refuses_unsealed_or_changed_identity_before_deletion(self):
        state = self.prepare()
        with self.assertRaises(d.Stop): d.cleanup(self.n, state, self.ledger)
        state['sealed'] = True; state['phase'] = 'Sealed'
        self.n.files[state['entries'][0]['path']]['ino'] += 1
        with self.assertRaises(d.Stop): d.cleanup(self.n, state, self.ledger)
        self.assertFalse(any(v.startswith('remove:') for v in self.n.mutations))

    def test_cleanup_validates_all_then_removes_reverse_owned_objects_only(self):
        state = self.prepare(); state['sealed'] = True; state['phase'] = 'Sealed'
        d.cleanup(self.n, state, self.ledger)
        self.assertEqual(state['cleanup'], 'Pass')
        self.assertEqual([x[7:] for x in self.n.mutations if x.startswith('remove:')],
                         [x['path'] for x in reversed(state['entries'])])
        self.assertEqual(set(self.n.files), {str(self.ledger)})


class EvidenceTests(unittest.TestCase):
    def test_stop_aware_bounded_evidence_never_continues_after_sink_failure(self):
        writer = Mock(side_effect=OSError('mock full disk'))
        e = d.Evidence(writer)
        with self.assertRaises(OSError): e.add('case-a', {'outcome': 'Fail'})
        with self.assertRaises(d.Stop): e.add('case-b', {'outcome': 'Pass'})
        self.assertEqual(writer.call_count, 1)
        e = d.Evidence(Mock())
        with self.assertRaises(d.Stop): e.add('case-a', {'data': 'x'*65536})
        self.assertTrue(e.stopped)

    def test_acl_exact_mask_and_named_uid_required(self):
        raw = struct.pack('<I', 2)+b''.join(struct.pack('<HHI', *x) for x in
             [(1,6,2**32-1),(2,4,1001),(4,0,2**32-1),(16,4,2**32-1),(32,0,2**32-1)])
        d.acl_check(raw, 1001)
        with self.assertRaises(d.Stop): d.acl_check(raw, 1002)
        with self.assertRaises(d.Stop): d.acl_check(raw[:-1], 1001)

    def test_deferral_never_accepts_ready_installation_or_missing_kernel_context(self):
        r = {'schemaVersion':1, 'requestId': RID, 'uid': 1001, 'bootId': BOOT, 'createdMs': 1, 'deadlineMs': 900001}
        c = {'schemaVersion':1, 'requestId': RID, 'bootId': BOOT, 'workerPid': 123}
        p = {'schemaVersion':1, 'observedMs':2, 'deadlineMs':900001, 'requestId': RID, 'uid': 1001, 'bootId': BOOT, 'state': 'deferred', 'sequence': 1,
             'detail': 'Invalid protected app-only record', 'nativeExit': None,
             'candidate': None, 'readyDeadlineMs': None}
        self.assertFalse(d.deferred_check(r, c, p, 1001, BOOT)['installationValidated'])
        for key, value in [('state', 'ready'), ('uid', 1002), ('candidate', {}),
                           ('nativeExit', 0), ('readyDeadlineMs', 120001), ('sequence', 33)]:
            bad = dict(p, **{key: value})
            with self.assertRaises(d.Stop): d.deferred_check(r, c, bad, 1001, BOOT)

    def test_process_checks_reject_reuse_exit_fd_leak_and_shared_group(self):
        p = {'pid': 123, 'startTicks': 7, 'bootId': BOOT, 'uid': 0, 'pidfdLive': True,
             'sid': 123, 'pgid': 123, 'fds': {'0':'/dev/null','1':'/dev/null','2':'/dev/null'}}
        d.process_check(p, p, True)
        for key, value in [('startTicks', 8), ('pidfdLive', False), ('sid', 100),
                           ('uid', 1001), ('fds', dict(p['fds'], **{'3':'pipe:[1]'}))]:
            with self.assertRaises(d.Stop): d.process_check(dict(p, **{key:value}), p, True)

    def test_sentinel_controller_never_signals_a_mismatched_gui(self):
        n = Mock()
        probe = {'testOnly': True, 'pid': 123, 'startTicks': 1, 'bootId': BOOT, 'uid': 0}
        n.wait_json.return_value = probe
        n.pidfd.side_effect = [11, 12]
        n.process.return_value = {'pid': 22, 'uid': 1001, 'startTicks': 99, 'bootId': BOOT, 'pidfdLive': True}
        r = {'requestId': RID, 'case': 'abrupt'}
        enrollment = {'subject': {'pid':22,'uid':1001,'startTicks':1,'bootId':BOOT}}
        with self.assertRaises(d.Stop): d.observe_sentinel(n, approval(), r, enrollment)
        n.kill_gui.assert_not_called()
        n.create.assert_not_called()
        self.assertEqual(n.close.call_count, 2)

class ReviewRegressionTests(unittest.TestCase):
    def test_cleanup_rejects_out_of_scope_duplicate_or_unowned_contents(self):
        ledger = Path('/run/sde-mint-validation-'+RUN+'/ownership.json')
        for defect in ['foreign', 'duplicate', 'extra-child']:
            n = FakeNative()
            state = d.prepare(n, approval(), ASSETS, 'production', ledger)
            state['sealed'] = True; state['phase'] = 'Sealed'
            if defect == 'foreign':
                state['entries'][0]['path'] = '/etc/passwd'
            elif defect == 'duplicate':
                state['entries'].append(state['entries'][0])
            else:
                n.files[str(d.ROOT/'unexpected')] = {}
            with self.subTest(defect=defect), self.assertRaises(d.Stop): d.cleanup(n, state, ledger)
            self.assertFalse(any(x.startswith('remove:') for x in n.mutations))

    def test_gui_and_sentinel_success_uses_enrolled_handles_and_ordered_barriers(self):
        for case in ['normal', 'abrupt']:
            run = d.ROOT/'app-only/runs'/RID
            probe = {'testOnly':True,'pid':123,'startTicks':7,'bootId':BOOT,'uid':0}
            gui = {'pid':22,'startTicks':8,'bootId':BOOT,'uid':1001,'pidfdLive':True}
            sent = dict(probe, sid=123,pgid=123,pidfdLive=True,
                        fds={'0':'/dev/null','1':'/dev/null','2':'/dev/null'},
                        cmd=['/usr/bin/python3','-I',str(run/'sde-update-trust'),'app-only-linux'])
            n = Mock()
            n.wait_json.side_effect = [probe,dict(probe,outcome='released')]
            n.pidfd.side_effect = [11,12]
            n.process.side_effect = [copy.deepcopy(gui),copy.deepcopy(sent)]
            n.ready_sentinel.return_value = copy.deepcopy(sent)
            n.closed.return_value = True
            result = d.observe_sentinel(n, approval(), {'requestId':RID,'case':case}, {'subject':gui})
            self.assertTrue(result['guiEnded']); self.assertTrue(result['sentinelEnded'])
            self.assertEqual(result['authenticationSafety'], 'Unproven')
            self.assertEqual(n.close.call_args_list[0].args, (11,))
            self.assertEqual(n.close.call_args_list[1].args, (12,))
            if case == 'abrupt': n.kill_gui.assert_called_once_with(11)
            else: n.kill_gui.assert_not_called()
            self.assertEqual(n.create.call_args.args[0][1], run/'release-sentinel')

    def test_second_pidfd_failure_closes_first_without_signals(self):
        n = Mock()
        n.wait_json.return_value = {'testOnly':True,'pid':123}
        n.pidfd.side_effect = [11,OSError('mock unsupported')]
        with self.assertRaises(OSError):
            d.observe_sentinel(n, approval(), {'requestId':RID}, {'subject':{'pid':22}})
        n.close.assert_called_once_with(11)
        n.kill_gui.assert_not_called()

    def test_production_capture_seals_only_exact_deferral_and_retains_limits(self):
        n = FakeNative()
        ledger = Path('/run/sde-mint-validation-'+RUN+'/ownership.json')
        state = d.prepare(n, approval(), ASSETS, 'production', ledger)
        run = d.ROOT/'app-only/runs'/RID
        request = {'schemaVersion':1,'requestId':RID,'uid':1001,'bootId':BOOT,'createdMs':1,'deadlineMs':900001}
        claim = {'schemaVersion':1,'requestId':RID,'bootId':BOOT,'workerPid':123}
        progress = {'schemaVersion':1,'requestId':RID,'uid':1001,'bootId':BOOT,'state':'deferred',
                    'sequence':1,'observedMs':2,'deadlineMs':900001,'readyDeadlineMs':None,
                    'detail':'Invalid protected app-only record','candidate':None,'nativeExit':None}
        contents = {'request.json':d.encode(request),'claimed':d.encode(claim),
                    'progress.json':d.encode(progress),'version.json':b'{}',
                    'sde-update-trust':ASSETS['verifier']}
        n.create(('dir',run,0o711,None))
        for name,data in contents.items(): n.create(('file',run/name,0o600,data))
        n.create(('file',d.TOOLS/'desktop-go',0o644,b'{}'))
        n.read = lambda path, limit=65536: contents[Path(path).name]
        n.wait_json = lambda path: d.strict_json(contents[Path(path).name])
        n.acl = Mock(return_value=struct.pack('<I',2)+b''.join(struct.pack('<HHI',*x) for x in
                    [(1,6,2**32-1),(2,4,1001),(4,0,2**32-1),(16,4,2**32-1),(32,0,2**32-1)]))
        def command(argv, timeout=5):
            if argv[-2] == 'app-only-progress':
                return (0,d.encode(progress)) if argv[2] == 'sde-student' else (1,b'')
            return 0,d.encode({'read':argv[2]=='sde-student','write':False})
        n.command = command
        n.replay = Mock()
        n.policy_provider = Mock(return_value={'uid':0,'pid':77})
        n.journal_events = Mock(return_value=[{'_UID':'0','_PID':'77','_SYSTEMD_UNIT':'polkit.service','_EXE':'/usr/lib/polkit-1/polkitd',
            'MESSAGE':'Operator successfully authenticated to gain ONE-SHOT authorization for action org.skyviewrobotics.sde.app-update for unix-process:25:99:1001'}])
        n.pidfd = Mock(side_effect=ProcessLookupError())
        r = {'subjectPid':25,'pid':22,'requestId':RID,'status':'Completed','exit':0,'case':'approved'}
        evidence = d.seal(n, approval(), state, 'approved', (r,1001), {'case':'approved','subject':{'pid':22},'journalCursor':'mock-cursor','policyProvider':{'uid':0,'pid':77}})
        self.assertTrue(state['sealed'])
        self.assertEqual(evidence['authenticationSafety'],'Unproven')
        self.assertFalse(evidence['worker']['installationValidated'])
        n.replay.assert_called_once_with(run)
        self.assertEqual(len(state['entries']), 24)


class ReadOnlyRunnerTests(unittest.TestCase):
    def test_mocked_runner_bounds_output_before_acceptance_and_closes_pipe(self):
        n = d.Native()
        child = Mock(pid=1234)
        child.poll.return_value = 0
        child.stdout.fileno.return_value = 99
        with patch.object(n, 'trusted'), patch.object(d.subprocess, 'Popen', return_value=child), \
             patch.object(d.os, 'set_blocking'), patch.object(d.os, 'read', side_effect=[b'ok',b'']), \
             patch.object(d.select, 'select', return_value=([child.stdout],[],[])), \
             patch.object(d.os, 'killpg') as kill:
            self.assertEqual(n.command(['/usr/bin/busctl','--version']), (0,b'ok'))
            kill.assert_not_called()
        child.stdout.close.assert_called_once()

    def test_mocked_runner_rejects_oversized_output_and_never_runs_unknown_command(self):
        n = d.Native()
        child = Mock(pid=1234)
        child.poll.return_value = 0
        child.stdout.fileno.return_value = 99
        with patch.object(n, 'trusted'), patch.object(d.subprocess, 'Popen', return_value=child), \
             patch.object(d.os, 'set_blocking'), patch.object(d.os, 'read', return_value=b'x'*8193), \
             patch.object(d.select, 'select', return_value=([child.stdout],[],[])):
            with self.assertRaises(d.Stop): n.command(['/usr/bin/gpg','--version'])
        with patch.object(d.subprocess, 'Popen') as spawn:
            with self.assertRaises(d.Stop): n.command(['/usr/bin/apt-get','install','x'])
            spawn.assert_not_called()


class AuditTests(unittest.TestCase):
    def test_audit_requires_trusted_provider_correct_subject_action_and_count(self):
        record = {'_UID':'0','_PID':'77','_SYSTEMD_UNIT':'polkit.service','_EXE':'/usr/lib/polkit-1/polkitd',
                  'MESSAGE':'Operator successfully authenticated to gain ONE-SHOT authorization for action org.skyviewrobotics.sde.app-update for unix-process:25:99:1001'}
        self.assertEqual(d.authorization_audit([record],25,'approved',{'uid':0,'pid':77})['successfulAuthorizations'],1)
        for change in [{'_UID':'1001'}, {'_PID':'78'}, {'_SYSTEMD_UNIT':'user@1001.service'},
                       {'MESSAGE':record['MESSAGE'].replace('sde.app-update','sde.other')},
                       {'MESSAGE':record['MESSAGE'].replace(':25:',':26:')}]:
            with self.assertRaises(d.Stop): d.authorization_audit([dict(record,**change)],25,'approved',{'uid':0,'pid':77})
        with self.assertRaises(d.Stop): d.authorization_audit([record,record],25,'approved',{'uid':0,'pid':77})
        with self.assertRaises(d.Stop): d.authorization_audit([record],25,'denied',{'uid':0,'pid':77})
        result = d.authorization_audit([],25,'inactive',{'uid':0,'pid':77})
        self.assertEqual(result['action'],'NotObserved')



class HostAdapterMockTests(unittest.TestCase):
    def test_kvm_ioctl_success_and_unsupported_both_close_owned_descriptor(self):
        from types import SimpleNamespace
        import fcntl
        for failure in [False, True]:
            with patch.object(h.Path, 'read_text', side_effect=['ID=ubuntu\nVERSION_ID="24.04"', 'MemAvailable: 6291456 kB']), \
                 patch.object(h.Native, 'trusted'), patch.object(h.Path, 'is_file', return_value=True), \
                 patch.object(h.os, 'open', return_value=99), patch.object(h.os, 'close') as close, \
                 patch.object(fcntl, 'ioctl', side_effect=OSError('unsupported') if failure else None, return_value=12), \
                 patch.object(h.os, 'statvfs', return_value=SimpleNamespace(f_bavail=36*1024**3,f_frsize=1)), \
                 patch.object(h.os, 'cpu_count', return_value=2), patch.object(h.platform, 'machine', return_value='x86_64'):
                result = h.collect(Path('/mock'), True, True, True)
            close.assert_called_once_with(99)
            self.assertEqual(result['kvm_api'], None if failure else 12)
            self.assertEqual(d.host_check(result)['ready'], not failure)



if __name__ == '__main__':
    unittest.main()
