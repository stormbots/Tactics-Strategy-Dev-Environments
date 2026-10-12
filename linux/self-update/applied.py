"""Embedded supervisor. Lease acquisition precedes reading the applied baseline."""
import importlib.util
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('sde_coordination', HERE / 'coordination.py')
coord = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coord)


def trusted(path):
    for item in (path, *path.parents):
        m = item.lstat()
        if m.st_uid != 0 or m.st_mode & 0o022 or not (stat.S_ISDIR(m.st_mode) or stat.S_ISREG(m.st_mode)):
            raise coord.CoordinationError('Untrusted applied baseline')
        if stat.S_ISREG(m.st_mode) and m.st_nlink != 1:
            raise coord.CoordinationError('Linked applied baseline')


def main():
    if os.geteuid() != 0:
        raise coord.CoordinationError('Root maintenance required')
    if sys.argv[1:] == []:
        # Child inherits real held descriptors, never a boolean bypass flag.
        return coord.run('system', ['/usr/bin/python3', '-I', str(HERE / 'applied.py'), '--leased'])
    if sys.argv[1:] != ['--leased']:
        raise coord.CoordinationError('Invalid maintenance invocation')
    coord.check()
    snapshot = HERE / 'applied-baseline'
    snapshot.mkdir(mode=0o700)
    (snapshot / 'lib').mkdir(mode=0o700)
    files = {'update.sh': Path('/usr/local/sbin/skyview-student-dev-update')}
    files.update({f'lib/{name}': Path('/usr/local/lib/skyview-student-dev') / name for name in ('common.sh', 'tool_records.py', 'coordination.sh', 'coordination.py')})
    try:
        for name, source in files.items():
            trusted(source)
            shutil.copyfile(source, snapshot / name)
        result = subprocess.run(['/bin/bash', str(snapshot / 'update.sh')], pass_fds=(int(os.environ[coord.SESSION]), int(os.environ[coord.OPERATION])), check=False)
        if result.returncode < 0:
            # Propagate only an already-finished child's signal so the outer
            # coordinator retains uncertain intent; never terminate package work.
            os.kill(os.getpid(), -result.returncode)
            raise coord.CoordinationError('Unknown child completion')
        return result.returncode
    finally:
        for name in files:
            path = snapshot / name
            if path.exists():
                path.unlink()
        (snapshot / 'lib').rmdir()
        snapshot.rmdir()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except BlockingIOError:
        sys.exit(75)
    except (coord.CoordinationError, OSError, ValueError, KeyError):
        print('Applied maintenance unavailable; mentor review required', file=sys.stderr)
        sys.exit(76)
