"""Fixed future checkout-only diagnostic. No native ports or repository imports.

Only bounded source/metadata reads and sanitized stdout; no chmod, registration,
process launch, network, KVM, media, package, guest or workspace-creation path.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import pwd
import grp
import re
import stat
import sys
import time

REPO = 'stormbots/Tactics-Strategy-Dev-Environments'
WORKFLOW = REPO + '/.github/workflows/mint-checkout-validation.yml@refs/heads/main'
SOURCES = ('tests/observe_mint_checkout.py', 'tests/run_mint_media_console.py',
           'tests/mint_media_console.py', 'tests/mint_media_native.py',
           'tests/start_mint_preparation_runner.py', 'tests/fixtures/linuxmint-iso-signing.asc')
LIMIT = 128 * 1024
EXPORT_LIMIT = 64 * 1024


class Stop(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Stop(reason)


def context(env):
    need(env.get('GITHUB_ACTIONS') == 'true' and env.get('GITHUB_EVENT_NAME') == 'workflow_dispatch' and
         env.get('GITHUB_REPOSITORY') == REPO and env.get('GITHUB_REF') == 'refs/heads/main' and
         env.get('GITHUB_WORKFLOW_REF') == WORKFLOW and env.get('GITHUB_JOB') == 'observe', 'CONTEXT')
    source = env.get('GITHUB_SHA','')
    need(re.fullmatch('[0-9a-f]{40}',source) is not None and
         source == env.get('CHECKOUT_APPROVED_SHA') == env.get('CHECKOUT_WORKFLOW_SHA'), 'SOURCE_BINDING')
    need(env.get('CHECKOUT_ENABLED') == 'true' and env.get('CHECKOUT_ACCESS_READY') == 'verified', 'ACTIVATION')
    digest = env.get('CHECKOUT_BUNDLE_SHA256','')
    need(re.fullmatch('[0-9a-f]{64}',digest) is not None, 'BUNDLE_APPROVAL')
    need(env.get('GITHUB_RUN_ATTEMPT') == '1' and
         re.fullmatch('[1-9][0-9]{0,19}',env.get('GITHUB_RUN_ID','')) is not None, 'RUN_CONTEXT')
    return source,digest


def signature(info):
    return (info.st_dev,info.st_ino,info.st_uid,info.st_mode,info.st_nlink,
            info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def read_regular(path, uid, limit, clock, deadline, expected=None):
    need(clock() < deadline, 'DEADLINE')
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_NOCTTY|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_uid == uid and before.st_nlink == 1 and
             not stat.S_IMODE(before.st_mode) & 0o022 and 0 < before.st_size <= limit, 'SOURCE_FILE')
        need(expected is None or signature(before) == signature(expected), 'SOURCE_CHANGED')
        raw=bytearray()
        while len(raw) <= limit:
            need(clock() < deadline, 'DEADLINE')
            block=os.read(fd,min(65536,limit+1-len(raw)))
            if not block:break
            raw.extend(block)
        need(len(raw) == before.st_size and signature(before) == signature(os.fstat(fd)), 'SOURCE_CHANGED')
        need(clock() < deadline, 'DEADLINE')
        return bytes(raw)
    finally:
        try:os.close(fd)
        except OSError:raise Stop('DESCRIPTOR_CLEANUP_UNCERTAIN') from None


def source_snapshot(root, name, uid, session, evidence, clock, deadline):
    path=root/name
    for parent in reversed(path.parents):
        need(clock() < deadline, 'DEADLINE')
        info=parent.lstat()
        private=parent == session or session in parent.parents
        acl='system.posix_acl_default' in os.listxattr(parent,follow_symlinks=False) if private else False
        row={'path':str(parent),'uid':info.st_uid,'mode':format(stat.S_IMODE(info.st_mode),'04o'),
             'defaultAcl':acl,'device':info.st_dev,'inode':info.st_ino}
        need(len(evidence['paths']) < 32 or str(parent) in evidence['paths'], 'EVIDENCE_BOUND')
        old=evidence['paths'].setdefault(str(parent),row)
        need(old == row, 'ANCESTRY_CHANGED')
        need(stat.S_ISDIR(info.st_mode) and info.st_uid in {0,uid} and
             not stat.S_IMODE(info.st_mode) & 0o022, 'SOURCE_OWNER')
        if private:
            need(info.st_uid == uid and stat.S_IMODE(info.st_mode) == 0o700 and not acl, 'PRIVATE_DIRECTORY')
    before=path.lstat()
    evidence['files'].append({'path':name,'uid':before.st_uid,
        'mode':format(stat.S_IMODE(before.st_mode),'04o'),'bytes':before.st_size})
    need(len(evidence['files']) <= len(SOURCES), 'EVIDENCE_BOUND')
    need(stat.S_ISREG(before.st_mode) and before.st_uid == uid and
         not stat.S_IMODE(before.st_mode) & 0o077, 'SOURCE_FILE')
    raw=read_regular(path,uid,LIMIT,clock,deadline,expected=before)
    evidence['files'][-1]['sha256']=hashlib.sha256(raw).hexdigest()
    return raw


def observed_umask(clock, deadline):
    # This fixed kernel path intentionally uses /proc/self; never dump its contents.
    need(clock() < deadline, 'DEADLINE')
    fd=os.open('/proc/self/status',os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
    try:
        raw=os.read(fd,16385)
        need(0 < len(raw) <= 16384 and clock() < deadline, 'STATUS_BOUND')
        values=re.findall(rb'^Umask:\s*([0-7]{4})$',raw,re.MULTILINE)
        need(len(values) == 1, 'UMASK_MISSING')
        return values[0].decode('ascii')
    finally:
        try:os.close(fd)
        except OSError:raise Stop('DESCRIPTOR_CLEANUP_UNCERTAIN') from None


def bundle_digest(snapshots):
    digest=hashlib.sha256(b'mint-checkout-bundle-v1\0')
    for name in SOURCES:
        raw=snapshots[name]
        digest.update(name.encode()+b'\0'+str(len(raw)).encode()+b'\0'+raw)
    return digest.hexdigest()


def run(env, evidence, *, snapshot=source_snapshot, mask=observed_umask, reader=read_regular, clock=time.monotonic):
    source,approved=context(env)
    evidence.update(sourceSha=source,workflowSha=env['CHECKOUT_WORKFLOW_SHA'],
                    runId=env['GITHUB_RUN_ID'],attempt=1,job='observe',paths={},files=[])
    uid=os.getuid();who=pwd.getpwuid(uid)
    need(uid >= 1000 and os.geteuid() == uid and who.pw_name == 'sde-runner', 'ACCOUNT')
    groups={grp.getgrgid(g).gr_name for g in set(os.getgroups())|{os.getgid()}}
    need(len(groups) <= 64 and all(type(g) is str and 0 < len(g) <= 64 and
         g.isascii() and g.isprintable() for g in groups) and
         not groups & {'root','sudo','admin','docker','lxd','libvirt'}, 'GROUPS')
    need(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'PLATFORM')
    root=Path(__file__).absolute().parents[1]
    home=Path(who.pw_dir)
    need(home.is_absolute() and '..' not in home.parts, 'HOME_PATH')
    session=home/'mint-prep-runner-private-session'
    expected=session/'_work-private'/'Tactics-Strategy-Dev-Environments'/'Tactics-Strategy-Dev-Environments'
    need(root == expected and env.get('GITHUB_WORKSPACE') == str(root), 'WORKSPACE_LOCATION')
    deadline=clock()+30
    evidence['effectiveUmask']=mask(clock,deadline)
    need(evidence['effectiveUmask'] == '0077', 'UMASK')
    # Fixed root-owned host metadata; no KVM, tool invocation or native media imports.
    info=reader(Path('/etc/linuxmint/info'),0,8192,clock,deadline)
    releases=re.findall(rb'^RELEASE=["\']?([^"\'\r\n]+)["\']?$',info,re.MULTILINE)
    need(releases == [b'22.3'], 'MINT_RELEASE')
    evidence['hostRelease']='22.3';evidence['uid']=uid
    evidence['account']=who.pw_name;evidence['groups']=sorted(groups)
    snapshots={name:snapshot(root,name,uid,session,evidence,clock,deadline) for name in SOURCES}
    observed=bundle_digest(snapshots)
    evidence['bundleSha256']=observed
    need(observed == approved, 'BUNDLE_BINDING')
    need(clock() < deadline, 'DEADLINE')


def export(evidence, passed, reason):
    record={'kind':'checkout-permissions-only','pass':passed,'reason':reason,'evidence':evidence,
        'mediaAuthentication':'NotRun','guestExecuted':False,'productionReady':False,
        'cleanupCorrectness':'NotValidated','wholeHostCleanupPerformed':False}
    raw=json.dumps(record,sort_keys=True,ensure_ascii=True)
    if len(raw.encode('ascii')) > EXPORT_LIMIT:
        raw=json.dumps({'kind':'checkout-permissions-only','pass':False,'reason':'EXPORT_BOUND',
                        'mediaAuthentication':'NotRun','productionReady':False,'guestExecuted':False,
                        'cleanupCorrectness':'NotValidated','wholeHostCleanupPerformed':False})
        return raw,1
    return raw,0 if passed else 1


def main():
    evidence={}
    try:
        need(len(sys.argv) == 1, 'NO_ARGUMENTS')
        run(os.environ,evidence)
        raw,code=export(evidence,True,'CHECKOUT_VALIDATED')
    except Exception as error:
        reason=str(error) if isinstance(error,Stop) else 'OBSERVATION_STOPPED'
        raw,code=export(evidence,False,reason)
    print(raw)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
