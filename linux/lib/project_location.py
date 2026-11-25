"""Read-only working-folder verification. Not remote identity or Save authority."""
import json
import os
from pathlib import Path
import re
import shutil
import sys
from editor_location import normal_user, query, safe_path


def inspect(path, run=query):
    result = dict(schema=1, status='incomplete', reason='inspectionIncomplete', root=None)
    if not normal_user():
        return dict(result, reason='normalUserRequired')
    if not safe_path(path) or re.search(r'[\u202a-\u202e\u2066-\u2069]', path):
        return dict(result, reason='unsupportedPath')
    try:
        root = Path(path).resolve(strict=True)
        if not root.is_dir():
            return dict(result, reason='notDirectory')
        if not safe_path(str(root)) or re.search(r'[\u202a-\u202e\u2066-\u2069]', str(root)):
            return dict(result, reason='unsupportedPath')
        git = shutil.which('git')
        if not git:
            return dict(result, reason='gitUnavailable')
        # Keep ordinary global/system trust configuration. Remove ambient repo
        # selection, tracing/output destinations and command-line config injection.
        remove = [key for key in os.environ if key.startswith('GIT_') and key not in
                  ('GIT_CONFIG_GLOBAL', 'GIT_CONFIG_SYSTEM', 'GIT_CONFIG_NOSYSTEM')]
        probe = run([git, '--no-pager', '--no-optional-locks', '-C', str(root), '-c', 'core.fsmonitor=false',
                     'rev-parse', '--show-toplevel', '--is-inside-work-tree'], 6,
                    remove_environment=remove)
        if probe.code != 0:
            return result  # Includes timeout, trust refusal and unreadable Git data.
        rows = probe.text.splitlines()
        if len(rows) != 2 or rows[1] != 'true' or not safe_path(rows[0]):
            return result
        if Path(rows[0]).resolve(strict=True) != root:
            return dict(result, reason='rootMismatch')
        return dict(result, status='verified', reason='verified', root=str(root))
    except (OSError, ValueError, RuntimeError):
        return dict(result, reason='locationUnavailable')


def validate(name, path):
    if not re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9._-]*', name) or name == '..':
        print('SKYVIEW_EVENT|validation|FAIL|A configured project folder name could not be checked.')
        return 1
    value = inspect(path)
    passed = value['status'] == 'verified'
    message = (f'Configured repository working folder verified: {name}' if passed else
               f'SDE could not finish checking the project folder for {name}. Review its location and Git access. Your files have not been changed.')
    print(f'SKYVIEW_EVENT|validation|{"PASS" if passed else "FAIL"}|{message}')
    return 0 if passed else 1


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--json':
        print(json.dumps(inspect(sys.argv[2]), separators=(',', ':')))
    elif len(sys.argv) == 4 and sys.argv[1] == '--validate':
        raise SystemExit(validate(sys.argv[2], sys.argv[3]))
    else:
        raise SystemExit(2)
