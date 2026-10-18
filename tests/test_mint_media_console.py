"""Mocked local checks only. No native network/GPG/KVM/QEMU or spare-host access."""
import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import mint_media_console as c
import mint_media_native as n

RUN = '11111111-1111-4111-8111-111111111111'
ROOT = '/home/sde-runner/mint-validation/' + RUN
KEY = (Path(__file__).parent/'fixtures/linuxmint-iso-signing.asc').read_bytes()
PAYLOAD = b'synthetic ISO bytes, not bootable media'
PIN = hashlib.sha256(PAYLOAD).hexdigest()
SUMS = (PIN+' *'+c.ISO+'\n').encode()
STATUS = ('[GNUPG:] NEWSIG\n[GNUPG:] VALIDSIG '+c.FINGERPRINT+
          ' 2026-01-01 1 0 4 0 1 10 00 '+c.FINGERPRINT+'\n').encode()


def facts():
    return dict(account='sde-runner', uid=1001, euid=1001, groups=['sde-runner','kvm'],
                os='linuxmint', release='22.3', arch='x86_64', kvm_api=12,
                trusted_tools=True, available_memory=6*1024**3, available_disk=40*1024**3)


class MemoryWorkspace:
    """In-memory port. No directory/file operations occur."""
    def __init__(self):
        self.run_id, self.path = RUN, ROOT
        self.files, self.sealed = {}, set()
        self.failure = None
        self.done = False
        self.fail_evidence = False
        self.fail_finish = False
        self.replaced = False
        self.plan_collision = False
        self.promoted = False

    def check(self):
        c.require(not self.replaced, 'WORKSPACE_REPLACED')
        c.require(not self.done and self.failure is None, 'WORKSPACE_STOPPED')

    def create(self, name):
        self.check()
        c.require(name not in self.files, 'FILE_COLLISION')
        self.files[name] = b''

    def write(self, name, data):
        self.check()
        c.require(name not in self.sealed, 'FILE_SEALED')
        c.require(sum(map(len,self.files.values()))+len(data) <= c.WORKSPACE_LIMIT, 'WORKSPACE_BUDGET')
        self.files[name] += data

    def seal(self, name):
        self.check(); self.sealed.add(name)

    def verify(self, name, size, digest, clock, deadline):
        self.check()
        c.require(clock() < deadline and len(self.files[name]) == size
                  and c.sha(self.files[name]) == digest, 'FILE_DIGEST')

    def store(self, name, data):
        self.create(name); self.write(name,data); self.seal(name)

    def promote(self, old, new):
        self.check()
        c.require(new not in self.files, 'FILE_COLLISION')
        self.files[new] = self.files.pop(old)
        self.sealed.remove(old); self.sealed.add(new); self.promoted=True

    def require_absent(self, names):
        self.check(); c.require(not self.plan_collision, 'PLAN_COLLISION')

    def finish(self, report):
        self.check(); c.require(not self.fail_finish, 'REPORT_IO')
        self.report = copy.deepcopy(report); self.done=True

    def fail(self, code):
        c.require(not self.fail_evidence, 'EVIDENCE_IO')
        self.failure=code


