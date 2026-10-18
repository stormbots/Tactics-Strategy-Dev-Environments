"""Isolated Mint preparation logic. Importing this module has no execution effects.

No CLI, runner/workflow integration, VM launch, disk creation or package executor.
Native ports must be explicitly supplied by a separately reviewed future caller.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import PurePosixPath
import re
from urllib.parse import urljoin, urlsplit
import uuid

BASE = 'https://mirrors.kernel.org/linuxmint/stable/22.3/'
ISO = 'linuxmint-22.3-cinnamon-64bit.iso'
KEY_SHA = '565ca5c2e7cf48a60a2f043af7147e27df13d80779948a46f3cceda4e5dcad9b'
FINGERPRINT = '27DEB15644C6B3CF3BD7D291300F846BA25BAE09'
METADATA_LIMIT = 64 * 1024
SIGNATURE_LIMIT = 8192
ISO_LIMIT = 6 * 1024**3
WORKSPACE_LIMIT = 8 * 1024**3
REPORT_LIMIT = 64 * 1024
CHUNK = 64 * 1024
JOB_SECONDS = 25 * 60


class Stop(Exception):
    """Only fixed reason codes, never native stdout/stderr or credentials."""


def require(ok, code):
    if not ok:
        raise Stop(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical_uuid(value):
    require(type(value) is str, 'RUN_ID')
    try:
        require(str(uuid.UUID(value)) == value, 'RUN_ID')
    except ValueError:
        raise Stop('RUN_ID') from None
    return value


def host_gate(facts):
    require(facts.get('account') == 'sde-runner' and type(facts.get('uid')) is int
            and facts['uid'] >= 1000 and facts.get('euid') == facts['uid'], 'HOST_ACCOUNT')
    require(type(facts.get('groups')) is list and all(type(g) is str for g in facts['groups']) and
            not set(facts['groups']) & {'root', 'sudo', 'admin', 'docker', 'lxd', 'libvirt'}, 'HOST_GROUPS')
    require(facts.get('os') == 'linuxmint' and facts.get('release') == '22.3'
            and facts.get('arch') == 'x86_64', 'HOST_PLATFORM')
    require(type(facts.get('kvm_api')) is int and facts['kvm_api'] == 12, 'HOST_KVM')
    require(facts.get('trusted_tools') is True, 'HOST_TOOLS')
    for name, minimum in [('available_memory', 6 * 1024**3), ('available_disk', 40 * 1024**3)]:
        require(type(facts.get(name)) is int and facts[name] >= minimum, 'HOST_RESOURCES')


def redirected_url(current, location):
    require(type(location) is str and 0 < len(location) <= 1024
            and not any(ord(c) <= 32 or ord(c) >= 127 for c in location), 'REDIRECT')
    target = urljoin(current, location)
    parsed = urlsplit(target)
    require(parsed.scheme == 'https' and parsed.netloc == 'mirrors.kernel.org'
            and parsed.username is None and parsed.password is None
            and not parsed.query and not parsed.fragment
            and parsed.path == urlsplit(current).path, 'REDIRECT_ORIGIN')
    return target


def authenticated_pin(checksums, signature_status, exit_code):
    require(type(checksums) is bytes and 0 < len(checksums) <= METADATA_LIMIT, 'CHECKSUM_SIZE')
    require(type(signature_status) is bytes and len(signature_status) <= 8192
            and type(exit_code) is int and exit_code == 0, 'SIGNATURE')
    try:
        text, status = checksums.decode('ascii'), signature_status.decode('ascii')
    except UnicodeError:
        raise Stop('METADATA_ENCODING') from None
    lines = [line.split() for line in status.splitlines() if line.startswith('[GNUPG:] ')]
    bad = {'BADSIG', 'ERRSIG', 'EXPSIG', 'EXPKEYSIG', 'REVKEYSIG', 'KEYEXPIRED',
           'SIGEXPIRED', 'KEYREVOKED', 'FAILURE', 'ERROR', 'NODATA', 'NO_PUBKEY'}
    require(not any(len(row) > 1 and row[1] in bad for row in lines), 'SIGNATURE_STATE')
    good = [row for row in lines if len(row) > 1 and row[1] == 'VALIDSIG']
    # VALIDSIG fingerprint date timestamp expire version reserved pubkey hash class primary-fpr
    require(len(good) == 1 and len(good[0]) == 12, 'SIGNATURE_COUNT')
    row = good[0]
    require(re.fullmatch('[0-9A-F]{40}', row[2]) is not None
            and row[11] == FINGERPRINT, 'SIGNER')
    matches = []
    for line in text.splitlines():
        if ISO in line:
            match = re.fullmatch(r'([0-9a-f]{64}) [ *]' + re.escape(ISO), line)
            require(match is not None, 'CHECKSUM_FORMAT')
            matches.append(match[1])
    require(len(matches) == 1, 'CHECKSUM_COUNT')
    return matches[0]


@dataclass(frozen=True)
class Transfer:
    """Result of one non-redirecting HTTP attempt; body is written through sink."""
    status: int
    location: str | None
    byte_count: int


class Sink:
    def __init__(self, workspace, name, limit, clock, deadline):
        self.workspace, self.name, self.limit = workspace, name, limit
        self.clock, self.deadline = clock, deadline
        self.count = 0
        self.hash = hashlib.sha256()
        self.small = bytearray() if limit <= METADATA_LIMIT else None
        workspace.create(name)

    def write(self, data):
        require(type(data) is bytes and 0 < len(data) <= CHUNK, 'CHUNK')
        require(self.clock() < self.deadline, 'TRANSFER_DEADLINE')
        require(self.count + len(data) <= self.limit, 'TRANSFER_SIZE')
        self.workspace.write(self.name, data)  # native port checks identity/budget before write
        self.hash.update(data)
        self.count += len(data)
        if self.small is not None:
            self.small.extend(data)

    def finish(self):
        require(self.clock() < self.deadline and self.count > 0, 'TRANSFER_INCOMPLETE')
        self.workspace.seal(self.name)
        self.workspace.verify(self.name, self.count, self.hash.hexdigest(), self.clock, self.deadline)
        return {'size': self.count, 'sha256': self.hash.hexdigest()}


def fetch(name, limit, seconds, workspace, transport, clock, job_deadline):
    deadline = min(job_deadline, clock() + seconds)
    require(clock() < deadline, 'JOB_DEADLINE')
    url = BASE + name
    # Redirects are not retries; no body file is created until a final 200 header.
    sink = None
    def make_sink():
        nonlocal sink
        require(sink is None, 'TRANSFER_REPLAY')
        sink = Sink(workspace, name + '.partial', limit, clock, deadline)
        return sink
    for redirects in range(4):
        result = transport.fetch(url, make_sink, limit, deadline)
        require(clock() < deadline, 'TRANSFER_DEADLINE')
        if result.status in {301, 302, 303, 307, 308}:
            require(sink is None and result.byte_count == 0 and redirects < 3, 'REDIRECT_LIMIT')
            url = redirected_url(url, result.location)
            continue
        require(result.status == 200 and sink is not None
                and result.byte_count == sink.count, 'HTTP_RESULT')
        summary = sink.finish()
        return sink, summary
    raise Stop('REDIRECT_LIMIT')


def checked_root(run_id, root):
    canonical_uuid(run_id)
    path = PurePosixPath(root)
    require(path.is_absolute() and str(path) == root
            and '..' not in path.parts and path.name == run_id
            and path.parent.name == 'mint-validation'
            and all(re.fullmatch(r'[A-Za-z0-9_.-]+', c) for c in path.parts[1:]), 'PLAN_PATH')
    vnc, qmp = str(path/'console.sock'), str(path/'control.sock')
    require(max(len(x.encode()) for x in (vnc, qmp)) <= 100, 'SOCKET_PATH')
    return path, vnc, qmp


def offline_plan(run_id, root, media):
    path, vnc, qmp = checked_root(run_id, root)
    require(media.get('authenticated') is True and media.get('filename') == ISO
            and type(media.get('sha256')) is str
            and re.fullmatch('[0-9a-f]{64}', media['sha256']) is not None, 'PLAN_MEDIA')
    argv = ['/usr/bin/qemu-system-x86_64', '-no-user-config', '-enable-kvm',
            '-m', '4096', '-smp', '2', '-uuid', run_id,
            '-drive', f'file={path}/guest.qcow2,format=qcow2,if=virtio',
            '-cdrom', str(path/ISO), '-boot', 'order=d', '-nic', 'none',
            '-display', 'none', '-vnc', 'unix:' + vnc,
            '-qmp', f'unix:{qmp},server=on,wait=off', '-monitor', 'none', '-serial', 'none']
    return {'schemaVersion': 1, 'kind': 'offline-console-plan', 'runId': run_id,
            'argv': argv, 'mediaSha256': media['sha256'], 'virtualDiskGiB': 30,
            'guestFilesystemWhenInstalled': 'ext4', 'diskCreated': False,
            'qemuStarted': False, 'consoleValidatedNatively': False,
            'launchAuthorized': False, 'requiresBeforeLaunch': [
                'separate-authorization', 'media-and-path-revalidation',
                'exclusive-disk-and-socket-creation', 'owned-controller-process-binding',
                'real-desktop-consent-and-redacted-password-entry', 'owned-process-cleanup']}


def prepare(*, run_id, source_sha, approved_sha, helper_sha, approved_helper_sha, key, facts, workspace, transport, verifier, clock):
    """Call only with explicitly constructed ports. No implicit native activation."""
    canonical_uuid(run_id)
    require(type(source_sha) is str and re.fullmatch('[0-9a-f]{40}', source_sha) is not None
            and source_sha == approved_sha, 'SOURCE_BINDING')
    require(type(helper_sha) is str and re.fullmatch('[0-9a-f]{64}', helper_sha) is not None
            and helper_sha == approved_helper_sha, 'HELPER_BINDING')
    require(type(key) is bytes and 0 < len(key) <= METADATA_LIMIT and sha(key) == KEY_SHA, 'KEY_BINDING')
    host_gate(facts)
    require(workspace.run_id == run_id, 'WORKSPACE_BINDING')
    workspace.check()
    checked_root(run_id, workspace.path)
    deadline = clock() + JOB_SECONDS
    try:
        workspace.store('signing-key.asc', key)
        sums, sums_record = fetch('sha256sum.txt', METADATA_LIMIT, 60, workspace, transport, clock, deadline)
        sig, sig_record = fetch('sha256sum.txt.gpg', SIGNATURE_LIMIT, 60, workspace, transport, clock, deadline)
        require(clock() < deadline, 'JOB_DEADLINE')
        code, status, versions = verifier.verify(key, bytes(sums.small), bytes(sig.small), workspace, deadline)
        require(set(versions) == {'gpg', 'curl'} and all(type(v) is str and 0 < len(v) <= 256
                and v.isascii() and v.isprintable() for v in versions.values()), 'TOOL_VERSION')
        pin = authenticated_pin(bytes(sums.small), status, code)
        workspace.store('authenticated-pin.json', json.dumps({'filename': ISO, 'sha256': pin,
                                                           'fingerprint': FINGERPRINT}).encode())
        # No ISO acquisition before signature and exact-edition validation.
        iso, iso_record = fetch(ISO, ISO_LIMIT, 900, workspace, transport, clock, deadline)
        require(iso_record['sha256'] == pin, 'ISO_DIGEST')
        workspace.promote(ISO + '.partial', ISO)
        media = dict(iso_record, filename=ISO, authenticated=True)
        plan = offline_plan(run_id, workspace.path, media)
        workspace.require_absent(['guest.qcow2', 'console.sock', 'control.sock'])
        require(clock() < deadline, 'JOB_DEADLINE')
        report = {'schemaVersion': 1, 'sourceSha': source_sha,
                  'helperSha256': helper_sha, 'runId': run_id,
                  'media': media, 'sourceUrl': BASE + ISO, 'signer': FINGERPRINT,
                  'keySha256': KEY_SHA, 'checksums': sums_record, 'signature': sig_record,
                  'toolVersions': versions, 'consolePlan': plan,
                  'nativeGuestTestsExecuted': False, 'productionReady': False}
        workspace.finish(report)  # durable report AND ownership manifest, or no Pass
        require(clock() < deadline, 'JOB_DEADLINE')
        return report
    except Exception as error:
        code = str(error) if isinstance(error, Stop) and re.fullmatch('[A-Z][A-Z0-9_]{0,63}', str(error)) else 'NATIVE_FAILURE'
        try:
            workspace.fail(code)
        except Exception:
            raise Stop('EVIDENCE_UNCERTAIN') from None
        raise Stop(code) from None
