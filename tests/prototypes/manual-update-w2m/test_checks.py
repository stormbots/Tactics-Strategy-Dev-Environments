"""W2m only: synthetic/mocked checks and saved-native evidence audits."""
from contextlib import redirect_stdout
import array
import copy
import errno
import fcntl
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import stat
import struct
import tempfile
import unittest
from unittest.mock import Mock, patch

spec=importlib.util.spec_from_file_location('w2m',Path(__file__).with_name('run_experiment.py'))
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)


def fixture(case='M2'):
    peer=dict(pid=100,uids=[1000]*4,gids=[1000]*4)
    pipe=[dict(fd=8,dev=1,ino=22,mode=stat.S_IFIFO|0o600,fdflags=fcntl.FD_CLOEXEC,flags=os.O_RDONLY),
          dict(fd=9,dev=1,ino=22,mode=stat.S_IFIFO|0o600,fdflags=fcntl.FD_CLOEXEC,flags=os.O_WRONLY)] if case=='M2' else []
    data=w.i.frame('action',case,100);n=len(data);digest=hashlib.sha256(data).hexdigest()
    flags=int(socket.MSG_CMSG_CLOEXEC | (socket.MSG_CTRUNC if case=='M2' else 0))
    sender=dict(identity=peer,record_bytes=n,return_value=n,errno=None,requests_sent=1,payload_sha256=digest,
                attached_fds=[p['fd'] for p in pipe],sent_pipe=pipe)
    credentials=[[100,1000,1000]]
    evaluation=dict(received_flags=flags,recvmsg_flags_argument=int(socket.MSG_CMSG_CLOEXEC),payload_capacity=w.i.MAX_RECORD,
        ancillary_capacity=w.partial_capacity() if case=='M2' else w.i.ANCILLARY,received_bytes=n,expected_record_bytes=n,
        declared_json_bytes=n-4,authorized_actions=0 if case=='M2' else 1,requests_received=1,observation_errors=[],
        fixture_payload_matches=True,payload_sha256=digest,pidfd_live=True,
        installed=[dict(pipe[0],fd=10)] if pipe else [],
        immediately_closed=[dict(fd=10,fstat_errno=errno.EBADF,getfd_errno=errno.EBADF)] if pipe else [],
        before=[dict(fd=0,dev=1,ino=2)],after=[dict(fd=0,dev=1,ino=2)],raw_credentials=credentials,
        ancillary=[dict(level=socket.SOL_SOCKET,type=socket.SCM_CREDENTIALS,bytes=12)]+([dict(level=socket.SOL_SOCKET,type=socket.SCM_RIGHTS,bytes=array.array('i').itemsize)] if pipe else []),
        decision=dict(accepted=case=='M1',reason=None if case=='M1' else 'truncated record/control',credentials=credentials if case=='M1' else [],
                      flags=flags,record_bytes=n,delivered_fds_closed=1 if pipe else 0))
    return evaluation,sender


