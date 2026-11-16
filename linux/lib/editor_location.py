"""Linux bundled VSCodium discovery and fixed CLI checks. No maintenance authority."""
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

FILES = ('resources/app/product.json', 'resources/app/package.json', 'resources/app/out/cli.js')
LIMITS = (1048576, 1048576, 16777216)
VERSION = re.compile(r'\d+\.\d+\.\d+(?:\.\d+)?')


@dataclass(frozen=True)
class Probe:
    code: int
    text: str = ''


def normal_user():
    return os.geteuid() != 0


def safe_path(value):
    return (isinstance(value, str) and 0 < len(value) <= 4096 and value.startswith('/')
            and not re.search(r'[\x00-\x1f\x7f|]', value))


def query(arguments, timeout):
    if timeout <= 0:
        return Probe(-1)
    environment = {k: v for k, v in os.environ.items()
                   if k not in ('NODE_OPTIONS', 'NODE_PATH', 'NODE_COMPILE_CACHE', 'NODE_V8_COVERAGE',
                                'ELECTRON_RUN_AS_NODE', 'VSCODE_DEV', 'VSCODE_CWD')}
    environment['ELECTRON_RUN_AS_NODE'] = '1'
    try:
        with tempfile.TemporaryDirectory(prefix='sde-editor-check-') as directory:
            with subprocess.Popen(arguments, cwd=directory, env=environment, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
                try:
                    with selectors.DefaultSelector() as selector:
                        selector.register(process.stdout, selectors.EVENT_READ, 0)
                        selector.register(process.stderr, selectors.EVENT_READ, 1)
                        buffers = [bytearray(), bytearray()]
                        deadline = time.monotonic() + timeout
                        while selector.get_map():
                            remaining = deadline - time.monotonic()
                            if remaining <= 0:
                                return Probe(-1)
                            for key, _ in selector.select(remaining):
                                block = os.read(key.fileobj.fileno(), 4096)
                                if not block:
                                    selector.unregister(key.fileobj)
                                else:
                                    buffers[key.data].extend(block)
                                    if len(buffers[key.data]) > 32768:
                                        return Probe(-1)
                        try:
                            code = process.wait(timeout=max(.001, deadline - time.monotonic()))
                        except subprocess.TimeoutExpired:
                            return Probe(-1)
                        return Probe(code, buffers[0].decode('utf-8', errors='strict').strip())
                finally:
                    if process.poll() is None:
                        # Only this fixed diagnostic process, never an installer.
                        process.kill()
    except (OSError, UnicodeError):
        return Probe(-1)


def desktop_executable(text):
    """Read one desktop Exec target; never evaluate its arguments or shell text."""
    active = False
    found = []
    for line in text.splitlines():
        if line.startswith('['):
            active = line.strip() == '[Desktop Entry]'
        elif active and line.startswith('Exec='):
            value = line[5:].lstrip()
            if value.startswith('"'):
                match = re.match(r'^"((?:[^"\\]|\\["\\`$])+)"(?:\s|$)', value)
                target = re.sub(r'\\(["\\`$])', r'\1', match[1]) if match else None
                remainder = value[match.end():] if match else ''
            else:
                parts = value.split(None, 1)
                target = parts[0] if parts else None
                remainder = parts[1] if len(parts) == 2 else ''
            # Profile or environment arguments would select a different editor
            # context. Unsupported launchers are incomplete, never evaluated.
            if (not safe_path(target) or any(argument not in
                    ('%f', '%F', '%u', '%U', '--unity-launch', '--reuse-window', '--new-window')
                    for argument in remainder.split())):
                return None
            found.append(target)
    return found[0] if len(found) == 1 else None


def discover():
    roots, complete = [], True
    reason = 'discoveryIncomplete'

    def root_from_launcher(launcher):
        nonlocal complete, reason
        try:
            target = Path(launcher).resolve(strict=True)
            if target.name != 'codium':
                complete = False
                return
            root = target.parent.parent if target.parent.name == 'bin' else target.parent
            add(root)
        except FileNotFoundError:
            complete = False
            reason = 'staleRegistration'
        except PermissionError:
            complete = False
            reason = 'accessDenied'
        except (OSError, ValueError, RuntimeError):
            complete = False

    def add(root):
        nonlocal complete
        if not safe_path(str(root)):
            complete = False
        elif str(root) not in roots:
            if len(roots) < 12:
                roots.append(str(root))
            else:
                complete = False

    target = shutil.which('codium')
    if target:
        root_from_launcher(target)
    home = Path.home()
    data = Path(os.environ.get('XDG_DATA_HOME') or home / '.local/share')
    directories = [data, *map(Path, (os.environ.get('XDG_DATA_DIRS') or '/usr/local/share:/usr/share').split(':'))]
    if len(directories) > 8:
        complete = False
    for directory in directories[:8]:
        if not safe_path(str(directory)):
            complete = False
            continue
        for name in ('codium.desktop', 'vscodium.desktop'):
            file = directory / 'applications' / name
            try:
                raw = limited_file(file, 16384)
                launcher = desktop_executable(raw.decode('utf-8', errors='strict'))
                if launcher:
                    root_from_launcher(launcher)
                else:
                    complete = False
            except FileNotFoundError:
                pass
            except (OSError, UnicodeError, ValueError):
                complete = False
    for root in (home / '.local/opt/VSCodium', home / '.local/share/VSCodium',
                 Path('/usr/share/codium'), Path('/usr/lib/codium'), Path('/opt/vscodium')):
        add(root)
    return roots, complete, reason


def limited_file(path, limit):
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise ValueError('inspectionLimit')
    with path.open('rb') as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError('inspectionLimit')
    return content


def metadata(root):
    root = Path(root).resolve(strict=True)
    executable = root / 'codium'
    info = executable.stat()
    if not safe_path(str(executable)) or not os.access(executable, os.X_OK):
        raise ValueError('unusableLauncher')
    if not stat.S_ISREG(info.st_mode) or info.st_size > 536870912 or executable.resolve(strict=True) != executable:
        raise ValueError('unsupportedLayout')
    with executable.open('rb') as stream:
        if stream.read(4) != b'\x7fELF':
            raise ValueError('unsupportedLayout')
    for relative in FILES:
        path = root / relative
        if path.resolve(strict=True) != path:
            raise ValueError('unsupportedLayout')
    product = json.loads(limited_file(root / FILES[0], LIMITS[0]))
    package = json.loads(limited_file(root / FILES[1], LIMITS[1]))
    if (not isinstance(product, dict) or product.get('nameShort') != 'VSCodium'
            or product.get('applicationName') != 'codium' or product.get('quality') != 'stable'
            or not isinstance(package, dict) or not isinstance(package.get('version'), str)
            or not VERSION.fullmatch(package['version'])):
        raise ValueError('wrongProduct')
    limited_file(root / FILES[2], LIMITS[2])
    return root, executable, package['version']


def selection_id(root):
    executable = root / 'codium'
    hashes = []
    for path, limit in [(executable, 536870912), *[(root / file, limit) for file, limit in zip(FILES, LIMITS)]]:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError('inspectionLimit')
        digest = hashlib.sha256()
        total = 0
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(65536), b''):
                total += len(block)
                if total > limit:
                    raise ValueError('inspectionLimit')
                digest.update(block)
        hashes.append(digest.hexdigest())
    return hashlib.sha256(('\n'.join(hashes) + '\n' + str(executable)).encode()).hexdigest()


