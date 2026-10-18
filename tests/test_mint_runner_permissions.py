"""Mocked-only launcher checks: no chmod, signals, umask or runner execution."""
import io
import json
from pathlib import Path
from types import SimpleNamespace as S
import unittest
from unittest.mock import Mock, patch

import start_mint_preparation_runner as p

HOME = Path('/home/sde-runner')
SESSION = HOME / p.SESSION


def directory(mode=0o700, uid=1001):
    return S(st_mode=0o40000|mode, st_uid=uid)


def settings():
    return dict(workFolder=p.WORK, ephemeral=True, agentName='sde-mint-prep-once',gitHubUrl=p.ORG)


class Inspection(unittest.TestCase):
    def invoke(self, *, overrides=None, entries=(), config=None, attributes=()):
        paths={x:directory(0o755,0) for x in SESSION.parents}
        paths[HOME]=directory(0o750)
        paths[SESSION]=directory()
        paths[SESSION/p.WORK]=directory()
        paths[SESSION/'run.sh']=S(st_mode=0o100700,st_uid=1001,st_nlink=1)
        paths.update(overrides or {})
        scan=Mock();scan.__enter__=Mock(return_value=iter(entries));scan.__exit__=Mock(return_value=False)
        with patch.object(p.os,'scandir',return_value=scan), \
             patch.object(p.os,'listxattr',return_value=list(attributes)), \
             patch.object(p.os,'chmod',side_effect=AssertionError('no permission repair')), \
             patch.object(p.os,'chown',side_effect=AssertionError('no owner repair')):
            # autospec supplies the actual Path receiver to the mocked metadata read.
            with patch.object(p.Path,'lstat',autospec=True,side_effect=lambda path:paths[path]):
                return p.inspect_runner(HOME,1001,reader=Mock(return_value=settings() if config is None else config))

    def test_fresh_private_session_accepted(self):
        self.assertEqual(self.invoke(),SESSION)

    def test_bad_ancestry_private_mode_symlink_and_owner_stop(self):
        for path,metadata in [(HOME,directory(0o770)),(HOME,directory(uid=1000)),
                (SESSION,directory(0o775)),(SESSION/p.WORK,directory(0o775)),
                (SESSION/p.WORK,S(st_mode=0o120777,st_uid=1001)),
                (SESSION/'run.sh',S(st_mode=0o100775,st_uid=1001,st_nlink=1))]:
            with self.subTest(path=path,metadata=metadata),self.assertRaises(p.Stop):
                self.invoke(overrides={path:metadata})

    def test_inherited_default_acl_is_rejected_without_repair(self):
        with self.assertRaisesRegex(p.Stop,'DEFAULT_ACL'):
            self.invoke(attributes=['system.posix_acl_default'])

    def test_reused_workspace_and_wrong_registration_stop(self):
        with self.assertRaisesRegex(p.Stop,'WORK_NOT_EMPTY'):self.invoke(entries=[S(name='retained')])
        for key,value in [('workFolder','_work'),('ephemeral',False),('agentName','other'),
                          ('gitHubUrl','https://github.com/other')]:
            with self.subTest(key=key),self.assertRaisesRegex(p.Stop,'RUNNER_SETTINGS'):
                self.invoke(config=dict(settings(),**{key:value}))

    def test_bounded_settings_no_follow_and_close_on_failure(self):
        raw=json.dumps(settings()).encode()
        st=S(st_mode=0o100600,st_uid=1001,st_nlink=1,st_size=len(raw),st_dev=1,st_ino=2,
             st_mtime_ns=1,st_ctime_ns=1)
        for data in (raw,raw[:-1]):
            with patch.object(p.os,'open',return_value=8) as opened, \
                 patch.object(p.os,'fstat',return_value=st),patch.object(p.os,'read',return_value=data), \
                 patch.object(p.os,'close') as close:
                if data==raw:self.assertEqual(p.read_settings(SESSION/'.runner',1001),settings())
                else:
                    with self.assertRaisesRegex(p.Stop,'SETTINGS_CHANGED'):p.read_settings(SESSION/'.runner',1001)
            self.assertTrue(opened.call_args.args[1] & p.os.O_NOFOLLOW)
            close.assert_called_once_with(8)

    def test_special_settings_file_is_nonblocking_and_rejected_before_read(self):
        fifo=S(st_mode=0o010600,st_uid=1001,st_nlink=1,st_size=1)
        with patch.object(p.os,'open',return_value=8) as opened,patch.object(p.os,'fstat',return_value=fifo), \
             patch.object(p.os,'read') as read,patch.object(p.os,'close') as close, \
             self.assertRaisesRegex(p.Stop,'SETTINGS_OWNER'):
            p.read_settings(SESSION/'.runner',1001)
        flags=opened.call_args.args[1]
        self.assertTrue(flags & p.os.O_NONBLOCK);self.assertTrue(flags & p.os.O_NOCTTY)
        self.assertTrue(flags & p.os.O_NOFOLLOW)
        read.assert_not_called();close.assert_called_once_with(8)

    def test_oversized_or_duplicate_settings_rejected(self):
        st=S(st_mode=0o100600,st_uid=1001,st_nlink=1,st_size=p.LIMIT+1)
        with patch.object(p.os,'open',return_value=8),patch.object(p.os,'fstat',return_value=st), \
             patch.object(p.os,'close'),patch.object(p.os,'read') as read,self.assertRaises(p.Stop):
            p.read_settings(SESSION/'.runner',1001)
        read.assert_not_called()
        raw=b'{"ephemeral":true,"ephemeral":false}'
        st=S(st_mode=0o100600,st_uid=1001,st_nlink=1,st_size=len(raw),st_dev=1,st_ino=2,
             st_mtime_ns=1,st_ctime_ns=1)
        with patch.object(p.os,'open',return_value=8),patch.object(p.os,'fstat',return_value=st), \
             patch.object(p.os,'close'),patch.object(p.os,'read',return_value=raw), \
             self.assertRaisesRegex(p.Stop,'SETTINGS_DUPLICATE'):p.read_settings(SESSION/'.runner',1001)

    def test_original_source_guard_still_rejects_observed_775_and_664_modes(self):
        import run_mint_media_console as caller
        for modes,reason in [([directory(0o775)],'SOURCE_OWNER'),
                ([directory(0o755),directory(0o755),
                  S(st_mode=0o100664,st_uid=1001,st_nlink=1,st_size=3)],'SOURCE_FILE')]:
            opened=[1,2] if reason=='SOURCE_OWNER' else [1,2,3,4]
            with self.subTest(reason=reason),patch.object(caller.os,'getuid',return_value=1001), \
                 patch.object(caller.os,'open',side_effect=opened),patch.object(caller.os,'fstat',side_effect=modes), \
                 patch.object(caller.os,'close'),patch.object(caller.os,'read') as read, \
                 patch.object(caller.os,'fchmod') as chmod,self.assertRaisesRegex(caller.GateError,reason):
                caller.read_source(Path('/checkout'),'tests/file.py')
            read.assert_not_called();chmod.assert_not_called()

    def test_settings_close_uncertainty_is_not_reported_as_success(self):
        with patch.object(p.os,'open',return_value=8),patch.object(p.os,'fstat',side_effect=OSError('synthetic')), \
             patch.object(p.os,'close',side_effect=OSError('synthetic close uncertainty')) as close, \
             self.assertRaisesRegex(p.Stop,'SETTINGS_CLEANUP_UNCERTAIN'):
            p.read_settings(SESSION/'.runner',1001)
        close.assert_called_once_with(8)


