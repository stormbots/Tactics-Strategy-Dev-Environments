"""W2j local evidence/ordering tests only, not additional native schedules."""
import copy
import errno
import fcntl
import importlib.util
import json
from pathlib import Path
import socket
import stat
import unittest
from unittest.mock import Mock, patch

spec=importlib.util.spec_from_file_location('w2j',Path(__file__).with_name('run_experiment.py'))
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)


def fixture(case='J2'):
    original=dict(pid=100,uids=[1000]*4,gids=[1000]*4)
    pipe=dict(fd=9,dev=1,ino=22,mode=stat.S_IFIFO|0o600,fdflags=fcntl.FD_CLOEXEC,flags=0)
    installed=dict(pipe,fd=10)
    sender=dict(identity=original,attached_fds=[9] if case=='J2' else [],sent_pipe=pipe,payload_sha256='dummy')
    evaluation=dict(authorized_actions=0 if case=='J2' else 1,requests_received=1,observation_errors=[],received_flags=0,
                    recvmsg_flags_argument=socket.MSG_CMSG_CLOEXEC,raw_credentials=[[100,1000,1000]],pidfd_live=True,
                    fixture_payload_matches=True,payload_sha256='dummy',before=[dict(fd=0,dev=1)],after=[dict(fd=0,dev=1)],
                    decision=dict(accepted=case=='J1',reason='unexpected ancillary/descriptor' if case=='J2' else None,delivered_fds_closed=1 if case=='J2' else 0),
                    installed=[installed] if case=='J2' else [],immediately_closed=[dict(fd=10,fstat_errno=errno.EBADF,getfd_errno=errno.EBADF)] if case=='J2' else [])
    return evaluation,sender


class LocalChecks(unittest.TestCase):
    def test_healthy_control(self):
        e,s=fixture('J1');self.assertEqual(w.verify_evaluation('J1',e,s),'Expected')

    def test_descriptor_rejection(self):
        e,s=fixture();self.assertEqual(w.verify_evaluation('J2',e,s),'Expected')

    def test_unexpected_acceptance_is_counterexample(self):
        e,s=fixture();e['authorized_actions']=1;e['decision']['accepted']=True
        self.assertEqual(w.verify_evaluation('J2',e,s),'CounterexampleDetected')

    def test_failed_healthy_is_not_counterexample(self):
        e,s=fixture('J1');e['authorized_actions']=0;e['decision']['accepted']=False
        with self.assertRaisesRegex(RuntimeError,'failed healthy'):w.verify_evaluation('J1',e,s)

    def test_boolean_counts_rejected(self):
        for name in ('authorized_actions','requests_received'):
            e,s=fixture();e[name]=False
            with self.subTest(field=name),self.assertRaisesRegex(RuntimeError,'invalid'):w.verify_evaluation('J2',e,s)

    def test_wrong_kernel_credentials_rejected(self):
        e,s=fixture();e['raw_credentials']=[[200,1000,1000]]
        with self.assertRaisesRegex(RuntimeError,'credentials'):w.verify_evaluation('J2',e,s)

    def test_no_cloexec_rejected(self):
        e,s=fixture();e['installed'][0]['fdflags']=0
        with self.assertRaisesRegex(RuntimeError,'CLOEXEC'):w.verify_evaluation('J2',e,s)

    def test_closure_must_be_observed_by_both_immediate_checks(self):
        for name in ('fstat_errno','getfd_errno'):
            e,s=fixture();e['immediately_closed'][0][name]=None
            with self.subTest(check=name),self.assertRaisesRegex(RuntimeError,'still open'):w.verify_evaluation('J2',e,s)

    def test_inventory_change_rejected(self):
        e,s=fixture();e['after'].append(dict(fd=99,dev=1))
        with self.assertRaisesRegex(RuntimeError,'inventory changed'):w.verify_evaluation('J2',e,s)

    def test_pipe_identity_and_baseline_fd_collision_rejected(self):
        for field in ('dev','ino','mode','flags','fd'):
            e,s=fixture()
            if field=='fd':e['before'].append(dict(fd=10));e['after']=copy.deepcopy(e['before'])
            else:e['installed'][0][field]+=1
            with self.subTest(field=field),self.assertRaises(RuntimeError):w.verify_evaluation('J2',e,s)

    def test_closure_probe_uses_no_fd_allocating_inventory(self):
        with patch.object(w.os,'fstat',side_effect=OSError(errno.EBADF,'closed')),patch.object(w.fcntl,'fcntl',side_effect=OSError(errno.EBADF,'closed')),patch.object(w,'fd_inventory') as inventory:
            r=w.immediately_closed(99)
        inventory.assert_not_called();self.assertEqual(r['fstat_errno'],errno.EBADF);self.assertEqual(r['getfd_errno'],errno.EBADF)

    def test_receive_closure_precedes_after_inventory(self):
        e,s=fixture();conn=Mock();conn.recvmsg.return_value=(b'data',[],0,None)
        order=[]
        def inventory():order.append('inventory');return []
        def validate(*args):order.append('validate');return dict(accepted=False)
        def closed(fd):order.append('closed');return dict(fd=fd)
        with patch.object(w,'fd_inventory',side_effect=inventory),patch.object(w,'rights_from',return_value=[99]),patch.object(w,'fd_info',return_value={}),patch.object(w.i,'validate',side_effect=validate),patch.object(w,'immediately_closed',side_effect=closed),patch.object(w.i,'live',return_value=True),patch.object(w.i,'descriptor',return_value={}):
            w.observe_receive(conn,s['identity'],123,'J2')
        self.assertEqual(order,['inventory','validate','closed','inventory'])
        conn.recvmsg.assert_called_once_with(w.i.MAX_RECORD,w.i.ANCILLARY,socket.MSG_CMSG_CLOEXEC)

    def test_observation_failure_still_runs_unchanged_cleanup(self):
        conn=Mock();conn.recvmsg.return_value=(b'data',[],0,None)
        with patch.object(w,'fd_inventory',return_value=[]),patch.object(w,'rights_from',return_value=[99]),patch.object(w,'fd_info',side_effect=OSError('metadata failure')),patch.object(w.i,'validate',return_value=dict(accepted=False)) as validate,patch.object(w,'immediately_closed',return_value={}),patch.object(w.i,'live',return_value=True),patch.object(w.i,'descriptor',return_value={}):
            result=w.observe_receive(conn,dict(pid=100),123,'J2')
        validate.assert_called_once();self.assertEqual(len(result['observation_errors']),1)