class FakeTransport:
    def __init__(self, workspace=None):
        self.calls=[]
        self.workspace=workspace
        self.override={}

    def fetch(self, url, make_sink, limit, deadline):
        name=url.rsplit('/',1)[-1]; self.calls.append(name)
        if name in self.override:
            return self.override[name](make_sink)
        body={'sha256sum.txt':SUMS,'sha256sum.txt.gpg':b'synthetic detached signature',c.ISO:PAYLOAD}[name]
        sink=make_sink(); sink.write(body)
        return c.Transfer(200,None,len(body))


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.ws=MemoryWorkspace(); self.transport=FakeTransport(self.ws)
        self.verifier=Mock()
        self.verifier.verify.return_value=(0,STATUS,{'gpg':'gpg synthetic','curl':'curl synthetic'})
        self.clock=Mock(return_value=10.0)

    def run_prep(self, **changes):
        args=dict(run_id=RUN, source_sha='a'*40, approved_sha='a'*40,
                  helper_sha='b'*64, approved_helper_sha='b'*64, key=KEY, facts=facts(),
                  workspace=self.ws,transport=self.transport,verifier=self.verifier,clock=self.clock)
        args.update(changes)
        return c.prepare(**args)

    def test_healthy_synthetic_media_and_plan_are_not_native_proof(self):
        result=self.run_prep()
        self.assertTrue(result['media']['authenticated'])
        self.assertEqual(self.transport.calls,['sha256sum.txt','sha256sum.txt.gpg',c.ISO])
        self.assertEqual(self.ws.files[c.ISO],PAYLOAD)
        self.assertIn(c.ISO,self.ws.sealed)
        self.assertFalse(result['consolePlan']['qemuStarted'])
        self.assertFalse(result['consolePlan']['diskCreated'])
        self.assertFalse(result['consolePlan']['launchAuthorized'])
        self.assertFalse(result['nativeGuestTestsExecuted'])
        self.assertFalse(result['productionReady'])
        argv=result['consolePlan']['argv']
        self.assertEqual(argv[argv.index('-nic')+1],'none')
        self.assertTrue(argv[argv.index('-vnc')+1].startswith('unix:'))
        self.assertNotIn('-fsdev',argv)
        self.assertNotIn('-spice',argv)

    def test_source_helper_key_and_host_gates_before_download(self):
        for changes in [dict(approved_sha='b'*40),dict(approved_helper_sha='c'*64),dict(key=b'wrong'),
                        dict(facts=dict(facts(),os='ubuntu')),dict(facts=dict(facts(),groups=['sudo'])),
                        dict(facts=dict(facts(),available_disk=1)),dict(run_id='../bad'),
                        dict(source_sha=5),dict(helper_sha=5)]:
            with self.subTest(changes=changes), self.assertRaises(c.Stop): self.run_prep(**changes)
        self.assertEqual(self.transport.calls,[])
        self.verifier.verify.assert_not_called()

    def test_signature_failure_prevents_iso_and_preserves_stop(self):
        self.verifier.verify.return_value=(1,STATUS,{'gpg':'gpg','curl':'curl'})
        with self.assertRaisesRegex(c.Stop,'SIGNATURE'): self.run_prep()
        self.assertNotIn(c.ISO,self.transport.calls)
        self.assertEqual(self.ws.failure,'SIGNATURE')
        self.assertFalse(self.ws.done)

    def test_disk_readback_corruption_stops_before_signature_or_iso(self):
        original=self.ws.write
        def corrupt(name, data):
            original(name, data)
            self.ws.files[name]=b'!' + self.ws.files[name][1:]
        self.ws.write=corrupt
        with self.assertRaisesRegex(c.Stop,'FILE_DIGEST'):self.run_prep()
        self.verifier.verify.assert_not_called()
        self.assertNotIn(c.ISO,self.transport.calls)
        self.assertFalse(self.ws.done)

    def test_wrong_digest_is_not_published_as_final_media(self):
        def bad(make):
            sink=make(); sink.write(b'corrupt'); return c.Transfer(200,None,7)
        self.transport.override[c.ISO]=bad
        with self.assertRaisesRegex(c.Stop,'ISO_DIGEST'): self.run_prep()
        self.assertNotIn(c.ISO,self.ws.files)
        self.assertIn(c.ISO+'.partial',self.ws.files)
        self.assertFalse(self.ws.promoted)
        self.assertEqual(self.ws.failure,'ISO_DIGEST')

    def test_partial_transfer_retained_and_not_retried(self):
        def broken(make):
            make().write(b'partial'); raise c.Stop('TOOL_EXIT')
        self.transport.override[c.ISO]=broken
        with self.assertRaisesRegex(c.Stop,'TOOL_EXIT'): self.run_prep()
        self.assertEqual(self.transport.calls.count(c.ISO),1)
        self.assertEqual(self.ws.files[c.ISO+'.partial'],b'partial')
        self.assertNotIn(c.ISO,self.ws.files)

    def test_deadline_size_and_evidence_failures_stop(self):
        def late(make):
            sink=make(); self.clock.return_value=2000; sink.write(b'x')
        self.transport.override[c.ISO]=late
        with self.assertRaisesRegex(c.Stop,'TRANSFER_DEADLINE'): self.run_prep()
        self.setUp()
        self.ws.fail_finish=True
        with self.assertRaisesRegex(c.Stop,'REPORT_IO'): self.run_prep()
        self.assertFalse(self.ws.done)
        self.assertEqual(self.ws.failure,'REPORT_IO')
        self.setUp(); self.ws.fail_finish=True;self.ws.fail_evidence=True
        with self.assertRaisesRegex(c.Stop,'EVIDENCE_UNCERTAIN'): self.run_prep()
        self.assertFalse(self.ws.done)

    def test_unknown_owner_and_console_collision_prevent_completion(self):
        self.ws.replaced=True
        with self.assertRaisesRegex(c.Stop,'WORKSPACE_REPLACED'): self.run_prep()
        self.assertFalse(self.transport.calls)
        self.setUp(); self.ws.plan_collision=True
        with self.assertRaisesRegex(c.Stop,'PLAN_COLLISION'): self.run_prep()
        self.assertFalse(self.ws.done)

    def test_untrusted_exception_text_is_not_exported(self):
        self.verifier.verify.side_effect=c.Stop('https://secret:token@example.invalid')
        with self.assertRaisesRegex(c.Stop,'NATIVE_FAILURE'): self.run_prep()
        self.assertEqual(self.ws.failure,'NATIVE_FAILURE')

    def test_socket_length_and_argument_injection_rejected_before_transfer(self):
        for root in ['/home/a,extra/mint-validation/'+RUN,
                     '/home/'+'x'*80+'/mint-validation/'+RUN, ROOT+'/../'+RUN]:
            self.ws.path=root
            with self.assertRaises(c.Stop): self.run_prep()
        self.assertFalse(self.transport.calls)

    def test_repeat_transfer_and_post_failure_resume_rejected(self):
        def twice(make):
            sink=make();sink.write(b'x');make()
        self.transport.override['sha256sum.txt']=twice
        with self.assertRaisesRegex(c.Stop,'TRANSFER_REPLAY'): self.run_prep()
        with self.assertRaisesRegex(c.Stop,'WORKSPACE_STOPPED'): self.run_prep()


