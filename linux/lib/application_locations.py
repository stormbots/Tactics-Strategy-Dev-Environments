"""Read-only DBeaver/browser discovery. Records never grant launch/update authority."""
import configparser
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import time
import zipfile

from editor_location import desktop_executable, limited_file, normal_user, query, safe_path
from pycharm_location import native_header

TOOLS = ('DBeaver', 'Chrome', 'Firefox')
NAMES = {'DBeaver': ('dbeaver', 'dbeaver-ce'), 'Chrome': ('google-chrome', 'google-chrome-stable', 'chrome'),
         'Firefox': ('firefox', 'firefox-esr', 'firefox-bin', 'firefox.sh')}
KNOWN = {'DBeaver': ('/usr/share/dbeaver-ce', '/usr/lib/dbeaver', '/opt/dbeaver'),
         'Chrome': ('/opt/google/chrome',), 'Firefox': ('/usr/lib/firefox', '/usr/lib/firefox-esr', '/opt/firefox')}
DESKTOP = {'DBeaver': ('dbeaver.desktop', 'dbeaver-ce.desktop'), 'Chrome': ('google-chrome.desktop',),
           'Firefox': ('firefox.desktop', 'firefox-esr.desktop')}


def empty(tool, status='incomplete', reason='discoveryIncomplete'):
    return dict(schema=1, component=tool, platform='linux', status=status, reason=reason, root=None,
                executable=None, version=None, runtimeVersion=None, selectionId=None,
                verificationScope=None, maintenanceEligibility='notEvaluated')


def discover(tool):
    roots, required = [], []
    complete = True

    def launcher(path):
        nonlocal complete
        try:
            target = Path(path).resolve(strict=True)
            if target.name not in NAMES[tool]:
                complete = False
                return
            root = target.parent
            if str(root) not in roots:
                roots.append(str(root))
            required.append(str(root))
        except (OSError, ValueError, RuntimeError):
            complete = False

    for name in NAMES[tool]:
        target = shutil.which(name)
        if target:
            launcher(target)
    home = Path.home()
    data = os.environ.get('XDG_DATA_HOME') or str(home / '.local/share')
    folders = [data, *(os.environ.get('XDG_DATA_DIRS') or '/usr/local/share:/usr/share').split(':')]
    if len(folders) > 8:
        complete = False
    for folder in folders[:8]:
        if not safe_path(folder):
            complete = False
            continue
        for name in DESKTOP[tool]:
            try:
                target = desktop_executable(limited_file(Path(folder) / 'applications' / name, 16384).decode('utf-8'))
                if target:
                    launcher(target)
                else:
                    complete = False
            except FileNotFoundError:
                pass
            except (OSError, ValueError, UnicodeError):
                complete = False
    candidates = [*roots, *KNOWN[tool], str(home / '.local/opt' / tool.lower())]
    if tool == 'Chrome':
        candidates.append(str(home / '.local/opt/google/chrome'))
    unique = list(dict.fromkeys(candidates))
    return unique[:12], required, complete and len(unique) <= 12


def checked(root, relative, maximum, executable=False):
    target = root / relative
    resolved = target.resolve(strict=True)
    if resolved != target:
        if not executable or not resolved.is_relative_to(root):
            raise ValueError('unsupportedLayout')
        target = resolved
    if not target.is_file() or target.stat().st_size > maximum:
        raise ValueError('unsupportedLayout')
    if executable:
        machine = {'x86_64': 62, 'aarch64': 183}.get(platform.machine())
        if not machine or not os.access(target, os.X_OK) or not native_header(target, machine):
            raise ValueError('unsupportedLayout')
    return target


def properties(text):
    values = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith(('#', '!')):
            continue
        if '=' not in line:
            raise ValueError('metadataIncomplete')
        key, value = line.split('=', 1)
        if key.strip() in values:
            raise ValueError('metadataIncomplete')
        values[key.strip()] = value.strip()
    return values