class NativeEvidenceChecks(unittest.TestCase):
    """Audit saved results without running native actors."""
    @classmethod
    def setUpClass(cls):
        cls.report=json.loads(Path(__file__).with_name('evidence').joinpath('linux-run.json').read_text())

    def event(self,c,name):return next(e['evidence'] for e in c['trace'] if e['barrier']==name)

    def test_source_hashes_and_result_scope(self):
        import hashlib
        self.assertEqual(self.report['source_sha256'],hashlib.sha256(w.SCRIPT.read_bytes()).hexdigest())
        self.assertEqual(self.report['helper_sha256'],hashlib.sha256(w.HELPER.read_bytes()).hexdigest())
        self.assertTrue(self.report['diagnostic_success']);self.assertEqual(self.report['authentication_safety'],'Unproven');self.assertFalse(self.report['production_readiness'])

    def test_actual_installed_fd_and_sender_validity(self):
        c=self.report['cases'][1];sent=self.event(c,'action-send-permitted');evaluated=self.event(c,'kernel-receive-validation-and-immediate-close')
        self.assertEqual(w.verify_evaluation('J2',evaluated,sent),'Expected')
        self.assertEqual(self.event(c,'sender-before')['pipe'],self.event(c,'sender-after')['pipe'])
        self.assertEqual(evaluated['decision']['delivered_fds_closed'],1)

    def test_counts_and_both_credential_directions(self):
        self.assertEqual([c['case'] for c in self.report['cases']],['J1','J2'])
        self.assertEqual([c['action_count'] for c in self.report['cases']],[1,0])
        for c in self.report['cases']:
            self.assertTrue(self.event(c,'client-credentials-and-server-reply')['verification']['accepted'])
            self.assertTrue(self.event(c,'server-reply-verified')['accepted'])
            sent=self.event(c,'action-send-permitted')
            self.assertEqual(sent['return_value'],sent['record_bytes']);self.assertIsNone(sent['errno'])

    def test_owned_cleanup_and_barriers(self):
        self.assertEqual(self.report['runner_before'],self.report['runner_after'])
        self.assertFalse(self.report['finalization_failures'])
        for c in self.report['cases']:
            self.assertFalse(c['failures']);self.assertTrue(c['cleanup']['root_removed'])
            self.assertFalse(Path(c['fixture']['root']).exists())
            self.assertEqual(len(c['cleanup']['actors']),2)
            self.assertTrue(all(a['reaped'] and a['exit_code']==0 and not a['forced'] for a in c['cleanup']['actors']))
            names=[t['barrier'] for t in c['trace']]
            self.assertLess(names.index('accepted-passcred-verified'),names.index('hello-send-permitted'))
            self.assertLess(names.index('sender-before'),names.index('action-send-permitted'))
            self.assertLess(names.index('action-send-permitted'),names.index('kernel-receive-validation-and-immediate-close'))
            self.assertLess(names.index('kernel-receive-validation-and-immediate-close'),names.index('sender-after'))


if __name__=='__main__':unittest.main(verbosity=2)