class PureValidationTests(unittest.TestCase):
    def test_signature_counterexamples_are_synthetic_not_crypto_validation(self):
        self.assertEqual(c.authenticated_pin(SUMS,STATUS,0),PIN)
        for sums,status,rc in [(SUMS+SUMS,STATUS,0),(SUMS,STATUS+STATUS,0),
                              (SUMS,STATUS.replace(c.FINGERPRINT.encode(),b'A'*40),0),
                              (SUMS,STATUS+b'[GNUPG:] EXPKEYSIG bad\n',0),
                              (SUMS.replace(b'cinnamon',b'xfce'),STATUS,0),
                              (SUMS+b'# '+c.ISO.encode(),STATUS,0),(SUMS,b'Good signature',0),
                              (SUMS,STATUS,False),(b'\xff',STATUS,0)]:
            with self.subTest(sums=sums),self.assertRaises(c.Stop): c.authenticated_pin(sums,status,rc)

    def test_redirect_scope_and_count(self):
        url=c.BASE+c.ISO
        self.assertEqual(c.redirected_url(url,url),url)
        for location in ['http://mirrors.kernel.org/linuxmint/stable/22.3/'+c.ISO,
                         'https://evil.invalid/'+c.ISO,'https://user:pass@mirrors.kernel.org/'+c.ISO,
                         '?token=value','/other-file.iso','\n'+url]:
            with self.assertRaises(c.Stop): c.redirected_url(url,location)
        transport=Mock()
        transport.fetch.return_value=c.Transfer(302,url,0)
        with self.assertRaisesRegex(c.Stop,'REDIRECT_LIMIT'):
            c.fetch(c.ISO,8,10,MemoryWorkspace(),transport,lambda:0,100)
        self.assertEqual(transport.fetch.call_count,4)

    def test_stream_limits_are_checked_before_writes(self):
        w=MemoryWorkspace();clock=Mock(return_value=0)
        sink=c.Sink(w,'test',3,clock,10)
        sink.write(b'ab')
        with self.assertRaisesRegex(c.Stop,'TRANSFER_SIZE'): sink.write(b'cd')
        self.assertEqual(w.files['test'],b'ab')
        with self.assertRaisesRegex(c.Stop,'CHUNK'): sink.write(b'x'*(c.CHUNK+1))
        clock.return_value=10
        with self.assertRaisesRegex(c.Stop,'TRANSFER_DEADLINE'): sink.write(b'x')
        self.assertEqual(w.files['test'],b'ab')
        iso=c.Sink(MemoryWorkspace(),'iso',c.ISO_LIMIT,lambda:0,10)
        self.assertIsNone(iso.small)

    def test_all_host_requirements_fail_closed(self):
        c.host_gate(facts())
        for key in facts():
            changed=facts();changed[key]=None
            with self.subTest(key=key),self.assertRaises(c.Stop): c.host_gate(changed)


