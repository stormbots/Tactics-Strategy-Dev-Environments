"""Static workflow and mocked caller checks. Never activate native ports."""
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

import yaml
import run_mint_media_console as d

ROOT = Path(__file__).resolve().parents[1]
RUN = '11111111-1111-4111-8111-111111111111'
SNAPSHOTS = {name: ('synthetic bytes for ' + name).encode() for name in d.SOURCES}
DIGEST = d.bundle_digest(SNAPSHOTS)


def env():
    return dict(GITHUB_ACTIONS='true', GITHUB_EVENT_NAME='workflow_dispatch',
        GITHUB_REPOSITORY=d.REPO, GITHUB_REF='refs/heads/main', GITHUB_WORKFLOW_REF=d.WORKFLOW,
        GITHUB_SHA='a'*40, PREP_APPROVED_SHA='a'*40, PREP_WORKFLOW_SHA='a'*40,
        PREP_ENABLED='true', PREP_ACCESS_READY='verified', PREP_APPROVED_HELPERS_SHA256=DIGEST,
        GITHUB_RUN_ID='123', GITHUB_RUN_ATTEMPT='1', GITHUB_JOB='prepare')


class DriverChecks(unittest.TestCase):
    def setUp(self):
        # Main's signal guard is exercised without installing real handlers.
        getsignal = patch.object(d.signal, 'getsignal', return_value=d.signal.SIG_DFL)
        setsignal = patch.object(d.signal, 'signal')
        getsignal.start(); setsignal.start()
        self.addCleanup(getsignal.stop); self.addCleanup(setsignal.stop)
        self.reader = Mock(side_effect=lambda root, name: SNAPSHOTS[name])
        self.core = Mock()
        self.core.prepare.return_value = {'productionReady': False, 'nativeGuestTestsExecuted': False}
        self.native = Mock()
        self.native.collect_host.return_value = {'account': 'sde-runner'}
        self.ws = MagicMock(run_id=RUN)
        self.ws.__enter__.return_value = self.ws
        self.native.Workspace.return_value = self.ws
        self.loader = Mock(return_value=(self.core, self.native))

    def execute(self, changes=None):
        return d.run(dict(env(), **(changes or {})), reader=self.reader, loader=self.loader,
                     run_uuid=lambda: RUN)

    def test_all_missing_gates_reject_before_source_or_host_access(self):
        for key in env():
            with self.subTest(key=key), self.assertRaises(d.GateError):
                self.execute({key: ''})
        self.reader.assert_not_called(); self.loader.assert_not_called()

    def test_wrong_context_and_rerun_rejected(self):
        for key, value in [('GITHUB_EVENT_NAME','push'), ('GITHUB_EVENT_NAME','pull_request'),
                ('GITHUB_REPOSITORY','fork/repo'), ('GITHUB_REF','refs/heads/feature'),
                ('GITHUB_WORKFLOW_REF',d.REPO+'/other.yml@refs/heads/main'),
                ('PREP_WORKFLOW_SHA','b'*40), ('PREP_APPROVED_SHA','b'*40),
                ('PREP_ENABLED','false'), ('PREP_ACCESS_READY','true'),
                ('GITHUB_RUN_ATTEMPT','2'), ('GITHUB_RUN_ID','../bad'), ('GITHUB_JOB','other'),
                ('PREP_APPROVED_HELPERS_SHA256','invalid')]:
            with self.subTest(key=key,value=value), self.assertRaises(d.GateError):
                self.execute({key:value})
        self.reader.assert_not_called(); self.loader.assert_not_called()

    def test_changed_source_bundle_prevents_loading_ports(self):
        self.reader.side_effect=lambda root,name: SNAPSHOTS[name]+b'changed'
        with self.assertRaisesRegex(d.GateError,'HELPER_BINDING'): self.execute()
        self.loader.assert_not_called()

    def test_bundle_includes_caller_key_and_both_helpers(self):
        self.assertEqual(set(d.SOURCES), {'tests/run_mint_media_console.py',
            'tests/mint_media_console.py','tests/mint_media_native.py',
            'tests/fixtures/linuxmint-iso-signing.asc'})
        for name in d.SOURCES:
            changed=dict(SNAPSHOTS); changed[name]+=b'x'
            self.assertNotEqual(d.bundle_digest(changed),DIGEST)

    def test_healthy_synthetic_ports_close_before_export(self):
        with patch.object(d,'ownership_record',return_value={'runId':RUN, 'cleanupPerformed':False}):
            output=json.loads(self.execute())
        self.assertFalse(output['report']['productionReady'])
        self.assertFalse(output['wholeHostCleanupPerformed'])
        self.assertEqual(output['actions']['runId'],'123')
        self.core.host_gate.assert_called_once_with(self.native.collect_host.return_value)
        self.native.Workspace.assert_called_once_with(RUN)
        self.ws.__exit__.assert_called_once()
        args=self.core.prepare.call_args.kwargs
        self.assertEqual(args['source_sha'],env()['GITHUB_SHA'])
        self.assertEqual(args['helper_sha'],DIGEST)
        self.assertEqual(args['key'],SNAPSHOTS[d.SOURCES[-1]])

    def test_host_rejection_prevents_workspace_and_transfers(self):
        self.core.host_gate.side_effect=d.GateError('HOST_PLATFORM')
        with self.assertRaisesRegex(d.GateError,'HOST_PLATFORM'):self.execute()
        self.native.Workspace.assert_not_called();self.core.prepare.assert_not_called()

    def test_prep_failure_still_closes_without_success_export(self):
        self.core.prepare.side_effect=d.GateError('SIGNATURE')
        with self.assertRaisesRegex(d.GateError,'SIGNATURE'):self.execute()
        self.ws.__exit__.assert_called_once()

    def test_close_uncertainty_prevents_success_export(self):
        self.ws.__exit__.side_effect=d.GateError('DESCRIPTOR_CLEANUP_UNCERTAIN')
        with patch.object(d,'ownership_record',return_value={}), \
             self.assertRaisesRegex(d.GateError,'DESCRIPTOR_CLEANUP_UNCERTAIN'):self.execute()

    def test_oversized_export_stops_and_closes(self):
        self.core.prepare.return_value={'oversized':'x'*d.EXPORT_LIMIT}
        with patch.object(d,'ownership_record',return_value={}), \
             self.assertRaisesRegex(d.GateError,'EXPORT_SIZE'):self.execute()
        self.ws.__exit__.assert_called_once()

    def test_ownership_export_is_bounded_and_bound_to_run(self):
        self.ws._file.return_value=9
        with patch.object(d.os,'fstat',return_value=SimpleNamespace(st_size=d.EXPORT_LIMIT+1)), \
             patch.object(d.os,'pread') as read,self.assertRaisesRegex(d.GateError,'EXPORT_SIZE'):
            d.ownership_record(self.ws)
        read.assert_not_called()
        for record in ({'runId':'other','cleanupPerformed':False},
                       {'runId':RUN,'cleanupPerformed':False}):
            raw=json.dumps(record).encode()
            with patch.object(d.os,'fstat',return_value=SimpleNamespace(st_size=len(raw))), \
                 patch.object(d.os,'pread',return_value=raw):
                if record['runId'] == RUN:
                    self.assertEqual(d.ownership_record(self.ws)['runId'],RUN)
                else:
                    with self.assertRaisesRegex(d.GateError,'EXPORT_OWNERSHIP'):d.ownership_record(self.ws)

    def test_partial_or_changing_manifest_cannot_export_valid_prefix(self):
        self.ws._file.return_value=9
        raw=json.dumps({'runId':RUN,'cleanupPerformed':False}).encode()
        for sizes in ([len(raw)+4], [len(raw),len(raw)+1]):
            with patch.object(d.os,'fstat',side_effect=[SimpleNamespace(st_size=x) for x in sizes]), \
                 patch.object(d.os,'pread',return_value=raw),self.assertRaisesRegex(d.GateError,'EXPORT_INCOMPLETE'):
                d.ownership_record(self.ws)

    def test_failure_output_sanitizes_arbitrary_exception_text(self):
        for failure, reason in [(RuntimeError('SECRET_TOKEN'),'PREPARATION_STOPPED'),
                                (d.GateError('SOURCE_BINDING'),'SOURCE_BINDING')]:
            out=io.StringIO()
            with patch.object(d,'run',side_effect=failure),patch.object(d.sys,'argv',['driver']), \
                 patch('sys.stdout',out):self.assertEqual(d.main(),1)
            value=json.loads(out.getvalue())
            self.assertEqual(value['reason'],reason)
            self.assertEqual(value['cleanupCorrectness'],'NotConfirmed')
            self.assertFalse(value['productionReady'])

    def test_cli_arguments_refused_without_activation(self):
        with patch.object(d,'run') as run,patch.object(d.sys,'argv',['driver','--url=bad']), \
             patch('sys.stdout',io.StringIO()):self.assertEqual(d.main(),1)
        run.assert_not_called()

    def test_source_read_bound_and_descriptor_cleanup_with_mocked_os(self):
        st=SimpleNamespace(st_uid=1001,st_mode=0o100600,st_nlink=1,st_size=3,
                           st_dev=1,st_ino=2,st_mtime_ns=1,st_ctime_ns=1)
        directory=SimpleNamespace(st_uid=1001,st_mode=0o40700)
        # /checkout/tests + source leaf, plus the initial root descriptor.
        with patch.object(d.os,'getuid',return_value=1001), \
             patch.object(d.os,'open',side_effect=[1,2,3,4]), \
             patch.object(d.os,'fstat',side_effect=[directory,directory,st,st]), \
             patch.object(d.os,'read',side_effect=[b'abc',b'']),patch.object(d.os,'close') as close:
            self.assertEqual(d.read_source(Path('/checkout'),'tests/file.py'),b'abc')
        self.assertEqual([c.args[0] for c in close.call_args_list],[1,2,4,3])
        st.st_size=d.FILE_LIMIT+1
        with patch.object(d.os,'getuid',return_value=1001),patch.object(d.os,'open',side_effect=[1,2,3,4]), \
             patch.object(d.os,'fstat',side_effect=[directory,directory,st]), \
             patch.object(d.os,'read') as read,patch.object(d.os,'close') as close, \
             self.assertRaisesRegex(d.GateError,'SOURCE_FILE'):
            d.read_source(Path('/checkout'),'tests/file.py')
        read.assert_not_called(); self.assertEqual(close.call_count,4)

    def test_source_owner_or_changed_bytes_reject_and_close(self):
        directory=SimpleNamespace(st_uid=1001,st_mode=0o40700)
        before=SimpleNamespace(st_uid=1001,st_mode=0o100600,st_nlink=1,st_size=3,
                               st_dev=1,st_ino=2,st_mtime_ns=1,st_ctime_ns=1)
        after=SimpleNamespace(**dict(vars(before),st_mtime_ns=2))
        with patch.object(d.os,'getuid',return_value=1001),patch.object(d.os,'open',side_effect=[1,2,3,4]), \
             patch.object(d.os,'fstat',side_effect=[directory,directory,before,after]), \
             patch.object(d.os,'read',side_effect=[b'abc',b'']),patch.object(d.os,'close') as close, \
             self.assertRaisesRegex(d.GateError,'SOURCE_CHANGED'):
            d.read_source(Path('/checkout'),'tests/file.py')
        self.assertEqual(close.call_count,4)
        directory.st_mode=0o40777
        with patch.object(d.os,'getuid',return_value=1001),patch.object(d.os,'open',side_effect=[1,2]), \
             patch.object(d.os,'fstat',return_value=directory),patch.object(d.os,'close') as close, \
             self.assertRaisesRegex(d.GateError,'SOURCE_OWNER'):
            d.read_source(Path('/checkout'),'tests/file.py')
        self.assertEqual([c.args[0] for c in close.call_args_list],[1,2])

    def test_snapshot_loader_uses_only_supplied_synthetic_bytes(self):
        snapshots={'tests/mint_media_console.py': b'value = 42',
                   'tests/mint_media_native.py': b'from mint_media_console import value'}
        with patch.dict(d.sys.modules):
            d.sys.modules.pop('mint_media_console',None)
            d.sys.modules.pop('mint_media_native',None)
            core,native=d.load_ports(snapshots)
            self.assertEqual(core.value,42);self.assertEqual(native.value,42)
            with self.assertRaisesRegex(d.GateError,'PRELOADED_HELPERS'): d.load_ports(snapshots)
        with patch.dict(d.sys.modules):
            d.sys.modules.pop('mint_media_console',None)
            d.sys.modules.pop('mint_media_native',None)
            snapshots['tests/mint_media_native.py']=b'raise RuntimeError("synthetic")'
            with self.assertRaises(RuntimeError):d.load_ports(snapshots)
            self.assertNotIn('mint_media_console',d.sys.modules)
            self.assertNotIn('mint_media_native',d.sys.modules)

    def test_real_helper_definitions_load_without_activating_native_ports(self):
        import fcntl
        import socket
        import subprocess
        snapshots={name:(ROOT/name).read_bytes() for name in
                   ('tests/mint_media_console.py','tests/mint_media_native.py')}
        with patch.dict(d.sys.modules), patch.object(d.os,'open',side_effect=AssertionError('native open')) as opened, \
             patch.object(fcntl,'ioctl',side_effect=AssertionError('native ioctl')) as ioctl, \
             patch.object(socket,'socket',side_effect=AssertionError('native socket')) as sock, \
             patch.object(subprocess,'Popen',side_effect=AssertionError('native process')) as process:
            d.sys.modules.pop('mint_media_console',None)
            d.sys.modules.pop('mint_media_native',None)
            core,native=d.load_ports(snapshots)
            self.assertEqual(core.ISO,'linuxmint-22.3-cinnamon-64bit.iso')
            self.assertTrue(callable(native.collect_host))
            opened.assert_not_called();ioctl.assert_not_called()
            sock.assert_not_called();process.assert_not_called()

    def test_failure_reports_owned_run_without_claiming_cleanup(self):
        def stopped(env, observation):
            observation['runId']=RUN
            raise d.GateError('EVIDENCE_UNCERTAIN')
        out=io.StringIO()
        with patch.object(d,'run',side_effect=stopped),patch.object(d.sys,'argv',['driver']), \
             patch('sys.stdout',out):self.assertEqual(d.main(),1)
        result=json.loads(out.getvalue())
        self.assertEqual(result['ownedRunId'],RUN)
        self.assertEqual(result['cleanupCorrectness'],'NotConfirmed')

    def test_source_parent_close_failure_closes_new_descriptor_without_retry(self):
        with patch.object(d.os,'open',side_effect=[1,2]),patch.object(d.os,'getuid',return_value=1001), \
             patch.object(d.os,'close',side_effect=[OSError('synthetic close uncertainty'),None]) as close, \
             self.assertRaisesRegex(d.GateError,'SOURCE_CLEANUP_UNCERTAIN'):
            d.read_source(Path('/checkout'),'tests/file.py')
        self.assertEqual([c.args[0] for c in close.call_args_list],[1,2])

    def test_source_final_close_failure_still_attempts_other_descriptors(self):
        directory=SimpleNamespace(st_uid=1001,st_mode=0o40700)
        file=SimpleNamespace(st_uid=1001,st_mode=0o100600,st_nlink=1,st_size=3,
                             st_dev=1,st_ino=2,st_mtime_ns=1,st_ctime_ns=1)
        with patch.object(d.os,'open',side_effect=[1,2,3,4]),patch.object(d.os,'getuid',return_value=1001), \
             patch.object(d.os,'fstat',side_effect=[directory,directory,file,file]), \
             patch.object(d.os,'read',side_effect=[b'abc',b'']), \
             patch.object(d.os,'close',side_effect=[None,None,OSError('synthetic close uncertainty'),None]) as close, \
             self.assertRaisesRegex(d.GateError,'SOURCE_CLEANUP_UNCERTAIN'):
            d.read_source(Path('/checkout'),'tests/file.py')
        self.assertEqual([c.args[0] for c in close.call_args_list],[1,2,4,3])

    def test_malformed_preloaded_module_does_not_break_sanitized_failure(self):
        out=io.StringIO()
        with patch.dict(d.sys.modules,{'mint_media_console':SimpleNamespace(Stop='not a type')}), \
             patch.object(d,'run',side_effect=RuntimeError('SECRET_TOKEN')), \
             patch.object(d.sys,'argv',['driver']),patch('sys.stdout',out):
            self.assertEqual(d.main(),1)
        self.assertEqual(json.loads(out.getvalue())['reason'],'PREPARATION_STOPPED')

    def test_signal_restore_failure_prevents_main_success_export(self):
        calls=[None,None,OSError('synthetic restore failure'),None]
        out=io.StringIO()
        with patch.object(d.signal,'signal',side_effect=calls),patch.object(d,'run',return_value='success'), \
             patch.object(d.sys,'argv',['driver']),patch('sys.stdout',out):
            self.assertEqual(d.main(),1)
        self.assertNotIn('success',out.getvalue())
        self.assertEqual(json.loads(out.getvalue())['reason'],'SIGNAL_RESTORE_UNCERTAIN')

    def test_caught_interruption_cannot_turn_into_main_success(self):
        out=io.StringIO()
        with patch.object(d.signal,'signal') as install:
            def suppressed(env, observation):
                handler=install.call_args_list[0].args[1]
                try:handler(d.signal.SIGTERM,None)
                except d.GateError:pass
                return 'must not export success'
            with patch.object(d,'run',side_effect=suppressed),patch.object(d.sys,'argv',['driver']), \
                 patch('sys.stdout',out):self.assertEqual(d.main(),1)
        result=json.loads(out.getvalue())
        self.assertTrue(result['interrupted'])
        self.assertEqual(result['reason'],'INTERRUPTED')
        self.assertNotIn('must not export success',out.getvalue())

    def test_interruption_marker_survives_helper_failure_translation(self):
        out=io.StringIO()
        with patch.object(d.signal,'signal') as install:
            def translated(env, observation):
                handler=install.call_args_list[0].args[1]
                try:handler(d.signal.SIGINT,None)
                except d.GateError:raise d.GateError('NATIVE_FAILURE') from None
            with patch.object(d,'run',side_effect=translated),patch.object(d.sys,'argv',['driver']), \
                 patch('sys.stdout',out):self.assertEqual(d.main(),1)
        result=json.loads(out.getvalue())
        self.assertTrue(result['interrupted'])
        self.assertEqual(result['reason'],'NATIVE_FAILURE')

    def test_synthetic_termination_reaches_real_owned_child_cleanup_logic(self):
        import mint_media_native as native
        process=Mock();process.stdout.fileno.return_value=7;process.poll.return_value=None
        selector=Mock()
        state={}
        with patch.object(d.signal,'signal') as install,patch.object(native,'_tool'), \
             patch.object(native.subprocess,'Popen',return_value=process), \
             patch.object(native.selectors,'DefaultSelector',return_value=selector), \
             patch.object(native.os,'set_blocking'),self.assertRaisesRegex(d.GateError,'INTERRUPTED'):
            with d.interruption_guard(state):
                handler=install.call_args_list[0].args[1]
                selector.select.side_effect=lambda timeout:handler(d.signal.SIGTERM,None)
                native._capture(['/usr/bin/curl','--disable','--version'],10,lambda:0)
        self.assertTrue(state['requested'])
        process.kill.assert_called_once();process.wait.assert_called_once_with(timeout=5)
        process.stdout.close.assert_called_once();selector.close.assert_called_once()


