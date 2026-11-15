"""Bounded, read-only Node 24/associated npm inspection. No manager commands."""
from dataclasses import dataclass
import itertools
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import tempfile
import time

PROBE = str(Path(__file__).with_name('node_runtime_probe.cjs'))
VERSION = re.compile(r'24\.\d{1,8}\.\d{1,8}')


@dataclass(frozen=True)
class Probe:
    code: int
    text: str = ''
    reason: str = 'completed'


def diagnostic(arguments, timeout):
    """Limit both pipes while reading; only our own diagnostic group is stopped."""
    if timeout <= 0:
        return Probe(-1, reason='timeout')
    environment = {k: v for k, v in os.environ.items()
                   if k not in ('NODE_OPTIONS', 'NODE_PATH', 'NODE_COMPILE_CACHE', 'NODE_V8_COVERAGE')
                   and not k.lower().startswith('npm_config_')}
    environment.update(npm_config_update_notifier='false', npm_config_ignore_scripts='true',
                       npm_config_audit='false', npm_config_fund='false')
    try:
        with tempfile.TemporaryDirectory(prefix='sde-node-check-') as directory:
            environment.update(npm_config_cache=str(Path(directory) / 'cache'), npm_config_logs_max='0')
            # Distinct empty configs avoid reading student/global npm settings.
            for kind in ('user', 'global'):
                config = Path(directory) / (kind + '.npmrc')
                config.write_text('')
                environment['npm_config_' + kind + 'config'] = str(config)
            with subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  env=environment, cwd=directory, start_new_session=True) as process:
                def stop(reason):
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    return Probe(-1, reason=reason)

                try:
                    with selectors.DefaultSelector() as selector:
                        selector.register(process.stdout, selectors.EVENT_READ, 0)
                        selector.register(process.stderr, selectors.EVENT_READ, 1)
                        buffers = [bytearray(), bytearray()]
                        deadline = time.monotonic() + timeout
                        while selector.get_map():
                            remaining = deadline - time.monotonic()
                            if remaining <= 0:
                                return stop('timeout')
                            for key, _ in selector.select(remaining):
                                data = os.read(key.fileobj.fileno(), 4096)
                                if not data:
                                    selector.unregister(key.fileobj)
                                else:
                                    buffers[key.data].extend(data)
                                    if len(buffers[key.data]) > 16384:
                                        return stop('invalidOutput')
                        try:
                            code = process.wait(timeout=max(.001, deadline - time.monotonic()))
                        except subprocess.TimeoutExpired:
                            return stop('timeout')
                        return Probe(code, buffers[0].decode('utf-8', errors='strict').strip())
                finally:
                    if process.poll() is None:
                        stop('unavailable')
    except (OSError, UnicodeError):
        return Probe(-1, reason='unavailable')


def safe_path(value):
    return (isinstance(value, str) and 0 < len(value) <= 4096 and value.startswith('/')
            and not re.search(r'[\x00-\x1f\x7f|]', value)
            and '\\' not in value and str(Path(value)) == value
            and '..' not in Path(value).parts)


def executable(value):
    if not safe_path(value) or not Path(value).is_file() or not os.access(value, os.X_OK):
        return False
    # Do not execute shell wrappers or source runtime-manager initialization.
    with open(value, 'rb') as stream:
        return stream.read(4) == b'\x7fELF'


def discover():
    candidates, complete = [], True

    def add(path):
        nonlocal complete
        if not safe_path(str(path)):
            complete = False
            return
        try:
            if path.absolute() == volta / 'bin/node' or '/shims/' in str(path):
                complete = False
                return
            resolved = path.resolve(strict=True)
            # Known acquisition/selection shims must not execute during checks.
            if '/shims/' in str(resolved) or resolved.name in ('volta', 'volta-shim'):
                complete = False
                return
            if not executable(str(resolved)):
                complete = False
            elif str(resolved) not in candidates:
                if len(candidates) < 12:
                    candidates.append(str(resolved))
                else:
                    complete = False
        except FileNotFoundError:
            if path.is_symlink():
                complete = False
        except (OSError, ValueError, RuntimeError):
            complete = False

    home = Path.home()
    volta = Path(os.environ.get('VOLTA_HOME') or home / '.volta').absolute()
    stores = [(Path(os.environ.get('NVM_DIR') or home / '.nvm') / 'versions/node', 'bin/node'),
              (volta / 'tools/image/node', 'bin/node'),
              (Path(os.environ.get('FNM_DIR') or Path(os.environ.get('XDG_DATA_HOME') or home / '.local/share') / 'fnm') / 'node-versions', 'installation/bin/node'),
              (home / '.fnm/node-versions', 'installation/bin/node')]
    for store, suffix in stores:
        if not safe_path(str(store)):
            complete = False
            continue
        try:
            with os.scandir(store) as entries:
                entries = list(itertools.islice(entries, 65))
            if len(entries) > 64:
                complete = False
            versions = sorted((entry.name for entry in entries[:64]
                               if re.fullmatch(r'v?24\.\d{1,8}\.\d{1,8}', entry.name)), reverse=True)
            if len(versions) > 8:
                complete = False
            for version in versions[:8]:
                add(store / version / suffix)
        except FileNotFoundError:
            pass
        except OSError:
            complete = False
    for candidate in (Path('/usr/bin/node'), Path('/usr/local/bin/node')):
        add(candidate)
    fallback = shutil.which('node')
    if fallback:
        add(Path(fallback))
    return candidates, complete


