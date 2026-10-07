Skyview Robotics Student Development Environment 1.1.2 — Windows installation environment fix.

### Windows

Download **Skyview-Dev-Setup-Windows-x64.exe**, open it, and follow the installer to update Skyview Dev Setup. If it offers to remove the previous app version before installing, follow that flow. Installed development tools and student projects are separate from the app.

Relaunch Skyview Dev Setup and retry **Install Development Environment**.

This fixes Chocolatey stopping at its system-cache permissions check before installing any development packages. The restricted administrator environment now includes SYSTEMDRIVE so Windows resolves the shared application-data directory correctly. Script and temporary paths use the spelling supported by PowerShell and older .NET tools. The helper still clears user environment variables and uses system-only executable/module paths; it does not relax cache permissions or disable Chocolatey's checks.

Windows CI now performs a real local Chocolatey fixture-package install/uninstall using this same environment builder. The fixture installs no development tools and runs only on the disposable GitHub runner. Another test checks Windows known-folder resolution, temporary-file operations and removal of inherited user variables.

### Linux Mint

Download **Skyview-Dev-Setup-LinuxMint-amd64.deb**, open it, install it, then launch **Skyview Development Environment Setup**. Linux provisioning behavior is unchanged.

Both installers and **SHA256SUMS.txt** are built and verified by CI. This remains a mentor-testing prerelease, with physical-laptop package installation and UAC/PolicyKit acceptance still required. Windows installers remain unsigned. Earlier releases remain available unchanged.
