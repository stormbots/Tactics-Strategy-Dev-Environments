"""Compile/inspect observer; execute memory-only mock checks. NO native schedules."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
FLAGS=['-std=c11','-O2','-fno-builtin','-fno-tree-loop-distribute-patterns','-Wall','-Wextra','-Werror']
EXPORTS={'recvmsg'}|{'w2n_v1_'+name for name in ('setup','abi','provider','status','arm','freeze','read')}


def run(output):
    report=dict(started=datetime.now(timezone.utc).isoformat(),scope='isolated W2n observer/local checks only',
                environment=dict(platform=platform.platform(),python=sys.version,uid=os.getuid(),gid=os.getgid()),
                commands=[],local_checks_success=False,native_n1='NotRun',native_n2='NotRun',
                w2m_native_m2='Fail (unchanged)',authentication_safety='Unproven',production_readiness=False,
                leak_sanitizer=dict(status='Unavailable in observed sandbox',
                   reason='Initial local attempt reported LeakSanitizer fatal: does not work under ptrace; address/undefined checks run with detect_leaks=0'),
                source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.iterdir() if p.suffix in ('.c','.h','.py')})
    root=Path(tempfile.mkdtemp(prefix='w2n-local-',dir=REPO/'work'))
    report['temporary_root']=str(root)
    original_root=root.stat()
    def command(args,env=None):
        r=subprocess.run(args,cwd=REPO,env=env,capture_output=True,text=True,timeout=30)
        report['commands'].append(dict(argv=[str(x) for x in args],exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr))
        if r.returncode:raise RuntimeError('local command failed: '+str(args[0]))
        return r.stdout
    try:
        if os.getuid()==0:raise RuntimeError('Blocked: run local checks unprivileged')
        for tool in ('cc','nm','objdump','readelf'):
            if not shutil.which(tool):raise RuntimeError('Blocked: existing tool missing: '+tool)
        command(['cc','--version'])
        library=root/'observer.so';unit=root/'check_local';sanitized=root/'check_sanitized'
        command(['cc',*FLAGS,'-fPIC','-fvisibility=hidden','-Wl,-z,now','-Wl,-z,relro','-Wl,-Bsymbolic-functions',
                 '-shared',str(HERE/'observer.c'),'-ldl','-o',str(library)])
        exported=command(['nm','-D','--defined-only',str(library)])
        if {line.split()[-1] for line in exported.splitlines()}!=EXPORTS:raise RuntimeError('unexpected shared-library exports')
        disasm=command(['objdump','-d','--disassemble=recvmsg',str(library)])
        calls=[line for line in disasm.splitlines() if re.search(r'\bcall\b',line)]
        if len([line for line in calls if re.search(r'\bcall\s+\*',line)])!=1 or any(
                not re.search(r'\bcall\s+\*',line) and '<_exit@plt>' not in line for line in calls):
            raise RuntimeError('wrapper has unexpected call sites; review compiler output')
        dynamic=command(['readelf','-d',str(library)])
        if 'BIND_NOW' not in dynamic:raise RuntimeError('missing immediate binding')
        report['linkage_review']=dict(exports=sorted(EXPORTS),wrapper_calls=calls,
            note='one indirect forwarded target; exceptional _exit only; source/linkage review, not interception proof')
        command(['cc',*FLAGS,str(HERE/'check_local.c'),'-o',str(unit)])
        undefined=command(['nm','-u',str(unit)])
        if re.search(r'\b(socket|connect|accept|sendmsg|recvmsg|syscall)(@|$)',undefined,re.M):
            raise RuntimeError('memory-only unit binary unexpectedly imports a native IPC function')
        capture=root/'synthetic-capture.bin'
        c_log=command([str(unit),str(capture)])
        count=re.search(r'local_mock_checks=(\d+); native_receives=0; descriptors_transferred=0',c_log)
        if not count:raise RuntimeError('missing local-check counts')
        report['c_mock_checks']=int(count[1])
        report['synthetic_capture_hex']=capture.read_bytes().hex()
        corpus=Path(str(capture)+'.corpus').read_bytes()
        report['synthetic_corpus']=dict(records=len(corpus)//1536,sha256=hashlib.sha256(corpus).hexdigest())
        env=dict(os.environ);env['W2N_SYNTHETIC_CAPTURE']=str(capture)
        py_log=command([sys.executable,'-m','unittest','discover','-s',str(HERE),'-p','test_evidence.py','-v'],env)
        # unittest progress is on stderr; store it exactly in the command record.
        py_output=report['commands'][-1]['stderr']+py_log
        count=re.search(r'Ran (\d+) tests',py_output)
        if not count:raise RuntimeError('missing Python-check counts')
        report['python_mock_checks']=int(count[1])
        command(['cc',*FLAGS,'-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(HERE/'check_local.c'),'-o',str(sanitized)])
        san_env=dict(os.environ);san_env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';san_env['UBSAN_OPTIONS']='halt_on_error=1'
        command([str(sanitized),str(root/'sanitized-capture.bin')],san_env)
        if capture.read_bytes()!=(root/'sanitized-capture.bin').read_bytes():raise RuntimeError('normal/sanitized synthetic captures disagree')
        if corpus!=Path(str(root/'sanitized-capture.bin')+'.corpus').read_bytes():raise RuntimeError('normal/sanitized mock corpora disagree')
        report['address_undefined_sanitizers']='Pass, same memory-only C checks; LeakSanitizer not validated'
        report['observer_binary_sha256']=hashlib.sha256(library.read_bytes()).hexdigest()
        report['local_checks_success']=True
    except Exception as exc:
        report['failure']=str(exc)
    finally:
        if report['local_checks_success'] and (root.is_symlink() or (root.stat().st_dev,root.stat().st_ino)!=(original_root.st_dev,original_root.st_ino)):
            report['local_checks_success']=False;report['failure']='local temporary root identity changed'
        if report['local_checks_success']:
            shutil.rmtree(root)
            report['cleanup']=dict(temporary_root_removed=not root.exists(),
                note='all local child commands completed; no preloads, sockets, native actors, FD transfers or settings changed')
        else:
            report['cleanup']=dict(temporary_root_removed=False,note='preserved failed local artifacts; no broad cleanup or unknown-process signaling')
        # Output is an explicitly chosen local evidence file; no remote writes.
        output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
        flags=os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW
        fd=os.open(output,flags,0o600)
        with os.fdopen(fd,'w') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:report[k] for k in ('local_checks_success','native_n1','native_n2','authentication_safety','production_readiness')}))
    return 0 if report['local_checks_success'] else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output');args=parser.parse_args()
    sys.exit(run(args.output))
