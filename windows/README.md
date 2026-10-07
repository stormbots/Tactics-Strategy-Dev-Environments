# Windows Student Development Environment

For normal student installation, use the [graphical installer](../README.md).
The terminal workflow below documents the **stable v1.0.1 manual fallback**.
Current 1.1.5 source no longer requires a fixed extraction directory; the GUI
packages this backend automatically. Node 24.x patches now use the same managed
Update operation; major-version changes remain mentor-controlled.

Standard Windows 11 development environment for Skyview Robotics
Tactics & Strategy student development laptops.

## Baseline

- Node.js LTS and npm
- Python 3.14.x and pip
- Git
- GitHub CLI
- VSCodium
- JetBrains PyCharm
- DBeaver
- Google Chrome
- Mozilla Firefox
- PowerShell 7
- OpenSSH client
- Supporting command-line utilities

The environment is provisioned primarily through Chocolatey. Google Chrome is
installed and verified separately so a transient Chocolatey browser-package
problem cannot abort the rest of the workstation baseline.

PyCharm is installed using JetBrains' current unified PyCharm product. Its core
features remain available for free after the included Pro trial ends; a paid Pro
subscription is only required for Pro-only functionality.

## Python Standard

Student laptops use **Python 3.14.x** as the standard Python runtime. The Windows
package installs Chocolatey's version-specific `python314` package rather than
the generic `python` package so normal maintenance stays within the Python 3.14
family instead of automatically moving the workstation to a future major/minor
runtime.

Python 3.14 patch and security updates are included in the normal Skyview tool
update process. Node.js remains separately pinned and mentor-controlled.

For new Python projects, use a project-local virtual environment instead of
installing project dependencies globally:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

PyCharm should use that project's `.venv` as its interpreter.

For Skyview AWS Lambda projects, target the `python3.14` Lambda runtime unless a
project explicitly specifies another version. The student Windows environment
matches the Python language/runtime version, but AWS Lambda runs on Linux. Any
package containing native/compiled code must therefore be built or packaged for
the Lambda Linux environment rather than copied directly from a Windows virtual
environment.

## Standard Deployment Location

The finished Windows deployment package must be extracted to:

```text
C:\SkyviewRobotics\DevSetup
```

For a normal release installation, that folder must contain these files directly
at its top level:

```text
C:\SkyviewRobotics\DevSetup\
├── Install-SkyviewStudentDev.ps1
├── repositories.csv
└── skyview-student-dev.<version>.nupkg
```

Do not run the package directly from Downloads, Desktop, or another temporary
location.

> **Important:** Do not use GitHub's **Code > Download ZIP** button as the
> deployment package. That downloads the entire source repository (`docs`,
> `linux`, `windows`, etc.), not the ready-to-install Windows package.

## Normal Installation from a Published Release

Use this workflow for student laptops once a Windows release has been published.

1. Open the repository's **Releases** page.
2. Download the Windows deployment asset named similar to:

   ```text
   Skyview-Windows-Dev-Package-v1.0.1.zip
   ```

3. Create or empty:

   ```text
   C:\SkyviewRobotics\DevSetup
   ```

4. Extract the **contents of the deployment ZIP directly into** that folder.
   Do not leave the three deployment files inside an extra nested folder.
5. Verify the folder contents. It should contain at least:

   ```text
   Install-SkyviewStudentDev.ps1
   repositories.csv
   skyview-student-dev.<version>.nupkg
   ```

6. Open **Windows PowerShell as Administrator**.
7. Run:

   ```powershell
   cd C:\SkyviewRobotics\DevSetup
   Set-ExecutionPolicy Bypass -Scope Process -Force
   .\Install-SkyviewStudentDev.ps1
   ```

The installer displays numbered phases, native Chocolatey output, and periodic
status heartbeats during quiet Chocolatey operations. A fresh installation may
take 10-20 minutes depending on network speed and the laptop.

If installation is interrupted or a component fails, correct the reported issue
and rerun the same installer. The provisioning process is designed to be safe to
rerun and will reuse already-installed components where possible.

## Testing an Unreleased Branch Build

Use this workflow only when testing a branch such as `windows-v1.0.1` before a
GitHub Release exists.

The ZIP downloaded from **Code > Download ZIP** is source code. It must be staged
into the deployment layout before the installer can run.

1. Download the branch source ZIP and extract it somewhere convenient, such as
   Downloads.
2. Open **Windows PowerShell as Administrator**.
3. Change to the extracted repository root. The current directory should contain
   the repository's `windows` folder.
4. Create the deployment folder:

   ```powershell
   New-Item -ItemType Directory -Path "C:\SkyviewRobotics\DevSetup" -Force
   ```

5. Copy the bootstrap files:

   ```powershell
   Copy-Item ".\windows\Install-SkyviewStudentDev.ps1" "C:\SkyviewRobotics\DevSetup\" -Force
   Copy-Item ".\windows\repositories.csv" "C:\SkyviewRobotics\DevSetup\" -Force
   ```

6. Build the Chocolatey package into the deployment folder:

   ```powershell
   choco pack ".\windows\chocolatey\skyview-student-dev.nuspec" --output-directory "C:\SkyviewRobotics\DevSetup"
   ```

7. Verify the staged deployment files:

   ```powershell
   Get-ChildItem C:\SkyviewRobotics\DevSetup
   ```

   Confirm that `Install-SkyviewStudentDev.ps1`, `repositories.csv`, and the
   generated `skyview-student-dev.<version>.nupkg` are present directly in that
   folder.

8. Run the installer:

   ```powershell
   cd C:\SkyviewRobotics\DevSetup
   Set-ExecutionPolicy Bypass -Scope Process -Force
   .\Install-SkyviewStudentDev.ps1
   ```

## Validation

After installation, sign out/in or reboot if newly installed commands are not
immediately visible. Then run:

```powershell
powershell -ExecutionPolicy Bypass -File C:\ProgramData\SkyviewRobotics\Test-SkyviewStudentDev.ps1
```

The validator checks the Python runtime and pip in addition to the rest of the
workstation baseline and expects Python 3.14.x.

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

If PowerShell reports that `Install-SkyviewStudentDev.ps1` is not recognized,
first check the deployment folder:

```powershell
Get-ChildItem C:\SkyviewRobotics\DevSetup
```

If you see repository folders such as `docs`, `linux`, and `windows` instead of
the three deployment files, you extracted a GitHub source ZIP rather than a
release deployment ZIP. Follow **Testing an Unreleased Branch Build** above, or
download the published release asset when one is available.

If the core Chocolatey package fails, review:

```text
C:\ProgramData\chocolatey\logs\chocolatey.log
```

The Skyview configuration script reports each configuration stage separately so
the failing operation can be identified without testing every command manually.

Ready-to-install packages are published through GitHub Releases.
