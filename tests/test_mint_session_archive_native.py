"""Mocked-only archive inspector/ports/controller checks. Never call native open."""
import ast
import ctypes
import errno
import json
import os
from types import SimpleNamespace as S
from pathlib import Path
import unittest
from unittest.mock import Mock, patch, call
import mint_session_archive_native as n
import mint_session_archive_plan as p
from test_mint_session_archive_plan import observed


def info(mode=0o40700, uid=1001, ino=12088154, size=0, nlink=1):
    return S(st_dev=66306, st_ino=ino, st_uid=uid, st_gid=1001,
             st_mode=mode, st_size=size, st_nlink=nlink)


def gates():
    return dict(activationDisabled=True, remoteRunnerAbsent=True, noQueuedOrActiveJobs=True)


class Controller(unittest.TestCase):
    def setUp(self):
        self.ports=Mock()
        self.ports.observation.return_value=observed()
        self.ports.create_source.return_value=[66306,99]
        self.ports.create_work.return_value=[66306,100]
        for target in ('umask','getsignal','signal'):
            obj=n.os if target=='umask' else n.signal
            mocked=patch.object(obj,target,return_value=0o022 if target=='umask' else None)
            value=mocked.start();self.addCleanup(mocked.stop)
            setattr(self,target,value)

    def execute(self, **kwargs):
        return n.execute(self.ports,Mock(return_value=gates()),authorized=True,**kwargs)

    def test_unauthorized_never_touches_os_or_ports(self):
        report=n.execute(self.ports,Mock())
        self.assertFalse(report['passed']);self.assertEqual(report['reason'],'NOT_AUTHORIZED')
        self.assertEqual(self.ports.mock_calls,[]);self.umask.assert_not_called()
        self.signal.assert_not_called()

    def test_healthy_order_is_journal_before_rename_and_setup(self):
        report=self.execute()
        self.assertTrue(report['passed']);self.assertEqual(report['lastKnownPhase'],'complete')
        self.assertFalse(report['nativeValidated']);self.assertFalse(report['wholeHostCleanupPerformed'])
        names=[c[0] for c in self.ports.mock_calls]
        self.assertLess(names.index('create_journal'),names.index('rename_source'))
        records=[c.args[0] for c in self.ports.record.call_args_list]
        self.assertEqual(records,['prepared','rename-pending','archived','source-create-pending',
                                 'source-created','work-create-pending','work-created','complete'])
        calls=self.ports.mock_calls
        self.assertLess(calls.index(call.record('rename-pending',{})),
                        calls.index(call.revalidate(journal=True)))
        self.assertLess(calls.index(call.revalidate(journal=True)),calls.index(call.rename_source()))
        self.ports.cleanup.assert_called_once_with()
        self.assertEqual(self.umask.call_args_list,[call(0o077),call(0o022)])

    def test_every_transition_failure_stops_later_mutations(self):
        stages=['open','observation','revalidate','create_journal','record','rename_source',
                'verify_archive','create_source','create_work','verify_fresh']
        mutations=['rename_source','create_source','create_work']
        for stage in stages:
            self.ports.reset_mock(side_effect=True)
            getattr(self.ports,stage).side_effect=OSError('SENSITIVE DETAIL')
            report=self.execute()
            self.assertFalse(report['passed'],stage)
            self.assertNotIn('SENSITIVE',json.dumps(report))
            self.ports.cleanup.assert_called_once_with()
            if stage in stages[:5]:self.ports.rename_source.assert_not_called()
            if stage in ('rename_source','verify_archive'):self.ports.create_source.assert_not_called()
            if stage=='create_source':self.ports.create_work.assert_not_called()
            for name in mutations:self.assertLessEqual(getattr(self.ports,name).call_count,1)

    def test_partial_journal_and_interruptions_never_continue_or_rollback(self):
        for fail_record in range(8):
            self.ports.reset_mock(side_effect=True)
            self.ports.record.side_effect=[None]*fail_record+[KeyboardInterrupt()]
            report=self.execute()
            self.assertFalse(report['passed']);self.assertFalse(report['retryAuthorized'])
            self.ports.cleanup.assert_called_once_with()
            if fail_record <= 1:self.ports.rename_source.assert_not_called()
            if fail_record <= 2:self.ports.create_source.assert_not_called()
            if fail_record <= 4:self.ports.create_work.assert_not_called()

    def test_changed_remote_gate_refuses_rename(self):
        remote=Mock(side_effect=[gates(),dict(gates(),activationDisabled=False)])
        report=n.execute(self.ports,remote,authorized=True)
        self.assertFalse(report['passed']);self.ports.rename_source.assert_not_called()
        self.ports.cleanup.assert_called_once_with()

    def test_cleanup_restore_uncertainty_cannot_report_pass(self):
        self.ports.cleanup.side_effect=OSError('uncertain')
        self.assertEqual(self.execute()['reason'],'CLOSE_UNCERTAIN')
        self.ports.cleanup.side_effect=None
        self.umask.side_effect=[0o022,OSError('uncertain')]
        self.assertEqual(self.execute()['reason'],'UMASK_RESTORE_UNCERTAIN')

    def test_sigterm_handler_stops_and_is_restored(self):
        def interrupt():
            handler=self.signal.call_args_list[0].args[1]
            handler(n.signal.SIGTERM,None)
        self.ports.rename_source.side_effect=interrupt
        report=self.execute()
        self.assertEqual(report['reason'],'INTERRUPTED')
        self.ports.create_source.assert_not_called()
        self.assertEqual(self.signal.call_args_list[-1],call(n.signal.SIGTERM,None))