class Launch(unittest.TestCase):
    def setUp(self):
        self.stack=[]
        for obj,name,value in [(p.os,'getuid',1001),(p.os,'geteuid',1001),(p.os,'getgid',1001),
                (p.os,'getgroups',[]),(p.pwd,'getpwuid',S(pw_name='sde-runner',pw_dir=str(HOME))),
                (p.grp,'getgrgid',S(gr_name='sde-runner')),(p,'inspect_runner',SESSION)]:
            item=patch.object(obj,name,return_value=value);self.stack.append(item);item.start();self.addCleanup(item.stop)

    def test_private_mask_active_at_exec_and_no_extra_command(self):
        masks=[];at_exec=[]
        def mask(value):
            old=masks[-1] if masks else 0o002;masks.append(value);return old
        def replaced(path,argv,env):
            at_exec.append((masks[-1],path,argv));raise RuntimeError('synthetic exec boundary')
        with patch.object(p.os,'umask',side_effect=mask),patch.object(p.os,'chdir'), \
             patch.object(p.os,'execve',side_effect=replaced),patch.object(p.sys,'argv',['launcher']), \
             patch('sys.stdout',io.StringIO()):self.assertEqual(p.main(),1)
        self.assertEqual(at_exec,[(0o077,str(SESSION/'run.sh'),[str(SESSION/'run.sh')])])
        self.assertEqual(0o777 & ~at_exec[0][0],0o700)
        self.assertEqual(0o666 & ~at_exec[0][0],0o600)
        self.assertEqual(masks,[0o077,0o002])

    def test_failed_preflight_never_executes_and_restores_mask(self):
        with patch.object(p,'inspect_runner',side_effect=p.Stop('WORK_NOT_EMPTY')), \
             patch.object(p.os,'umask',return_value=0o002) as mask,patch.object(p.os,'execve') as execute, \
             patch.object(p.sys,'argv',['launcher']),patch('sys.stdout',io.StringIO()):self.assertEqual(p.main(),1)
        self.assertEqual([x.args[0] for x in mask.call_args_list],[0o077,0o002]);execute.assert_not_called()

    def test_wrong_account_or_cli_stops_before_mask_or_exec(self):
        for argv,uid in [(['launcher','--path=other'],1001),(['launcher'],0)]:
            with patch.object(p.sys,'argv',argv),patch.object(p.os,'getuid',return_value=uid), \
                 patch.object(p.os,'umask') as mask,patch.object(p.os,'execve') as execute, \
                 patch('sys.stdout',io.StringIO()):self.assertEqual(p.main(),1)
            mask.assert_not_called();execute.assert_not_called()

    def test_privileged_group_or_effective_uid_mismatch_stops_before_listener(self):
        cases=[(1001,name) for name in ('root','sudo','admin','docker','lxd','libvirt')]+[(0,'sde-runner')]
        for effective_uid,group in cases:
            with self.subTest(euid=effective_uid,group=group), \
                 patch.object(p.os,'geteuid',return_value=effective_uid), \
                 patch.object(p.grp,'getgrgid',return_value=S(gr_name=group)), \
                 patch.object(p.os,'umask') as mask,patch.object(p.os,'execve') as execute, \
                 patch.object(p.sys,'argv',['launcher']),patch('sys.stdout',io.StringIO()):
                self.assertEqual(p.main(),1)
            mask.assert_not_called();execute.assert_not_called()

    def test_startup_hooks_removed_while_proxy_and_ca_are_preserved(self):
        supplied={name:'synthetic-hook' for name in p.STARTUP_HOOKS}
        supplied.update({'BASH_FUNC_cp%%':'synthetic-function', 'HTTPS_PROXY':'https://proxy.invalid',
                         'SSL_CERT_FILE':'/synthetic/ca.pem', 'PATH':'/usr/bin:/bin'})
        with patch.dict(p.os.environ,supplied,clear=True),patch.object(p.os,'umask',return_value=0o002), \
             patch.object(p.os,'chdir'),patch.object(p.os,'execve',side_effect=OSError('synthetic')) as execute, \
             patch.object(p.sys,'argv',['launcher']),patch('sys.stdout',io.StringIO()):self.assertEqual(p.main(),1)
        self.assertEqual(execute.call_args.args[2],{'HTTPS_PROXY':'https://proxy.invalid',
            'SSL_CERT_FILE':'/synthetic/ca.pem','PATH':'/usr/bin:/bin'})

    def test_failed_mask_restoration_is_sanitized_and_not_retried(self):
        output=io.StringIO()
        with patch.object(p,'inspect_runner',side_effect=p.Stop('WORK_NOT_EMPTY')), \
             patch.object(p.os,'umask',side_effect=[0o002,OSError('synthetic secret text')]) as mask, \
             patch.object(p.os,'execve') as execute,patch.object(p.sys,'argv',['launcher']), \
             patch('sys.stdout',output):self.assertEqual(p.main(),1)
        result=json.loads(output.getvalue())
        self.assertEqual(result['reason'],'UMASK_RESTORE_UNCERTAIN')
        self.assertFalse(result['started']);self.assertFalse(result['retryAuthorized'])
        self.assertEqual(mask.call_count,2);execute.assert_not_called()
        self.assertNotIn('secret',output.getvalue())

    def test_unexpected_exec_return_is_a_failure(self):
        output=io.StringIO()
        with patch.object(p.os,'umask',return_value=0o002),patch.object(p.os,'chdir'), \
             patch.object(p.os,'execve',return_value=None),patch.object(p.sys,'argv',['launcher']), \
             patch('sys.stdout',output):self.assertEqual(p.main(),1)
        self.assertEqual(json.loads(output.getvalue())['reason'],'EXEC_RETURNED')


if __name__=='__main__':unittest.main()
