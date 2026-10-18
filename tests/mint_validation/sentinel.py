#!/usr/bin/python3 -I
"""TEST ONLY. No package/network/command executor. Fixed 30s root-owned barrier."""
import json
import os
from pathlib import Path
import sys
import stat
import time
import uuid


def main():
    if os.geteuid() != 0 or sys.argv[1:] != ['app-only-linux']:
        raise RuntimeError('Fixed test-only sentinel invocation required')
    run = Path(__file__).absolute().parent
    if run.parent != Path('/var/lib/skyview-robotics/self-update/app-only/runs') or str(uuid.UUID(run.name)) != run.name:
        raise RuntimeError('Invalid sentinel snapshot')
    for path in (run, *run.parents):
        m = path.lstat()
        if m.st_uid != 0 or m.st_mode & 0o022 or not path.is_dir() or path.is_symlink():
            raise RuntimeError('Untrusted sentinel directory')
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    start = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]
    record = {'schemaVersion': 1, 'testOnly': True, 'pid': os.getpid(), 'startTicks': int(start),
              'bootId': boot, 'uid': os.geteuid(), 'ppid': os.getppid(),
              'sid': os.getsid(0), 'pgid': os.getpgid(0)}
    fd = os.open(run / 'sentinel-probe.tmp', os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(json.dumps(record).encode()); f.flush(); os.fsync(f.fileno())
    os.replace(run/'sentinel-probe.tmp', run/'sentinel.json')
    until = time.clock_gettime(time.CLOCK_BOOTTIME) + 30
    while time.clock_gettime(time.CLOCK_BOOTTIME) < until:
        try:
            m = (run / 'release-sentinel').lstat()
            if m.st_uid != 0 or m.st_mode & 0o077 or not stat.S_ISREG(m.st_mode) or m.st_nlink != 1:
                raise RuntimeError('Invalid sentinel release')
            ended = dict(record, outcome='released')
            fd = os.open(run/'sentinel-ended.tmp', os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as f:
                f.write(json.dumps(ended).encode()); f.flush(); os.fsync(f.fileno())
            os.replace(run/'sentinel-ended.tmp', run/'sentinel-ended.json')
            return
        except FileNotFoundError:
            time.sleep(0.02)
    raise RuntimeError('Test-only sentinel barrier deadline expired')


if __name__ == '__main__':
    main()
