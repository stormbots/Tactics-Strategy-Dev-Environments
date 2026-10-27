"""Read-only Update checks. No index refresh, package changes or lock removal."""
import concurrent.futures
import argparse
import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

SOURCES = {
    "Ubuntu/Mint packages": "https://archive.ubuntu.com/ubuntu/dists/noble/Release",
    "GitHub CLI packages": "https://cli.github.com/packages/dists/stable/InRelease",
    "Node packages": "https://deb.nodesource.com/node_24.x/dists/nodistro/InRelease",
    "VSCodium packages": "https://download.vscodium.com/debs/dists/vscodium/InRelease",
    "DBeaver packages": "https://dbeaver.io/debs/dbeaver-ce/Release",
    "Microsoft packages": "https://packages.microsoft.com/ubuntu/24.04/prod/dists/noble/InRelease",
    "Chrome packages": "https://dl.google.com/linux/chrome/deb/dists/stable/Release",
    "Python packages": "https://ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu/dists/noble/InRelease",
    "PyCharm releases": "https://data.services.jetbrains.com/products/releases?code=PCP&latest=true&type=release",
    "Editor extensions": "https://open-vsx.org/api/-/query?size=1",
}
def row(name, status, detail): return dict(name=name, status=status, detail=detail)
def disk(path, required, label):
    try:
        free=shutil.disk_usage(path).free
        return row(label, "pass" if free>=required else "blocking", f"Required free: {required//(1024**2)} MiB; available: {free//(1024**2)} MiB. Update budget; actual downloads can vary.")
    except OSError:
        return row(label,"unavailable","Free space could not be read. Ask a mentor before updating if disk space is uncertain.")
def package_state():
    try:
        keys=set()
        for name in ("/var/lib/dpkg/lock", "/var/lib/dpkg/lock-frontend", "/var/lib/apt/lists/lock", "/var/cache/apt/archives/lock"):
            try:
                s=os.stat(name); keys.add((os.major(s.st_dev),os.minor(s.st_dev),s.st_ino))
            except FileNotFoundError:
                pass
        for line in Path('/proc/locks').read_text().splitlines():
            for field in line.split():
                parts=field.split(':')
                if len(parts)==3:
                    try: key=(int(parts[0],16),int(parts[1],16),int(parts[2]))
                    except ValueError: continue
                    if key in keys: return row("Package manager","blocking","APT or dpkg holds a package lock. Wait for the other operation; do not remove locks.")
        result=subprocess.run(['/usr/bin/dpkg','--audit'],capture_output=True,timeout=5,check=False)
        if result.returncode or result.stdout.strip():
            return row("Package manager","blocking","dpkg reports incomplete package state. Ask a mentor to review before retrying.")
        return row("Package manager","pass","No active package locks or dpkg audit problems were detected. Native package operations recheck locks.")
    except (OSError,subprocess.TimeoutExpired):
        return row("Package manager","unavailable","Package state could not be fully inspected. Native package-manager checks still apply.")
def connectivity(item):
    name,url=item
    try:
        request=urllib.request.Request(url,method='HEAD',headers={'User-Agent':'Skyview-SDE-preflight/1'})
        with urllib.request.urlopen(request,timeout=4) as response:
            return row(name,"pass" if response.status<400 else "unavailable","Source responded. This does not guarantee later installer/CDN availability.")
    except (OSError,ValueError):
        return row(name,"unavailable","Source availability could not be confirmed. Check the connection and retry; continuing may fail during downloads.")
def inspect(operation="update"):
    if operation not in ("install", "update"):
        raise ValueError("Unsupported preflight operation")
    system_required=(8 if operation == "install" else 3)*1024**3
    user_required=(1*1024**3 if operation == "install" else 512*1024**2)
    rows=[disk('/',system_required,"System disk"),disk(Path.home(),user_required,"User disk"),package_state()]
    rows.append(row("Restart","warning" if Path('/var/run/reboot-required').exists() else "pass","Restart is pending; save work and arrange a restart before updating." if Path('/var/run/reboot-required').exists() else "No standard pending-restart marker was found; detection is not exhaustive."))
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        rows.extend(pool.map(connectivity,SOURCES.items()))
    return rows
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--operation',choices=('install','update'),default='update')
    print(json.dumps(inspect(parser.parse_args().operation)))
