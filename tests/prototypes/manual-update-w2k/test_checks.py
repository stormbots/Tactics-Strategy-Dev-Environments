"""W2k local evidence/ordering tests only, not additional native schedules."""
import copy
import errno
import fcntl
import importlib.util
import hashlib
import json
from pathlib import Path
import socket
import stat
import unittest
from unittest.mock import Mock, patch

spec=importlib.util.spec_from_file_location('w2k',Path(__file__).with_name('run_experiment.py'))
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)


def fixture(case='K2'):
    original=dict(pid=100,uids=[1000]*4,gids=[1000]*4)
    pipe=dict(fd=9,dev=1,ino=22,mode=stat.S_IFIFO|0o600,fdflags=fcntl.FD_CLOEXEC,flags=0)
    installed=dict(pipe,fd=10)
    complete=w.i.frame('action',case,original['pid']);record_size=len(complete)
    full_hash=hashlib.sha256(complete).hexdigest();prefix_hash=hashlib.sha256(complete[:8]).hexdigest()
    sender=dict(identity=original,attached_fds=[9] if case=='K2' else [],sent_pipe=pipe,payload_sha256=full_hash,payload_prefix_sha256=prefix_hash,record_bytes=record_size)
    evaluation=dict(authorized_actions=0 if case=='K2' else 1,requests_received=1,observation_errors=[],received_flags=int(socket.MSG_TRUNC) if case=='K2' else 0,
                    payload_capacity=8 if case=='K2' else w.i.MAX_RECORD,received_bytes=8 if case=='K2' else record_size,
                    ancillary_capacity=w.i.ANCILLARY,expected_record_bytes=record_size,declared_json_bytes=record_size-4,prefix_matches=True,
                    recvmsg_flags_argument=int(socket.MSG_CMSG_CLOEXEC),raw_credentials=[[100,1000,1000]],pidfd_live=True,
                    fixture_payload_matches=case=='K1',payload_sha256=prefix_hash if case=='K2' else full_hash,before=[dict(fd=0,dev=1)],after=[dict(fd=0,dev=1)],
                    ancillary=[dict(level=socket.SOL_SOCKET,type=socket.SCM_CREDENTIALS,bytes=12)]+([dict(level=socket.SOL_SOCKET,type=socket.SCM_RIGHTS,bytes=4)] if case=='K2' else []),
                    decision=dict(flags=int(socket.MSG_TRUNC) if case=='K2' else 0,record_bytes=8 if case=='K2' else record_size,accepted=case=='K1',reason='truncated record/control' if case=='K2' else None,delivered_fds_closed=1 if case=='K2' else 0),
                    installed=[installed] if case=='K2' else [],immediately_closed=[dict(fd=10,fstat_errno=errno.EBADF,getfd_errno=errno.EBADF)] if case=='K2' else [])
    return evaluation,sender


