#!/usr/bin/python3
"""Fixed systemd hooks: persist non-secret service history, never run tools."""
import datetime
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

ROOT = Path('/var/lib/skyview-robotics/self-update')
HISTORY = ROOT / 'maintenance-history.json'


def trusted(path):
    for item in (path, *path.parents):
        m = item.lstat()
        if m.st_uid != 0 or m.st_mode & 0o022 or not (stat.S_ISDIR(m.st_mode) or stat.S_ISREG(m.st_mode)):
            raise RuntimeError('Untrusted maintenance history path')
        if stat.S_ISREG(m.st_mode) and m.st_nlink != 1:
            raise RuntimeError('Linked maintenance history')


def publish(record):
    trusted(ROOT)
    if HISTORY.exists() or HISTORY.is_symlink():
        trusted(HISTORY)
    temp = ROOT / (str(uuid.uuid4()) + '.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(record, stream)
            stream.flush()
            os.fchmod(stream.fileno(), 0o644)
            os.fsync(stream.fileno())
        os.replace(temp, HISTORY)
        fd = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if temp.exists():
            temp.unlink()


def record_attempt(operation, environment):
    invocation = environment.get('INVOCATION_ID', '')
    if not re.fullmatch('[0-9a-f]{32}', invocation):
        raise RuntimeError('Systemd invocation identity required')
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    record = dict(schemaVersion=1, invocation=invocation, startedAt=now,
                  completedAt=None, lastResult='unavailable')
    if operation == 'finish':
        # A failed pre-start hook must also replace a previous success. Do not
        # infer success from missing exit information or a stale worker receipt.
        try:
            trusted(HISTORY)
            previous = json.loads(HISTORY.read_text())
            if previous.get('invocation') == invocation:
                record['startedAt'] = previous['startedAt']
        except (OSError, ValueError, RuntimeError, KeyError):
            pass
        result = environment.get('SERVICE_RESULT')
        code, status = environment.get('EXIT_CODE'), environment.get('EXIT_STATUS')
        if result == 'success' and code == 'exited' and status == '0':
            record['lastResult'] = 'success'
        elif result in ('success', 'exit-code') and code == 'exited' and status == '75':
            record['lastResult'] = 'deferred'
        elif (result and result != 'success') or (code and (code != 'exited' or status != '0')):
            record['lastResult'] = 'failure'
        record['completedAt'] = now
    elif operation != 'start':
        raise RuntimeError('Invalid history operation')
    publish(record)


def main():
    if os.geteuid() != 0 or len(sys.argv) != 2:
        raise RuntimeError('Root systemd history hook required')
    os.umask(0o077)
    record_attempt(sys.argv[1], os.environ)


if __name__ == '__main__':
    main()
