# SDE_COORDINATION_V1
# SDE_COORDINATION_ADMISSION_V2
"""Fixed machine gates; never elevates or interprets state as commands.

The Bash entry points supervise their children here. Inherited descriptors retain
leases if a supervising process dies. A root-owned journal survives crashes/reboot
and blocks another mutation even if a package child closed inherited descriptors.
"""
import errno
import fcntl
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import uuid

ROOT = Path('/var/lib/skyview-robotics-coordination')
JOURNAL = ROOT / 'transaction.json'
SESSION = 'SKYVIEW_SESSION_FD'
OPERATION = 'SKYVIEW_OPERATION_FD'

class CoordinationError(Exception):
    pass

def directories():
    for path in (ROOT, *ROOT.parents):
        m = path.lstat()
        if not stat.S_ISDIR(m.st_mode) or m.st_uid != 0 or m.st_mode & 0o022:
            raise CoordinationError('Untrusted SDE coordination directory.')

def trusted(m):
    return (stat.S_ISREG(m.st_mode) and m.st_uid == 0 and
            not m.st_mode & 0o222 and m.st_nlink == 1 and m.st_size == 0)

def gate(name, shared, inherited=None):
    directories()
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    probe = os.open(ROOT / name, flags)
    try:
        expected = os.fstat(probe)
        if not trusted(expected):
            raise CoordinationError('Untrusted SDE coordination gate.')
        if inherited is not None:
            fd = int(inherited)
            if fd < 3:
                raise CoordinationError('Invalid inherited SDE gate.')
            actual = os.fstat(fd)
            if not trusted(actual) or (actual.st_dev, actual.st_ino) != (expected.st_dev, expected.st_ino):
                raise CoordinationError('Invalid inherited SDE gate.')
            fd = os.dup(fd)
        else:
            fd = os.dup(probe)
    finally:
        os.close(probe)
    try:
        fcntl.flock(fd, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
        return fd
    except BaseException:
        os.close(fd)
        raise

def check():
    # A boolean environment flag is never sufficient to bypass acquisition.
    leases = []
    try:
        leases.append(gate('sessions.gate', True, os.environ[SESSION]))
        leases.append(gate('operations.gate', False, os.environ[OPERATION]))
    finally:
        for fd in leases:
            os.close(fd)

def no_interruption():
    # Scope alone is also a recovery barrier. Never ignore inaccessible state.
    for path in (JOURNAL, ROOT / 'installation-scope.json'):
        try:
            path.lstat()
        except FileNotFoundError:
            continue
        raise CoordinationError('An interrupted system operation needs mentor review before another change.')

def admitted_session(inherited=None):
    no_interruption()
    # An existing GUI retains S; asking it to enter A again would block normal
    # operations during Ready. Its inherited descriptor still needs validation.
    admission = None if inherited is not None else gate('admission.gate', True)
    session = None
    try:
        no_interruption()
        session = gate('sessions.gate', True, inherited)
        no_interruption()
        result, session = session, None
        return result
    finally:
        if session is not None:
            os.close(session)
        if admission is not None:
            os.close(admission)

def sync_directory():
    fd = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def run(mode, command):
    session = admitted_session(os.environ.get(SESSION))
    operation = None
    journal = False
    try:
        env = {**os.environ, SESSION: str(session)}
        leases = [session]
        if mode != 'session':
            operation = gate('operations.gate', False)
            leases.append(operation)
            no_interruption()
            env[OPERATION] = str(operation)
            if mode == 'system':
                if os.geteuid() != 0:
                    raise CoordinationError('System operations require administrator authentication.')
                fd = os.open(JOURNAL, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
                with os.fdopen(fd, 'w') as stream:
                    json.dump(dict(schema=1, id=str(uuid.uuid4()), pid=os.getpid(), kind='system'), stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                sync_directory()
                journal = True
        else:
            env.pop(OPERATION, None)
        result = subprocess.run(command, env=env, pass_fds=tuple(leases), check=False)
        # A normal nonzero exit is a completed failed attempt; a signal or wrapper
        # crash is uncertain and leaves the protected journal for mentor recovery.
        if journal and result.returncode >= 0:
            JOURNAL.unlink()
            sync_directory()
        return result.returncode if result.returncode >= 0 else 1
    finally:
        if operation is not None:
            os.close(operation)
        os.close(session)

def main():
    try:
        if sys.argv[1:] == ['check']:
            check()
            return 0
        if len(sys.argv) >= 4 and sys.argv[1] == 'run' and sys.argv[2] in ('session', 'operation', 'system'):
            return run(sys.argv[2], sys.argv[3:])
        raise CoordinationError('Invalid SDE coordination invocation.')
    except BlockingIOError:
        print('SKYVIEW_EVENT|warning|deferred|SDE is busy. Maintenance will retry at its next scheduled invocation.', file=sys.stderr)
        return 75
    except (CoordinationError, OSError, ValueError, KeyError) as error:
        # Never include caller-controlled paths or environment values in diagnostics.
        message = str(error) if isinstance(error, CoordinationError) else 'SDE coordination is unavailable. Install or repair the application first.'
        print('SKYVIEW_EVENT|error|coordination|' + message, file=sys.stderr)
        return 76

if __name__ == '__main__':
    sys.exit(main())
