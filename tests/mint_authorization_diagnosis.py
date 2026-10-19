"""Read-only desktop diagnosis. Never authorizes, starts an agent or changes SDE."""
import configparser
import json
import os
from pathlib import Path
import re
import subprocess


def probe(*arguments):
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=10,
                                env={**os.environ, 'LC_ALL': 'C'})
        return {'exit': result.returncode, 'stdout': result.stdout[:16384],
                'stderr': result.stderr[:2048]}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {'unavailable': type(error).__name__}


def autostart(path, known_agents=()):
    """Read relevant desktop keys only; never execute or shell-expand Exec."""
    if not path.is_file() or path.stat().st_size > 16384:
        return None
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.read_string(path.read_text())
    entry = parser['Desktop Entry']
    if (path.name not in known_agents and
            not re.search(r'polkit|policykit', path.name + ' ' + entry.get('Exec', ''), re.I)):
        return None
    keys = ['Exec', 'TryExec', 'Hidden', 'OnlyShowIn', 'NotShowIn',
            'X-GNOME-Autostart-enabled', 'X-GNOME-Autostart-Phase']
    return {key: entry[key] for key in keys if key in entry}


def report():
    if os.geteuid() == 0:
        raise ValueError('Run in the existing Mint desktop terminal as its ordinary user')
    release = Path('/etc/os-release').read_text()
    if not re.search(r'^ID=\"?linuxmint\"?$', release, re.M):
        raise ValueError('This diagnosis requires the actual Mint desktop')
    uid = os.getuid()
    result = {'schemaVersion': 1, 'uid': uid, 'readOnly': True,
              'authorizationAttempted': False,
              'desktop': {key: os.environ.get(key) for key in
                          ['XDG_SESSION_ID', 'XDG_SESSION_TYPE', 'XDG_CURRENT_DESKTOP']}}
    session = os.environ.get('XDG_SESSION_ID', 'self')
    if not re.fullmatch('[a-zA-Z0-9_-]{1,64}', session):
        raise ValueError('Unexpected session identity')
    result['session'] = probe('/usr/bin/loginctl', 'show-session', session,
                              '-p', 'User', '-p', 'Active', '-p', 'Remote',
                              '-p', 'Type', '-p', 'Class', '-p', 'State', '-p', 'Desktop')
    result['daemon'] = probe('/usr/bin/systemctl', 'show', 'polkit.service',
                             '-p', 'ActiveState', '-p', 'SubState', '-p', 'MainPID')
    result['action'] = probe('/usr/bin/pkaction', '--action-id',
                             'org.skyviewrobotics.sde.app-update', '--verbose')
    result['packages'] = probe('/usr/bin/dpkg-query', '-W',
                               '-f=${binary:Package}\t${Version}\t${db:Status-Status}\n',
                               'skyview-dev-setup', 'polkitd', 'pkexec',
                               '*polkit*', '*policykit*')
    # Package file lists identify the actual executable; no guessed launch path.
    packages = result['packages'].get('stdout', '').splitlines()
    names = sorted({line.split('\t')[0] for line in packages
                    if line.endswith('\tinstalled') and
                    re.search(r'polkit|policykit', line.split('\t')[0])})
    result['packagedAgentFiles'] = {}
    for package in names[:16]:
        listing = probe('/usr/bin/dpkg-query', '-L', package)
        result['packagedAgentFiles'][package] = [line for line in
            listing.get('stdout', '').splitlines()
            if re.search(r'agent|autostart|\.desktop$', line, re.I)]
    result['autostart'] = {}
    known_agents = set()
    for directory in [Path('/etc/xdg/autostart'), Path.home() / '.config/autostart']:
        for path in sorted(directory.glob('*.desktop'))[:256]:
            try:
                entry = autostart(path, known_agents)
                if entry is not None:
                    known_agents.add(path.name)
                    result['autostart'][str(path)] = entry
            except (OSError, ValueError, configparser.Error, KeyError) as error:
                result['autostart'][str(path)] = {'unavailable': type(error).__name__}
    result['agentProcesses'] = []
    for directory in Path('/proc').iterdir():
        if not directory.name.isdecimal():
            continue
        try:
            executable = (directory / 'exe').readlink()
            if re.search(r'polkit|policykit', executable.name, re.I):
                result['agentProcesses'].append({'pid': int(directory.name),
                    'uid': directory.stat().st_uid, 'executable': str(executable)})
        except OSError:
            pass  # Other-UID /proc restrictions do not prove absence.
    result['processVisibilityLimited'] = True
    result['preservedState'] = {}
    for name in [
        '/usr/local/libexec/skyview-app-update-request',
        '/usr/share/polkit-1/actions/org.skyviewrobotics.sde.app-update.policy',
        '/var/lib/skyview-robotics-coordination/transaction.json',
        '/var/lib/skyview-robotics-coordination/installation-scope.json',
        '/usr/local/sbin/skyview-student-dev-update',
        '/usr/local/lib/skyview-student-dev/coordination.py',
    ]:
        try:
            metadata = Path(name).lstat()
            item = {'present': True, 'uid': metadata.st_uid,
                    'mode': oct(metadata.st_mode & 0o7777)}
            if name.endswith(('skyview-student-dev-update', 'coordination.py')):
                with Path(name).open('rb') as stream:
                    data = stream.read(65537)
                item['admissionV2Marker'] = b'# SDE_COORDINATION_ADMISSION_V2' in data.splitlines()
            result['preservedState'][name] = item
        except FileNotFoundError:
            result['preservedState'][name] = {'present': False}
        except OSError as error:
            result['preservedState'][name] = {'unknown': type(error).__name__}
    return result


if __name__ == '__main__':
    print(json.dumps(report(), indent=2))
