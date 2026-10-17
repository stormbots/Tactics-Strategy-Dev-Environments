"""Byte fixtures/mocks only; never loads/preloads a shared library or opens sockets."""
import copy
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import struct
import unittest
from unittest.mock import Mock

spec=importlib.util.spec_from_file_location('w2n_evidence',Path(__file__).with_name('evidence.py'))
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
RUN=bytes([1])+bytes(15)


def put(raw,offset,value,fmt='<I'):struct.pack_into(fmt,raw,offset,value)


def synthetic_status(capture):
    b=bytearray(256);b[:8]=b'W2NSTAT1'
    for off,value in [(8,1),(12,256),(16,5),(20,1),(32,2),(64,101),(68,41),(120,41),(124,1536),(136,1)]:put(b,off,value)
    for off,value in [(40,1),(72,1),(80,2),(88,2),(96,1),(104,1),(112,1),(128,2)]:put(b,off,value,'<Q')
    b[48:64]=capture[48:64];return b


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=Path(os.environ['W2N_SYNTHETIC_CAPTURE']).read_bytes()

    def test_C_mock_corpus_invalid_and_error_records_remain_distinct(self):
        raw=Path(os.environ['W2N_SYNTHETIC_CAPTURE']+'.corpus').read_bytes()
        self.assertEqual(len(raw)%1536,0)
        qualities=set();results=[]
        for offset in range(0,len(raw),1536):
            block=raw[offset:offset+1536];result=e.decode('capture',block)
            qualities.add(result['quality']);results.append(result['result'])
        self.assertEqual(qualities,{1,2,3});self.assertIn(-1,results)

    def test_independent_decoder_of_C_synthetic_capture(self):
        c=e.decode('capture',self.raw)
        self.assertEqual(c['quality'],1);self.assertEqual(c['result'],23)
        self.assertEqual([h['type'] for h in c['control']],[2,1])
        self.assertEqual(c['control'][1]['values'],[77])

    def test_padding_is_redacted_not_exported(self):
        self.assertEqual(self.raw[512+28:512+32],bytes(4))
        self.assertEqual(self.raw[768+28:768+32],bytes(4))
        b=bytearray(self.raw);b[512+28]=0xde
        with self.assertRaisesRegex(ValueError,'hidden'):e.decode('capture',bytes(b))

    def test_hidden_known_data_cannot_claim_valid(self):
        b=bytearray(self.raw);b[512+48:512+52]=bytes(4);b[768+48:768+52]=bytes(4);put(b,216,44)
        with self.assertRaises(ValueError):e.decode('capture',bytes(b))

    def test_non_binary_mask_and_visibility_count_rejected(self):
        for off,value in [(768,2),(216,1)]:
            b=bytearray(self.raw)
            if off==768:b[off]=value
            else:put(b,off,value)
            with self.subTest(offset=off),self.assertRaises(ValueError):e.decode('capture',bytes(b))

    def test_unknown_version_bits_profile_reserved_bytes(self):
        for off,value,fmt in [(8,2,'<I'),(24,1<<40,'<Q'),(240,1<<40,'<Q'),(248,1,'<I'),(236,0,'<I')]:
            b=bytearray(self.raw);put(b,off,value,fmt)
            with self.subTest(offset=off),self.assertRaises(ValueError):e.decode('capture',bytes(b))

    def test_unknown_quality_and_sanitizer_rejected(self):
        for off in (20,212):
            b=bytearray(self.raw);put(b,off,99)
            with self.subTest(offset=off),self.assertRaises(ValueError):e.decode('capture',bytes(b))

    def test_capture_size_and_unavailable_scalars(self):
        with self.assertRaises(ValueError):e.decode('capture',self.raw[:-1])
        b=bytearray(self.raw);put(b,240,255 & ~2,'<Q')
        with self.assertRaisesRegex(ValueError,'unavailable'):e.decode('capture',bytes(b))

    def test_valid_capture_must_bind_counter_window_and_capacities(self):
        for off,value,fmt in [(80,3,'<Q'),(112,2,'<Q'),(152,56,'<Q'),(184,256,'<Q')]:
            b=bytearray(self.raw);put(b,off,value,fmt)
            with self.subTest(offset=off),self.assertRaises(ValueError):e.decode('capture',bytes(b))

    def test_native_header_length_overflow_cannot_hide_in_valid_mask(self):
        b=bytearray(self.raw);put(b,512+32,(1<<64)-1,'<Q')
        with self.assertRaises(ValueError):e.decode('capture',bytes(b))

    def test_partial_rights_integer_rejected(self):
        b=bytearray(self.raw);put(b,512+32,21,'<Q')
        with self.assertRaises(ValueError):e.decode('capture',bytes(b))

    def test_independent_synthetic_invalid_header_view(self):
        b=bytearray(self.raw);put(b,20,2);put(b,24,1<<11,'<Q');put(b,212,2);put(b,224,32);put(b,228,1)
        b[512+32:512+52]=bytes(20);b[768+32:768+52]=bytes(20);put(b,216,28)
        result=e.decode('capture',bytes(b));self.assertEqual(result['quality'],2)
        self.assertEqual(len(result['control']),1)

    def test_error_record_never_inherits_Hello_data(self):
        b=bytearray(self.raw)
        for off in (132,160,168,172,192,200,216,220,228):put(b,off,0,'<Q' if off in (160,192,200) else '<I')
        put(b,20,3);put(b,24,1<<10,'<Q');put(b,144,-1,'<q');put(b,140,4);put(b,240,49,'<Q');put(b,208,17);put(b,212,3)
        b[512:]=bytes(1024);self.assertEqual(e.decode('capture',bytes(b))['result'],-1)
        put(b,132,8)
        with self.assertRaises(ValueError):e.decode('capture',bytes(b))

    def test_expected_outcome_is_not_authentication_acceptance(self):
        result=e.require_observer_consistency(self.raw,bytes(synthetic_status(self.raw)))
        self.assertEqual(result,dict(observer_integrity='Consistent',authentication_safety='Unproven',production_readiness=False))
        self.assertNotIn('cleanup_result',result)

    def test_late_status_issue_overrides_old_valid_capture(self):
        status=synthetic_status(self.raw);put(status,24,8,'<Q')
        with self.assertRaises(ValueError):e.require_observer_consistency(self.raw,bytes(status))

    def test_every_final_status_endpoint_window_quality_and_resolution_must_match(self):
        for off,value,fmt in [(20,2,'<I'),(136,2,'<I'),(68,42,'<I'),(96,0,'<Q'),(104,0,'<Q'),(112,0,'<Q'),(120,42,'<I')]:
            b=synthetic_status(self.raw);put(b,off,value,fmt)
            with self.subTest(offset=off),self.assertRaises(ValueError):e.require_observer_consistency(self.raw,bytes(b))

    def test_status_rejects_impossible_process_lifecycle_and_counter_fields(self):
        for off,value,fmt in [(64,0,'<I'),(88,3,'<Q'),(136,0,'<I'),(16,0,'<I')]:
            b=synthetic_status(self.raw);put(b,off,value,fmt)
            with self.subTest(offset=off),self.assertRaises(ValueError):e.decode('status',bytes(b))

    def test_foreign_status_identity_and_late_calls_rejected(self):
        for off,value,fmt in [(64,102,'<I'),(80,3,'<Q'),(128,3,'<Q')]:
            b=synthetic_status(self.raw);put(b,off,value,fmt)
            with self.subTest(offset=off),self.assertRaises(ValueError):e.require_observer_consistency(self.raw,bytes(b))

    def test_three_chunks_roundtrip_and_exact_line_bound(self):
        lines=e.envelope(self.raw,'capture',RUN,2,19)
        self.assertEqual(len(lines),3);self.assertTrue(all(len(x.encode())<=2048 for x in lines))
        self.assertEqual(e.assemble(lines),self.raw)
        self.assertEqual(e.assemble(list(reversed(lines))),self.raw)

    def test_missing_and_duplicate_chunks(self):
        lines=e.envelope(self.raw,'capture',RUN,2,19)
        for corrupt in (lines[:2],[lines[0],lines[0],lines[2]]):
            with self.assertRaises(ValueError):e.assemble(corrupt)

    def test_foreign_chunk_generation_call_sample_and_range(self):
        for field,value in [('generation','2'),('call','3'),('sample',20),('offset',1),('n',511),('run','02'+'00'*15)]:
            lines=e.envelope(self.raw,'capture',RUN,2,19);obj=json.loads(lines[1]);obj[field]=value;lines[1]=json.dumps(obj)+'\n'
            with self.subTest(field=field),self.assertRaises(ValueError):e.assemble(lines)

    def test_envelope_binary_ID_mismatch_and_unsigned_decimal_overflow(self):
        for val in ('01','-1',str(1<<64),True):
            lines=e.envelope(self.raw,'capture',RUN,2,19)
            for index,line in enumerate(lines):
                obj=json.loads(line);obj['call']=val;lines[index]=json.dumps(obj)+'\n'
            with self.subTest(value=val),self.assertRaises(ValueError):e.assemble(lines)

    def test_unknown_duplicate_JSON_keys_and_long_lines(self):
        lines=e.envelope(self.raw,'capture',RUN,2,19)
        for bad in ('{"kind":"w2n-block",'+lines[0][1:], lines[0][:-2]+',"extra":1}\n', ' '*2048+'\n'):
            with self.subTest(prefix=bad[:30]),self.assertRaises(ValueError):e.assemble([bad]+lines[1:])

    def test_strict_types_hex_and_newline(self):
        for field,value in [('case',True),('sample',False),('version',True),('hex','F'*1024)]:
            lines=e.envelope(self.raw,'capture',RUN,2,19);obj=json.loads(lines[0]);obj[field]=value;lines[0]=json.dumps(obj)+'\n'
            with self.subTest(field=field),self.assertRaises(ValueError):e.assemble(lines)
        with self.assertRaises(ValueError):e.assemble([x.rstrip('\n') for x in e.envelope(self.raw,'capture',RUN,2,19)])

    def test_pre_setup_status_exception_not_allowed_for_capture(self):
        b=bytearray(256);b[:8]=b'W2NSTAT1';put(b,8,1);put(b,12,256);put(b,64,101);put(b,68,0xffffffff);put(b,120,0xffffffff)
        self.assertEqual(e.assemble(e.envelope(bytes(b),'status',RUN,1,0)),bytes(b))
        with self.assertRaises(ValueError):e.envelope(self.raw,'capture',bytes([2])+bytes(15),2,1)

    def test_all_explicit_ctypes_declarations_without_loading_library(self):
        lib=Mock();self.assertIs(e.bind_verified_handle(lib),lib)
        for name in ('setup','abi','provider','status','arm','freeze','read'):
            self.assertIs(getattr(lib,'w2n_v1_'+name).restype,ctypes.c_int32)
        self.assertEqual(lib.w2n_v1_read.argtypes[:3],[ctypes.c_uint64,ctypes.c_uint32,ctypes.c_uint32])

    def test_python_argument_ranges_reject_unsigned_wrap(self):
        for fd in (-1,1<<31,True):
            with self.subTest(fd=fd),self.assertRaises(ValueError):e.arm_arguments(fd,1)
        for value in (-1,1<<64,True):
            with self.subTest(count=value),self.assertRaises(ValueError):e.arm_arguments(41,value)
        for run,case,phase in [(bytes(16),1,1),(RUN,True,1),(RUN,1,True)]:
            with self.assertRaises(ValueError):e.setup_arguments(run,case,phase)
        with self.assertRaises(ValueError):e.read_arguments(1,(1<<32)-1)
        self.assertEqual(e.read_arguments(1,512)[:3],(1,512,512))

    def test_report_overflow_reserve_and_stop(self):
        report=e.BoundedReport();self.assertTrue(report.append({'note':'local fixture'}))
        self.assertFalse(report.append({'oversize':'x'*(128*1024)}))
        with self.assertRaises(ValueError):report.append({'late':1})
        result=report.finish({'ignored':'must not replace overflow'})
        self.assertLessEqual(len(result),128*1024);self.assertIn(b'"Incomplete"',result)
        self.assertNotIn(b'oversize',result)

    def test_overflow_preserves_bounded_original_counterexample_and_failure(self):
        report=e.BoundedReport();self.assertTrue(report.append({'fill':'x'*(report.LIMIT-report.RESERVE-100)}))
        self.assertFalse(report.append({'overflow':'x'*200}))
        outcome=dict(authorization_result='CounterexampleDetected',authorized_actions=1,failure='original failure')
        result=report.finish(outcome);terminal=json.loads(result.splitlines()[-1])
        self.assertEqual(terminal['observation_result'],'Incomplete')
        self.assertEqual(terminal['original_outcome'],outcome)
        self.assertLessEqual(len(result),report.LIMIT)
        self.assertEqual(result,report.finish({'authorization_result':'Safe'}))

    def test_overflow_cannot_silently_discard_an_oversized_outcome(self):
        report=e.BoundedReport();self.assertFalse(report.append({'large':'x'*report.LIMIT}))
        with self.assertRaises(ValueError):report.finish({'failure':'x'*report.RESERVE})
        self.assertIsNone(report.terminal)

    def test_report_terminal_is_immutable_and_bounded(self):
        report=e.BoundedReport();report.append({'source':'mock'})
        first=report.finish({'observation_result':'NotRun'})
        self.assertEqual(first,report.finish({'observation_result':'Complete'}))
        other=e.BoundedReport()
        with self.assertRaises(ValueError):other.finish({'large':'x'*4096})


if __name__=='__main__':unittest.main(verbosity=2)
