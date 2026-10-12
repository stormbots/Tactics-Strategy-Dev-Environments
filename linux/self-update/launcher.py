#!/usr/bin/python3
"""Fixed root launcher; private snapshots survive package file replacement."""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import uuid

ROOT = Path('/var/lib/skyview-robotics/self-update')


def trusted(path):
    for item in (path, *path.parents):
        m = item.lstat()
        if m.st_uid != 0 or m.st_mode & 0o022 or not (stat.S_ISDIR(m.st_mode) or stat.S_ISREG(m.st_mode)):
            raise RuntimeError('Untrusted maintenance path')
        if stat.S_ISREG(m.st_mode) and m.st_nlink != 1:
            raise RuntimeError('Linked maintenance file')


def main():
    if os.geteuid() != 0 or len(sys.argv) != 1:
        raise RuntimeError('Root maintenance required')
    os.umask(0o077)
    for name in ('active.json', 'engines', 'runs', 'logs'):
        trusted(ROOT / name)
    active = json.loads((ROOT / 'active.json').read_text())
    generation = active['generation']
    if active['schemaVersion'] != 1 or str(uuid.UUID(generation)) != generation:
        raise RuntimeError('Invalid engine receipt')
    run = ROOT / 'runs' / str(uuid.uuid4())
    run.mkdir(mode=0o700)
    code = 1
    log = ROOT / 'logs' / (run.name + '.log')
    try:
        for name in ('sde-update-trust', 'version.json'):
            source = ROOT / 'engines' / generation / name
            trusted(source)
            shutil.copyfile(source, run / name)
        (run / 'sde-update-trust').chmod(0o700)
        version = json.loads((run / 'version.json').read_text())
        if version != dict(schemaVersion=1, version=active['version']):
            raise RuntimeError('Snapshot receipt mismatch')
        with log.open('xb') as stream:
            result = subprocess.run([str(run / 'sde-update-trust'), 'maintain-linux'], env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'HOME': '/root', 'LC_ALL': 'C'}, stdout=stream, stderr=subprocess.STDOUT, check=False)
        code = result.returncode if result.returncode >= 0 else 1
        # A killed worker has unknown children; preserve its snapshot for review.
        if result.returncode >= 0:
            for name in ('sde-update-trust', 'version.json', 'coordination.py', 'applied.py'):
                path = run / name
                if path.exists():
                    trusted(path)
                    path.unlink()
            run.rmdir()
    finally:
        completed = []
        for path in (ROOT / 'logs').glob('*.log'):
            if str(uuid.UUID(path.stem)) == path.stem and not (ROOT / 'runs' / path.stem).exists():
                trusted(path)
                completed.append(path)
        for path in sorted(completed, key=lambda p: p.stat().st_mtime, reverse=True)[8:]:
            path.unlink()
    return code


if __name__ == '__main__':
    sys.exit(main())