class LocalChecks(unittest.TestCase):
    def test_healthy_control(self):
        e,s=fixture('K1');self.assertEqual(w.verify_evaluation('K1',e,s),'Expected')

    def test_payload_truncation_rejection(self):
        e,s=fixture();self.assertEqual(w.verify_evaluation('K2',e,s),'Expected')

    def test_unexpected_acceptance_is_counterexample(self):
        e,s=fixture();e['authorized_actions']=1;e['decision']['accepted']=True
        self.assertEqual(w.verify_evaluation('K2',e,s),'CounterexampleDetected')

    def test_missing_payload_flag_or_ancillary_truncation_stops(self):
        # Synthetic flags only; no ancillary-truncation native schedule.
        for flags in (0,socket.MSG_CTRUNC,socket.MSG_TRUNC|socket.MSG_CTRUNC):
            e,s=fixture();e['received_flags']=flags
            with self.subTest(flags=flags),self.assertRaises(RuntimeError):w.verify_evaluation('K2',e,s)

    def test_wrong_eight_byte_receive_or_ancillary_capacity_stops(self):
        for name,value in [('payload_capacity',9),('received_bytes',7),('ancillary_capacity',1),('declared_json_bytes',999),('prefix_matches',False),('payload_sha256','wrong')]:
            e,s=fixture();e[name]=value
            with self.subTest(field=name),self.assertRaises(RuntimeError):w.verify_evaluation('K2',e,s)

    def test_incomplete_or_different_sender_fixture_is_rejected(self):
        for field,value in [('record_bytes',8),('payload_sha256','wrong'),('payload_prefix_sha256','wrong')]:
            e,s=fixture();s[field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):w.verify_evaluation('K2',e,s)

    def test_ancillary_rejection_alone_is_not_truncation_proof(self):
        e,s=fixture();e['decision']['reason']='unexpected ancillary/descriptor'
        with self.assertRaisesRegex(RuntimeError,'wrong descriptor rejection'):w.verify_evaluation('K2',e,s)

    def test_failed_healthy_is_not_counterexample(self):
        e,s=fixture('K1');e['authorized_actions']=0;e['decision']['accepted']=False
        with self.assertRaisesRegex(RuntimeError,'failed healthy'):w.verify_evaluation('K1',e,s)

    def test_boolean_counts_rejected(self):
        for name in ('authorized_actions','requests_received'):
            e,s=fixture();e[name]=False
            with self.subTest(field=name),self.assertRaisesRegex(RuntimeError,'invalid'):w.verify_evaluation('K2',e,s)

    def test_wrong_kernel_credentials_rejected(self):
        e,s=fixture();e['raw_credentials']=[[200,1000,1000]]
        with self.assertRaisesRegex(RuntimeError,'credentials'):w.verify_evaluation('K2',e,s)

    def test_no_cloexec_rejected(self):
        e,s=fixture();e['installed'][0]['fdflags']=0
        with self.assertRaisesRegex(RuntimeError,'CLOEXEC'):w.verify_evaluation('K2',e,s)

    def test_closure_must_be_observed_by_both_immediate_checks(self):
        for name in ('fstat_errno','getfd_errno'):
            e,s=fixture();e['immediately_closed'][0][name]=None
            with self.subTest(check=name),self.assertRaisesRegex(RuntimeError,'still open'):w.verify_evaluation('K2',e,s)

    def test_inventory_change_rejected(self):
        e,s=fixture();e['after'].append(dict(fd=99,dev=1))
        with self.assertRaisesRegex(RuntimeError,'inventory changed'):w.verify_evaluation('K2',e,s)

    def test_pipe_identity_and_baseline_fd_collision_rejected(self):
        for field in ('dev','ino','mode','flags','fd'):
            e,s=fixture()
            if field=='fd':e['before'].append(dict(fd=10));e['after']=copy.deepcopy(e['before'])
            else:e['installed'][0][field]+=1
            with self.subTest(field=field),self.assertRaises(RuntimeError):w.verify_evaluation('K2',e,s)

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
            w.observe_receive(conn,s['identity'],123,'K2')
        self.assertEqual(order,['inventory','validate','closed','inventory'])
        conn.recvmsg.assert_called_once_with(w.TRUNCATED_PAYLOAD_BYTES,w.i.ANCILLARY,socket.MSG_CMSG_CLOEXEC)

    def test_observation_failure_still_runs_unchanged_cleanup(self):
        conn=Mock();conn.recvmsg.return_value=(b'data',[],0,None)
        with patch.object(w,'fd_inventory',return_value=[]),patch.object(w,'rights_from',return_value=[99]),patch.object(w,'fd_info',side_effect=OSError('metadata failure')),patch.object(w.i,'validate',return_value=dict(accepted=False)) as validate,patch.object(w,'immediately_closed',return_value={}),patch.object(w.i,'live',return_value=True),patch.object(w.i,'descriptor',return_value={}):
            result=w.observe_receive(conn,dict(pid=100),123,'K2')
        validate.assert_called_once();self.assertEqual(len(result['observation_errors']),1)


