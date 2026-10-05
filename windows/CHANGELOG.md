# Windows Environment Changelog

## 1.0.1 (Unreleased)

Working revision based on acceptance testing of `windows-v1.0.0`.

### Planned / Implemented

- Restore native Chocolatey progress output during initial installation.
- Add numbered top-level installer phases so long-running work does not appear hung.
- Add a 20-second Chocolatey heartbeat during silent dependency-resolution/download periods so users can tell the installer is still active.
- Preserve native Chocolatey console output while the heartbeat is running.
- Correct heartbeat process handling so Chocolatey's exit code is reliably captured after the child process exits; do not emit a heartbeat after the process has already completed.
- Add numbered configuration stages inside the Chocolatey install script.
- Standardize the deployment-package location as `C:\SkyviewRobotics\DevSetup`.
- Update installation documentation and examples to use the standardized location.
- Keep supporting-file references relative to the running package where practical.
- Improve Chocolatey failure output with exit code, log location, and rerun guidance.
- Remove Google Chrome as a hard Chocolatey metapackage dependency.
- Install Chrome separately from Google's official MSI and verify its Authenticode signature.
- Allow a Chrome installation problem to be reported without discarding the completed core development environment.
- Exclude Chrome from Chocolatey-based maintenance updates; Chrome uses Google Update.
- Make partial-install recovery and rerunning the installer an explicit supported workflow.
- Fix File Explorer configuration so an existing `HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced` key is not recreated with `New-Item -Force`, which caused `UnauthorizedAccessException` during acceptance testing.
- Prevent harmless VSCodium/Node deprecation warnings written to stderr from aborting extension installation under Windows PowerShell 5.1 with `$ErrorActionPreference = 'Stop'`; extension success is now determined by the VSCodium process exit code.
- Improve validation output so intentionally-unconfigured GitHub authentication is reported as expected rather than as a PowerShell error.
- Expand validation to check the Windows OpenSSH client and scheduled development-tool update task.

### Acceptance Testing Notes

The original v1.0.0 `Attempted to perform an unauthorized operation` failure was isolated by the new stage-level diagnostics. The failure occurred in the File Explorer configuration stage while attempting to recreate an existing registry key. The v1.0.1 branch now only creates that key when it does not already exist, then sets `HideFileExt` directly.

A separate transient overwrite failure was observed for `C:\ProgramData\SkyviewRobotics\AutoUpdate-SkyviewTools.ps1` during partial-install recovery. After renaming the existing file, configuration completed successfully. A subsequent full rerun of the configuration script passed all 10 stages with the managed files already present, confirming expected idempotent behavior on the acceptance-test laptop.

The acceptance-test laptop also passed the workstation validation baseline for Git, GitHub CLI, Node.js 24, npm, VSCodium, PowerShell 7, Developer Mode, long paths, visible file extensions, Chrome, Firefox, and DBeaver.

During end-to-end bootstrap testing, Chocolatey could remain silent for several minutes after `By installing, you accept licenses for the packages.` even with native progress enabled. v1.0.1 now runs Chocolatey as a child process while emitting a 20-second liveness heartbeat with elapsed time, without suppressing Chocolatey's own output.

A later end-to-end test reached VSCodium extension installation but failed because VSCodium emitted a Node.js `[DEP0169]` deprecation warning on stderr. Windows PowerShell 5.1 promoted that native stderr output into a terminating error because the package script uses `$ErrorActionPreference = 'Stop'`. v1.0.1 now temporarily relaxes the error preference only around the VSCodium native process, preserves its console output, and uses `$LASTEXITCODE` to determine whether each extension actually failed.

The subsequent end-to-end test completed the Chocolatey package successfully, but the outer bootstrap falsely reported failure because the heartbeat wrapper did not reliably capture the completed child process exit code. The wrapper now refreshes the process after `WaitForExit()`, validates and returns the actual exit code, and suppresses a heartbeat when the process has already exited.

Before release, repeat the end-to-end test using the rebuilt v1.0.1 deployment package from `C:\SkyviewRobotics\DevSetup`, including the heartbeat behavior and the standalone Chrome-install path on a machine where Chrome is not already present.
