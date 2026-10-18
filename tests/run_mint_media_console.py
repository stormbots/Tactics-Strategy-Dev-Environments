"""Fixed future workflow caller. Never invoke during mocked-only validation.

No CLI arguments, URLs, shell commands, QEMU launch, package or cleanup executor.
Only the reviewed Actions workflow may activate the native ports.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

REPO = 'stormbots/Tactics-Strategy-Dev-Environments'
WORKFLOW = REPO + '/.github/workflows/mint-media-console-prep.yml@refs/heads/main'
SOURCES = ('tests/run_mint_media_console.py', 'tests/mint_media_console.py',
           'tests/mint_media_native.py', 'tests/fixtures/linuxmint-iso-signing.asc')
FILE_LIMIT = 128 * 1024
EXPORT_LIMIT = 64 * 1024


class GateError(Exception):
    pass


def need(ok, code):
    if not ok:
        raise GateError(code)


def context(env):
    """Values supplied by the fixed workflow, not dispatch inputs or CLI args."""
    need(env.get('GITHUB_ACTIONS') == 'true' and
         env.get('GITHUB_EVENT_NAME') == 'workflow_dispatch' and
         env.get('GITHUB_REPOSITORY') == REPO and
         env.get('GITHUB_REF') == 'refs/heads/main' and
         env.get('GITHUB_WORKFLOW_REF') == WORKFLOW, 'WORKFLOW_CONTEXT')
    source = env.get('GITHUB_SHA', '')
    need(re.fullmatch('[0-9a-f]{40}', source) is not None and
         source == env.get('PREP_APPROVED_SHA') == env.get('PREP_WORKFLOW_SHA'), 'SOURCE_BINDING')
    need(env.get('PREP_ENABLED') == 'true' and env.get('PREP_ACCESS_READY') == 'verified', 'ACTIVATION')
    digest = env.get('PREP_APPROVED_HELPERS_SHA256', '')
    need(re.fullmatch('[0-9a-f]{64}', digest) is not None, 'HELPER_APPROVAL')
    for name in ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT'):
        need(re.fullmatch('[1-9][0-9]{0,19}', env.get(name, '')) is not None, 'RUN_CONTEXT')
    need(env.get('GITHUB_RUN_ATTEMPT') == '1', 'NO_RERUN')
    need(env.get('GITHUB_JOB') == 'prepare', 'RUN_CONTEXT')
    return source, digest


def read_source(root, name):
    """Bounded non-symlink source snapshots; no writable/shared source ancestry."""
    parts = Path(name).parts
    need(root.is_absolute() and '..' not in root.parts, 'SOURCE_ROOT')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        uid = os.getuid()
        for part in (*root.parts[1:], *parts[:-1]):
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd); fd = nxt
            st = os.fstat(fd)
            need(st.st_uid in {0, uid} and not stat.S_IMODE(st.st_mode) & 0o022, 'SOURCE_OWNER')
        leaf = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
        try:
            before = os.fstat(leaf)
            need(stat.S_ISREG(before.st_mode) and before.st_uid in {0, uid} and
                 before.st_nlink == 1 and not stat.S_IMODE(before.st_mode) & 0o022 and
                 0 < before.st_size <= FILE_LIMIT, 'SOURCE_FILE')
            raw = bytearray()
            while len(raw) <= FILE_LIMIT:
                block = os.read(leaf, min(65536, FILE_LIMIT + 1 - len(raw)))
                if not block:
                    break
                raw.extend(block)
            after = os.fstat(leaf)
            need(len(raw) == before.st_size and len(raw) <= FILE_LIMIT and
                 (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                 (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'SOURCE_CHANGED')
            return bytes(raw)
        finally:
            os.close(leaf)
    finally:
        os.close(fd)


def bundle_digest(snapshots):
    # Versioned unambiguous framing in fixed source order, including this caller.
    digest = hashlib.sha256(b'mint-prep-bundle-v1\0')
    for name in SOURCES:
        raw = snapshots[name]
        digest.update(name.encode('ascii') + b'\0' + str(len(raw)).encode('ascii') + b'\0' + raw)
    return digest.hexdigest()


def load_ports(snapshots):
    """Execute approved in-memory snapshots, avoiding a second import by path."""
    import types
    need('mint_media_console' not in sys.modules and 'mint_media_native' not in sys.modules,
         'PRELOADED_HELPERS')
    installed = []
    try:
        for name in ('mint_media_console', 'mint_media_native'):
            module = types.ModuleType(name)
            sys.modules[name] = module
            installed.append(name)
            exec(compile(snapshots['tests/' + name + '.py'], '<approved-' + name + '>', 'exec'), module.__dict__)
    except BaseException:
        for name in installed:
            sys.modules.pop(name, None)
        raise
    return sys.modules['mint_media_console'], sys.modules['mint_media_native']


def ownership_record(workspace):
    fd = workspace._file('ownership.json')
    raw = os.pread(fd, EXPORT_LIMIT + 1, 0)
    need(0 < len(raw) <= EXPORT_LIMIT, 'EXPORT_SIZE')
    workspace._file('ownership.json')
    record = json.loads(raw)
    need(record.get('runId') == workspace.run_id and record.get('cleanupPerformed') is False,
         'EXPORT_OWNERSHIP')
    return record


def run(env, *, reader=read_source, loader=load_ports, run_uuid=uuid.uuid4, observation=None):
    source, approved = context(env)  # gate before any source/host/workspace access
    root = Path(__file__).absolute().parents[1]
    snapshots = {name: reader(root, name) for name in SOURCES}
    need(bundle_digest(snapshots) == approved, 'HELPER_BINDING')
    core, native = loader(snapshots)
    facts = native.collect_host()
    core.host_gate(facts)
    run_id = str(uuid.UUID(str(run_uuid())))
    if observation is not None:
        observation['runId'] = run_id
    with native.Workspace(run_id) as workspace:
        report = core.prepare(run_id=run_id, source_sha=source, approved_sha=source,
            helper_sha=approved, approved_helper_sha=approved,
            key=snapshots['tests/fixtures/linuxmint-iso-signing.asc'], facts=facts,
            workspace=workspace, transport=native.CurlTransport(),
            verifier=native.GpgVerifier(), clock=native.time.monotonic)
        ownership = ownership_record(workspace)
        export = {'report': report, 'ownership': ownership,
                  'actions': {'runId': env['GITHUB_RUN_ID'], 'attempt': env['GITHUB_RUN_ATTEMPT'],
                              'job': env['GITHUB_JOB'], 'sourceSha': source},
                  'host': facts, 'wholeHostCleanupPerformed': False}
        raw = json.dumps(export, sort_keys=True, ensure_ascii=True)
        need(len(raw.encode('ascii')) <= EXPORT_LIMIT, 'EXPORT_SIZE')
    # A close error prevents a success export. No token/env/tool stderr is printed.
    return raw


def main():
    observation = {}
    try:
        need(len(sys.argv) == 1, 'NO_ARGUMENTS')
        print(run(os.environ, observation=observation))
        return 0
    except Exception as error:
        core = sys.modules.get('mint_media_console')
        controlled = isinstance(error, GateError) or (core is not None and isinstance(error, core.Stop))
        code = str(error) if controlled and re.fullmatch('[A-Z][A-Z0-9_]{0,63}', str(error)) else 'PREPARATION_STOPPED'
        print(json.dumps({'pass': False, 'reason': code, 'ownedRunId': observation.get('runId'),
                          'nativeGuestTestsExecuted': False,
                          'productionReady': False, 'cleanupCorrectness': 'NotConfirmed'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
