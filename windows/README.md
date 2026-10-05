# Windows Student Development Environment

Standard Windows 11 development environment for Skyview Robotics
Tactics & Strategy student development laptops.

## Baseline

- Node.js LTS and npm
- Git
- GitHub CLI
- VSCodium
- DBeaver
- Google Chrome
- Mozilla Firefox
- PowerShell 7
- OpenSSH client
- Supporting command-line utilities

The environment is provisioned primarily through Chocolatey. Google Chrome is
installed and verified separately so a transient Chocolatey browser-package
problem cannot abort the rest of the workstation baseline.

## Standard Deployment Location

Extract the complete Windows development package to:

```text
C:\SkyviewRobotics\DevSetup
```

The folder should contain the bootstrap script and the local Chocolatey package.
Do not run the package directly from Downloads, Desktop, or another temporary
location.

## Installation

1. Download the current Windows release ZIP from GitHub Releases.
2. Create or empty:

   ```text
   C:\SkyviewRobotics\DevSetup
   ```

3. Extract the entire ZIP into that folder.
4. Open **Windows PowerShell as Administrator**.
5. Run:

   ```powershell
   cd C:\SkyviewRobotics\DevSetup
   Set-ExecutionPolicy Bypass -Scope Process -Force
   .\Install-SkyviewStudentDev.ps1
   ```

The installer displays numbered phases and native Chocolatey progress. A fresh
installation may take 10-20 minutes depending on network speed and the laptop.

If installation is interrupted or a component fails, correct the reported issue
and rerun the same installer. The provisioning process is designed to be safe to
rerun and will reuse already-installed components where possible.

## Validation

After installation, sign out/in or reboot if newly installed commands are not
immediately visible. Then run:

```powershell
powershell -ExecutionPolicy Bypass -File C:\ProgramData\SkyviewRobotics\Test-SkyviewStudentDev.ps1
```

## Persistent Locations

```text
C:\SkyviewRobotics\DevSetup
    Deployment package used by mentors during installation or repair

C:\ProgramData\SkyviewRobotics
    Persistent maintenance scripts, validation tools, configuration, and logs

C:\Development
    Student development repositories
```

## Troubleshooting

If the core Chocolatey package fails, review:

```text
C:\ProgramData\chocolatey\logs\chocolatey.log
```

The Skyview configuration script reports each configuration stage separately so
the failing operation can be identified without testing every command manually.

Ready-to-install packages are published through GitHub Releases.