class NativeEvidenceChecks(unittest.TestCase):
    """Audit saved results without running native actors."""
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).with_name('evidence');path=root/'reviewed-linux-run.json'
        cls.report=json.loads((path if path.exists() else root/'linux-run.json').read_text())

    def event(self,c,name):return next(e['evidence'] for e in c['trace'] if e['barrier']==name)

    def test_source_hashes_and_result_scope(self):
        import hashlib
        self.assertEqual(self.report['source_sha256'],hashlib.sha256(w.SCRIPT.read_bytes()).hexdigest())
        self.assertEqual(self.report['helper_sha256'],hashlib.sha256(w.HELPER.read_bytes()).hexdigest())
        self.assertTrue(self.report['diagnostic_success']);self.assertEqual(self.report['authentication_safety'],'Unproven');self.assertFalse(self.report['production_readiness'])

    def test_actual_payload_truncation_installed_fd_and_sender_validity(self):
        c=self.report['cases'][1];sent=self.event(c,'action-send-permitted');evaluated=self.event(c,'kernel-receive-validation-and-immediate-close')
        self.assertEqual(w.verify_evaluation('K2',evaluated,sent),'Expected')
        self.assertEqual(self.event(c,'sender-before')['pipe'],self.event(c,'sender-after')['pipe'])
        self.assertEqual(evaluated['decision']['delivered_fds_closed'],1)
        self.assertTrue(evaluated['received_flags'] & socket.MSG_TRUNC)
        self.assertFalse(evaluated['received_flags'] & socket.MSG_CTRUNC)
        self.assertEqual(evaluated['received_bytes'],8)
        self.assertGreater(sent['return_value'],8)

    def test_counts_and_both_credential_directions(self):
        self.assertEqual([c['case'] for c in self.report['cases']],['K1','K2'])
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
            self.assertTrue(w.verify_case_evidence(c))
            self.assertFalse(c['failures']);self.assertTrue(c['cleanup']['root_removed'])
            self.assertFalse(Path(c['fixture']['root']).exists())
            self.assertEqual(len(c['cleanup']['actors']),2)
            self.assertTrue(all(a['reaped'] and a['exit_code']==0 and not a['forced'] for a in c['cleanup']['actors']))
            names=[t['barrier'] for t in c['trace']]
            self.assertLess(names.index('accepted-passcred-verified'),names.index('hello-send-permitted'))
            self.assertLess(names.index('sender-before'),names.index('action-send-permitted'))
            self.assertLess(names.index('action-send-permitted'),names.index('kernel-receive-validation-and-immediate-close'))
            self.assertLess(names.index('kernel-receive-validation-and-immediate-close'),names.index('sender-after'))


class EvidenceIntegrityChecks(unittest.TestCase):
    """Synthetic/mocked audit checks only; no ancillary-truncation or extra native cases."""
    def test_inventory_missing_baseline_fd_is_not_silently_ignored(self):
        from types import SimpleNamespace
        scan=Mock();scan.__enter__=Mock(return_value=iter([SimpleNamespace(name='0'),SimpleNamespace(name='99')]))
        scan.__exit__=Mock(return_value=False)
        with patch.object(w.os,'scandir',return_value=scan),patch.object(w.os,'stat',return_value=SimpleNamespace(st_dev=10,st_ino=20)),patch.object(w.os,'listdir',return_value=['0','99']),patch.object(w,'fd_info',side_effect=[dict(fd=0,dev=1,ino=2,mode=stat.S_IFCHR),OSError(errno.EBADF,'missing baseline')]):
            with self.assertRaises(OSError):w.fd_inventory()

    def test_inventory_excludes_only_observed_live_directory(self):
        from types import SimpleNamespace
        directory=dict(fd=7,dev=10,ino=20,mode=stat.S_IFDIR)
        baseline=dict(fd=0,dev=1,ino=2,mode=stat.S_IFCHR)
        scan=Mock();scan.__enter__=Mock(return_value=iter([SimpleNamespace(name='0'),SimpleNamespace(name='7')]))
        scan.__exit__=Mock(return_value=False)
        with patch.object(w.os,'scandir',return_value=scan),patch.object(w.os,'stat',return_value=SimpleNamespace(st_dev=10,st_ino=20)),patch.object(w.os,'listdir',return_value=['0','7']),patch.object(w,'fd_info',side_effect=[baseline,directory]):
            self.assertEqual(w.fd_inventory(),[baseline])

    def test_unknown_duplicate_wrong_size_ancillary_rejected(self):
        for corruption in ('extra','duplicate','size','missing'):
            e,s=fixture()
            if corruption=='extra':e['ancillary'].append(dict(level=999,type=999,bytes=4))
            elif corruption=='duplicate':e['ancillary'].append(copy.deepcopy(e['ancillary'][0]))
            elif corruption=='size':e['ancillary'][1]['bytes']=8
            else:e['ancillary']=e['ancillary'][:1]
            with self.subTest(corruption=corruption),self.assertRaisesRegex(RuntimeError,'ancillary'):w.verify_evaluation('K2',e,s)

    def test_boolean_closed_count_rejected(self):
        e,s=fixture();e['decision']['delivered_fds_closed']=True
        with self.assertRaisesRegex(RuntimeError,'closed-FD count'):w.verify_evaluation('K2',e,s)

    def case(self):
        root=Path(__file__).with_name('evidence');path=root/'reviewed-linux-run.json'
        return copy.deepcopy(json.loads((path if path.exists() else root/'linux-run.json').read_text())['cases'][1])

    def test_guard_and_identity_evidence_corruption_rejected(self):
        for corruption in ('option','enrollment','hello','namespace','explicit','counter','endpoint','pipe'):
            c=self.case()
            def ev(name):return next(t['evidence'] for t in c['trace'] if t['barrier']==name)
            if corruption=='option':ev('client-ready-before-connect')['descriptor']['passcred']=0
            elif corruption=='enrollment':ev('trusted-client-enrollment')['enrolled']['pid']+=1
            elif corruption=='hello':ev('server-reply-verified')['credentials'][0][0]+=1
            elif corruption=='namespace':ev('client-ready-before-connect')['identity']['namespaces']['user']='foreign'
            elif corruption=='explicit':ev('action-send-permitted')['requested_credentials']=None
            elif corruption=='counter':ev('sender-after')['requests_sent']=False
            elif corruption=='endpoint':ev('sender-after')['descriptor']['device']+=1
            else:ev('owned-pipe-created')['pipe'][1]['flags']=0
            with self.subTest(corruption=corruption),self.assertRaises(RuntimeError):w.verify_case_evidence(c)

    def test_trace_reordering_and_duplicate_barriers_rejected(self):
        for duplicate in (False,True):
            c=self.case()
            if duplicate:c['trace'].append(copy.deepcopy(c['trace'][0]))
            else:
                first=next(n for n,t in enumerate(c['trace']) if t['barrier']=='action-send-permitted')
                second=next(n for n,t in enumerate(c['trace']) if t['barrier']=='sender-after')
                times=sorted(t['at'] for t in c['trace'])
                c['trace'][first],c['trace'][second]=c['trace'][second],c['trace'][first]
                for n,t in enumerate(c['trace']):t.update(index=n,at=times[n])
            with self.subTest(duplicate=duplicate),self.assertRaises(RuntimeError):w.verify_case_evidence(c)

    def test_duplicate_inventory_fd_rejected(self):
        e,s=fixture();e['before']*=2;e['after']=copy.deepcopy(e['before'])
        with self.assertRaisesRegex(RuntimeError,'duplicate inventory'):w.verify_evaluation('K2',e,s)


