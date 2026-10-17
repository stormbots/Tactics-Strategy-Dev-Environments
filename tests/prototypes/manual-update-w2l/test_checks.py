"""W2l local checks and saved evidence audits, not extra native schedules."""
from contextlib import redirect_stdout
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import socket
import struct
import tempfile
import unittest
from unittest.mock import Mock, patch

spec=importlib.util.spec_from_file_location('w2l',Path(__file__).with_name('run_experiment.py'))
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)


def fixture(case='L2'):
    peer=dict(pid=100,uids=[1000]*4,gids=[1000]*4)
    data=w.i.frame('action',case,peer['pid']);size=len(data);digest=hashlib.sha256(data).hexdigest()
    flags=int(socket.MSG_CMSG_CLOEXEC | (socket.MSG_CTRUNC if case=='L2' else 0))
    credentials=[] if case=='L2' else [[100,1000,1000]]
    ancillary=[] if case=='L2' else [dict(level=socket.SOL_SOCKET,type=socket.SCM_CREDENTIALS,bytes=12)]
    sender=dict(identity=peer,record_bytes=size,return_value=size,errno=None,requests_sent=1,payload_sha256=digest,attached_fds=[])
    evaluation=dict(received_flags=flags,recvmsg_flags_argument=int(socket.MSG_CMSG_CLOEXEC),payload_capacity=w.i.MAX_RECORD,
                    ancillary_capacity=0 if case=='L2' else w.i.ANCILLARY,received_bytes=size,expected_record_bytes=size,
                    declared_json_bytes=size-4,authorized_actions=0 if case=='L2' else 1,requests_received=1,observation_errors=[],
                    fixture_payload_matches=True,payload_sha256=digest,pidfd_live=True,installed=[],immediately_closed=[],
                    before=[dict(fd=0,dev=1,ino=2)],after=[dict(fd=0,dev=1,ino=2)],raw_credentials=credentials,ancillary=ancillary,
                    decision=dict(accepted=case=='L1',reason='truncated record/control' if case=='L2' else None,
                                  credentials=copy.deepcopy(credentials),flags=flags,record_bytes=size,delivered_fds_closed=0))
    return evaluation,sender


