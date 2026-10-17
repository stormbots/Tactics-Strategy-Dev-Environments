"""Read-only host/media preflight, never boot/provision a VM or fetch a URL."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import tempfile

from .driver import (Native, Stop, require, host_check, media_check, ISO)


def collect(workspace, disposable_ack=False, isolated_console=False, no_mounts=False):
    n = Native()
    data = Path('/etc/os-release').read_text()
    osr = dict(line.split('=', 1) for line in data.splitlines() if '=' in line)
    mem = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    kvm_api = None
    try:
        import fcntl
        fd = os.open('/dev/kvm', os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            kvm_api = fcntl.ioctl(fd, 0xAE00, 0)  # KVM_GET_API_VERSION; no VM created
        finally:
            os.close(fd)
    except OSError:
        pass
    tools = True
    for path in ['/usr/bin/qemu-system-x86_64', '/usr/bin/qemu-img', '/usr/bin/ssh', '/usr/bin/gpg']:
        try:
            n.trusted(Path(path))
            require(Path(path).is_file(), 'Missing preflight tool')
        except (OSError, Stop):
            tools = False
    disk = os.statvfs(workspace)
    return {'os': osr.get('ID', '').strip('"'), 'version': osr.get('VERSION_ID', '').strip('"'),
            'arch': platform.machine(), 'disposable': disposable_ack,
            'kvm_api': kvm_api, 'cpus': os.cpu_count(),
            'available_memory': int(mem.get('MemAvailable', '0 kB').split()[0]) * 1024,
            'available_disk': disk.f_bavail * disk.f_frsize, 'tools_trusted': tools,
            'loopback_console': isolated_console, 'no_host_mounts': no_mounts}


def verify_media(directory, key, pin):
    n = Native()
    # Fresh non-shared GnuPG home; no ambient keyring/config/auto key retrieval.
    with tempfile.TemporaryDirectory(prefix='sde-mint-gpg-') as home:
        args = ['/usr/bin/gpg', '--no-options', '--batch', '--homedir', home,
                '--no-auto-key-retrieve', '--no-autostart', '--status-fd', '1']
        private = Path(home)
        for source, name, limit in [(key, 'key.asc', 65536),
                     (directory/'sha256sum.txt', 'sums', 65536),
                     (directory/'sha256sum.txt.gpg', 'signature', 8192)]:
            data = n.read(source, limit, protected=False)
            with (private/name).open('xb') as target:
                target.write(data)
        code, _ = n.command(args + ['--import', str(private/'key.asc')])
        require(code == 0, 'Mint signing key import failed')
        sums = (private/'sums').read_text(encoding='ascii')
        code, status = n.command(args + ['--verify', str(private/'signature'), str(private/'sums')])
        h = hashlib.sha256()
        size = 0
        fd = os.open(directory/ISO, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(fd, 'rb') as stream:
            require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'Expected regular ISO')
            while block := stream.read(1024 * 1024):
                size += len(block)
                require(size <= 6 * 1024**3, 'ISO size bound')
                h.update(block)
        require(size > 0, 'Empty ISO')
        return media_check(sums, status.decode('ascii'), code, h.hexdigest(), pin)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute-read-only', action='store_true')
    p.add_argument('--workspace', type=Path)
    p.add_argument('--disposable-host-ack', action='store_true')
    p.add_argument('--loopback-console-ack', action='store_true')
    p.add_argument('--no-host-mounts-ack', action='store_true')
    p.add_argument('--media', type=Path)
    p.add_argument('--signing-key', type=Path)
    p.add_argument('--pin')
    a = p.parse_args(argv)
    require(a.execute_read_only and a.workspace, 'Read-only probe requires explicit execution')
    facts = collect(a.workspace, a.disposable_host_ack, a.loopback_console_ack, a.no_host_mounts_ack)
    result = host_check(facts)
    result['observedAndDeclaredFacts'] = facts
    result['declarationsAreAttestation'] = False
    result['hostProbeExecuted'] = True
    if a.media:
        require(a.signing_key and a.pin, 'Media key/pin required')
        result['media'] = verify_media(a.media, a.signing_key, a.pin)
    else:
        result['ready'] = False
        result['blockers'].append('authenticated-media')
    print(json.dumps(result, indent=2))
    return 0 if result['ready'] else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Stop, OSError, ValueError):
        print('Host/media preflight stopped; no VM was provisioned.')
        raise SystemExit(2)
