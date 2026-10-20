# v1.2.12: Windows Start/taskbar icon follow-up

## Candidate status

**Preparation only: publication and authentication are pending.** Install only
after the handoff confirms the exact main source, successful native checks,
protected signing run and all five published asset hashes. Expected
[testing release](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/v1.2.12).
Unsigned Actions artifacts are not that confirmation.

The owner accepted the Mint Cinnamon icon on v1.2.11 after correcting an
accidental v1.2.10 reinstall. Preserve that result and the previously accepted
Windows/Mint theme, zoom, accessibility and validation checks. Windows 11's
v1.2.11 Start/taskbar icon is still square despite the correct installed binary;
the caption icon is rounded. Only the Windows fix needs focused owner UAT.

## Authenticate and upgrade Windows after the handoff

Save work, close SDE normally and wait for maintenance/install/package work to
finish. Record installed version, baseline, pause policy, schedule and preferences.
Keep that policy as configured. Download these five assets from the exact
v1.2.12 prerelease into one new folder:

- `Skyview-Dev-Setup-Windows-x64.exe`
- `Skyview-Dev-Setup-LinuxMint-amd64.deb`
- `SHA256SUMS.txt`
- `sde-update.json`
- `sde-update.json.minisig`

Open PowerShell in that folder using the existing trusted installed verifier:

```powershell
$worker = 'C:\Program Files\Skyview Dev Setup\backend\windows\self-update\sde-update-trust.exe'
& $worker verify (Get-Location).Path v1.2.12
if ($LASTEXITCODE -ne 0) { throw 'Stop: candidate authentication failed.' }
```

After successful verification, use an Administrator PowerShell in the same folder:

```powershell
$package = (Resolve-Path '.\Skyview-Dev-Setup-Windows-x64.exe').Path
$p = Start-Process $package -ArgumentList '/S','/UPDATE' -Wait -PassThru
$p.ExitCode
```

Expect exit 0 and no forced reboot. Report any other result; 3010 needs separate
reboot assessment. Stop on authentication failure or a missing trusted verifier.
App Install/Repair/Update buttons manage development tools, not this candidate.

## Focused Windows 11 checks

1. Launch from Start as the normal user. Confirm displayed **1.2.12** and retained
   preferences, baseline, pause policy and schedule.
2. Check the Start-menu icon and running taskbar icon at normal size on dark and
   light backgrounds. Expect the supplied rounded white tile and transparent
   exterior, matching the already rounded caption icon.
3. Record the existing pinned icon separately, then close and launch from the
   updated Start entry. If still pinned, compare that shortcut with the running
   app. Report any stale pin; do not delete global icon caches or reboot to make
   the initial result pass. A second check after re-pinning may help diagnose it.
4. Report Pass/Fail and explicit acceptance of the revised Windows appearance.
   Include a screenshot if a square icon remains. Full prior UI UAT is retained.

A newly created GUI-finish-page desktop shortcut can still use the executable's
icon reference; this candidate specifically tests Start and the running taskbar,
plus updates existing desktop shortcuts. Report a desktop-shortcut finding if
observed rather than counting it as a passing Start/taskbar result.

## Results

| Field | Windows 11 | Mint Cinnamon |
| --- | --- | --- |
| Candidate version / authentication | Pending handoff | v1.2.11 accepted; no new UAT required |
| Upgrade / displayed version / settings retained | Not run | Prior acceptance retained |
| Start icon, dark/light | Not run | v1.2.11 owner reports correct |
| Running taskbar icon, dark/light | Not run | v1.2.11 owner reports correct |
| Existing pin / launch from updated Start | Not run | Not applicable to Windows fix |
| Findings / explicit acceptance / local date | Pending | Revised icon accepted in owner follow-up |

Keep #63 and milestone 1 open until the owner accepts the Windows fix and any
named limitations. Automated Windows Server rendering and Mint package probes
are engineering evidence, not Windows 11/Cinnamon desktop acceptance. Stable
promotion and fleet rollout remain separate.