def empty_record(reason='discoveryIncomplete', status='incomplete'):
    return dict(schema=1, component='VSCodium', platform='linux', status=status, reason=reason,
                root=None, executable=None, cli=None, version=None, electronVersion=None,
                selectionId=None, maintenanceEligibility='notEvaluated')


def inspect(run=query, find=discover):
    record = empty_record()
    if not normal_user():
        return empty_record('normalUserRequired')
    deadline = time.monotonic() + 15
    def probe(arguments, maximum):
        return run(arguments, max(0, min(maximum, deadline - time.monotonic())))
    try:
        roots, complete, discovery_reason = find()
        record['reason'] = discovery_reason
        incomplete, unusable = not complete or len(roots) > 12, False
        for candidate in roots[:12]:
            try:
                root, executable, version = metadata(candidate)
                identity = probe([str(executable), str(Path(__file__).with_name('editor_identity.cjs'))], 6)
                value = json.loads(identity.text) if identity.code == 0 else None
                template = empty_record()
                if (not isinstance(value, dict) or set(value) != set(template) or type(value['schema']) is not int or value['schema'] != 1
                        or value['component'] != 'VSCodium' or value['platform'] != 'linux'
                        or value['status'] != 'candidate' or value['reason'] != 'identityObserved'
                        or value['maintenanceEligibility'] != 'notEvaluated'
                        or value['root'] != str(root) or value['executable'] != str(executable)
                        or value['cli'] != str(root / FILES[2]) or value['version'] != version
                        or not isinstance(value['electronVersion'], str)
                        or not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][\w.-]+)?', value['electronVersion'])
                        or value['selectionId'] != selection_id(root)):
                    incomplete |= identity.code == -1 or identity.code == 0
                    unusable |= identity.code not in (0, -1)
                    continue
                result = probe([str(executable), str(root / FILES[2]), '--version'], 3)
                if result.code != 0 or result.text.splitlines()[:1] != [version]:
                    incomplete |= result.code == -1
                    unusable |= result.code != -1
                    continue
                if selection_id(root) != value['selectionId']:
                    incomplete = True
                    record['reason'] = 'changedDuringCheck'
                    continue
                value.update(status='verified', reason='verified')
                return value
            except FileNotFoundError:
                if Path(candidate).exists():
                    incomplete = True
                    record['reason'] = 'staleRegistration'
            except PermissionError:
                incomplete = True
                record['reason'] = 'accessDenied'
            except ValueError as error:
                if str(error) in ('wrongProduct', 'unusableLauncher', 'unsupportedLayout'):
                    unusable = True
                    record['reason'] = str(error)
                else:
                    incomplete = True
            except (OSError, TypeError, KeyError, RuntimeError):
                incomplete = True
        if incomplete:
            return record
        return empty_record(record['reason'] if record['reason'] in ('wrongProduct', 'unusableLauncher', 'unsupportedLayout') else 'commandFailed', 'unusable') if unusable else empty_record('notDiscovered', 'notFound')
    except (OSError, ValueError, TypeError):
        return record