class LocalChecks(unittest.TestCase):
    def test_healthy_control(self):
        e,s=fixture('L1');self.assertEqual(w.verify_evaluation('L1',e,s),'Expected')

    def test_complete_payload_with_ancillary_truncation_is_expected_rejection(self):
        e,s=fixture();self.assertTrue(e['fixture_payload_matches']);self.assertEqual(w.verify_evaluation('L2',e,s),'Expected')

    def test_accepting_matching_payload_without_credentials_is_counterexample(self):
        e,s=fixture();e['decision']['accepted']=True;e['authorized_actions']=1
        self.assertEqual(w.verify_evaluation('L2',e,s),'CounterexampleDetected')

    def test_missing_actual_ctrunc_or_unexpected_payload_truncation_stops(self):
        for flags in (0,int(socket.MSG_TRUNC),int(socket.MSG_CTRUNC|socket.MSG_TRUNC)):
            e,s=fixture();e['received_flags']=flags;e['decision']['flags']=flags
            with self.subTest(flags=flags),self.assertRaises(RuntimeError):w.verify_evaluation('L2',e,s)

    def test_zero_ancillary_and_normal_payload_capacities_required(self):
        for field,value in [('ancillary_capacity',1),('payload_capacity',8)]:
            e,s=fixture();e[field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):w.verify_evaluation('L2',e,s)

    def test_delivered_or_cached_credentials_cannot_pass_zero_capacity_case(self):
        for field,value in [('raw_credentials',[[100,1000,1000]]),('ancillary',[dict(level=1,type=2,bytes=12)])]:
            e,s=fixture();e[field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):w.verify_evaluation('L2',e,s)
        e,s=fixture();e['decision']['credentials']=[[100,1000,1000]]
        with self.assertRaises(RuntimeError):w.verify_evaluation('L2',e,s)

    def test_missing_credentials_reason_alone_is_not_truncation_evidence(self):
        e,s=fixture();e['decision']['reason']='missing/duplicate credentials'
        with self.assertRaisesRegex(RuntimeError,'truncation-specific'):w.verify_evaluation('L2',e,s)

    def test_unchanged_validator_never_uses_complete_payload_as_identity(self):
        e,s=fixture();peer=s['identity'];data=w.i.frame('action','L2',peer['pid'])
        expected=dict(tag='action',attempt='L2',claim_pid=peer['pid'])
        for flags,reason in [(int(socket.MSG_CTRUNC),'truncated record/control'),(0,'missing/duplicate credentials')]:
            d=w.i.validate(data,[],flags,peer,expected,True)
            self.assertFalse(d['accepted']);self.assertEqual(d['reason'],reason);self.assertEqual(d['credentials'],[])

    def test_descriptor_evidence_forbidden(self):
        for field,value in [('installed',[dict(fd=99)]),('immediately_closed',[dict(fd=99)])]:
            e,s=fixture();e[field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):w.verify_evaluation('L2',e,s)
        e,s=fixture();s['attached_fds']=[99]
        with self.assertRaises(RuntimeError):w.verify_evaluation('L2',e,s)

    def test_changed_receiver_inventory_fails(self):
        e,s=fixture();e['after'].append(dict(fd=99,dev=1,ino=3))
        with self.assertRaisesRegex(RuntimeError,'inventory changed'):w.verify_evaluation('L2',e,s)

    def test_duplicate_inventory_fd_fails(self):
        e,s=fixture();e['before']*=2;e['after']=copy.deepcopy(e['before'])
        with self.assertRaises(RuntimeError):w.verify_evaluation('L2',e,s)

    def test_integer_sizes_and_counts_are_required(self):
        for field in ('ancillary_capacity','received_bytes','authorized_actions','requests_received'):
            e,s=fixture();e[field]=float(e[field])
            with self.subTest(field=field),self.assertRaises(RuntimeError):w.verify_evaluation('L2',e,s)

    def test_complete_canonical_payload_and_successful_send_required(self):
        for field,value in [('payload_sha256','wrong'),('return_value',8),('errno',1),('record_bytes',8)]:
            e,s=fixture();s[field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):w.verify_evaluation('L2',e,s)
        e,s=fixture();e['received_bytes']=8
        with self.assertRaises(RuntimeError):w.verify_evaluation('L2',e,s)

    def test_validator_flags_and_length_must_match_receive(self):
        for field,value in [('flags',0),('record_bytes',8),('delivered_fds_closed',1)]:
            e,s=fixture();e['decision'][field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):w.verify_evaluation('L2',e,s)

    def test_sender_submits_only_explicit_credentials_and_no_rights(self):
        peer=dict(pid=100,uids=[1000]*4,gids=[1000]*4);conn=Mock();data=w.i.frame('action','L2',100)
        conn.sendmsg.return_value=len(data)
        with patch.object(w.i,'identity',return_value=peer),patch.object(w.i,'descriptor',return_value={}):r=w.sender_send(conn,'L2')
        conn.sendmsg.assert_called_once_with([data],[(socket.SOL_SOCKET,socket.SCM_CREDENTIALS,struct.pack('3i',100,1000,1000))])
        self.assertEqual(r['attached_fds'],[])

    def test_receiver_calls_guard_with_actual_flags_and_empty_ancillary(self):
        peer=dict(pid=100,uids=[1000]*4,gids=[1000]*4);data=w.i.frame('action','L2',100);flags=int(socket.MSG_CTRUNC)
        conn=Mock();conn.recvmsg.return_value=(data,[],flags,None)
        with patch.object(w,'fd_inventory',return_value=[]),patch.object(w.i,'live',return_value=True),patch.object(w.i,'descriptor',return_value={}),patch.object(w.i,'validate',wraps=w.i.validate) as validate:
            result=w.observe_receive(conn,peer,99,'L2')
        conn.recvmsg.assert_called_once_with(w.i.MAX_RECORD,0,socket.MSG_CMSG_CLOEXEC)
        validate.assert_called_once_with(data,[],flags,peer,dict(tag='action',attempt='L2',claim_pid=100),True)
        self.assertFalse(result['decision']['accepted']);self.assertEqual(result['raw_credentials'],[])

    def test_failed_healthy_is_not_a_security_counterexample(self):
        e,s=fixture('L1');e['authorized_actions']=0;e['decision']['accepted']=False
        with self.assertRaisesRegex(RuntimeError,'failed healthy'):w.verify_evaluation('L1',e,s)

    def test_failed_healthy_stops_dependent_native_case(self):
        with tempfile.TemporaryDirectory() as root:
            out=Path(root)/'result.json'
            # Entire actor run is mocked: no native process/socket experiment.
            with patch.object(w,'fd_inventory',return_value=[]),patch.object(w.i,'subreaper',return_value=0),patch.object(w,'run_case',return_value=dict(case='L1',result='Fail',failures=['synthetic healthy failure'])) as run,redirect_stdout(io.StringIO()):
                self.assertEqual(w.main(out),1)
            run.assert_called_once_with('L1');self.assertFalse(json.loads(out.read_text())['diagnostic_success'])


class EvidenceChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=json.loads(Path(__file__).with_name('evidence').joinpath('linux-run.json').read_text())
    def ev(self,c,name):return next(t['evidence'] for t in c['trace'] if t['barrier']==name)

    def test_source_hashes_and_result_scope(self):
        self.assertEqual(self.report['source_sha256'],hashlib.sha256(w.SCRIPT.read_bytes()).hexdigest())
        self.assertEqual(self.report['helper_sha256'],hashlib.sha256(w.HELPER.read_bytes()).hexdigest())
        self.assertTrue(self.report['diagnostic_success']);self.assertEqual(self.report['authentication_safety'],'Unproven');self.assertFalse(self.report['production_readiness'])

    def test_native_cases_have_expected_counts_and_full_payload(self):
        self.assertEqual([c['case'] for c in self.report['cases']],['L1','L2'])
        self.assertEqual([c['action_count'] for c in self.report['cases']],[1,0])
        for c in self.report['cases']:
            self.assertTrue(w.verify_case_evidence(c))
            e=self.ev(c,'kernel-receive-and-truncation-check');s=self.ev(c,'action-send-permitted')
            self.assertEqual(e['received_bytes'],s['return_value']);self.assertEqual(e['payload_sha256'],s['payload_sha256'])
            self.assertEqual(s['attached_fds'],[])
        e=self.ev(self.report['cases'][1],'kernel-receive-and-truncation-check')
        self.assertTrue(e['received_flags']&socket.MSG_CTRUNC);self.assertFalse(e['received_flags']&socket.MSG_TRUNC)
        self.assertEqual(e['ancillary'],[]);self.assertEqual(e['raw_credentials'],[])

    def test_owned_cleanup_and_unchanged_settings(self):
        self.assertEqual(self.report['runner_before'],self.report['runner_after']);self.assertFalse(self.report['finalization_failures'])
        for c in self.report['cases']:
            self.assertFalse(c['failures']);self.assertTrue(c['cleanup']['root_removed']);self.assertFalse(Path(c['fixture']['root']).exists())
            self.assertEqual(len(c['cleanup']['actors']),2)
            self.assertTrue(all(a['reaped'] and a['exit_code']==0 and not a['forced'] for a in c['cleanup']['actors']))

    def test_corrupted_readiness_enrollment_and_post_observation_order_rejected(self):
        for kind in ('options','enrollment','ordering'):
            c=copy.deepcopy(self.report['cases'][1])
            if kind=='options':self.ev(c,'accepted-passcred-verified')['descriptor']['passcred']=0
            elif kind=='enrollment':self.ev(c,'trusted-client-enrollment')['enrolled']['pid']+=1
            else:
                last=next(n for n,t in enumerate(c['trace']) if t['barrier'].startswith('runner-instance-after-'))
                first=next(n for n,t in enumerate(c['trace']) if t['barrier']=='receiver-before-send')
                times=sorted(t['at'] for t in c['trace']);record=c['trace'].pop(last);c['trace'].insert(first,record)
                for n,t in enumerate(c['trace']):t.update(index=n,at=times[n])
            with self.subTest(kind=kind),self.assertRaises(RuntimeError):w.verify_case_evidence(c)


if __name__=='__main__':unittest.main(verbosity=2)
