"""Mocked-only delivery/supervision checks: never fork, signal or access host files."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace as S
import unittest
from unittest.mock import Mock, patch, call
import mint_archive_supervisor as s

SOURCES={'mint_session_archive_plan':b'plan bytes', 'mint_session_archive_native':b'native bytes'}
PINS={k:hashlib.sha256(v).hexdigest() for k,v in SOURCES.items()}


def result():
    return dict(renameErrno=0,passed=True,reason='SETUP_RECORDED',lastKnownPhase='complete',
        cleanupStatus=dict(descriptors='ClosedAsReported',umask='Restored',signals='Restored'),
        nativeValidated=False,authenticationSafety='NotValidated',wholeHostCleanupPerformed=False,
        retryAuthorized=False)


def info(mode=0o100600,size=3,ino=1):
    return S(st_dev=1,st_ino=ino,st_uid=1001,st_mode=mode,st_size=size,st_nlink=1,
             st_mtime_ns=1,st_ctime_ns=1)


class Supervisor(unittest.TestCase):
    def setUp(self):
        pin=patch.object(s,'PINS',PINS);pin.start();self.addCleanup(pin.stop)
        for obj,name in ((s.os,'umask'),(s.signal,'signal'),(s.signal,'getsignal')):
            p=patch.object(obj,name,return_value=0o022 if name=='umask' else None)
            setattr(self,name,p.start());self.addCleanup(p.stop)
        self.delivery=Mock(owned=[5,6])
        self.delivery.snapshots.return_value=dict(SOURCES)
        self.process=Mock()
        self.process.collect.return_value=result()
        self.process.stop.return_value='ReapedAsReported'
        self.process.evidence.return_value=dict(pid=101,armed=True,pidfdRetained=True,reaped=True)
        self.gates=Mock()

    def run_supervisor(self):
        return s.supervise(self.delivery,self.process,self.gates,authorized=True)

    def test_unauthorized_is_inert(self):
        report=s.supervise(self.delivery,self.process,self.gates)
        self.assertFalse(report['passed']);self.umask.assert_not_called()
        self.assertEqual(self.delivery.mock_calls,[]);self.assertEqual(self.process.mock_calls,[])

    def test_healthy_verified_bytes_and_non_authoritative_durable_record(self):
        report=self.run_supervisor()
        self.assertTrue(report['passed']);self.assertFalse(report['nativeValidated'])
        self.process.start.assert_called_once_with(SOURCES,self.gates,(5,6))
        records=self.delivery.persist.call_args_list
        self.assertEqual(len(records),2)
        persisted=records[-1].args[0]
        self.assertFalse(persisted['passed']);self.assertTrue(persisted['workerReportedPass'])
        self.assertFalse(persisted['returnedAfterCloseout']);self.assertTrue(report['returnedAfterCloseout'])
        self.assertEqual(persisted['finalAuthority'],'returned-report-after-closeout')
        self.process.stop.assert_called_once_with();self.process.cleanup.assert_called_once_with()
        self.delivery.cleanup.assert_called_once_with()
        self.assertEqual(self.umask.call_args_list,[call(0o077),call(0o022)])

    def test_changed_helper_blocks_fork(self):
        self.delivery.snapshots.return_value=dict(SOURCES,mint_session_archive_native=b'changed')
        report=self.run_supervisor()
        self.assertFalse(report['passed']);self.process.start.assert_not_called()
        self.assertEqual(report['reason'],'BUNDLE_DIGEST')

    def test_initial_persistence_failure_prevents_child(self):
        self.delivery.persist.side_effect=OSError('SECRET')
        report=self.run_supervisor()
        self.assertFalse(report['passed']);self.process.start.assert_not_called()
        self.assertNotIn('SECRET',json.dumps(report))
        self.assertEqual(self.delivery.persist.call_count,1)

    def test_timeout_is_not_pass_and_worker_always_stopped(self):
        self.process.collect.side_effect=s.Stop('WORKER_TIMEOUT')
        report=self.run_supervisor()
        self.assertFalse(report['passed']);self.assertEqual(report['reason'],'WORKER_TIMEOUT')
        self.process.stop.assert_called_once_with();self.process.cleanup.assert_called_once_with()

    def test_unconfirmed_child_skips_final_blocking_report_write(self):
        self.process.stop.side_effect=s.Stop('CHILD_UNCONFIRMED')
        report=self.run_supervisor()
        self.assertFalse(report['passed']);self.assertEqual(report['childTermination'],'Unconfirmed')
        self.assertEqual(report['reason'],'CHILD_UNCONFIRMED')
        self.assertEqual(self.delivery.persist.call_count,1)

    def test_close_and_mask_failures_cannot_report_pass(self):
        self.delivery.cleanup.side_effect=OSError()
        self.assertFalse(self.run_supervisor()['passed'])
        self.delivery.cleanup.side_effect=None
        self.umask.side_effect=[0o022,OSError()]
        self.assertEqual(self.run_supervisor()['reason'],'UMASK_RESTORE_UNCERTAIN')

    def test_final_persistence_failure_and_invalid_worker_cannot_pass(self):
        self.delivery.persist.side_effect=[None,OSError('SECRET')]
        report=self.run_supervisor()
        self.assertFalse(report['passed']);self.assertEqual(report['reportPersistence'],'Unconfirmed')
        self.assertNotIn('SECRET',json.dumps(report));self.process.stop.assert_called_once_with()
        self.delivery.persist.side_effect=None
        self.process.collect.return_value=dict(result(),passed=1)
        self.assertFalse(self.run_supervisor()['passed'])

    def test_create_report_uncertainty_is_not_retried(self):
        self.delivery.create_report.side_effect=OSError()
        report=self.run_supervisor()
        self.assertFalse(report['passed']);self.delivery.persist.assert_not_called()
        self.process.start.assert_not_called();self.delivery.cleanup.assert_called_once_with()

    def test_sigterm_requests_stop_and_restores_handlers(self):
        def signalled():
            self.signal.call_args_list[0].args[1](s.signal.SIGTERM,None)
            raise s.Stop('INTERRUPTED')
        self.process.collect.side_effect=signalled
        report=self.run_supervisor()
        self.assertFalse(report['passed']);self.assertTrue(self.process.stop_requested)
        self.process.stop.assert_called_once_with()
        self.assertEqual(self.signal.call_args_list[-1],call(s.signal.SIGTERM,None))


class Validation(unittest.TestCase):
    def test_bundle_framing_and_pins_are_fixed(self):
        with patch.object(s,'PINS',PINS):
            s.verify_bundle(SOURCES)
            for bad in ({},dict(SOURCES,extra=b'x'),dict(SOURCES,mint_session_archive_plan=b'x')):
                with self.assertRaises(s.Stop):s.verify_bundle(bad)
        self.assertEqual(s.SOURCE_SHA,'887ebc9485ec2b18064cb9f3515929dd37436e61')

    def test_result_schema_rejects_partial_duplicate_or_false_pass(self):
        raw=json.dumps(result()).encode();self.assertTrue(s.validate_result(raw)['passed'])
        for bad in (b'',raw[:-1],b'x'*(s.LIMIT+1),b'{"passed":false,"passed":true}'):
            with self.assertRaises((s.Stop,ValueError)):s.validate_result(bad)
        for key,value in [('passed',1),('nativeValidated',True),('reason','SECRET\n'),
                          ('renameErrno',True),('lastKnownPhase','prepared')]:
            value=dict(result(),**{key:value})
            with self.subTest(key=key),self.assertRaises(s.Stop):s.validate_result(json.dumps(value).encode())
        bad=result();bad['cleanupStatus']['descriptors']='Uncertain'
        with self.assertRaises(s.Stop):s.validate_result(json.dumps(bad).encode())

    def test_worker_loads_only_immutable_bytes_not_pathname_import(self):
        sources={'mint_session_archive_plan':b'VALUE=1\n',
                 'mint_session_archive_native':('class Native: pass\n'
                    'def execute(*args,**kwargs): return '+repr(result())+'\n').encode()}
        pins={k:hashlib.sha256(v).hexdigest() for k,v in sources.items()}
        modules={k:v for k,v in s.sys.modules.items() if k not in pins}
        with patch.object(s,'PINS',pins),patch.dict(s.sys.modules,modules,clear=True):
            report=s.validate_result(s.worker(sources,Mock()))
            self.assertTrue(report['passed']);self.assertFalse(set(pins)&set(s.sys.modules))
        with patch.object(s,'PINS',pins),patch.dict(s.sys.modules,{'mint_session_archive_plan':Mock()}), \
             self.assertRaisesRegex(s.Stop,'HELPER_PRELOADED'):s.worker(sources,Mock())

    def test_pinned_helpers_match_repository_source_without_execution(self):
        root=Path(__file__).resolve().parent
        for name,digest in s.PINS.items():
            raw=(root/(name+'.py')).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),digest)

    def test_no_download_runner_or_generic_command_path(self):
        tree=ast.parse(Path(s.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                self.assertFalse({a.name for a in node.names}&{'subprocess','socket','urllib','requests'})
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                self.assertNotIn(node.func.attr,{'execve','execv','system','Popen','chmod','chown','rename',
                                                'replace','unlink','rmdir','kill'})
        self.assertFalse(hasattr(s,'main'))


class Delivery(unittest.TestCase):
    def test_snapshot_flags_bounds_identity_and_digest(self):
        d=s.Delivery();d.control=7
        with patch.object(s,'PINS',{'one':hashlib.sha256(b'abc').hexdigest()}), \
             patch.object(s.os,'open',return_value=10) as opened, \
             patch.object(s.os,'fstat',return_value=info()), \
             patch.object(s.os,'read',side_effect=[b'abc',b'']),patch.object(s.os,'close') as close:
            self.assertEqual(d.snapshots(),{'one':b'abc'})
        flags=opened.call_args.args[1]
        for flag in (os.O_NOFOLLOW,os.O_CLOEXEC,os.O_NONBLOCK,os.O_NOCTTY):self.assertTrue(flags&flag)
        close.assert_called_once_with(10)
        with patch.object(s,'PINS',{'one':'a'*64}),patch.object(s.os,'open',return_value=10), \
             patch.object(s.os,'fstat',return_value=info(mode=0o100664)), \
             patch.object(s.os,'read') as read,patch.object(s.os,'close'),self.assertRaises(s.Stop):d.snapshots()
        read.assert_not_called()

    def test_successful_report_is_fsynced_and_read_back(self):
        d=s.Delivery();d.control=7;d.report=10;d.report_identity=info(size=0)
        with patch.object(s.os,'fstat',side_effect=lambda *a:info(size=len(d.content))), \
             patch.object(s.os,'stat',side_effect=lambda *a,**kw:info(size=len(d.content))), \
             patch.object(s.os,'pread',side_effect=lambda *a:d.content), \
             patch.object(s.os,'write',side_effect=lambda fd,raw:len(raw)) as write, \
             patch.object(s.os,'fsync') as sync:d.persist({'kind':'synthetic'})
        write.assert_called_once();sync.assert_called_once_with(10)
        self.assertEqual(json.loads(d.content),{'kind':'synthetic'})

    def test_report_exclusive_bounds_short_write_and_readback(self):
        d=s.Delivery();d.control=7
        with patch.object(s.os,'open',return_value=10) as opened, \
             patch.object(s.os,'fstat',return_value=info(size=0)),patch.object(s.os,'fsync'):
            d.create_report()
        self.assertTrue(opened.call_args.args[1]&os.O_EXCL)
        with patch.object(s.os,'fstat',return_value=info(size=0)), \
             patch.object(s.os,'stat',return_value=info(size=0)), \
             patch.object(s.os,'pread',return_value=b''),patch.object(s.os,'write',return_value=1) as write, \
             self.assertRaisesRegex(s.Stop,'REPORT_SHORT_WRITE'):d.persist({'test':1})
        write.assert_called_once()
        with patch.object(s.os,'write') as write,self.assertRaisesRegex(s.Stop,'REPORT_BOUND'):
            d.persist({'huge':'x'*s.LIMIT})
        write.assert_not_called()

    def test_pinned_directory_replacement_and_uncertain_close_stop(self):
        d=s.Delivery();d.pinned=[(7,'fixed',8,(1,1,1001,0o40700))]
        with patch.object(s.os,'stat',return_value=info(mode=0o40700,ino=2)), \
             patch.object(s.os,'fstat',return_value=info(mode=0o40700)), \
             self.assertRaisesRegex(s.Stop,'DELIVERY_PATH_CHANGED'):d.validate_paths()
        d.owned=[7,8]
        with patch.object(s.os,'close',side_effect=[OSError(),None]) as close, \
             self.assertRaisesRegex(s.Stop,'DELIVERY_CLOSE'):d.cleanup()
        self.assertEqual(close.call_args_list,[call(8),call(7)])


class Process(unittest.TestCase):
    def test_parent_death_binding_and_original_parent_check(self):
        fn=Mock(return_value=0)
        with patch.object(s.ctypes,'CDLL',return_value=S(prctl=fn)), \
             patch.object(s.os,'getppid',return_value=100):s.arm_parent_death(100)
        fn.assert_called_once_with(1,s.signal.SIGKILL,0,0,0)
        self.assertEqual(fn.argtypes,[s.ctypes.c_int]+[s.ctypes.c_ulong]*4)
        for result,parent in ((-1,100),(0,1)):
            fn=Mock(return_value=result)
            with patch.object(s.ctypes,'CDLL',return_value=S(prctl=fn)), \
                 patch.object(s.os,'getppid',return_value=parent), \
                 self.assertRaisesRegex(s.Stop,'PARENT_CHANGED'):s.arm_parent_death(100)

    def test_uncertain_barrier_close_does_not_prevent_pidfd_termination(self):
        p=s.Process(clock=Mock(return_value=0));p.pid=101;p.pidfd=14;p.barrier=11;p.owned=[11,14]
        with patch.object(s.os,'close',side_effect=OSError()) as close, \
             patch.object(p,'exited',side_effect=[False,True]), \
             patch.object(s.signal,'pidfd_send_signal') as send:
            self.assertEqual(p.stop(),'ReapedAsReported')
        close.assert_called_once_with(11)
        send.assert_called_once_with(14,s.signal.SIGTERM,None,0)
        self.assertIsNone(p.barrier)
        with patch.object(s.os,'close') as close,self.assertRaisesRegex(s.Stop,'PROCESS_CLOSE'):p.cleanup()
        close.assert_called_once_with(14)

    def test_parent_barrier_pins_pidfd_before_arming_once(self):
        p=s.Process(clock=Mock(return_value=0))
        events=[]
        with patch.object(s,'PINS',PINS),patch.object(s.os,'pipe2',side_effect=[(10,11),(12,13)]), \
             patch.object(s.os,'fork',return_value=101) as fork,patch.object(s.os,'getpid',return_value=100), \
             patch.object(s.os,'close'), \
             patch.object(s.os,'pidfd_open',side_effect=lambda *a:events.append('pidfd') or 14), \
             patch.object(s.os,'write',side_effect=lambda *a:events.append('arm') or 1):
            p.start(SOURCES,Mock(),())
        fork.assert_called_once_with();self.assertEqual(events,['pidfd','arm'])
        self.assertTrue(p.armed);self.assertEqual(p.owned,[12,14])

    def test_collect_valid_result_requires_eof_and_zero_exit(self):
        p=s.Process(clock=Mock(return_value=0));p.deadline=35;p.result=12;p.pidfd=14;p.pid=101
        with patch.object(s.os,'read',side_effect=[json.dumps(result()).encode(),b'']), \
             patch.object(p,'exited',return_value=True),patch.object(s.select,'poll'):
            p.status=0;self.assertTrue(p.collect()['passed'])
        with patch.object(s.os,'read',return_value=b''),patch.object(p,'exited',return_value=True), \
             self.assertRaisesRegex(s.Stop,'WORKER_EXIT'):
            p.status=256;p.collect()

    def test_timeout_and_output_overflow_stop(self):
        p=s.Process(clock=Mock(return_value=35));p.deadline=35
        with self.assertRaisesRegex(s.Stop,'WORKER_TIMEOUT'):p.collect()
        p.clock.return_value=0;p.result=12
        with patch.object(s.os,'read',return_value=b'x'*(s.LIMIT+1)),self.assertRaisesRegex(s.Stop,'OUTPUT_BOUND'):
            p.collect()

    def test_stop_escalates_only_through_retained_pidfd_with_bounded_waits(self):
        p=s.Process(clock=Mock(side_effect=[0,3,3,6]));p.pid=101;p.pidfd=14
        with patch.object(p,'exited',return_value=False), \
             patch.object(s.signal,'pidfd_send_signal') as send,self.assertRaisesRegex(s.Stop,'CHILD_UNCONFIRMED'):
            p.stop()
        self.assertEqual(send.call_args_list,[call(14,s.signal.SIGTERM,None,0),call(14,s.signal.SIGKILL,None,0)])
        p=s.Process();p.pid=101;p.barrier=11;p.owned=[11]
        with patch.object(s.os,'close') as close,patch.object(p,'exited',return_value=False), \
             self.assertRaisesRegex(s.Stop,'CHILD_UNCONFIRMED'):p.stop()
        close.assert_called_once_with(11)


if __name__=='__main__':unittest.main()