def validation(policy):
    record = inspect()
    print('SKYVIEW_EVENT|application|VSCodium|' + json.dumps(record, separators=(',', ':')))
    failures = 0
    def result(status, message):
        nonlocal failures
        failures += status == 'FAIL'
        print(f'SKYVIEW_EVENT|validation|{status}|{message}')
        print(f'{status}  {message}')
    if record['status'] != 'verified':
        message = ('The supported search did not find VSCodium.' if record['status'] == 'notFound'
                   else 'Open SDE without administrator privileges to check your editor.' if record['reason'] == 'normalUserRequired'
                   else 'SDE could not finish checking this editor installation. Review the check details.')
        result('FAIL', 'VSCodium: ' + message)
        return 10
    result('PASS', f'VSCodium: {record["version"]}; application identity and selected launcher verified')
    try:
        required = [line.strip() for line in limited_file(Path(policy), 65536).decode('utf-8').splitlines() if line.strip() and not line.lstrip().startswith('#')]
        if not required or any(not re.fullmatch(r'[A-Za-z0-9_-]+\.[A-Za-z0-9_.-]+', item) for item in required):
            raise ValueError('policy')
        output = query([record['executable'], record['cli'], '--list-extensions'], 6)
        if output.code != 0 or selection_id(Path(record['root'])) != record['selectionId']:
            result('FAIL', 'VSCodium: SDE could not finish checking the installed extensions.')
        else:
            installed = {item.lower() for item in output.text.splitlines()}
            for extension in required:
                result('PASS' if extension.lower() in installed else 'FAIL', 'VSCodium extension missing: ' + extension if extension.lower() not in installed else 'VSCodium extension installed: ' + extension)
    except (OSError, ValueError, UnicodeError):
        result('FAIL', 'VSCodium: SDE could not read or verify the required extension list.')
    return 10 if failures else 0


if __name__ == '__main__':
    if sys.argv[1:] == ['--json']:
        print(json.dumps(inspect(), separators=(',', ':')))
    elif len(sys.argv) == 3 and sys.argv[1] == '--validate':
        raise SystemExit(validation(sys.argv[2]))
    else:
        raise SystemExit(2)
