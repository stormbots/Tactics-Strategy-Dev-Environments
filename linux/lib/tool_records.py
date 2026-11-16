"""Read-only tool/version metadata; never refresh APT or install packages."""
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

PACKAGES = {"Git": "git", "GitHub CLI": "gh", "Node.js": "nodejs",
            "Python": "python3.14", "Python venv": "python3.14-venv", "VSCodium": "codium", "DBeaver": "dbeaver-ce",
            "Chrome": "google-chrome-stable", "Firefox": "firefox",
            "PowerShell 7": "powershell", "OpenSSH": "openssh-client", "7-Zip": "p7zip-full"}
TOOLS = ["Git", "GitHub CLI", "Node.js", "Python", "Python venv", "VSCodium", "DBeaver", "PyCharm", "Chrome", "Firefox", "PowerShell 7", "OpenSSH", "7-Zip", "npm"]
PYCHARM_API = "https://data.services.jetbrains.com/products/releases?code=PCP&latest=true&type=release"

def command(*args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=2,
                           env={"PATH": "/usr/local/bin:/usr/bin:/bin", "LC_ALL": "C"}, check=False)
        return p.stdout.strip() if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None

def release_version(value):
    match = re.search(r"\d+(?:\.\d+)+(?:[^\s]*)?", value or "")
    return match[0] if match else None

def candidate_for(package):
    if package == "nodejs":
        # Match the Node 24 resolver used by Update-SkyviewStudentDev.sh.
        rows = command("apt-cache", "madison", package) or ""
        return next((p[1].strip() for line in rows.splitlines()
                     if len(p := line.split("|")) >= 3 and p[1].strip().startswith("24.")), None)
    policy = command("apt-cache", "policy", package) or ""
    match = re.search(r"^\s*Candidate:\s*(\S+)", policy, re.M)
    result = match[1] if match and match[1] != "(none)" else None
    if package in ("python3.14", "python3.14-venv") and result and not re.match(r"(?:\d+:)?3\.14\.", result):
        return None
    return result

def records(check_updates, snapshot=None, node=None, editor=None, pycharm=None):
    selected = node if node and node.get('status') == 'passed' else {}
    for tool in TOOLS:
        current = available = None
        reason = None
        state = "notChecked" if not check_updates else "unavailable"
        if tool == 'Node.js':
            # Runtime evidence and APT inventory describe different contracts.
            # A snapshot is advisory version data, never maintenance permission.
            current = snapshot.get(tool) if snapshot is not None else selected.get('version')
            installed = command('dpkg-query', '-W', '-f=${db:Status-Status}\t${Version}', 'nodejs') if check_updates else None
            tracked = installed.split('\t', 1)[1] if installed and installed.startswith('installed\t') else None
            normalized = re.fullmatch(r'(?:\d+:)?(24\.\d+\.\d+)(?:[-+~].*)?', tracked or '')
            if check_updates and (not current or not normalized or normalized[1] != current):
                state, reason = 'native', 'maintenanceUnverified'
            elif check_updates:
                candidate = candidate_for('nodejs')
                if candidate:
                    state = 'current'
                    if command('dpkg', '--compare-versions', candidate, 'gt', tracked) is not None:
                        available = candidate
                    elif command('dpkg', '--compare-versions', candidate, 'le', tracked) is None:
                        state = 'unavailable'
        elif tool == 'VSCodium':
            current = snapshot.get(tool) if snapshot is not None else editor.get('version') if editor and editor.get('status') == 'verified' else None
            # Selected app usability does not establish APT ownership. The
            # accepted maintenance review is a separate, unfinished contract.
            state = 'native' if check_updates else 'notChecked'
            reason = 'applicationMaintenanceUnverified' if check_updates else None
        elif tool in PACKAGES:
            package = PACKAGES[tool]
            installed = ("installed\t" + snapshot[tool] if snapshot.get(tool) else None) if snapshot is not None else command("dpkg-query", "-W", "-f=${db:Status-Status}\t${Version}", package)
            if installed and installed.startswith("installed\t"):
                current = installed.split("\t", 1)[1]
                if check_updates:
                    candidate = candidate_for(package)
                    if candidate:
                        state = "current"
                        # dpkg's comparison handles epochs and Debian revisions.
                        if command("dpkg", "--compare-versions", candidate, "gt", current) is not None:
                            available = candidate
                        elif command("dpkg", "--compare-versions", candidate, "le", current) is None:
                            # A failed/unavailable comparison is not proof of current.
                            state = "unavailable"
        elif tool == "npm":
            current = snapshot.get(tool) if snapshot is not None else selected.get('npmVersion')
            state = "native"  # npm ships with the managed Node runtime.
        elif tool == 'PyCharm':
            current = snapshot.get(tool) if snapshot is not None else pycharm.get('version') if pycharm and pycharm.get('status') == 'verified' else None
            state = 'native' if check_updates else 'notChecked'
            reason = 'applicationMaintenanceUnverified' if check_updates else None
        yield {"tool": tool, "installedVersion": current, "availableVersion": available,
               "updateAvailable": bool(available), "updateCheck": state,
               "updateReason": reason or ("noCandidate" if state == "unavailable" else None),
               "source": "Application observation" if tool in ('PyCharm', 'VSCodium') else "Local APT metadata" if tool in PACKAGES else "Node runtime"}

