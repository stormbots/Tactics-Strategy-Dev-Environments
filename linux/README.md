# Skyview Robotics Linux Mint Student Development Package

For normal student installation, use the [graphical installer](../README.md).
The ZIP instructions below document the **stable v1.0.1 manual fallback**.
Current source is version 1.2.1 and retains the same manual Bash entry points.
The GUI's supported target is Mint Cinnamon 22.x amd64.

**Version:** 1.0.1
**Target:** Linux Mint Cinnamon student development laptops
**Primary baseline:** Linux Mint 22.x (Ubuntu 24.04/Noble package base)
**Also supported by the installer:** Linux Mint 21.x (Ubuntu 22.04/Jammy package base)

This package is the Linux Mint counterpart to `Skyview-Windows-Dev-Package-v1.0.1`. It intentionally keeps the two environments as close as practical while respecting Linux packaging conventions and Linux Mint's defaults.

## What it installs

| Windows baseline | Linux Mint equivalent / implementation |
|---|---|
| Git | `git` from APT |
| GitHub CLI | `gh` from GitHub's official APT repository |
| Node.js 24 LTS + npm | NodeSource 24.x APT repository; major version remains pinned to 24 |
| VSCodium | VSCodium APT repository |
| VSCodium extensions | Same extension set as Windows, installed from Open VSX |
| DBeaver Community | DBeaver's Debian repository |
| Google Chrome | Official Google `.deb`, which registers Google's update repository |
| Firefox | Linux Mint/Ubuntu APT package |
| PowerShell 7 | Microsoft's Ubuntu APT repository |
| OpenSSH | `openssh-client` |
| 7-Zip | `p7zip-full` / `7z` |
| Python 3.14 | Deadsnakes PPA, installed alongside Mint's system Python |
| PyCharm | Latest stable unified PyCharm tarball from JetBrains, installed under `/opt/pycharm-*` |

### VSCodium extensions

- ESLint — `dbaeumer.vscode-eslint`
- Prettier — `esbenp.prettier-vscode`
- EditorConfig — `EditorConfig.EditorConfig`
- Error Lens — `usernamehw.errorlens`
- Code Spell Checker — `streetsidesoftware.code-spell-checker`
- REST Client — `humao.rest-client`
- Git Graph — `mhutchie.git-graph`
- Vitest — `vitest.explorer`

### Deliberately not installed

As with the Windows baseline, this package does **not** install:

- PostgreSQL server or a local database server
- Docker
- WSL (not applicable on Linux)
- AWS CLI or AWS development tooling
- Yarn or pnpm
- WPILib / FRC robot-programming tooling
- AI coding tools
- C/C++ build environments beyond dependencies pulled in by installed packages

Python packages are expected to live in project `.venv` environments rather than being installed globally.

## Install

1. Start from a normal Linux Mint Cinnamon desktop session using the shared student/local-admin account.
2. Extract this ZIP to a local directory.
3. Optionally edit `repositories.csv` before installation if repositories should be cloned automatically.
4. Open a terminal in the extracted directory.
5. Run:

```bash
chmod +x Install-SkyviewStudentDev.sh
./Install-SkyviewStudentDev.sh
```

**Do not run the installer with `sudo`.** It runs user-specific steps as the logged-in student/shared account and requests `sudo` only for system changes.

The installer is designed to be idempotent and may be re-run.

## Repository provisioning

`repositories.csv` is optional and is empty by default except for its header:

```csv
name,url,branch,enabled
```

Example:

```csv
name,url,branch,enabled
design-system-workshop,https://github.com/rdpollard/design-system-workshop.git,main,true
```

Enabled repositories are cloned to:

```text
~/Development/<name>
```

If the target directory already contains a Git repository, it is left alone. The installer does not automatically pull or modify existing repositories.

## Git behavior

The installer applies these global defaults to the shared account:

```text
init.defaultBranch = main
fetch.prune = true
pull.ff = only
```

It intentionally does **not** configure `user.name`, `user.email`, or GitHub authentication.

## VSCodium defaults