def dbeaver_layout(root):
    executable = checked(root, 'dbeaver', 67108864, True)
    product_file = checked(root, '.eclipseproduct', 65536)
    product = properties(limited_file(product_file, 65536).decode('utf-8'))
    if (product.get('name') != 'DBeaver' or product.get('id') != 'org.jkiss.dbeaver.product'
            or len(product.get('version', '')) > 80 or not re.fullmatch(r'\d+\.\d+\.\d+(?:\.\d+)?', product.get('version', ''))):
        raise ValueError('wrongProduct')
    ini_file = checked(root, 'dbeaver.ini', 65536)
    lines = [line.strip() for line in limited_file(ini_file, 65536).decode('utf-8').splitlines() if line.strip()]
    def flag(name, default=None):
        indexes = [i for i, value in enumerate(lines) if value == name]
        if not indexes:
            return default
        if len(indexes) != 1 or indexes[0] + 1 >= len(lines):
            raise ValueError('unsupportedLayout')
        return lines[indexes[0] + 1]
    startup = flag('-startup')
    if not startup or not re.fullmatch(r'plugins/org\.(?:jkiss\.dbeaver|eclipse\.equinox)\.launcher_[A-Za-z0-9_.-]+\.jar', startup):
        raise ValueError('unsupportedLayout')
    jar = checked(root, startup, 67108864)
    with zipfile.ZipFile(jar) as archive:
        info = archive.getinfo('META-INF/MANIFEST.MF')
        if info.file_size > 65536:
            raise ValueError('inspectionLimit')
        with archive.open(info) as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError('inspectionLimit')
        manifest = raw.decode('utf-8').replace('\r\n ', '').replace('\n ', '')
        symbolic = re.search(r'(?m)^Bundle-SymbolicName: ([^;\r\n]+)', manifest)
        if not symbolic or symbolic[1] not in ('org.jkiss.dbeaver.launcher', 'org.eclipse.equinox.launcher'):
            raise ValueError('wrongProduct')
    vm = flag('-vm', 'jre/bin/java')
    if vm and Path(vm).is_absolute():
        vm = str(Path(vm).relative_to(root))
    if vm.endswith('/bin'):
        vm += '/java'
    if (not vm.endswith('/bin/java') or vm.startswith('/') or '..' in vm.split('/')
            or any(part in ('', '.') for part in vm.split('/')) or not safe_path(str(root / vm))):
        raise ValueError('unsupportedLayout')
    runtime = checked(root, vm, 536870912, True)
    minimums = [int(m[1]) for line in lines if (m := re.fullmatch(r'-Dosgi\.requiredJavaVersion=(\d{1,3})', line))]
    if len(minimums) > 1:
        raise ValueError('metadataIncomplete')
    return executable, product['version'], runtime, minimums[0] if minimums else 1, [product_file, ini_file, jar]


def firefox_metadata(root):
    file = checked(root, 'application.ini', 65536)
    info = configparser.ConfigParser(interpolation=None, strict=True)
    info.read_string(limited_file(file, 65536).decode('utf-8'))
    app = info['App']
    version = re.fullmatch(r'(\d+(?:\.\d+){1,3})(?:esr)?', app.get('Version', ''))
    if (app.get('Name') != 'Firefox' or app.get('ID', '').lower() != '{ec8030f7-c20a-464f-9b0e-13a3a9e97384}'
            or len(app.get('Version', '')) > 80 or not version):
        raise ValueError('wrongProduct')
    return version[1], file


def fingerprint(files, root):
    hashes = []
    for file in files:
        if file.resolve(strict=True) != file or not file.is_file():
            raise ValueError('changedDuringCheck')
        digest, total = hashlib.sha256(), 0
        with file.open('rb') as stream:
            for block in iter(lambda: stream.read(65536), b''):
                total += len(block)
                if total > 536870912:
                    raise ValueError('inspectionLimit')
                digest.update(block)
        hashes.append(digest.hexdigest())
    return hashlib.sha256(('\n'.join(hashes) + '\n' + str(root)).encode()).hexdigest()