if __name__ == "__main__" and "--preview" in sys.argv:
    snapshot = {r["tool"]: r["installedVersion"] for r in json.loads(sys.stdin.read(16384))}
    print(json.dumps(list(records(True, snapshot))))
elif __name__ == "__main__":
    node = None
    editor = None
    pycharm = None
    if '--node-observation' in sys.argv or '--runtime-observations' in sys.argv:
        raw = sys.stdin.read(32769)
        rows = raw.splitlines() if '--runtime-observations' in sys.argv else [raw]
        try:
            value = json.loads(rows[0]) if rows and len(rows[0]) <= 16384 else None
            if (isinstance(value, dict) and value.get('schema') == 1 and value.get('component') == 'Node.js'
                    and value.get('requiredFamily') == '24' and value.get('status') == 'passed'
                    and value.get('reason') == 'verified' and value.get('maintenanceEligibility') == 'notEvaluated'
                    and re.fullmatch(r'24\.\d{1,8}\.\d{1,8}', value.get('version') or '')
                    and re.fullmatch(r'[0-9][A-Za-z0-9.!+_-]{0,119}', value.get('npmVersion') or '')):
                node = value
        except (ValueError, TypeError):
            pass
        try:
            if len(rows) in (2, 3) and len(raw) <= 32768:
                app = json.loads(rows[1])
                if (isinstance(app, dict) and app.get('schema') == 1 and app.get('component') == 'VSCodium'
                        and app.get('platform') == 'linux' and app.get('status') == 'verified'
                        and app.get('maintenanceEligibility') == 'notEvaluated'
                        and isinstance(app.get('version'), str) and re.fullmatch(r'\d+\.\d+\.\d+(?:\.\d+)?', app['version'])):
                    editor = app
        except (ValueError, TypeError):
            pass
        try:
            if len(rows) == 3 and len(raw) <= 32768:
                app = json.loads(rows[2])
                if (isinstance(app, dict) and app.get('schema') == 1 and app.get('component') == 'PyCharm'
                        and app.get('platform') == 'linux' and app.get('status') == 'verified'
                        and app.get('maintenanceEligibility') == 'notEvaluated'
                        and isinstance(app.get('version'), str) and re.fullmatch(r'20\d{2}\.\d{1,2}(?:\.\d{1,3}){0,2}', app['version'])):
                    pycharm = app
        except (ValueError, TypeError):
            pass
    for record in records("--check-updates" in sys.argv[1:], node=node, editor=editor, pycharm=pycharm):
        print("SKYVIEW_EVENT|tool|" + record["tool"] + "|" + json.dumps(record, separators=(",", ":")))
        if record["updateAvailable"]:
            print(f'SKYVIEW_EVENT|update|available|{record["tool"]}: {record["installedVersion"]} to {record["availableVersion"]}')