class SignalChecks(unittest.TestCase):
    def test_first_termination_unwinds_and_repeated_signal_does_not_abort_cleanup(self):
        cleaned=[]
        with patch.object(d.signal,'getsignal',side_effect=['old TERM','old INT']), \
             patch.object(d.signal,'signal') as install,self.assertRaisesRegex(d.GateError,'INTERRUPTED'):
            with d.interruption_guard():
                handler=install.call_args_list[0].args[1]
                try:
                    handler(d.signal.SIGTERM,None)  # synthetic invocation, not a signal
                finally:
                    handler(d.signal.SIGINT,None)
                    cleaned.append(True)
        self.assertEqual(cleaned,[True])
        self.assertEqual([c.args for c in install.call_args_list[-2:]],
                         [(d.signal.SIGINT,'old INT'),(d.signal.SIGTERM,'old TERM')])

    def test_partial_handler_installation_restores_every_saved_handler(self):
        body=Mock()
        with patch.object(d.signal,'getsignal',side_effect=['old TERM','old INT']), \
             patch.object(d.signal,'signal',side_effect=[None,OSError('synthetic install failure'),None,None]) as install, \
             self.assertRaises(OSError):
            with d.interruption_guard():body()
        body.assert_not_called()
        self.assertEqual([c.args for c in install.call_args_list[-2:]],
                         [(d.signal.SIGINT,'old INT'),(d.signal.SIGTERM,'old TERM')])

    def test_restore_uncertainty_attempts_both_handlers(self):
        with patch.object(d.signal,'getsignal',return_value=d.signal.SIG_DFL), \
             patch.object(d.signal,'signal',side_effect=[None,None,OSError('synthetic restore uncertainty'),None]) as install, \
             self.assertRaisesRegex(d.GateError,'SIGNAL_RESTORE_UNCERTAIN'):
            with d.interruption_guard():pass
        self.assertEqual(install.call_count,4)