def npm_paths(selected):
    path = Path(selected)
    if path.parent.name != 'bin' or path.name != 'node':
        return set()
    paths = {str(path.parent.parent / 'lib/node_modules/npm/bin/npm-cli.js')}
    if selected == '/usr/bin/node':
        paths.add('/usr/share/nodejs/npm/bin/npm-cli.js')
    return paths


def verify(run=diagnostic, find=discover):
    record = dict(schema=1, component='Node.js', requiredFamily='24', status='incomplete',
                  reason='discoveryIncomplete', version=None, executable=None,
                  npmVersion=None, npmCli=None, maintenanceEligibility='notEvaluated')
    deadline = time.monotonic() + 15

    def query(arguments):
        remaining = max(0, min(2.5, deadline - time.monotonic()))
        return run(arguments, remaining) if remaining else Probe(-1, reason='timeout')

    def identity(probe):
        try:
            value = json.loads(probe.text)
            if (probe.code == 0 and isinstance(value, dict) and set(value) == {'version', 'executable'}
                    and isinstance(value['version'], str) and re.fullmatch(r'\d{1,8}\.\d{1,8}\.\d{1,8}', value['version'])
                    and executable(value['executable'])):
                return value
        except (ValueError, TypeError, OSError):
            pass
        return None

    try:
        candidates, complete = find()
        incomplete, unusable = not complete or len(candidates) > 12, False
        # Preserve selected failure evidence if a later unrelated candidate fails.
        for candidate in candidates[:12]:
            if not executable(candidate):
                incomplete = True
                continue
            probe = query([candidate, PROBE, 'identity'])
            value = identity(probe)
            if not value:
                incomplete |= probe.reason != 'completed' or probe.code == 0
                unusable |= probe.code != 0 and probe.reason == 'completed'
                continue
            if not VERSION.fullmatch(value['version']):
                continue
            selected = str(Path(value['executable']).resolve(strict=True))
            confirmed = identity(query([selected, PROBE, 'identity']))
            if not confirmed or confirmed['version'] != value['version'] or not os.path.samefile(selected, confirmed['executable']):
                incomplete = True
                continue
            record.update(version=confirmed['version'], executable=selected)
            probe = query([selected, PROBE, 'npm'])
            try:
                npm = json.loads(probe.text)
                valid = (probe.code == 0 and isinstance(npm, dict)
                         and set(npm) == {'version', 'executable', 'npmVersion', 'npmCli'}
                         and npm['version'] == record['version'] and npm['executable'] == selected
                         and safe_path(npm['npmCli']) and npm['npmCli'] in npm_paths(selected)
                         and isinstance(npm['npmVersion'], str)
                         and re.fullmatch(r'[0-9][A-Za-z0-9.!+_-]{0,119}', npm['npmVersion']))
            except (ValueError, TypeError):
                valid = False
            if valid:
                probe = query([selected, npm['npmCli'], '--version', '--ignore-scripts', '--no-update-notifier',
                               '--no-audit', '--no-fund'])
                valid = probe.code == 0 and probe.text == npm['npmVersion']
            if valid:
                record.update(status='passed', reason='verified', npmVersion=npm['npmVersion'], npmCli=npm['npmCli'])
                return record
            if probe.reason != 'completed':
                incomplete = True
                record.update(reason='npmTimeout' if probe.reason == 'timeout' else 'discoveryIncomplete')
            else:
                unusable = True
                record.update(reason='npmFailed')
        record['status'] = 'incomplete' if incomplete else 'unusable' if unusable else 'notFound'
        if record['status'] == 'notFound':
            record.update(reason='notDiscovered', version=None, executable=None)
        elif record['reason'] == 'discoveryIncomplete' and not incomplete:
            record['reason'] = 'nodeFailed'
        return record
    except (OSError, ValueError, TypeError, RuntimeError):
        record.update(status='incomplete', reason='discoveryIncomplete')
        return record


def report(record):
    print('SKYVIEW_EVENT|runtime|Node.js|' + json.dumps(record, separators=(',', ':')))
    status = 'PASS' if record['status'] == 'passed' else 'FAIL'
    if status == 'PASS':
        message = f'Node.js: Node {record["version"]} and its npm {record["npmVersion"]} verified'
    elif record['status'] == 'notFound':
        message = 'Node.js: the supported search did not find Node 24. Other versions can stay installed.'
    elif record['status'] == 'incomplete':
        message = 'Node.js: SDE could not finish checking Node 24 and its npm. This does not mean they are missing.'
    elif record['reason'] == 'npmFailed':
        message = 'Node.js: Node 24 was found, but its npm did not pass the check. Review the check details.'
    else:
        message = 'Node.js: a required Node check did not work. Review the check details.'
    print(f'SKYVIEW_EVENT|validation|{status}|{message}')
    print(f'{status}  {message}')
    return 0 if status == 'PASS' else 10


if __name__ == '__main__':
    raise SystemExit(report(verify()))
