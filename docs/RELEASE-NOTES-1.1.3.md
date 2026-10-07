# Skyview Dev Setup 1.1.3

Windows installation now handles existing Chocolatey-managed Node.js packages before installing the required Node 24 LTS runtime. Previously, a machine with Node 26 through `nodejs`/`nodejs.install` stopped with MSI error 1603: a later Node version was already installed. Install, Repair and managed updates share the migration policy, check package ownership, resolve the approved version before removal, and verify Node 24 afterward. Unmanaged or mismatched runtimes receive a specific remediation message. Chocolatey's dependent-package checks remain enabled.

The Windows backend package is now 1.1.3 so the new migration helper is included in both initial setup and maintenance. Download progress percentages are suppressed; status heartbeats and package results remain visible.

CI tests install the actual Node 26.1.0 MSI, migrate to Node 24.21.0 using the app's clean helper environment, retry the operation, and check the package channel and pin. The same test then runs the full Windows system setup, including the real development dependencies and maintenance configuration. These machine changes run only on disposable GitHub runners. User-profile/editor configuration and physical-laptop behavior still require acceptance testing.

Follow the Windows installer's update/reinstall flow, relaunch Skyview Dev Setup, and retry **Install Development Environment**. Successfully installed packages from a previous attempt are reused. Node 26 is replaced with the required Node 24; student projects and existing editor settings are preserved.

This remains an unsigned mentor-testing prerelease. Physical-laptop provisioning, reboots, maintenance and accessibility acceptance checks remain required. The Linux baseline and earlier releases remain available.
