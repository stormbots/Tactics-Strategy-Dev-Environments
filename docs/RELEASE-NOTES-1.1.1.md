Skyview Robotics Student Development Environment 1.1.1 — Windows validation hotfix.

### Windows

Download **Skyview-Dev-Setup-Windows-x64.exe** and open it to upgrade Skyview Dev Setup. Launch the app and run **Validate**. There is no need to uninstall first or reinstall the development tools to apply this app fix.

This fixes Windows PowerShell 5.1 failing with `Join-Path: ... argument "drive" is null` before any validation checks ran. Packaged script paths now use the spelling supported by PowerShell while native trust checks retain canonical paths. The same correction applies to Install, Repair and Update script launches. Regression tests cover extended paths, spaces, UNC conversion and actual PowerShell relative lookups.

### Linux Mint

Download **Skyview-Dev-Setup-LinuxMint-amd64.deb**, open it, install it, then launch **Skyview Development Environment Setup**. Linux provisioning behavior is unchanged.

Both installers and **SHA256SUMS.txt** are built and verified by CI. This remains a mentor-testing prerelease; laptop acceptance and native screen-reader checks are required before fleet deployment. Windows installers remain unsigned. Earlier releases and existing student tools, settings and projects are preserved.