class LocalChecks(unittest.TestCase):
    def test_healthy(self):
        e,s=fixture('M1');self.assertEqual(w.verify_evaluation('M1',e,s),'Expected')
    def test_partial_delivery(self):
        e,s=fixture();self.assertEqual(w.verify_evaluation('M2',e,s),'Expected')
    def test_fixed_capacity_formula(self):
        self.assertEqual(w.partial_capacity(),socket.CMSG_SPACE(struct.calcsize('3i'))+socket.CMSG_LEN(array.array('i').itemsize))
    def test_missing_ctrunc_or_payload_truncation_stops(self):
        for flags in (0,int(socket.MSG_TRUNC),int(socket.MSG_CTRUNC|socket.MSG_TRUNC)):
            e,s=fixture();e['received_flags']=e['decision']['flags']=flags
            with self.subTest(flags=flags),self.assertRaises(RuntimeError):w.verify_evaluation('M2',e,s)
    def test_capacities_cannot_be_tuned(self):
        for field in ('payload_capacity','ancillary_capacity'):
            e,s=fixture();e[field]+=1
            with self.subTest(field=field),self.assertRaises(RuntimeError):w.verify_evaluation('M2',e,s)
    def test_zero_or_two_installed_descriptors_not_pass(self):
        for count in (0,2):
            e,s=fixture();e['installed']*=count;e['immediately_closed']*=count;e['decision']['delivered_fds_closed']=count
            with self.subTest(count=count),self.assertRaises(RuntimeError):w.verify_evaluation('M2',e,s)
    def test_actual_credential_and_ancillary_shape_required(self):
        for field,value in [('raw_credentials',[]),('raw_credentials',[[101,1000,1000]]),('ancillary',[])]:
            e,s=fixture();e[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(RuntimeError):w.verify_evaluation('M2',e,s)
    def test_cloexec_and_immediate_closure_required(self):
        for kind in ('cloexec','fstat','getfd','identity'):
            e,s=fixture()
            if kind=='cloexec':e['installed'][0]['fdflags']=0
            elif kind=='identity':e['immediately_closed'][0]['fd']+=1
            else:e['immediately_closed'][0][kind+'_errno']=None
            with self.subTest(kind=kind),self.assertRaises(RuntimeError):w.verify_evaluation('M2',e,s)
    def test_installed_descriptor_must_match_sent_pipe_end(self):
        e,s=fixture();e['installed'][0]['ino']+=1
        with self.assertRaises(RuntimeError):w.verify_evaluation('M2',e,s)
    def test_both_owned_ends_must_be_sent(self):
        e,s=fixture();s['attached_fds']=[8]
        with self.assertRaises(RuntimeError):w.verify_evaluation('M2',e,s)
    def test_inventory_must_stay_identical(self):
        e,s=fixture();e['after'].append(dict(fd=99))
        with self.assertRaises(RuntimeError):w.verify_evaluation('M2',e,s)
    def test_duplicate_inventory_rejected(self):
        e,s=fixture();e['before']*=2;e['after']=copy.deepcopy(e['before'])
        with self.assertRaises(RuntimeError):w.verify_evaluation('M2',e,s)
    def test_complete_payload_and_successful_send_required(self):
        for field,value in [('return_value',8),('errno',1),('payload_sha256','bad')]:
            e,s=fixture();s[field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):w.verify_evaluation('M2',e,s)
        e,s=fixture();e['received_bytes']=8
        with self.assertRaises(RuntimeError):w.verify_evaluation('M2',e,s)
    def test_truncation_specific_rejection_required(self):
        e,s=fixture();e['decision']['reason']='unexpected ancillary/descriptor'
        with self.assertRaises(RuntimeError):w.verify_evaluation('M2',e,s)
    def test_validator_cannot_acquire_credentials_after_truncation(self):
        e,s=fixture();e['decision']['credentials']=[[100,1000,1000]]
        with self.assertRaises(RuntimeError):w.verify_evaluation('M2',e,s)
    def test_unexpected_authorization_is_counterexample(self):
        e,s=fixture();e['authorized_actions']=1;e['decision']['accepted']=True
        self.assertEqual(w.verify_evaluation('M2',e,s),'CounterexampleDetected')
    def test_healthy_rejection_is_not_counterexample(self):
        e,s=fixture('M1');e['authorized_actions']=0
        with self.assertRaises(RuntimeError):w.verify_evaluation('M1',e,s)
    def test_strict_integer_counts_and_sizes(self):
        for field in ('authorized_actions','received_flags','ancillary_capacity','requests_received'):
            e,s=fixture();e[field]=float(e[field])
            with self.subTest(field=field),self.assertRaises(RuntimeError):w.verify_evaluation('M2',e,s)
    def test_validator_flags_and_length_bound_to_receive(self):
        for field in ('flags','record_bytes'):
            e,s=fixture();e['decision'][field]=0
            with self.subTest(field=field),self.assertRaises(RuntimeError):w.verify_evaluation('M2',e,s)
    def test_sender_exact_credentials_and_two_rights(self):
        conn=Mock();peer=dict(pid=100,uids=[1000]*4,gids=[1000]*4);data=w.i.frame('action','M2',100)
        conn.sendmsg.return_value=len(data)
        with patch.object(w.i,'identity',return_value=peer),patch.object(w.i,'descriptor',return_value={'passcred':1}),patch.object(w,'fd_info',side_effect=lambda fd:dict(fd=fd)):
            r=w.sender_send(conn,'M2',[8,9])
        conn.sendmsg.assert_called_once_with([data],[(socket.SOL_SOCKET,socket.SCM_CREDENTIALS,struct.pack('3i',100,1000,1000)),(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[8,9]).tobytes())])
        self.assertEqual(r['attached_fds'],[8,9])
    def test_disabled_pre_send_passcred_stops(self):
        with patch.object(w.i,'identity',return_value=dict(pid=100,uids=[1000]*4,gids=[1000]*4)),patch.object(w.i,'descriptor',return_value={'passcred':0}):
            conn=Mock()
            with self.assertRaises(RuntimeError):w.sender_send(conn,'M1',[])
            conn.sendmsg.assert_not_called()
    def test_receive_actual_flags_and_cleanup_before_inventory(self):
        peer=dict(pid=100,uids=[1000]*4,gids=[1000]*4);data=w.i.frame('action','M2',100)
        anc=[(socket.SOL_SOCKET,socket.SCM_CREDENTIALS,struct.pack('3i',100,1000,1000)),(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[10]).tobytes())]
        flags=int(socket.MSG_CTRUNC);conn=Mock();conn.recvmsg.return_value=(data,anc,flags,None);order=[]
        def inv():order.append('inventory');return []
        def validate(*args):order.append('validate');return dict(accepted=False)
        def closed(fd):order.append('closed');return dict(fd=fd)
        with patch.object(w,'fd_inventory',side_effect=inv),patch.object(w,'fd_info',return_value=dict(fd=10)),patch.object(w,'immediately_closed',side_effect=closed),patch.object(w.i,'live',return_value=True),patch.object(w.i,'descriptor',return_value={}),patch.object(w.i,'validate',side_effect=validate) as guard:
            w.observe_receive(conn,peer,99,'M2')
        conn.recvmsg.assert_called_once_with(w.i.MAX_RECORD,w.partial_capacity(),socket.MSG_CMSG_CLOEXEC)
        guard.assert_called_once_with(data,anc,flags,peer,dict(tag='action',attempt='M2',claim_pid=100),True)
        self.assertEqual(order,['inventory','validate','closed','inventory'])
    def test_failed_healthy_stops_second_case(self):
        with tempfile.TemporaryDirectory() as root,patch.object(w,'fd_inventory',return_value=[]),patch.object(w.i,'subreaper',return_value=0),patch.object(w,'run_case',return_value=dict(case='M1',result='Fail',failures=['synthetic'])) as run,redirect_stdout(io.StringIO()):
            self.assertEqual(w.main(Path(root)/'report.json'),1)
            run.assert_called_once_with('M1')