class NativeAdapterMockTests(unittest.TestCase):
    def test_curl_stream_parser_no_native_process(self):
        w=MemoryWorkspace()
        response=b'HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nabc'
        def make():
            return c.Sink(w,'data',3,lambda:0,10)
        with patch.object(n,'_stream_process',return_value=(x for x in [response[:12],response[12:]])) as process:
            result=n.CurlTransport(lambda:0).fetch(c.BASE+c.ISO,make,3,10)
        self.assertEqual(result.byte_count,3)
        argv=process.call_args.args[0]
        self.assertEqual(argv[:2],['/usr/bin/curl','--disable'])
        self.assertNotIn('--location',argv)
        self.assertNotIn('--insecure',argv)
        self.assertEqual(w.files['data'],b'abc')

    def test_http_rejections_and_redirect_never_create_body(self):
        for raw in [b'HTTP/1.1 404 Nope\r\n\r\nx',
                    b'HTTP/1.1 200 OK\r\nContent-Length: 99\r\n\r\nx',
                    b'HTTP/1.1 200 OK\r\nContent-Length: 1\r\nContent-Length: 1\r\n\r\nx',
                    b'HTTP/1.1 200 OK\r\nContent-Encoding: gzip\r\n\r\nx',
                    b'bad headers',b'x'*16385]:
            def gen(): yield raw
            make=Mock()
            with patch.object(n,'_stream_process',return_value=gen()),self.assertRaises(c.Stop):
                n.CurlTransport(lambda:0).fetch(c.BASE+c.ISO,make,8,10)
            make.assert_not_called()
        def redir(): yield b'HTTP/1.1 302 Found\r\nLocation: https://evil.invalid/\r\n\r\nbody'
        make=Mock()
        with patch.object(n,'_stream_process',return_value=redir()):
            result=n.CurlTransport(lambda:0).fetch(c.BASE+c.ISO,make,8,10)
        self.assertEqual(result.status,302); make.assert_not_called()

    def test_verifier_rejects_unpinned_key_before_any_native_call(self):
        ws=Mock()
        with patch.object(n,'_capture') as process,self.assertRaises(c.Stop):
            n.GpgVerifier(lambda:0).verify(b'bad',SUMS,b'sig',ws,100)
        ws.gpg_home.assert_not_called();process.assert_not_called()

    def test_owned_tool_process_deadline_closes_stdout_and_waits_for_kill(self):
        process=Mock();process.stdout.fileno.return_value=7;process.poll.return_value=None
        selector=Mock()
        with patch.object(n,'_tool'),patch.object(n.subprocess,'Popen',return_value=process) as spawn,\
             patch.object(n.selectors,'DefaultSelector',return_value=selector),\
             patch.object(n.os,'set_blocking'):
            stream=n._stream_process(['/usr/bin/curl','--version'],1,lambda:2)
            with self.assertRaisesRegex(c.Stop,'PROCESS_DEADLINE'):list(stream)
        process.kill.assert_called_once();process.wait.assert_called_once_with(timeout=5)
        process.stdout.close.assert_called_once();selector.close.assert_called_once()
        self.assertTrue(spawn.call_args.kwargs['close_fds'])
        self.assertTrue(spawn.call_args.kwargs['start_new_session'])
        self.assertNotIn('shell',spawn.call_args.kwargs)

    def test_owned_children_preserve_runner_tracking_without_inheriting_credentials(self):
        for tracked in (False,True):
            process=Mock();process.stdout.fileno.return_value=7;process.poll.return_value=0
            process.wait.return_value=0
            selector=Mock();selector.select.return_value=[object()]
            synthetic={'HTTPS_PROXY':'https://synthetic-proxy.invalid',
                       'SSL_CERT_FILE':'/synthetic/ca.pem','GITHUB_TOKEN':'synthetic-secret',
                       'SSH_AUTH_SOCK':'/synthetic/agent','LD_PRELOAD':'/synthetic/inject.so'}
            if tracked:synthetic['RUNNER_TRACKING_ID']='synthetic-job-tracking'
            with self.subTest(tracked=tracked),patch.dict(n.os.environ,synthetic,clear=True), \
                 patch.object(n,'_tool'),patch.object(n.subprocess,'Popen',return_value=process) as spawn, \
                 patch.object(n.selectors,'DefaultSelector',return_value=selector), \
                 patch.object(n.os,'set_blocking'),patch.object(n.os,'read',return_value=b''):
                self.assertEqual(n._capture(['/usr/bin/curl','--disable','--version'],10,lambda:0),b'')
            passed=spawn.call_args.kwargs['env']
            expected={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C',
                      'HTTPS_PROXY':synthetic['HTTPS_PROXY'],'SSL_CERT_FILE':synthetic['SSL_CERT_FILE']}
            if tracked:expected['RUNNER_TRACKING_ID']=synthetic['RUNNER_TRACKING_ID']
            self.assertEqual(passed,expected)
            self.assertNotIn('synthetic-job-tracking',spawn.call_args.args[0])
            process.kill.assert_not_called()

    def test_workspace_rejects_replacement_and_symlink_identity(self):
        w=object.__new__(n.Workspace)
        w.fd=3;w.files={'a':(8,(1,2,1001,0o400,1))}
        good=SimpleNamespace(st_dev=1,st_ino=2,st_uid=1001,st_mode=0o100400,st_nlink=1)
        bad=SimpleNamespace(**dict(vars(good),st_ino=99))
        with patch.object(n.os,'fstat',return_value=good),patch.object(n.os,'stat',return_value=bad),self.assertRaises(c.Stop):
            w._file('a')
        bad=SimpleNamespace(**dict(vars(good),st_mode=0o120400))
        with patch.object(n.os,'fstat',return_value=bad),patch.object(n.os,'stat',return_value=bad),self.assertRaises(c.Stop):
            w._file('a')

    def test_seal_failure_never_sets_finish_pass(self):
        w=object.__new__(n.Workspace);w.files={'x':(8,(1,2,1001,0o600,1))};w.fd=3
        with patch.object(w,'check'),patch.object(w,'_file',return_value=8),\
             patch.object(n.os,'fsync',side_effect=OSError('synthetic fsync failure')),\
             patch.object(n.os,'fchmod') as chmod,self.assertRaises(OSError):w.seal('x')
        chmod.assert_not_called()

    def test_gpg_uses_private_snapshots_and_fixed_noninteractive_options(self):
        ws=Mock();ws.gpg_home.return_value=ROOT+'/gnupg'
        with patch.object(n.os,'open',return_value=7),patch.object(n.os,'write',side_effect=lambda fd,b:len(b)), \
             patch.object(n.os,'fsync'),patch.object(n.os,'fchmod'),patch.object(n.os,'close') as close, \
             patch.object(n,'_capture',side_effect=[b'import ok',STATUS,b'gpg synthetic\n',b'curl synthetic\n']) as capture:
            code,status,versions=n.GpgVerifier(lambda:0).verify(KEY,SUMS,b'sig',ws,100)
        self.assertEqual((code,status),(0,STATUS));self.assertEqual(set(versions),{'gpg','curl'})
        self.assertEqual(close.call_count,3)
        for call in capture.call_args_list[:3]:
            args=call.args[0]
            self.assertIn('--no-options',args);self.assertIn('--no-autostart',args)
            self.assertIn('--no-auto-key-retrieve',args)
            self.assertEqual(args[args.index('--homedir')+1],ROOT+'/gnupg')
        self.assertEqual(capture.call_args_list[3].args[0],['/usr/bin/curl','--disable','--version'])

    def test_native_ancestry_symlink_failure_closes_owned_fds(self):
        st=SimpleNamespace(st_uid=0,st_mode=0o40755)
        with patch.object(n.os,'open',side_effect=[10,11,OSError('synthetic ELOOP')]), \
             patch.object(n.os,'fstat',return_value=st),patch.object(n.os,'close') as close, \
             self.assertRaises(OSError):n._owned_directory('/home/sde-runner',1001)
        self.assertEqual([x.args[0] for x in close.call_args_list],[10,11])

    def test_native_writes_budget_collision_and_short_writes(self):
        w=object.__new__(n.Workspace);w.fd=3;w.written=0
        with patch.object(w,'check'),patch.object(w,'_file',return_value=8), \
             patch.object(n.os,'write',side_effect=[2,1]) as write:
            w.files={'x':(8,(1,2,1001,0o600,1))};w.write('x',b'abc')
            self.assertEqual(w.written,3);self.assertEqual(write.call_count,2)
        w.written=c.WORKSPACE_LIMIT
        with patch.object(w,'check'),patch.object(n.os,'write') as write,self.assertRaises(c.Stop):
            w.write('x',b'z')
        write.assert_not_called()
        w.files={}
        with patch.object(w,'check'),patch.object(n.os,'open',side_effect=FileExistsError),self.assertRaises(FileExistsError):
            w.create('report.json')
        self.assertEqual(w.files,{})

    def test_create_inspection_failure_closes_untracked_descriptor_once(self):
        for failure in (OSError('synthetic fstat failure'),
                        SimpleNamespace(st_uid=0, st_nlink=1, st_mode=0o100600)):
            w=object.__new__(n.Workspace);w.fd=3;w.uid=1001;w.files={}
            with self.subTest(failure=failure), patch.object(w,'check'), \
                 patch.object(n.os,'open',return_value=8), \
                 patch.object(n.os,'fstat',side_effect=failure if isinstance(failure,Exception) else None,
                              return_value=failure), patch.object(n.os,'close') as close, \
                 self.assertRaises((OSError,c.Stop)):
                w.create('report.json')
            close.assert_called_once_with(8)
            self.assertEqual(w.files,{})

    def test_create_inspection_cleanup_uncertainty_is_explicit(self):
        w=object.__new__(n.Workspace);w.fd=3;w.uid=1001;w.files={}
        with patch.object(w,'check'), patch.object(n.os,'open',return_value=8), \
             patch.object(n.os,'fstat',side_effect=OSError('synthetic inspection failure')), \
             patch.object(n.os,'close',side_effect=OSError('synthetic close failure')) as close, \
             self.assertRaisesRegex(c.Stop,'DESCRIPTOR_CLEANUP_UNCERTAIN'):
            w.create('report.json')
        close.assert_called_once_with(8)
        self.assertEqual(w.files,{})

    def test_native_readback_checks_actual_file_bytes(self):
        w=object.__new__(n.Workspace)
        with patch.object(w,'check'),patch.object(w,'_file',return_value=8), \
             patch.object(n.os,'fstat',return_value=SimpleNamespace(st_size=3)), \
             patch.object(n.os,'pread',return_value=b'bad'), self.assertRaisesRegex(c.Stop,'FILE_DIGEST'):
            w.verify('x',3,c.sha(b'abc'),lambda:0,10)

    def test_native_finish_failure_does_not_claim_completion(self):
        w=object.__new__(n.Workspace);w.finished=False;w.run_id=RUN;w.root_identity=(1,2,1001,0o700)
        def store(name,value):
            if name=='ownership.json':raise OSError('synthetic manifest fsync failure')
        with patch.object(w,'audit',return_value=[]),patch.object(w,'store',side_effect=store),self.assertRaises(OSError):
            w.finish({'synthetic':True})
        self.assertFalse(w.finished)

    def test_capture_overflow_closes_stream_and_cleanup_uncertainty_is_explicit(self):
        closed=[]
        def stream():
            try:yield b'x'*8193
            finally:closed.append(True)
        with patch.object(n,'_stream_process',return_value=stream()),self.assertRaisesRegex(c.Stop,'TOOL_OUTPUT'):
            n._capture(['/usr/bin/gpg','--version'],10,lambda:0)
        self.assertEqual(closed,[True])
        process=Mock();process.stdout.fileno.return_value=7;process.poll.return_value=None
        process.wait.side_effect=n.subprocess.TimeoutExpired('owned curl',5)
        with patch.object(n,'_tool'),patch.object(n.subprocess,'Popen',return_value=process), \
             patch.object(n.selectors,'DefaultSelector'),patch.object(n.os,'set_blocking'), \
             self.assertRaisesRegex(c.Stop,'PROCESS_CLEANUP_UNCERTAIN'):
            list(n._stream_process(['/usr/bin/curl','--version'],1,lambda:2))
        process.kill.assert_called_once()

    def test_constructor_rejection_closes_run_and_parent_descriptors(self):
        parent=SimpleNamespace(st_uid=1001,st_mode=0o40700)
        run=SimpleNamespace(st_uid=1001,st_mode=0o40777)
        with patch.object(n.os,'getuid',return_value=1001),patch.object(n.os,'geteuid',return_value=1001), \
             patch.object(n.os,'getgid',return_value=1001),patch.object(n.os,'getgroups',return_value=[]), \
             patch.object(n.pwd,'getpwuid',return_value=SimpleNamespace(pw_name='sde-runner',pw_dir='/home/sde-runner')), \
             patch.object(n.grp,'getgrgid',return_value=SimpleNamespace(gr_name='sde-runner')), \
             patch.object(n,'_owned_directory',return_value=2),patch.object(n.os,'open',side_effect=[3,4]), \
             patch.object(n.os,'mkdir'),patch.object(n.os,'fsync'), \
             patch.object(n.os,'fstat',side_effect=[parent,run]),patch.object(n.os,'close') as close, \
             self.assertRaisesRegex(c.Stop,'WORKSPACE'):n.Workspace(RUN)
        self.assertEqual({x.args[0] for x in close.call_args_list},{2,3,4})

    def test_directory_child_link_count_is_not_identity_but_replacement_is(self):
        w=object.__new__(n.Workspace);w.finished=False;w.failed=False;w.closed=False
        w.fd=3;w.path=ROOT;w.uid=1001;w.root_identity=(1,2,1001,0o700)
        same=SimpleNamespace(st_dev=1,st_ino=2,st_uid=1001,st_mode=0o40700,st_nlink=3)
        with patch.object(n,'_owned_directory',return_value=9),patch.object(n.os,'fstat',return_value=same),patch.object(n.os,'close'):
            w.check()
        changed=SimpleNamespace(**dict(vars(same),st_ino=99))
        with patch.object(n,'_owned_directory',return_value=9),patch.object(n.os,'fstat',return_value=changed), \
             patch.object(n.os,'close'),self.assertRaisesRegex(c.Stop,'WORKSPACE_REPLACED'):w.check()

    def test_descriptor_cleanup_attempts_each_once_and_reports_uncertainty(self):
        w=object.__new__(n.Workspace);w.closed=False;w.fd=3;w.files={'a':(8,None),'b':(9,None)}
        with patch.object(n.os,'close',side_effect=[OSError('synthetic close uncertainty'),None,None]) as close, \
             self.assertRaisesRegex(c.Stop,'DESCRIPTOR_CLEANUP_UNCERTAIN'):w.close()
        self.assertEqual([x.args[0] for x in close.call_args_list],[8,9,3])
        with patch.object(n.os,'close') as close:w.close()
        close.assert_not_called()

    def test_mint_host_collector_with_mocked_files_tools_and_ioctl(self):
        import fcntl
        file_data={10:b'RELEASE=22.3\n',11:b'ID=linuxmint\n',12:b'MemAvailable: 6291456 kB\n'}
        offsets={fd:0 for fd in file_data}
        def opened(path,*args,**kwargs):return {'info':10,'os-release':11,'meminfo':12,'/dev/kvm':7}[str(path)]
        def read(fd,size):
            start=offsets[fd];offsets[fd]+=size
            return file_data[fd][start:start+size]
        st=SimpleNamespace(st_uid=0,st_mode=0o100444,st_nlink=1)
        with patch.object(n.os,'getuid',return_value=1001),patch.object(n.os,'geteuid',return_value=1001), \
             patch.object(n.os,'getgid',return_value=1001),patch.object(n.os,'getgroups',return_value=[108]), \
             patch.object(n.pwd,'getpwuid',return_value=SimpleNamespace(pw_name='sde-runner',pw_dir='/home/sde-runner')), \
             patch.object(n.grp,'getgrgid',return_value=SimpleNamespace(gr_name='kvm')), \
             patch.object(n.Path,'resolve',lambda self,**kw:self),patch.object(n,'_owned_directory',return_value=9), \
             patch.object(n,'_tool'),patch.object(n.os,'open',side_effect=opened),patch.object(n.os,'read',side_effect=read), \
             patch.object(n.os,'fstat',return_value=st),patch.object(n.os,'stat',return_value=st), \
             patch.object(n.os,'fstatvfs',return_value=SimpleNamespace(f_bavail=40*1024**3,f_frsize=1)), \
             patch.object(fcntl,'ioctl',return_value=12),patch('platform.machine',return_value='x86_64'), \
             patch.object(n.os,'close') as close:
            result=n.collect_host()
        self.assertEqual(result['os'],'linuxmint');self.assertEqual(result['release'],'22.3')
        self.assertEqual(result['kvm_api'],12)
        self.assertEqual([x.args[0] for x in close.call_args_list].count(7),1)

    def test_selector_initialization_failure_still_reaps_owned_child(self):
        process=Mock();process.stdout.fileno.return_value=7;process.poll.return_value=None
        with patch.object(n,'_tool'),patch.object(n.subprocess,'Popen',return_value=process), \
             patch.object(n.selectors,'DefaultSelector',side_effect=OSError('synthetic selector failure')), \
             self.assertRaises(OSError):list(n._stream_process(['/usr/bin/curl','--version'],10,lambda:0))
        process.kill.assert_called_once();process.wait.assert_called_once_with(timeout=5)
        process.stdout.close.assert_called_once()

    def test_inventory_is_bounded_while_iterating(self):
        entries=Mock();entries.__enter__=Mock(return_value=iter([SimpleNamespace(name=str(i)) for i in range(5)]))
        entries.__exit__=Mock(return_value=False)
        with patch.object(n.os,'scandir',return_value=entries),self.assertRaisesRegex(c.Stop,'INVENTORY_SIZE'):
            n._names(9,3)
        entries.__exit__.assert_called_once()

    def test_successful_owned_process_is_reaped_without_kill(self):
        process=Mock();process.stdout.fileno.return_value=7;process.poll.return_value=0
        process.wait.return_value=0
        selector=Mock();selector.select.return_value=[object()]
        with patch.object(n,'_tool'),patch.object(n.subprocess,'Popen',return_value=process), \
             patch.object(n.selectors,'DefaultSelector',return_value=selector), \
             patch.object(n.os,'set_blocking'),patch.object(n.os,'read',side_effect=[b'abc',b'']):
            self.assertEqual(n._capture(['/usr/bin/curl','--disable','--version'],10,lambda:0),b'abc')
        process.wait.assert_called_once();process.kill.assert_not_called()
        selector.close.assert_called_once();process.stdout.close.assert_called_once()

    def test_iso_publication_collision_does_not_unlink_partial(self):
        w=object.__new__(n.Workspace);w.fd=3;w.files={c.ISO+'.partial':(8,None)}
        with patch.object(w,'check'),patch.object(w,'_file',return_value=8), \
             patch.object(n.os,'link',side_effect=FileExistsError),patch.object(n.os,'unlink') as unlink, \
             self.assertRaises(FileExistsError):w.promote(c.ISO+'.partial',c.ISO)
        unlink.assert_not_called();self.assertIn(c.ISO+'.partial',w.files)

    def test_no_execution_entrypoint_or_qemu_process_call(self):
        for name in ['mint_media_console.py','mint_media_native.py']:
            source=(Path(__file__).parent/name).read_text()
            ast.parse(source)
            self.assertNotIn("if __name__ ==",source)
            self.assertNotIn('os.system(',source)
            self.assertNotIn('subprocess.run(',source)
        self.assertEqual(n.TOOLS,{'/usr/bin/curl','/usr/bin/gpg'})


if __name__ == '__main__':
    unittest.main()
