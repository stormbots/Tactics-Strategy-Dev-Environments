# v1.2.10: UI milestone installation and focused UAT

## Candidate status

**Published/authenticated; owner UAT returned October 19, 2026.**
[Testing release](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/v1.2.10)
is from source `35a2228070ea2391668e88d617adbd382aeb3c99`.
[Protected run 39326251992](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/39326251992)
passed, including authentication of all five published assets. Codex independently
verified the pinned-key signature, both installers, checksums and GitHub asset
digests; [PR #83](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/83)
records the complete publication receipt and hashes.

The owner reported **Windows Pass, Mint Pass for every results row below**.
They then explicitly rejected the perfectly square icon shape and supplied
`skyview_logo_rounded_square.svg` as an acceptable rounded-square design.
This finding qualifies the icon/overall acceptance rows: themes, zoom and
guidance are accepted; #63 and milestone acceptance await the revised icon.
See [v1.2.11 focused icon UAT](UI-UAT-1.2.11.md); do not repeat accepted UI checks.

The changed product behavior since accepted v1.2.9 is the **white-background
application icon**. Existing themes, five zoom values and validation guidance
are retained. v1.2.9's recorded owner acceptance remains valid historical
evidence; this pass checks the new package and closes any explicitly identified
acceptance gaps. Use the [detailed matrix](UI-MILESTONE-UAT.md) for deeper cases.

## Authenticate and install, once the handoff is confirmed

Save work and close SDE normally. Wait for maintenance/install/package work to
finish. Record the current app version, tool baseline, schedule and application-
update pause setting. Keep that policy as configured. Download these five assets
from the exact v1.2.10 prerelease into one new folder:

- `Skyview-Dev-Setup-Windows-x64.exe`
- `Skyview-Dev-Setup-LinuxMint-amd64.deb`
- `SHA256SUMS.txt`
- `sde-update.json`
- `sde-update.json.minisig`

On an existing trusted Windows installation, open PowerShell in that folder:

```powershell
$worker = 'C:\Program Files\Skyview Dev Setup\backend\windows\self-update\sde-update-trust.exe'
& $worker verify (Get-Location).Path v1.2.10
if ($LASTEXITCODE -ne 0) { throw 'Stop: candidate authentication failed.' }
```

After successful verification, use an Administrator PowerShell in the same folder:

```powershell
$package = (Resolve-Path '.\Skyview-Dev-Setup-Windows-x64.exe').Path
$p = Start-Process $package -ArgumentList '/S','/UPDATE' -Wait -PassThru
$p.ExitCode
```

Expect exit 0 and no forced reboot. Report any other code; 3010 requires separate
reboot assessment. Launch SDE as the normal user after installation.

On an existing trusted Mint installation, from the downloaded folder:

```bash
worker='/usr/lib/Skyview Dev Setup/backend/linux/self-update/sde-update-trust'
"$worker" verify "$PWD" v1.2.10
```

Stop on any nonzero result or missing trusted verifier. After successful verification:

```bash
sudo env DEBIAN_FRONTEND=noninteractive apt-get -y --no-remove --no-install-recommends \
  -o DPkg::Lock::Timeout=30 -o Dpkg::Options::=--force-confdef \
  -o Dpkg::Options::=--force-confold install ./Skyview-Dev-Setup-LinuxMint-amd64.deb
dpkg-query -W skyview-dev-setup
```

Expect successful configuration and version 1.2.10. Stop/report failures without
forcing package transactions. App Install/Repair/Update buttons manage tools;
they do not install this application candidate. Missing trusted-verifier cases
need a separate bootstrap handoff.

## Focused UAT

Record results separately for Windows 11/WebView2 and Mint Cinnamon/WebKitGTK.
Use the regular workstation's normal OS scaling; do not manufacture failures or
run Repair solely to test guidance. Known-failure fixture cases require the
[controlled disposable procedure](UI-NATIVE-UAT-FIXTURES.md).

1. **Version and icon:** About and Schedule's App version in this window show
   1.2.10. Check the taskbar/dock and Start/menu icon at normal size on dark and
   light backgrounds. The artwork stays recognizable with a white background.
   If a pinned shortcut still shows the old cached icon, record that observation
   and compare the newly launched app/menu icon; do not declare success from the
   asset preview alone.
2. **Appearance:** System follows live OS theme changes where supported; Light
   and Dark override the OS. Select a nondefault zoom, close/reopen and confirm
   both preferences persist. Try 90/100/115/130/150% on Overview, Validation,
   Schedule and About in both themes. Check normal and minimum 640x600 windows,
   the compact settings panel, reachable controls and no clipping/overlap.
3. **Keyboard/accessibility:** Tab/Shift+Tab and Enter/Space operate appearance
   buttons; focus remains visible across zoom limits, resize and panel dismissal.
   With Narrator/Orca if available, check useful control names, selected/expanded
   states, zoom announcements and validation/operation status. Check reduced
   motion and Windows high contrast. Name any unavailable checks explicitly.
4. **Preserved work:** change theme/zoom during a normal Validate. It finishes
   once with continuous logs; page, operation choice and Advanced selection are
   retained. No appearance or Review action starts privileged work by itself.
5. **Guidance and retained settings:** inspect existing validation results and
   Technical details. Failures explain impact and a safe next action; optional
   Git identity/auth remains informational. Review Repair/Update only selects
   the mode and explains its broader scope. Confirm schedule, pause policy and
   baseline remain as recorded. Unavailable failure classes remain Not run.

## Results to return

| Field | Windows | Mint |
| --- | --- | --- |
| Candidate version / source / authentication | Owner: Pass | Owner: Pass |
| OS / webview / desktop / OS scale | Owner: Pass | Owner: Pass |
| Prior app version; baseline; pause/schedule | Owner: Pass | Owner: Pass |
| Installation / displayed version | Owner: Pass | Owner: Pass |
| White icon on dark/light taskbar or dock | Owner: Pass; square shape rejected | Owner: Pass; square shape rejected |
| Themes / persistence / zoom / layout | Owner: Pass | Owner: Pass |
| Keyboard / speech / contrast / reduced motion | Owner: Pass | Owner: Pass |
| Validate continuity / guidance / settings retained | Owner: Pass | Owner: Pass |
| Findings or explicitly accepted limitations | Owner: Pass; rounded icon requested | Owner: Pass; rounded icon requested |
| Owner acceptance / date | October 19: UI accepted; icon revision pending | October 19: UI accepted; icon revision pending |

These are the owner's aggregate results, not independently observed native tests.
Exact OS/webview versions, scale values and individual assistive-technology
observations were not supplied; no values or per-tool results are inferred.

Pass/Fail/Blocked/Not run plus plain-language observations are sufficient; Codex
interprets logs and maintains the record. Include page/theme/zoom/window size for
a visual problem. After findings are resolved, explicitly state acceptance of
#4/#5/#6/#63 and any named platform limitations. Codex then closes the accepted
issues and milestone. Candidate availability alone does not close them or
authorize stable promotion, fleet rollout or policy changes.