def inspect(tool, run=query, find=discover):
    if not normal_user():
        return empty(tool, reason='normalUserRequired')
    if tool == 'Chrome' and platform.machine() != 'x86_64':
        return empty(tool, 'notApplicable', 'unsupportedPlatform')
    record = empty(tool)
    deadline = time.monotonic() + 15
    try:
        candidates, required, complete = find(tool)
        incomplete, unusable = not complete or len(candidates) > 12, False
        for candidate in candidates[:12]:
            try:
                if time.monotonic() >= deadline:
                    incomplete = True
                    break
                root = Path(candidate).resolve(strict=True)
                if not safe_path(str(root)):
                    raise ValueError('unsupportedLayout')
                runtime, minimum, files = None, None, []
                if tool == 'DBeaver':
                    executable, version, runtime, minimum, files = dbeaver_layout(root)
                elif tool == 'Firefox':
                    name = next((name for name in ('firefox', 'firefox-esr', 'firefox-bin') if (root / name).exists()), 'firefox')
                    executable = checked(root, name, 536870912, True)
                    version, metadata = firefox_metadata(root)
                    files = [metadata]
                else:
                    executable, version = checked(root, 'chrome', 536870912, True), None
                files = [executable, *files, *([runtime] if runtime else [])]
                before = fingerprint(files, root)
                output = run([str(runtime or executable), '--version'], max(0, min(4, deadline - time.monotonic())))
                if output.code != 0:
                    incomplete |= output.code == -1
                    unusable |= output.code != -1
                    record['reason'] = 'commandFailed'
                    continue
                runtime_version = None
                if tool == 'DBeaver':
                    match = re.search(r'(?m)^(?:openjdk|java) (\d+(?:\.\d+)*(?:[+_.-][\w.+-]+)?)(?:\s|$)', output.text)
                    if not match or len(match[1]) > 80 or int(re.match(r'\d+', match[1])[0]) < minimum:
                        raise ValueError('runtimeCheckFailed')
                    runtime_version = match[1]
                else:
                    pattern = r'(?m)^Google Chrome (\d+(?:\.\d+){3})\s*$' if tool == 'Chrome' else r'(?m)^Mozilla Firefox (\d+(?:\.\d+){1,3})(?:esr)?\s*$'
                    matches = re.findall(pattern, output.text)
                    if len(matches) != 1 or (version and matches[0] != version):
                        raise ValueError('wrongProduct')
                    version = matches[0]
                    if len(version) > 80:
                        raise ValueError('wrongProduct')
                if fingerprint(files, root) != before:
                    raise ValueError('changedDuringCheck')
                return dict(record, status='verified', reason='verified', root=str(root), executable=str(executable),
                            version=version, runtimeVersion=runtime_version, selectionId=before,
                            verificationScope='productAndRuntime' if runtime else 'productAndVersion')
            except FileNotFoundError:
                if candidate in required or Path(candidate).exists():
                    incomplete = True
                    record['reason'] = 'staleRegistration'
            except PermissionError:
                incomplete = True
                record['reason'] = 'accessDenied'
            except ValueError as error:
                if str(error) in ('wrongProduct', 'runtimeCheckFailed'):
                    unusable = True
                    record['reason'] = str(error)
                else:
                    incomplete = True
                    record['reason'] = 'changedDuringCheck' if str(error) == 'changedDuringCheck' else 'inspectionIncomplete'
            except (OSError, TypeError, KeyError, RuntimeError, configparser.Error, zipfile.BadZipFile):
                incomplete = True
        return record if incomplete else empty(tool, 'unusable', record['reason']) if unusable else empty(tool, 'notFound', 'notDiscovered')
    except (OSError, ValueError, TypeError):
        return record


if __name__ == '__main__':
    failures = 0
    for tool in TOOLS:
        record = inspect(tool)
        print('SKYVIEW_EVENT|application|' + tool + '|' + json.dumps(record, separators=(',', ':')))
        status = 'PASS' if record['status'] == 'verified' else 'WARNING' if record['status'] == 'notApplicable' else 'FAIL'
        failures += status == 'FAIL'
        message = (f'{tool}: {record["version"]}; product and version evidence verified' if status == 'PASS'
                   else f'{tool}: automated Chrome parity is only enforced on amd64.' if status == 'WARNING'
                   else f'{tool}: The supported search did not find {tool}.' if record['status'] == 'notFound'
                   else f'{tool}: Open SDE without administrator privileges to check this app.' if record['reason'] == 'normalUserRequired'
                   else f'{tool}: SDE could not finish checking this installation. Review the check details.')
        print(f'SKYVIEW_EVENT|validation|{status}|{message}')
        print(f'{status}  {message}')
    raise SystemExit(10 if failures else 0)