For a new VSCodium profile, the package configures:

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "files.eol": "\n",
  "terminal.integrated.defaultProfile.linux": "bash"
}
```

If an existing `settings.json` is strict JSON, the installer backs it up and merges these baseline values. If the existing file is JSON-with-comments (JSONC) and cannot be parsed safely with `jq`, the installer preserves it and emits a warning instead of overwriting it.

## Python behavior

Linux Mint depends on its distribution-provided Python interpreter for system utilities. This package therefore installs `python3.14` **alongside** the system Python and never changes `/usr/bin/python3`.

Create project environments with:

```bash
cd ~/Development/<project>
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

The validator verifies that Python 3.14 can create a virtual environment containing pip.

## PyCharm behavior

Linux Mint disables Snap by default, so this package does not enable Snap just to install PyCharm. Instead it:

1. Queries JetBrains' release API for the latest stable unified PyCharm release.
2. Downloads the official Linux tarball.
3. Verifies the JetBrains SHA-256 checksum.
4. Installs it to `/opt/pycharm-<version>`.
5. Maintains `/opt/pycharm` and `/usr/local/bin/pycharm` symlinks.
6. Creates a system desktop entry.

Current PyCharm is a unified product: core features remain free; a new install may initially expose a Pro trial.

## Weekly maintenance

Installation enables:

```text
skyview-student-dev-update.timer
```

The timer runs weekly on Sunday around 03:00, with up to one hour of randomized delay. `Persistent=true` means a missed run occurs after the laptop is next powered on.

The maintenance job updates only the provisioned development package set. It does **not** run a full distribution upgrade; Linux Mint Update Manager remains responsible for normal OS/security maintenance.

The updater keeps:

- Node.js on the **24.x** repository line
- Python on the **3.14.x** package family
- VSCodium extensions are refreshed in the student profile by the GUI's Install, Repair, and Update operations, rather than by root maintenance.
- PyCharm on the current stable JetBrains release

Run maintenance manually with:

```bash
sudo /usr/local/sbin/skyview-student-dev-update
```

Check the next scheduled run with:

```bash
systemctl list-timers skyview-student-dev-update.timer
```

## Validation

The installer runs validation automatically. It can also be run later:

```bash
/usr/local/sbin/skyview-student-dev-validate
```

Validation checks:

- Linux Mint and Cinnamon
- Git and shared-account Git defaults
- GitHub CLI installation and auth state (authentication is informational, not required)
- Node.js 24.x and npm
- Python 3.14.x plus functional `venv`/pip
- VSCodium and all required extensions
- VSCodium baseline settings
- DBeaver, Chrome, Firefox, PowerShell, OpenSSH, and 7-Zip
- PyCharm managed installation
- `~/Development`
- Optional configured repository clones
- Weekly systemd maintenance timer

## Persistent files

After installation, package-managed files live in normal Linux locations:

```text
/etc/skyview-robotics/student-dev/             configuration and target-user metadata
/usr/local/lib/skyview-student-dev/            shared script library
/usr/local/share/skyview-robotics/student-dev/ package data
/usr/local/sbin/skyview-student-dev-update     manual/systemd updater
/usr/local/sbin/skyview-student-dev-validate   validator
/var/lib/skyview-robotics/student-dev/         package state
/var/log/skyview-robotics/student-dev/         install/update logs
~/Development/                                 student repositories and projects
```

## Package contents

```text
Install-SkyviewStudentDev.sh
Update-SkyviewStudentDev.sh
Validate-SkyviewStudentDev.sh
repositories.csv
extensions.txt
VERSION
README.md
config/
  codium-settings.json
lib/
  common.sh
systemd/
  skyview-student-dev-update.service
  skyview-student-dev-update.timer
```

## Upstream installation sources

The installer uses current vendor-supported/recommended Linux distribution channels where practical:

- GitHub CLI: https://github.com/cli/cli/blob/trunk/docs/install_linux.md
- NodeSource Node.js 24: https://deb.nodesource.com/
- VSCodium: https://vscodium.com/install
- DBeaver: https://dbeaver.io/download/
- PowerShell: https://learn.microsoft.com/powershell/scripting/install/install-ubuntu
- PyCharm: https://www.jetbrains.com/help/pycharm/installation-guide.html
- PyCharm release metadata: https://data.services.jetbrains.com/products/releases?code=PCP&latest=true&type=release
- Python 3.14 PPA: https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa
