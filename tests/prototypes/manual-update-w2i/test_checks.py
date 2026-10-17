"""Synthetic validator checks only; no hostile native credential/FD schedules."""
import array
import importlib.util
import json
import os
from pathlib import Path
import socket
import struct
import unittest

spec = importlib.util.spec_from_file_location('w2i', Path(__file__).with_name('run_experiment.py'))
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class SyntheticValidatorChecks(unittest.TestCase):
    def setUp(self):
        self.enrolled = w.identity()
        self.body = dict(tag='action', attempt='SYNTHETIC', claim_pid=os.getpid())
        self.data = w.frame(**dict(tag='action', attempt='SYNTHETIC', claimed=os.getpid()))
        self.creds = [(socket.SOL_SOCKET, socket.SCM_CREDENTIALS,
                       struct.pack('3i', os.getpid(), os.getuid(), os.getgid()))]

    def validate(self, data=None, anc=None, flags=0, alive=True):
        return w.validate(self.data if data is None else data, self.creds if anc is None else anc,
                          flags, self.enrolled, self.body, alive)

    def test_valid_explicit_metadata_control(self):
        self.assertTrue(self.validate()['accepted'])

    def test_missing_duplicate_wrong_size_credentials(self):
        for anc in ([], self.creds*2, [(socket.SOL_SOCKET, socket.SCM_CREDENTIALS, b'x')]):
            with self.subTest(anc=anc):
                self.assertFalse(self.validate(anc=anc)['accepted'])

    def test_payload_pid_cannot_replace_sender(self):
        anc = [(socket.SOL_SOCKET, socket.SCM_CREDENTIALS, struct.pack('3i', os.getpid()+1000, os.getuid(), os.getgid()))]
        self.assertEqual(self.validate(anc=anc)['reason'], 'sender mismatch')

    def test_wrong_uid_gid(self):
        for u, g in ((os.getuid()+1, os.getgid()), (os.getuid(), os.getgid()+1)):
            self.assertFalse(self.validate(anc=[(socket.SOL_SOCKET, socket.SCM_CREDENTIALS, struct.pack('3i', os.getpid(), u, g))])['accepted'])

    def test_dead_enrolled_instance(self):
        self.assertFalse(self.validate(alive=False)['accepted'])

    def test_truncation_flags(self):
        for flag in (socket.MSG_TRUNC, socket.MSG_CTRUNC, socket.MSG_TRUNC | socket.MSG_CTRUNC):
            self.assertFalse(self.validate(flags=flag)['accepted'])

    def test_lengths_empty_multiple_oversize(self):
        for raw in (b'', b'\0\0\0\0', self.data[:-1], self.data+self.data, struct.pack('!I', 20000)+b'x'*20000):
            self.assertFalse(self.validate(data=raw)['accepted'])

    def test_malformed_utf8_duplicate_json_depth_schema(self):
        for raw in (b'\xff', b'{', b'{"tag":"action","tag":"action","attempt":"SYNTHETIC","claim_pid":1}',
                    b'['*10000+b']'*10000,
                    b'{"tag":"action","attempt":"SYNTHETIC","claim_pid":true}',
                    b'{"tag":"action","attempt":"SYNTHETIC","claim_pid":1,"extra":1}'):
            self.assertFalse(self.validate(data=struct.pack('!I',len(raw))+raw)['accepted'])

    def test_unknown_control_type(self):
        self.assertFalse(self.validate(anc=self.creds+[(12345,12345,b'')])['accepted'])

    def test_rights_closed_on_rejection_and_truncation(self):
        # These are locally owned pipe descriptors inserted as SYNTHETIC metadata,
        # not descriptors installed by a native recvmsg of hostile traffic.
        for flags in (0, socket.MSG_CTRUNC):
            read_fd, write_fd = os.pipe()
            try:
                anc=self.creds+[(socket.SOL_SOCKET, socket.SCM_RIGHTS,array.array('i',[read_fd]).tobytes())]
                decision=self.validate(anc=anc,flags=flags)
                self.assertFalse(decision['accepted'])
                self.assertEqual(decision['delivered_fds_closed'],1)
                with self.assertRaises(OSError):os.fstat(read_fd)
            finally:
                os.close(write_fd)

    def test_no_credential_cache_between_calls(self):
        self.assertTrue(self.validate()['accepted'])
        self.assertFalse(self.validate(anc=[])['accepted'])

    def test_no_close_of_payload_named_descriptor(self):
        fd, other=os.pipe()
        try:
            body=dict(self.body,claim_pid=fd)
            raw=json.dumps(body).encode()
            self.assertFalse(self.validate(data=struct.pack('!I',len(raw))+raw)['accepted'])
            os.fstat(fd)
        finally:
            os.close(fd);os.close(other)


class NativeEvidenceChecks(unittest.TestCase):
    """Audit saved native evidence; does not execute further native schedules."""
    @classmethod
    def setUpClass(cls):
        cls.report=json.loads(Path(__file__).with_name('evidence').joinpath('linux-run.json').read_text())

    def trace(self, case, name):
        return next(e['evidence'] for e in case['trace'] if e['barrier']==name)

    def test_source_hash_and_readiness_scope(self):
        import hashlib
        self.assertEqual(self.report['source_sha256'],hashlib.sha256(w.SCRIPT.read_bytes()).hexdigest())
        self.assertTrue(self.report['diagnostic_success'])
        self.assertEqual(self.report['authentication_safety'],'Unproven')
        self.assertFalse(self.report['production_readiness'])

    def test_case_counts_and_actual_forgery_errno(self):
        self.assertEqual([c['case'] for c in self.report['cases']],['I1','I2','I3'])
        self.assertEqual([c['action_count'] for c in self.report['cases']],[1,0,0])
        c=self.report['cases'][2]; sent=self.trace(c,'holder-send-permitted')
        self.assertEqual(sent['return_value'],-1)
        self.assertEqual(sent['errno'],w.errno.EPERM)
        status=self.trace(c,'independent-receiver-count-after-forgery')
        self.assertEqual(status['requests_received'],0)
        self.assertFalse(status['queued_record'])

    def test_independent_holder_kernel_attribution(self):
        c=self.report['cases'][1]; original=self.trace(c,'original-before')['identity']
        holder=c['holder']; decision=self.trace(c,'record-evaluation')
        self.assertNotEqual(original['pid'],holder['pid'])
        self.assertEqual(decision['credentials'],[[holder['pid'],holder['uids'][0],holder['gids'][0]]])
        self.assertEqual(decision['reason'],'sender mismatch')
        self.assertFalse(decision['accepted'])
        self.assertEqual(self.trace(c,'original-after')['requests_sent'],0)

    def test_options_and_both_hello_directions(self):
        for c in self.report['cases']:
            self.assertEqual(self.trace(c,'listener-ready-before-connect')['listener']['passcred'],1)
            self.assertEqual(self.trace(c,'client-passcred-ready')['descriptor']['passcred'],1)
            self.assertEqual(self.trace(c,'accepted-options-verified-before-send')['descriptor']['passcred'],1)
            self.assertTrue(self.trace(c,'hello-credentials-and-reply')['verification']['accepted'])
            self.assertTrue(self.trace(c,'server-credentials-verified')['accepted'])
            names=[t['barrier'] for t in c['trace']]
            self.assertLess(names.index('trusted-client-enrollment'),names.index('connect-permitted'))
            self.assertLess(names.index('accepted-options-verified-before-send'),names.index('hello-send-permitted'))

    def test_holder_inheritance_live_original_and_namespace(self):
        for c in self.report['cases'][1:]:
            original=self.trace(c,'original-before')
            spawned=self.trace(c,'holder-inheritance')
            ready=self.trace(c,'holder-ready-after-handle-retained')
            self.assertEqual(spawned['pass_fds'],[original['descriptor']['fd']])
            self.assertTrue(spawned['close_fds'])
            self.assertTrue(ready['inherited']['inheritable'])
            self.assertEqual(ready['descriptor']['inode'],original['descriptor']['inode'])
            self.assertEqual(c['holder']['ppid'],original['identity']['pid'])
            self.assertEqual(c['holder']['namespaces'],original['identity']['namespaces'])
            self.assertTrue(self.trace(c,'runner-original-before')['pidfd_live'])
            self.assertTrue(self.trace(c,'runner-original-after')['pidfd_live'])

    def test_cleanup_and_barrier_integrity(self):
        self.assertEqual(self.report['runner_fds_before_after'],[4,4])
        self.assertEqual(self.report['subreaper_before'],self.report['subreaper_after'])
        for c in self.report['cases']:
            self.assertEqual(c['failures'],[])
            self.assertTrue(c['cleanup']['root_removed'])
            self.assertFalse(Path(c['root']).exists())
            self.assertEqual([e['index'] for e in c['trace']],list(range(len(c['trace']))))
            self.assertTrue(all(a['reaped'] and a['exit_code']==0 and not a['forced'] for a in c['cleanup']['direct_children']))
            if c['case']!='I1':
                self.assertTrue(c['cleanup']['holder_pidfd_exited'])
                self.assertEqual(self.trace(c,'holder-stop-and-reap')['exit_code'],0)

    def test_actor_close_waits_after_exit_acknowledgement(self):
        from unittest.mock import Mock, patch
        a=w.Actor.__new__(w.Actor)
        a.proc=Mock();a.proc.pid=1234;a.proc.poll.return_value=0;a.proc.wait.return_value=0
        a.fd=99;a.stopping=True
        with patch.object(w.os,'close'),patch.object(w.signal,'pidfd_send_signal') as signal_send:
            result=a.close()
        self.assertFalse(result['forced'])
        signal_send.assert_not_called()
        self.assertEqual(a.proc.wait.call_count,2)


if __name__=='__main__':unittest.main(verbosity=2)
