"""Optional standard-user-file inspection; never changes editor settings."""
import json
from pathlib import Path
import re
import stat
import sys
import node_runtime

RECOMMENDATIONS = [('editor.formatOnSave', True), ('editor.defaultFormatter', 'esbenp.prettier-vscode'), ('files.eol', '\n')]
REASONS = {'read': ('verified',), 'missing': ('defaults',),
           'unreadable': ('accessDenied', 'readFailed'), 'invalid': ('invalidContents',),
           'unavailable': ('parserUnavailable', 'inspectionLimit', 'locationUnavailable', 'encodingUnavailable')}


def empty_record(path, status='unavailable', reason='parserUnavailable'):
    return dict(schema=1, component='VSCodium', scope='standardUserFile', path=path,
                status=status, reason=reason, recommendations=[])


def observation(text, path):
    try:
        value = json.loads(text)
        if (not isinstance(value, dict) or set(value) != set(empty_record(path))
                or type(value['schema']) is not int or value['schema'] != 1 or value['component'] != 'VSCodium'
                or value['scope'] != 'standardUserFile' or value['path'] != path
                or value['reason'] not in REASONS.get(value['status'], ())
                or not isinstance(value['recommendations'], list)):
            return None
        rows = value['recommendations']
        if value['status'] != 'read':
            return value if rows == [] else None
        if len(rows) != 3:
            return None
        for row, (key, recommended) in zip(rows, RECOMMENDATIONS):
            if (not isinstance(row, dict) or set(row) != {'key', 'recommended', 'status', 'value'}
                    or row['key'] != key or type(row['recommended']) is not type(recommended)
                    or row['recommended'] != recommended or row['status'] not in ('matches', 'different', 'unset')
                    or not (row['value'] is None or type(row['value']) is bool
                            or isinstance(row['value'], str) and len(row['value']) <= 256)):
                return None
            matches = type(row['value']) is type(recommended) and row['value'] == recommended
            if ((row['status'] == 'matches') != matches or row['status'] == 'unset' and row['value'] is not None):
                return None
        return value
    except (ValueError, TypeError, KeyError):
        return None


def verify(path, node, run=node_runtime.diagnostic):
    path = str(path)
    if not node_runtime.safe_path(path):
        return empty_record(None, reason='locationUnavailable')
    result = empty_record(path)
    phase = 'access'
    try:
        # Access/absence can be established even when a parser cannot run.
        info = Path(path).stat()
        if not stat.S_ISREG(info.st_mode):
            return empty_record(path, 'unreadable', 'readFailed')
        with open(path, 'rb') as stream:
            stream.read(1)
        if info.st_size > 1048576:
            return empty_record(path, reason='inspectionLimit')
        phase = 'parser'
        if (not isinstance(node, dict) or not isinstance(node.get('version'), str)
                or not re.fullmatch(r'24\.\d{1,8}\.\d{1,8}', node['version'])
                or not node_runtime.executable(node.get('executable'))):
            return result
        probe = run([node['executable'], str(Path(__file__).with_name('editor_settings_probe.cjs')), path], 2.5)
        if probe.code == 0:
            return observation(probe.text, path) or result
    except FileNotFoundError:
        return empty_record(path, 'missing', 'defaults') if phase == 'access' else result
    except PermissionError:
        return empty_record(path, 'unreadable', 'accessDenied') if phase == 'access' else result
    except (OSError, ValueError, TypeError):
        return empty_record(path, 'unreadable', 'readFailed') if phase == 'access' else result
    return result


def report(record):
    print('SKYVIEW_EVENT|preferences|VSCodium|' + json.dumps(record, separators=(',', ':')))
    if record['status'] == 'read':
        message = 'VSCodium preferences were read. Your choices were preserved; they may differ from the suggestions.'
    elif record['status'] == 'missing':
        message = 'VSCodium has no user preferences file here. It can use its defaults.'
    elif record['reason'] == 'accessDenied':
        message = 'SDE could not open the file that stores your VSCodium preferences because it did not have permission to read it. Your settings have not been changed, and VSCodium may still work normally.'
    elif record['status'] == 'invalid':
        message = 'SDE could open your VSCodium preferences file, but could not understand its contents. Your settings have not been changed.'
    elif record['status'] == 'unreadable':
        message = 'SDE could not read your VSCodium preferences file. Your settings have not been changed; the cause is not yet known.'
    else:
        message = 'SDE could not finish checking your VSCodium preferences. Your settings have not been changed. This does not mean they are missing or damaged.'
    status = 'INFO' if record['status'] in ('read', 'missing') else 'WARNING'
    print(f'SKYVIEW_EVENT|validation|{status}|{message}')
    print(f'{status}  {message}')
    # Optional preferences do not fail independently verified required features.
    return 0 if status == 'INFO' else 20


if __name__ == '__main__':
    try:
        raw = sys.stdin.read(16385)
        node = json.loads(raw) if len(raw) <= 16384 else None
    except (ValueError, TypeError):
        node = None
    raise SystemExit(report(verify(sys.argv[1], node)))
