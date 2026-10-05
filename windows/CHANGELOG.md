# Windows Environment Changelog

## 1.0.1 (Unreleased)

Working revision based on acceptance testing of `windows-v1.0.0`.

### Planned / Implemented

- Restore native Chocolatey progress output during initial installation.
- Add numbered top-level installer phases so long-running work does not appear hung.
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

### Acceptance Testing Notes

The original v1.0.0 `Attempted to perform an unauthorized operation` failure was isolated by the new stage-level diagnostics. The failure occurred in the File Explorer configuration stage while attempting to recreate an existing registry key. The v1.0.1 branch now only creates that key when it does not already exist, then sets `HideFileExt` directly.

A separate transient overwrite failure was observed for `C:\ProgramData\SkyviewRobotics\AutoUpdate-SkyviewTools.ps1` during partial-install recovery. After renaming the existing file, the configuration stage completed successfully. Continue testing rerun/idempotency behavior before release.

Do not publish or merge v1.0.1 until the full configuration script and validation pass on the acceptance-test laptop.
