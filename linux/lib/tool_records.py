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
        p = subprocess.run(args, capture_output=True, text=True, timeout=15,
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

def records(check_updates):
    for tool in TOOLS:
        current = available = None
        state = "notChecked" if not check_updates else "unavailable"
        if tool in PACKAGES:
            package = PACKAGES[tool]
            installed = command("dpkg-query", "-W", "-f=${db:Status-Status}\t${Version}", package)
            if installed and installed.startswith("installed\t"):
                current = installed.split("\t", 1)[1]
                if check_updates:
                    candidate = candidate_for(package)
                    if candidate:
                        state = "current"
                        # dpkg's comparison handles epochs and Debian revisions.
                        if command("dpkg", "--compare-versions", candidate, "gt", current) is not None:
                            available = candidate
        elif tool == "npm":
            current = release_version(command("npm", "--version"))
            state = "native"  # npm ships with the managed Node runtime.
        elif tool == "PyCharm":
            try:
                current = json.loads(Path("/opt/pycharm/product-info.json").read_text())["version"]
            except (OSError, ValueError, KeyError):
                pass
            if check_updates and current:
                try:
                    with urllib.request.urlopen(PYCHARM_API, timeout=8) as response:
                        latest = json.load(response)["PCP"][0]
                    candidate = latest["version"]
                    # Only compare stable numeric releases, never advertise a downgrade.
                    if re.fullmatch(r"\d+(?:\.\d+)+", current) and re.fullmatch(r"\d+(?:\.\d+)+", candidate) and latest["downloads"].get("linux"):
                        state = "current"
                        if tuple(map(int, candidate.split("."))) > tuple(map(int, current.split("."))):
                            available = candidate
                except (OSError, ValueError, KeyError, IndexError):
                    pass
        yield {"tool": tool, "installedVersion": current, "availableVersion": available,
               "updateAvailable": bool(available), "updateCheck": state}

if __name__ == "__main__":
    for record in records("--check-updates" in sys.argv[1:]):
        print("SKYVIEW_EVENT|tool|" + record["tool"] + "|" + json.dumps(record, separators=(",", ":")))
        if record["updateAvailable"]:
            print(f'SKYVIEW_EVENT|update|available|{record["tool"]}: {record["installedVersion"]} to {record["availableVersion"]}')