class W2kReviewChecks(unittest.TestCase):
    """Corrupted local evidence only; no new native fault/ancillary schedules."""
    def case(self):
        root=Path(__file__).with_name('evidence');p=root/'reviewed-linux-run.json'
        return copy.deepcopy(json.loads((p if p.exists() else root/'linux-run.json').read_text())['cases'][1])

    def test_float_receive_sizes_and_flags_rejected(self):
        for field in ('payload_capacity','ancillary_capacity','received_bytes','expected_record_bytes','declared_json_bytes','recvmsg_flags_argument'):
            e,s=fixture();e[field]=float(e[field])
            with self.subTest(field=field),self.assertRaises(RuntimeError):w.verify_evaluation('K2',e,s)
        e,s=fixture();s['record_bytes']=float(s['record_bytes'])
        with self.assertRaises(RuntimeError):w.verify_evaluation('K2',e,s)

    def test_validator_must_see_actual_flags_and_length(self):
        for field,value in [('flags',0),('record_bytes',53)]:
            e,s=fixture();e['decision'][field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):w.verify_evaluation('K2',e,s)

    def test_post_liveness_observation_cannot_precede_evaluation(self):
        c=self.case()
        after=next(n for n,t in enumerate(c['trace']) if t['barrier'].startswith('runner-instance-after-'))
        before=next(n for n,t in enumerate(c['trace']) if t['barrier']=='receiver-before-send')
        times=sorted(t['at'] for t in c['trace'])
        record=c['trace'].pop(after)
        c['trace'].insert(before,record)
        for n,t in enumerate(c['trace']):t.update(index=n,at=times[n])
        with self.assertRaises(RuntimeError):w.verify_case_evidence(c)

    def test_receiver_counter_baseline_must_be_zero(self):
        for field in ('authorized_actions','requests_received'):
            c=self.case();record=next(t['evidence'] for t in c['trace'] if t['barrier']=='receiver-before-send');record[field]=1
            with self.subTest(field=field),self.assertRaises(RuntimeError):w.verify_case_evidence(c)

    def test_receiver_endpoint_must_match_accepted_socket_and_inventory(self):
        for corruption in ('descriptor','inventory'):
            c=self.case();e=next(t['evidence'] for t in c['trace'] if t['barrier']=='kernel-receive-validation-and-immediate-close')
            if corruption=='descriptor':e['descriptor']['inode']+=1
            else:
                target=e['descriptor']['fd']
                for inventory in (e['before'],e['after']):
                    next(fd for fd in inventory if fd['fd']==target)['ino']+=1
            with self.subTest(corruption=corruption),self.assertRaises(RuntimeError):w.verify_case_evidence(c)


if __name__=='__main__':unittest.main(verbosity=2)