class WorkflowChecks(unittest.TestCase):
    def setUp(self):
        self.w=yaml.load((ROOT/'.github/workflows/mint-media-console-prep.yml').read_text(),Loader=yaml.BaseLoader)
        self.job=self.w['jobs']['prepare']

    def allowed(self, **changes):
        values={'github.event_name':'workflow_dispatch','github.repository':d.REPO,
                'github.ref':'refs/heads/main','github.workflow_ref':d.WORKFLOW,
                'github.sha':'a'*40,'github.workflow_sha':'a'*40,'github.run_attempt':1,
                'vars.MINT_PREP_ENABLED':'true','vars.MINT_PREP_ACCESS_READY':'verified',
                'vars.MINT_PREP_APPROVED_SHA':'a'*40,'vars.MINT_PREP_HELPERS_SHA256':DIGEST}
        values.update(changes);expression=self.job['if']
        for key in sorted(values,key=len,reverse=True): expression=expression.replace(key,repr(values[key]))
        return eval(expression.replace('&&',' and '),{'__builtins__':{}},{})

    def test_disabled_defaults_and_each_approval_gate(self):
        self.assertTrue(self.allowed())
        for name in ('vars.MINT_PREP_ENABLED','vars.MINT_PREP_ACCESS_READY',
                     'vars.MINT_PREP_APPROVED_SHA','vars.MINT_PREP_HELPERS_SHA256'):
            self.assertFalse(self.allowed(**{name:''}))
        for key,value in [('github.event_name','pull_request'),('github.event_name','push'),
                ('github.event_name','workflow_call'),('github.repository','fork/repo'),
                ('github.ref','refs/heads/feature'),('github.workflow_ref','other'),
                ('github.workflow_sha','b'*40),('github.run_attempt',2)]:
            self.assertFalse(self.allowed(**{key:value}))

    def test_fixed_group_environment_no_dispatch_inputs_and_no_artifact_export(self):
        self.assertEqual(self.w['on'],{'workflow_dispatch':''})
        self.assertEqual(self.w['permissions'],{'contents':'read'})
        self.assertEqual(self.w['concurrency'],{'group':'spare-mint-host','cancel-in-progress':'false'})
        self.assertEqual(set(self.w['jobs']),{'prepare'})
        self.assertEqual(self.job['environment'],'mint-host-access')
        self.assertEqual(self.job['runs-on'],{'group':'org/sde-mint-isolated','labels':'sde-mint-prep'})
        self.assertEqual(self.job['timeout-minutes'],'25')
        steps=self.job['steps'];self.assertEqual(len(steps),2)
        self.assertEqual(steps[0]['uses'],'actions/checkout@11d5960a326750d5838078e36cf38b85af677262')
        self.assertEqual(steps[0]['with'],{'ref':'${{ github.sha }}','persist-credentials':'false',
                                         'submodules':'false','lfs':'false'})
        self.assertEqual(steps[1]['run'],'/usr/bin/python3 -I -B tests/run_mint_media_console.py')
        self.assertEqual(steps[1]['shell'],'bash --noprofile --norc -e -o pipefail {0}')
        self.assertEqual(set(steps[1]['env']),{'PREP_ENABLED','PREP_ACCESS_READY','PREP_APPROVED_SHA',
                                             'PREP_WORKFLOW_SHA','PREP_APPROVED_HELPERS_SHA256'})
        self.assertNotIn('secrets.',str(steps));self.assertNotIn('sudo',str(steps))


if __name__ == '__main__':
    unittest.main()
