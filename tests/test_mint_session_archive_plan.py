"""Mocked observations and static checks only; no filesystem/process mutations."""
import ast
import copy
from pathlib import Path
import unittest
from unittest.mock import Mock
import mint_session_archive_plan as p


def directory(uid, mode, ino):
    return dict(kind='directory', uid=uid, mode=mode, device=66306,
                inode=ino, defaultAcl=False)


def observed():
    return dict(schema=1, account='sde-runner', uid=1001, euid=1001, home=p.HOME,
        groups=['kvm', 'sde-runner', 'users'], activationDisabled=True,
        remoteRunnerAbsent=True, noQueuedOrActiveJobs=True,
        dedicatedAccountQuiescent=True, localRegistrationAbsent=True,
        scanComplete=True, scanStable=True, scanSeconds=1,
        archiveAbsent=True, noReplaceRenameAvailable=True, sameFilesystem=True,
        directories={'/':directory(0,'0755',2), '/home':directory(0,'0755',11927553),
            p.HOME:directory(1001,'0750',12064907),
            p.SOURCE:directory(1001,'0700',12088154),
            p.LEGACY:directory(1001,'0700',12345)})


class ArchivePlan(unittest.TestCase):
    def test_healthy_is_only_data_and_preserves_both_evidence_trees(self):
        obs=observed();before=copy.deepcopy(obs);inspect=Mock(return_value=obs)
        plan=p.prepare(inspect)
        inspect.assert_called_once_with();self.assertEqual(obs,before)
        self.assertFalse(plan['executionAuthorized']);self.assertFalse(plan['nativeValidated'])
        self.assertFalse(plan['recursiveChanges'])
        self.assertEqual(plan['preserve'],[p.LEGACY,p.ARCHIVE])
        self.assertEqual([r['op'] for r in plan['operations']],
                         ['rename-no-replace','verify-identity','mkdir-exclusive','mkdir-exclusive'])
        self.assertNotIn(p.LEGACY,str(plan['operations']))
        self.assertEqual(plan['onFailure'],'stop-preserve-state-no-retry-no-rollback')

    def test_each_missing_observation_stops(self):
        for key in observed():
            obs=observed();del obs[key]
            with self.subTest(key=key),self.assertRaises(p.Stop):p.prepare(Mock(return_value=obs))

    def test_false_or_unknown_safety_facts_stop(self):
        for key,value in observed().items():
            if value is not True:continue
            for bad in (False,None,1,'true'):
                obs=observed();obs[key]=bad
                with self.subTest(key=key,bad=bad),self.assertRaises(p.Stop):p.prepare(Mock(return_value=obs))

    def test_account_groups_home_and_deadline_mismatch_stop(self):
        for key,bad in [('uid',0),('euid',0),('account','ryan'),('home','/tmp'),
                        ('groups',['sde-runner','sudo']),('scanSeconds',31),
                        ('scanSeconds',float('nan')),('scanSeconds',float('inf'))]:
            obs=observed();obs[key]=bad
            with self.subTest(key=key,bad=bad),self.assertRaises(p.Stop):p.prepare(Mock(return_value=obs))

    def test_unsafe_or_changed_directory_stops(self):
        for path in observed()['directories']:
            for key,bad in [('kind','symlink'),('uid',999),('mode','0775'),('inode',0)]:
                obs=observed();obs['directories'][path][key]=bad
                with self.subTest(path=path,key=key),self.assertRaises(p.Stop):p.prepare(Mock(return_value=obs))
        for key,bad in [('inode',12088155),('device',7),('defaultAcl',True)]:
            obs=observed();obs['directories'][p.SOURCE][key]=bad
            with self.subTest(key=key),self.assertRaises(p.Stop):p.prepare(Mock(return_value=obs))

    def test_extra_or_missing_paths_stop(self):
        for extra in (False,True):
            obs=observed()
            if extra:obs['directories']['/tmp']=directory(1001,'0700',9)
            else:del obs['directories'][p.LEGACY]
            with self.assertRaises(p.Stop):p.prepare(Mock(return_value=obs))

    def test_inspector_failure_not_retried(self):
        inspect=Mock(side_effect=OSError('synthetic'))
        with self.assertRaises(OSError):p.prepare(inspect)
        inspect.assert_called_once_with()

    def test_no_native_executor_or_cli_exists(self):
        tree=ast.parse(Path(p.__file__).read_text())
        for node in ast.walk(tree):
            self.assertNotIsInstance(node,(ast.Import,ast.ImportFrom))
            if isinstance(node,ast.Call):
                if isinstance(node.func,ast.Attribute):
                    self.assertEqual(node.func.attr,'get')
        self.assertFalse(hasattr(p,'main'))


if __name__=='__main__':unittest.main()
