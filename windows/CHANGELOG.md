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

### Acceptance-Test Issue Still Open

During v1.0.0 acceptance testing, the Skyview configuration script failed with:

```text
Attempted to perform an unauthorized operation.
```

The exact operation has not yet been isolated. v1.0.1 adds step-level configuration diagnostics specifically so the next test run identifies the failing stage. Do not publish or merge v1.0.1 until this failure is understood and corrected.
