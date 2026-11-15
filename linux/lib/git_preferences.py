"""Read-only Git functionality and recommendation observations, outside projects."""
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass

RECOMMENDATIONS = [('init.defaultBranch', 'main'), ('fetch.prune', 'true'), ('pull.ff', 'only')]
REPOSITORY_ENV = ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE', 'GIT_PREFIX')


@dataclass(frozen=True)
class Probe:
    code: int
    text: str = ''


def diagnostic(arguments, directory):
    environment = {k: v for k, v in os.environ.items() if k not in REPOSITORY_ENV}
    try:
        result = subprocess.run(arguments, cwd=directory, env=environment, capture_output=True,
                                text=True, encoding='utf-8', errors='strict', timeout=3, check=False)
        if len(result.stdout) > 8192 or len(result.stderr) > 8192:
            return Probe(-1)
        return Probe(result.returncode, result.stdout)
    except (OSError, UnicodeError, subprocess.TimeoutExpired):
        return Probe(-1)


def readable_file(path):
    try:
        if not stat.S_ISREG(path.stat().st_mode):
            return False
        with path.open('rb') as stream:
            stream.read(1)
    except FileNotFoundError:
        return not path.is_symlink()
    except OSError:
        return False
    return True


def readable_sources(directory):
    # Git may silently ignore an unreadable global file and return "unset".
    # Check access without collecting the file contents or credential settings.
    if 'GIT_CONFIG_GLOBAL' in os.environ:
        sources = [os.environ['GIT_CONFIG_GLOBAL']]
    else:
        home = Path.home()
        sources = [str(home / '.gitconfig'), str(Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config') / 'git/config')]
    if os.environ.get('GIT_CONFIG_SYSTEM') and os.environ.get('GIT_CONFIG_NOSYSTEM', '').lower() not in ('1', 'true', 'yes', 'on'):
        sources.append(os.environ['GIT_CONFIG_SYSTEM'])
    for source in sources:
        path = Path(source)
        if not path.is_absolute():
            path = Path(directory) / path
        if not readable_file(path):
            return False
    return True


def readable_includes(result, directory):
    if result.code == 1 and result.text == '':
        return True
    fields = result.text.split('\0')
    if result.code != 0 or fields[-1] != '' or len(fields) % 2 != 1 or len(fields) > 65:
        return False
    for origin, value in zip(fields[0:-1:2], fields[1:-1:2]):
        if not origin.startswith('file:') or not value or re.search(r'[\x00-\x1f]', value):
            return False
        path = Path(value)
        if not path.is_absolute():
            source = Path(origin[5:])
            if not source.is_absolute():
                source = Path(directory) / source
            path = source.parent / path
        if not readable_file(path):
            return False
    return True


def verify(run=diagnostic, find=shutil.which):
    preferences = [dict(key=key, recommended=value, status='unreadable', value=None)
                   for key, value in RECOMMENDATIONS]
    record = dict(schema=1, component='Git', status='incomplete', reason='checkUnavailable',
                  version=None, scope='globalOutsideRepository', preferences=preferences)
    try:
        selected = find('git')
        if not selected:
            record.update(status='notFound', reason='notDiscovered')
            return record
        with tempfile.TemporaryDirectory(prefix='sde-git-check-') as directory:
            if not readable_sources(directory):
                record.update(reason='configReadFailed')
                return record
            def query(arguments):
                return run([selected, '--no-pager', '--no-optional-locks', *arguments], directory)

            # --version itself does not need pager/configuration setup.
            result = run([selected, '--version'], directory)
            match = re.fullmatch(r'git version (\d+\.\d+(?:\.\d+)?[A-Za-z0-9.+_-]{0,80})\s*', result.text)
            if result.code != 0 or not match:
                record.update(status='incomplete' if result.code == -1 else 'unusable', reason='commandFailed')
                # Git can reject malformed configuration before even printing
                # its version. Confirm the separate config-read outcome.
                if result.code > 0 and query(['config', '--includes', '--get', 'init.defaultBranch']).code not in (0, 1):
                    record.update(status='incomplete', reason='configReadFailed')
                return record
            record['version'] = match[1]
            # Query one harmless key to parse applicable system/global sources.
            # Do not dump configuration, identity, credential helpers or headers.
            readable = query(['config', '--includes', '--get', 'init.defaultBranch']).code in (0, 1)
            includes = query(['config', '--global', '--includes', '--show-origin', '--null', '--path', '--get-all', 'include.path'])
            readable = readable_includes(includes, directory) and readable
            for preference in preferences:
                arguments = ['config', '--global', '--includes', '--null']
                if preference['key'] == 'fetch.prune':
                    arguments.append('--type=bool')
                result = query([*arguments, '--get', preference['key']])
                if result.code == 1 and result.text == '':
                    preference['status'] = 'unset'
                elif result.code == 0 and result.text.endswith('\0'):
                    value = result.text[:-1]
                    if len(value) <= 512 and not re.search(r'[\x00-\x1f\x7f|]', value):
                        preference.update(value=value, status='matches' if value == preference['recommended'] else 'different')
                if preference['status'] == 'unreadable':
                    readable = False
            record.update(status='passed' if readable else 'incomplete',
                          reason='verified' if readable else 'configReadFailed')
    except (OSError, ValueError, TypeError):
        record.update(status='incomplete', reason='checkUnavailable')
    return record


def report(record):
    print('SKYVIEW_EVENT|preferences|Git|' + json.dumps(record, separators=(',', ':')))
    status = 'PASS' if record['status'] == 'passed' else 'FAIL'
    if status == 'PASS':
        message = 'Git: Git is available. Your existing preferences were preserved.'
    elif record['status'] == 'notFound':
        message = 'Git: SDE could not find Git.'
    elif record['status'] == 'unusable':
        message = 'Git: the Git command did not work. Review the check details.'
    elif record['reason'] == 'configReadFailed':
        message = 'Git: SDE could not finish reading your Git settings. Review the check details.'
    else:
        message = 'Git: SDE could not finish checking Git. Review the check details.'
    print(f'SKYVIEW_EVENT|validation|{status}|{message}')
    print(f'{status}  {message}')
    return 0 if status == 'PASS' else 10


if __name__ == '__main__':
    raise SystemExit(report(verify()))