def audit_stopped_report(report):
    """Offline relationships for the stopped M2 prefix; no socket/process calls."""
    require=w.require
    c=report['cases'][1];trace=c['trace']
    names=['server-ready-before-connect','client-ready-before-connect','trusted-client-enrollment','trusted-server-enrollment',
           'connect-permitted','accepted-passcred-verified','hello-send-permitted','client-credentials-and-server-reply',
           'server-reply-verified','owned-pipe-created','receiver-before-send','sender-before','action-send-permitted','kernel-receive-and-truncation-check']
    require([t['barrier'] for t in trace]==names,'stopped barrier sequence')
    require([t['index'] for t in trace]==list(range(len(trace))),'stopped trace indices')
    times=[t['at'] for t in trace]
    require(all(type(t) in (int,float) and t>=0 and t<float('inf') for t in times) and times==sorted(times),'invalid stopped timestamps')
    ev={t['barrier']:t['evidence'] for t in trace}
    runner=report['environment']['runner'];server=ev[names[0]]['identity'];client=ev[names[1]]['identity']
    require(server['pid']!=client['pid'],'distinct owned actors')
    for actor in (server,client):
        w.i.unprivileged(actor)
        require(actor['ppid']==runner['pid'] and actor['namespaces']==runner['namespaces'],'runner ownership/namespace mismatch')
    for name,peer in [('trusted-client-enrollment',client),('trusted-server-enrollment',server)]:
        enrolled=ev[name]
        require(enrolled['enrolled']==peer and enrolled['pidfd_live'] is True and enrolled['inheritable'] is False,'stopped enrollment mismatch')
    for d in (ev[names[0]]['listener'],ev[names[1]]['descriptor'],ev['connect-permitted']['descriptor'],ev['accepted-passcred-verified']['descriptor']):
        require(d['passcred']==1 and d['type']==socket.SOCK_SEQPACKET and d['inheritable'] is False,'stopped socket guards')
    for decision,peer in [(ev['client-credentials-and-server-reply']['verification'],client),(ev['server-reply-verified'],server)]:
        require(decision['accepted'] is True and decision['pidfd_live'] is True and decision['credentials']==[[peer['pid'],peer['uids'][0],peer['gids'][0]]],'stopped hello credentials')
    baseline=ev['receiver-before-send'];before=ev['sender-before'];sent=ev['action-send-permitted'];made=ev['owned-pipe-created'];e=ev['kernel-receive-and-truncation-check'];d=e['decision']
    require(baseline['identity']==server and before['identity']==sent['identity']==made['identity']==client,'stopped identity mismatch')
    for value,wanted in [(baseline['authorized_actions'],0),(baseline['requests_received'],0),(before['requests_sent'],0),(sent['requests_sent'],1),(e['requests_received'],1),(e['authorized_actions'],0),(c['action_count'],0)]:
        w.i.check_count(value,'invalid stopped integer count');require(value==wanted,'stopped counter mismatch')
    require(before['pipe']==made['pipe']==sent['sent_pipe'] and len(made['pipe'])==2,'stopped pipe ownership')
    read,write=made['pipe']
    require(type(read['fd']) is int and type(write['fd']) is int and read['fd']!=write['fd'],'distinct sent FDs')
    require(sent['attached_fds']==[read['fd'],write['fd']],'both owned pipe ends attached')
    require(stat.S_ISFIFO(read['mode']) and all(read[k]==write[k] for k in ('dev','ino','mode')),'same owned pipe')
    require(read['flags']&os.O_ACCMODE==os.O_RDONLY and write['flags']&os.O_ACCMODE==os.O_WRONLY,'pipe access mode evidence')
    require(sent['requested_credentials']==[client['pid'],client['uids'][0],client['gids'][0]],'requested sender credentials')
    require(w.i.same_endpoint(before['descriptor'],sent['descriptor']),'sender endpoint mismatch')
    accepted=ev['accepted-passcred-verified']['descriptor']
    require(w.i.same_endpoint(accepted,e['descriptor']) and accepted['fd']==e['descriptor']['fd'],'receiver endpoint mismatch')
    frame=w.i.frame('action','M2',client['pid']);digest=hashlib.sha256(frame).hexdigest()
    for value in (sent['record_bytes'],sent['return_value'],e['received_bytes'],e['expected_record_bytes'],d['record_bytes']):
        w.i.check_count(value,'invalid stopped byte count');require(value==len(frame),'stopped payload length mismatch')
    w.i.check_count(e['declared_json_bytes'],'invalid stopped prefix length')
    require(sent['errno'] is None and e['declared_json_bytes']==len(frame)-4 and e['fixture_payload_matches'] is True,'complete stopped payload evidence')
    require(sent['payload_sha256']==e['payload_sha256']==digest,'stopped payload hash mismatch')
    for field in ('received_flags','recvmsg_flags_argument','payload_capacity','ancillary_capacity'):
        w.i.check_count(e[field],'invalid stopped receive integer')
    w.i.check_count(d['flags'],'invalid validator flags')
    require(d['flags']==e['received_flags'],'validator flags mismatch')
    require(e['received_flags']&socket.MSG_CTRUNC and not e['received_flags']&socket.MSG_TRUNC,'stopped truncation flags')
    require(e['recvmsg_flags_argument']==socket.MSG_CMSG_CLOEXEC and e['payload_capacity']==w.i.MAX_RECORD and e['ancillary_capacity']==w.partial_capacity(),'stopped capacities/receive flags')
    require(e['pidfd_live'] is True and e['observation_errors']==[],'stopped liveness/observation failure')
    for inventory in (e['before'],e['after']):
        numbers=[]
        for fd in inventory:
            for field in ('fd','dev','ino','mode','flags','fdflags'):w.i.check_count(fd[field],'invalid inventory metadata')
            numbers.append(fd['fd'])
        require(len(numbers)==len(set(numbers)),'duplicate inventory descriptor')
        matches=[fd for fd in inventory if fd['fd']==accepted['fd']]
        require(len(matches)==1 and matches[0]['dev']==accepted['device'] and matches[0]['ino']==accepted['inode'],'accepted endpoint inventory mismatch')
    require(c['case']=='M2' and c['result']=='Fail' and c['failures']==['receiver FD inventory changed'],'stopped failure classification')
    require(d['accepted'] is False and d['reason']=='truncated record/control' and d['credentials']==[],'stopped rejection mismatch')
    require(not c.get('counterexample'),'unexpected authority counterexample claim')
    cleanup=c['cleanup']['actors']
    require(len(cleanup)==2 and {a['pid'] for a in cleanup}=={client['pid'],server['pid']},'cleanup ownership mismatch')
    for a in cleanup:
        require(type(a['pid']) is int and type(a['exit_code']) is int and a['exit_code']==-15 and a['reaped'] is True and a['forced'] is True,'stopped cleanup accounting')
    require(c['cleanup']['root_removed'] is True,'fixture cleanup missing')
    return True


class EvidenceChecks(unittest.TestCase):
    """Audit the preserved stopped failure, never relabel it as native success."""
    @classmethod
    def setUpClass(cls):
        path=Path(__file__).with_name('evidence')/'linux-run.json'
        if not path.exists():raise unittest.SkipTest('native report not yet generated')
        cls.report=json.loads(path.read_text())
    def ev(self,c,name):return next(t['evidence'] for t in c['trace'] if t['barrier']==name)
    def test_stopped_prefix_relationships(self):
        self.assertTrue(audit_stopped_report(self.report))
    def test_corrupted_stopped_relationships_rejected(self):
        for kind in ('duplicate','flags','runner','enrollment','order','attachment','hash','counts','endpoint','cleanup'):
            r=copy.deepcopy(self.report);c=r['cases'][1];e=self.ev(c,'kernel-receive-and-truncation-check')
            if kind=='duplicate':e['before'].append(copy.deepcopy(e['before'][0]))
            elif kind=='flags':e['decision']['flags']=0
            elif kind=='runner':r['environment']['runner']['pid']+=100000
            elif kind=='enrollment':self.ev(c,'trusted-client-enrollment')['enrolled']['start_ticks']+=1
            elif kind=='order':c['trace'][2],c['trace'][3]=c['trace'][3],c['trace'][2]
            elif kind=='attachment':self.ev(c,'action-send-permitted')['attached_fds']=[5]
            elif kind=='hash':self.ev(c,'action-send-permitted')['payload_sha256']='wrong'
            elif kind=='counts':e['authorized_actions']=False
            elif kind=='endpoint':e['descriptor']['inode']+=1
            else:c['cleanup']['actors'].append(copy.deepcopy(c['cleanup']['actors'][0]))
            with self.subTest(kind=kind),self.assertRaises(RuntimeError):audit_stopped_report(r)

    def test_hashes_and_failed_disposition_preserved(self):
        r=self.report
        self.assertEqual(r['source_sha256'],hashlib.sha256(w.SCRIPT.read_bytes()).hexdigest())
        self.assertEqual(r['helper_sha256'],hashlib.sha256(w.HELPER.read_bytes()).hexdigest())
        self.assertIs(r['diagnostic_success'],False);self.assertEqual(r['primitive_result'],'Incomplete/Fail/Blocked')
        self.assertEqual(r['authentication_safety'],'Unproven');self.assertIs(r['production_readiness'],False)
        self.assertFalse(r.get('failure'));self.assertFalse(r['finalization_failures'])
    def test_healthy_pass_and_partial_failure_with_zero_actions(self):
        r=self.report
        self.assertEqual([c['case'] for c in r['cases']],['M1','M2'])
        self.assertEqual([c['result'] for c in r['cases']],['Pass','Fail'])
        self.assertEqual([c['action_count'] for c in r['cases']],[1,0])
        self.assertTrue(w.verify_case_evidence(r['cases'][0],completed=True))
        c=r['cases'][1];self.assertEqual(c['failures'],['receiver FD inventory changed'])
        with self.assertRaisesRegex(RuntimeError,'inventory changed'):
            w.verify_evaluation('M2',self.ev(c,'kernel-receive-and-truncation-check'),self.ev(c,'action-send-permitted'))
    def test_actual_truncation_payload_and_returned_ancillary(self):
        c=self.report['cases'][1];e=self.ev(c,'kernel-receive-and-truncation-check');sender=self.ev(c,'action-send-permitted')
        self.assertEqual(e['ancillary_capacity'],w.partial_capacity());self.assertEqual(e['payload_capacity'],w.i.MAX_RECORD)
        self.assertTrue(e['received_flags']&socket.MSG_CTRUNC);self.assertFalse(e['received_flags']&socket.MSG_TRUNC)
        self.assertEqual(e['received_bytes'],sender['return_value']);self.assertTrue(e['fixture_payload_matches'])
        self.assertEqual(e['payload_sha256'],sender['payload_sha256'])
        self.assertEqual(e['decision']['reason'],'truncated record/control');self.assertIs(e['decision']['accepted'],False)
        self.assertEqual(e['decision']['credentials'],[]);self.assertEqual(e['authorized_actions'],0)
        raw=e['raw_ancillary'];self.assertEqual(len(raw),1)
        self.assertEqual((raw[0]['level'],raw[0]['type']),(socket.SOL_SOCKET,socket.SCM_CREDENTIALS))
        actual=list(struct.unpack('3i',bytes.fromhex(raw[0]['hex'])))
        self.assertEqual(e['raw_credentials'],[actual])
        peer=sender['identity'];self.assertEqual(actual,[peer['pid'],peer['uids'][0],peer['gids'][0]])
        self.assertEqual(e['ancillary'],[dict(level=socket.SOL_SOCKET,type=socket.SCM_CREDENTIALS,bytes=12)])
    def test_inventory_exposes_unreturned_pipe_fd_and_no_immediate_closure_proof(self):
        c=self.report['cases'][1];e=self.ev(c,'kernel-receive-and-truncation-check');sender=self.ev(c,'action-send-permitted')
        baseline={fd['fd']:fd for fd in e['before']};after={fd['fd']:fd for fd in e['after']}
        self.assertEqual(len(baseline),6);self.assertEqual(len(after),7)
        self.assertTrue(all(after[n]==fd for n,fd in baseline.items()))
        added=[fd for n,fd in after.items() if n not in baseline];self.assertEqual(len(added),1)
        fd=added[0];self.assertTrue(fd['fdflags']&fcntl.FD_CLOEXEC);self.assertTrue(stat.S_ISFIFO(fd['mode']))
        matches=[p for p in sender['sent_pipe'] if all(fd[k]==p[k] for k in ('dev','ino','mode','flags'))]
        self.assertEqual(len(matches),1);self.assertEqual(len(sender['attached_fds']),2)
        self.assertEqual(e['installed'],[]);self.assertEqual(e['immediately_closed'],[])
        self.assertEqual(e['decision']['delivered_fds_closed'],0)
        # No later sender validity observation was taken after the stop condition.
        self.assertNotIn('sender-after',[t['barrier'] for t in c['trace']])
        self.assertFalse(c.get('counterexample'))  # no authorization counterexample
    def test_owned_cleanup_and_settings_after_stop(self):
        r=self.report;self.assertEqual(r['runner_before'],r['runner_after'])
        for c in r['cases']:
            self.assertTrue(c['cleanup']['root_removed']);self.assertFalse(Path(c['fixture']['root']).exists())
            pids={self.ev(c,name)['identity']['pid'] for name in ('server-ready-before-connect','client-ready-before-connect')}
            self.assertEqual({a['pid'] for a in c['cleanup']['actors']},pids)
            self.assertTrue(all(a['reaped'] is True for a in c['cleanup']['actors']))
            self.assertEqual(c['fixture']['mode'],'0o700');self.assertEqual(c['socket_fixture']['mode'],'0o600')
        self.assertTrue(all(a['exit_code']==0 and not a['forced'] for a in r['cases'][0]['cleanup']['actors']))
        self.assertTrue(all(a['exit_code']==-15 and a['forced'] for a in r['cases'][1]['cleanup']['actors']))
    def test_healthy_stop_and_cleanup_corruption_rejected(self):
        for kind in ('stop','cleanup','missing'):
            c=copy.deepcopy(self.report['cases'][0])
            if kind=='stop':c['trace'][-1]['evidence']['actions']=0
            elif kind=='cleanup':c['cleanup']['actors'][0]['pid']+=10000
            else:c['trace']=c['trace'][:-2]
            with self.subTest(kind=kind),self.assertRaises(RuntimeError):w.verify_case_evidence(c,completed=True)


if __name__=='__main__':unittest.main(verbosity=2)