class Ports(unittest.TestCase):
    def native(self):
        ports=n.Native(clock=Mock(return_value=0))
        ports.deadline=30;ports.home=7;ports.source=8;ports.legacy=9
        return ports

    def test_directory_open_is_pinned_nofollow_cloexec(self):
        ports=self.native()
        with patch.object(n.os,'open',return_value=10) as opened:
            self.assertEqual(ports.directory('fixed',7),10)
        args=opened.call_args
        self.assertEqual(args.kwargs,{'dir_fd':7})
        for flag in (os.O_NOFOLLOW,os.O_CLOEXEC,os.O_DIRECTORY):self.assertTrue(args.args[1]&flag)
        self.assertEqual(ports.owned,[10])

    def test_bad_modes_acl_and_missing_observations_fail(self):
        ports=self.native()
        for value in (info(mode=0o40775),info(mode=0o120700),info(uid=0)):
            with patch.object(n.os,'fstat',return_value=value),self.assertRaises(n.Stop):
                ports.row(8,1001,0o700)
        with patch.object(n.os,'fstat',return_value=info()), \
             patch.object(n.os,'listxattr',return_value=['system.posix_acl_default']),self.assertRaises(n.Stop):
            ports.row(8,1001,0o700)
        with patch.object(n.os,'stat',side_effect=PermissionError()),self.assertRaises(PermissionError):
            ports.absent(7,'fixed')
        with patch.object(n.os,'stat',return_value=info()),self.assertRaisesRegex(n.Stop,'PATH_EXISTS'):
            ports.absent(7,'fixed')

    def test_exact_rename_abi_and_no_fallback_on_errno(self):
        fn=Mock();lib=S(renameat2=fn)
        self.assertIs(n.bind_rename(lib),fn)
        self.assertEqual(fn.argtypes,[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint])
        self.assertEqual(fn.restype,ctypes.c_int)
        for error in (errno.EEXIST,errno.ENOSYS,errno.EOPNOTSUPP,errno.EXDEV,errno.EINTR):
            ports=self.native();ports.rename=Mock(return_value=-1)
            with patch.object(n.ctypes,'get_errno',return_value=error), \
                 patch.object(n.os,'fsync') as sync,self.assertRaisesRegex(n.Stop,'RENAME_STOP'):
                ports.rename_source()
            ports.rename.assert_called_once_with(7,n.SOURCE.encode(),7,n.ARCHIVE.encode(),1)
            sync.assert_not_called();self.assertEqual(ports.rename_errno,error)

    def test_successful_rename_flushes_parent_once(self):
        ports=self.native();ports.rename=Mock(return_value=0)
        with patch.object(n.os,'fsync') as sync:ports.rename_source()
        sync.assert_called_once_with(7)

    def test_signal_during_open_does_not_lose_descriptor_ownership(self):
        ports=self.native()
        def opened(*args,**kwargs):
            ports.stop_requested=True  # deferred signal, no asynchronous exception
            return 11
        with patch.object(n.os,'open',side_effect=opened):
            self.assertEqual(ports.directory('fixed',7),11)
        self.assertEqual(ports.owned,[11])
        with self.assertRaisesRegex(n.Stop,'INTERRUPTED'):ports.check()
        with patch.object(n.os,'close') as close:ports.cleanup()
        close.assert_called_once_with(11)

    def test_journal_flush_failure_stops_without_second_write(self):
        ports=self.native();ports.journal=10
        with patch.object(ports,'journal_info'), \
             patch.object(n.os,'write',side_effect=lambda fd,b:len(b)) as write, \
             patch.object(n.os,'fsync',side_effect=OSError('uncertain')), \
             self.assertRaises(OSError):ports.record('rename-pending',{})
        write.assert_called_once();self.assertEqual(ports.sequence,0)

    def test_close_uncertainty_attempts_all_fds_once(self):
        ports=self.native();ports.owned=[7,8,9]
        with patch.object(n.os,'close',side_effect=[OSError(),None,None]) as close, \
             self.assertRaisesRegex(n.Stop,'CLOSE_UNCERTAIN'):ports.cleanup()
        self.assertEqual(close.call_args_list,[call(9),call(8),call(7)])
        self.assertEqual(ports.owned,[])

    def test_journal_exclusive_and_short_write_never_retried(self):
        ports=self.native()
        with patch.object(ports,'absent'),patch.object(n.os,'open',return_value=10) as opened, \
             patch.object(n.os,'fstat',return_value=info(mode=0o100600,ino=77)), \
             patch.object(ports,'journal_info'),patch.object(n.os,'fsync'):
            ports.create_journal()
        flags=opened.call_args.args[1]
        self.assertTrue(flags&os.O_EXCL);self.assertTrue(flags&os.O_NOFOLLOW)
        self.assertEqual(opened.call_args.args[2],0o600)
        with patch.object(ports,'journal_info'),patch.object(n.os,'write',return_value=1) as write, \
             patch.object(n.os,'fsync') as sync,self.assertRaisesRegex(n.Stop,'JOURNAL_SHORT_WRITE'):
            ports.record('prepared',{})
        write.assert_called_once();sync.assert_not_called()

    def test_journal_bounds_fsync_and_exact_readback(self):
        ports=self.native();ports.journal=10
        with patch.object(ports,'journal_info'), \
             patch.object(n.os,'write',side_effect=lambda fd,b:len(b)) as write, \
             patch.object(n.os,'fsync') as sync, \
             patch.object(n.os,'pread',side_effect=lambda *args:ports.journal_bytes):
            ports.record('prepared',{'identity':list(p.IDENTITY)})
        self.assertEqual(ports.sequence,1);write.assert_called_once();sync.assert_called_once_with(10)
        with patch.object(ports,'journal_info'),patch.object(n.os,'write') as write, \
             self.assertRaisesRegex(n.Stop,'JOURNAL_BOUND'):
            ports.record('oversize',{'data':'x'*p.RECORD_LIMIT})
        write.assert_not_called()
        with patch.object(ports,'journal_info'),patch.object(n.os,'write',side_effect=lambda fd,b:len(b)), \
             patch.object(n.os,'fsync'),patch.object(n.os,'pread',return_value=b'changed'), \
             self.assertRaisesRegex(n.Stop,'JOURNAL_READBACK'):ports.record('changed',{})

    def test_journal_replacement_link_and_mode_rejected(self):
        ports=self.native();ports.journal=10
        correct=info(mode=0o100600,ino=77)
        ports.journal_signature=n.sig(correct)
        for bad in (info(mode=0o100644,ino=77),info(mode=0o100600,ino=78),
                    info(mode=0o100600,ino=77,nlink=2)):
            with patch.object(n.os,'fstat',return_value=correct),patch.object(n.os,'stat',return_value=bad), \
                 self.assertRaisesRegex(n.Stop,'JOURNAL_CHANGED'):ports.journal_info()

    def test_deadline_stops_before_open_or_mutation(self):
        ports=self.native();ports.clock.return_value=30
        with patch.object(n.os,'open') as opened,self.assertRaisesRegex(n.Stop,'DEADLINE'):
            ports.directory('fixed',7)
        opened.assert_not_called()
        with patch.object(n.os,'mkdir') as mkdir,self.assertRaisesRegex(n.Stop,'DEADLINE'):
            ports.create_directory('fixed',7)
        mkdir.assert_not_called()

    def test_proc_parser_uses_kernel_uid_parent_and_start_time(self):
        ports=self.native()
        # comm contains spaces and parentheses; field 22 must still be starttime.
        raw=b'101 (test (controller)) S 100 '+b'0 '*17+b'500 0\n'
        safe_status=(b'Uid:\t1001 1001 1001 1001\nThreads:\t1\n'
                     b'CapInh:\t0000000000000000\nCapPrm:\t0000000000000000\n'
                     b'CapEff:\t0000000000000000\nCapAmb:\t0000000000000000\n')
        entries=Mock()
        entries.__enter__=Mock(return_value=iter([S(name='101'),S(name='not-a-pid')]))
        entries.__exit__=Mock(return_value=False)
        with patch.object(n.os,'scandir',return_value=entries), \
             patch.object(ports,'directory',return_value=11),patch.object(ports,'close'), \
             patch.object(ports,'read_proc',side_effect=[safe_status,raw]):
            self.assertEqual(ports.process_scan(10),{101:(100,500)})
        for status in (b'Uid:\t1001 0 0 0\n',b'Uid: 1001\n',b'Name: missing uid\n',
                       safe_status.replace(b'Threads:\t1',b'Threads:\t2'),
                       safe_status.replace(b'CapEff:\t0000000000000000',b'CapEff:\t0000000000000001')):
            entries.__enter__.return_value=iter([S(name='101')])
            with patch.object(n.os,'scandir',return_value=entries), \
                 patch.object(ports,'directory',return_value=11),patch.object(ports,'close'), \
                 patch.object(ports,'read_proc',return_value=status),self.assertRaises(n.Stop):
                ports.process_scan(10)

    def test_proc_read_budget_and_fd_close_on_bound_failure(self):
        ports=self.native();ports.read_bytes=n.PROC_BYTES
        with patch.object(n.os,'open',return_value=11),patch.object(n.os,'read',return_value=b'abc'), \
             patch.object(n.os,'close') as close,self.assertRaisesRegex(n.Stop,'PROC_BOUND'):
            ports.read_proc(10,'status',100)
        close.assert_called_once_with(11)
        self.assertEqual(ports.owned,[])

    def test_process_changes_after_pidfd_enrollment_stop(self):
        ports=self.native();context={101:(1,500)}
        with patch.object(ports,'directory',return_value=11),patch.object(ports,'close'), \
             patch.object(ports,'process_scan',side_effect=[context,context,{101:(1,501)}]), \
             patch.object(n.os,'getpid',return_value=101),patch.object(n.os,'pidfd_open',return_value=21), \
             self.assertRaisesRegex(n.Stop,'PROCESS_CHANGED'):
            ports.quiescence()
        self.assertIn(21,ports.owned)  # controller cleanup still owns it

    def test_mkdir_is_exclusive_and_not_retried_after_flush_failure(self):
        ports=self.native()
        with patch.object(n.os,'mkdir',side_effect=FileExistsError()) as mkdir, \
             patch.object(ports,'directory') as opened,self.assertRaises(FileExistsError):
            ports.create_directory('fixed',7)
        mkdir.assert_called_once_with('fixed',0o700,dir_fd=7);opened.assert_not_called()
        with patch.object(n.os,'mkdir') as mkdir,patch.object(ports,'directory',return_value=11), \
             patch.object(ports,'row'),patch.object(n.os,'fsync',side_effect=OSError('flush uncertain')), \
             self.assertRaises(OSError):ports.create_directory('fixed',7)
        mkdir.assert_called_once()

    def test_open_failure_does_not_create_journal_or_mutate_directories(self):
        ports=n.Native(clock=Mock(return_value=0))
        with patch.object(n.os,'getuid',return_value=0),patch.object(n.os,'geteuid',return_value=0), \
             patch.object(n.os,'open') as opened,patch.object(n.os,'mkdir') as mkdir, \
             self.assertRaisesRegex(n.Stop,'ACCOUNT'):ports.open()
        opened.assert_not_called();mkdir.assert_not_called()

    def test_changed_pinned_path_stops_revalidation(self):
        ports=self.native();ports.pinned=[(7,n.SOURCE,8)]
        ports.signatures={8:n.sig(info())}
        with patch.object(ports,'quiescence'),patch.object(n.os,'stat',return_value=info(ino=999)), \
             patch.object(n.os,'fstat',return_value=info()),self.assertRaisesRegex(n.Stop,'PATH_CHANGED'):
            ports.revalidate()

    def test_proc_entry_count_is_bounded_without_recursive_scan(self):
        ports=self.native();entries=Mock()
        entries.__enter__=Mock(return_value=iter([S(name='not-pid')]*(n.PROC_ENTRIES+1)))
        entries.__exit__=Mock(return_value=False)
        with patch.object(n.os,'scandir',return_value=entries), \
             patch.object(ports,'directory') as opened,self.assertRaisesRegex(n.Stop,'PROC_COUNT'):
            ports.process_scan(10)
        opened.assert_not_called()

    def test_final_directory_substitution_cannot_pass(self):
        ports=self.native();ports.fresh=12;ports.work=13
        with patch.object(ports,'revalidate'),patch.object(ports,'row'), \
             patch.object(n.os,'stat',return_value=info(ino=999)), \
             patch.object(n.os,'fstat',return_value=info(ino=111)), \
             self.assertRaisesRegex(n.Stop,'FRESH_PATH_CHANGED'):ports.verify_fresh()

    def test_no_cli_process_launch_or_repair_fallback_exists(self):
        tree=ast.parse(Path(n.__file__).read_text())
        allowed={'ctypes','grp','json','os','pwd','select','signal','stat','sys','time',
                 'mint_session_archive_plan'}
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):self.assertTrue(all(x.name in allowed for x in node.names))
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                if ast.unparse(node.func) in ('self.owned.remove','self.rename'):
                    continue
                self.assertNotIn(node.func.attr,{'execve','execv','system','Popen','run',
                    'unlink','remove','rmdir','rename','replace','chmod','chown','kill'})
        self.assertFalse(hasattr(n,'main'))
        self.assertNotIn('__main__',Path(n.__file__).read_text())
        for statement in tree.body:
            if isinstance(statement,ast.Expr):
                self.assertIsInstance(statement.value,ast.Constant)

    def test_quiescence_only_allows_enrolled_controller_ancestry(self):
        ports=self.native()
        context={101:(100,500),100:(1,400)}
        with patch.object(ports,'directory',return_value=11),patch.object(ports,'close'), \
             patch.object(ports,'process_scan',return_value=context), \
             patch.object(n.os,'getpid',return_value=101),patch.object(n.os,'pidfd_open',side_effect=[21,22]), \
             patch.object(n.select,'poll') as poll:
            poll.return_value.poll.return_value=[]
            ports.quiescence()
            self.assertEqual(ports.procs,context)
            poll.return_value.poll.return_value=[(21,1)]
            with self.assertRaisesRegex(n.Stop,'CONTROLLER_EXITED'):ports.quiescence()
        ports=self.native()
        with patch.object(ports,'directory',return_value=11),patch.object(ports,'close'), \
             patch.object(ports,'process_scan',return_value=dict(context,**{'unrelated':(1,600)})), \
             patch.object(n.os,'getpid',return_value=101),self.assertRaisesRegex(n.Stop,'ACCOUNT_NOT_QUIESCENT'):
            ports.quiescence()


if __name__=='__main__':unittest.main()
