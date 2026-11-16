"""Bounded, ordinary-user PyCharm bundle checks; never installs or opens an IDE."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import time

from editor_location import desktop_executable, limited_file, normal_user, query, safe_path

VERSION = re.compile(r'20\d{2}\.\d{1,2}(?:\.\d{1,3}){0,2}')


def native_header(path, machine):
    with path.open('rb') as stream:
        head = stream.read(20)
    return (len(head) == 20 and head[:6] == b'\x7fELF\x02\x01'
            and int.from_bytes(head[18:20], 'little') == machine)


def empty(status='incomplete', reason='discoveryIncomplete'):
    return dict(schema=1, component='PyCharm', platform='linux', status=status, reason=reason,
                root=None, launcher=None, runtime=None, version=None, runtimeVersion=None,
                productCode=None, selectionId=None, maintenanceEligibility='notEvaluated')


def discover():
    roots, complete = [], True
    registered = []

    def add(root, required=False):
        nonlocal complete
        if not safe_path(str(root)):
            complete = False
        elif str(root) not in roots:
            roots.append(str(root))
        if required:
            registered.append(str(root))

    def launcher(path):
        nonlocal complete
        try:
            target = Path(path).resolve(strict=True)
            if target.name not in ('pycharm', 'pycharm.sh') or target.parent.name != 'bin':
                complete = False
            else:
                add(target.parent.parent, True)
        except (OSError, ValueError, RuntimeError):
            complete = False

    target = shutil.which('pycharm')
    if target:
        launcher(target)
    home = Path.home()
    data = os.environ.get('XDG_DATA_HOME') or str(home / '.local/share')
    directories = [data, *(os.environ.get('XDG_DATA_DIRS') or '/usr/local/share:/usr/share').split(':')]
    if len(directories) > 8:
        complete = False
    for directory in directories[:8]:
        if not safe_path(directory):
            complete = False
            continue
        for name in ('pycharm.desktop', 'jetbrains-pycharm.desktop', 'jetbrains-pycharm-ce.desktop'):
            try:
                text = limited_file(Path(directory) / 'applications' / name, 16384).decode('utf-8')
                target = desktop_executable(text)
                if target:
                    launcher(target)
                else:
                    complete = False
            except FileNotFoundError:
                pass
            except (OSError, ValueError, UnicodeError):
                complete = False
    add(Path('/opt/pycharm'))
    # Known installation parents only: one directory level, never a drive scan.
    for parent in (Path('/opt'), home / '.local/opt', Path(data) / 'JetBrains/Toolbox/apps'):
        try:
            entries = []
            with os.scandir(parent) as scan:
                for index, entry in enumerate(scan):
                    if index >= 256:
                        complete = False
                        break
                    if re.fullmatch(r'(?i)pycharm(?:[-_ ].*)?', entry.name) and entry.is_dir():
                        entries.append(entry.path)
            for path in sorted(entries):
                add(Path(path))
        except FileNotFoundError:
            pass
        except OSError:
            complete = False
    if len(roots) > 12:
        complete = False
    return roots[:12], registered, complete


def layout(candidate):
    root = Path(candidate).resolve(strict=True)
    if not safe_path(str(root)):
        raise ValueError('unsupportedLayout')
    metadata = root / 'product-info.json'
    if metadata.resolve(strict=True) != metadata:
        raise ValueError('unsupportedLayout')
    info = json.loads(limited_file(metadata, 1048576))
    if (not isinstance(info, dict) or info.get('name') not in ('PyCharm', 'PyCharm Community Edition')
            or info.get('productCode') not in ('PC', 'PY') or not isinstance(info.get('version'), str)
            or not VERSION.fullmatch(info['version'])):
        raise ValueError('wrongProduct')
    launches = info.get('launch')
    if not isinstance(launches, list) or len(launches) > 8:
        raise ValueError('unsupportedLayout')
    arch = {'x86_64': 'amd64', 'aarch64': 'aarch64'}.get(platform.machine())
    matches = [v for v in launches if isinstance(v, dict) and v.get('os') == 'Linux'
               and v.get('arch') in (None, arch)]
    if not arch or len(matches) != 1:
        raise ValueError('unsupportedLayout')
    launch = matches[0]
    minimum = info.get('minRequiredJavaVersion')
    if minimum is not None and (type(minimum) is not int or not 1 <= minimum <= 999):
        raise ValueError('unsupportedLayout')
    if launch.get('launcherPath') not in ('bin/pycharm', 'bin/pycharm.sh') or launch.get('javaExecutablePath') != 'jbr/bin/java':
        raise ValueError('unsupportedLayout')
    launcher, runtime = root / launch['launcherPath'], root / 'jbr/bin/java'
    for file in (launcher, runtime):
        if file.resolve(strict=True) != file or not os.access(file, os.X_OK):
            raise ValueError('unsupportedLayout')
    # The launcher is inspected as data; only the fixed bundled Java gets a probe.
    head = limited_file(launcher, 16777216)[:128]
    if not (head.startswith(b'\x7fELF') or head.startswith((b'#!/bin/sh', b'#!/bin/bash', b'#!/usr/bin/env bash'))):
        raise ValueError('unsupportedLayout')
    machine = 62 if arch == 'amd64' else 183
    if head.startswith(b'\x7fELF') and not native_header(launcher, machine):
        raise ValueError('unsupportedLayout')
    if not runtime.is_file() or runtime.stat().st_size > 536870912:
        raise ValueError('unsupportedLayout')
    if not native_header(runtime, machine):
        raise ValueError('unsupportedLayout')
    return root, launcher, runtime, info


def fingerprint(root, launcher, runtime):
    hashes = []
    for file, maximum in ((root / 'product-info.json', 1048576), (launcher, 16777216), (runtime, 536870912)):
        if file.resolve(strict=True) != file or not file.is_file() or file.stat().st_size > maximum:
            raise ValueError('inspectionLimit')
        digest, total = hashlib.sha256(), 0
        with file.open('rb') as stream:
            for block in iter(lambda: stream.read(65536), b''):
                total += len(block)
                if total > maximum:
                    raise ValueError('inspectionLimit')
                digest.update(block)
        hashes.append(digest.hexdigest())
    return hashlib.sha256(('\n'.join(hashes) + '\n' + str(root)).encode()).hexdigest()


def inspect(run=query, find=discover):
    if not normal_user():
        return empty(reason='normalUserRequired')
    record = empty()
    deadline = time.monotonic() + 15
    try:
        roots, required, complete = find()
        incomplete, unusable = not complete or len(roots) > 12, False
        for candidate in roots[:12]:
            try:
                if time.monotonic() >= deadline:
                    incomplete = True
                    break
                root, launcher, runtime, info = layout(candidate)
                before = fingerprint(root, launcher, runtime)
                result = run([str(runtime), '--version'], max(0, min(4, deadline - time.monotonic())))
                version = re.search(r'(?m)^(?:openjdk|java) (\d+(?:\.[0-9]+)*(?:[+_.-][\w.+-]+)?)(?:\s|$)', result.text)
                if (result.code != 0 or not version or 'JBR-' not in result.text
                        or len(version[1]) > 80
                        or int(re.match(r'\d+', version[1])[0]) < (info.get('minRequiredJavaVersion') or 1)):
                    incomplete |= result.code == -1
                    unusable |= result.code != -1
                    record['reason'] = 'runtimeCheckIncomplete' if result.code == -1 else 'runtimeCheckFailed'
                    continue
                if fingerprint(root, launcher, runtime) != before:
                    incomplete = True
                    record['reason'] = 'changedDuringCheck'
                    continue
                return dict(record, status='verified', reason='verified', root=str(root), launcher=str(launcher),
                            runtime=str(runtime), version=info['version'], runtimeVersion=version[1],
                            productCode=info['productCode'], selectionId=before)
            except FileNotFoundError:
                if candidate in required or Path(candidate).exists():
                    incomplete = True
                    record['reason'] = 'staleRegistration'
            except PermissionError:
                incomplete = True
                record['reason'] = 'accessDenied'
            except ValueError as error:
                if str(error) == 'wrongProduct':
                    unusable = True
                    record['reason'] = 'wrongProduct'
                else:
                    incomplete = True
            except (OSError, TypeError, RuntimeError):
                incomplete = True
        return record if incomplete else empty('unusable', record['reason']) if unusable else empty('notFound', 'notDiscovered')
    except (OSError, ValueError, TypeError):
        return record


if __name__ == '__main__':
    record = inspect()
    print('SKYVIEW_EVENT|application|PyCharm|' + json.dumps(record, separators=(',', ':')))
    status = 'PASS' if record['status'] == 'verified' else 'FAIL'
    message = ('PyCharm: ' + record['version'] + '; product and bundled runtime verified' if status == 'PASS'
               else 'PyCharm: The supported search did not find PyCharm.' if record['status'] == 'notFound'
               else 'PyCharm: Open SDE without administrator privileges to check PyCharm.' if record['reason'] == 'normalUserRequired'
               else 'PyCharm: SDE could not finish checking this installation. Review the check details.')
    print(f'SKYVIEW_EVENT|validation|{status}|{message}')
    print(f'{status}  {message}')
    raise SystemExit(0 if status == 'PASS' else 10)
