# v1.2.11: rounded-square icon installation and focused UAT

## Candidate status

**Published and authenticated:** [v1.2.11 testing release](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/v1.2.11),
source `792f0dc6c4b39a856b23be5fc656e12ed06ae63f`,
[successful candidate run](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/39336851263).
All five downloaded assets were checked against the published digests; the
repository-pinned verifier authenticated the manifest and both installers.

**Owner follow-up:** Mint Cinnamon's rounded icon is accepted on v1.2.11.
Its initial square-icon report came from an accidental v1.2.10 reinstall.
Windows 11 remains unresolved: caption rounded, Start/taskbar square after
unpin/relaunch and a fresh reinstall. Installed version 1.2.11 and executable
SHA256 `703343e676f82878e2757b748f495e6d92005c84aa54c1d487e78f4a9bbf61d0`
match the authenticated package. A disposable Windows probe reproduced stale
Shell pixels after replacing the executable at its stable path. Continue with
[the Windows-specific follow-up](UI-UAT-1.2.12.md); preserve Mint acceptance.

The owner returned Pass for every v1.2.10 UAT row on **Windows 11 and Mint
Cinnamon**, then explicitly rejected the square icon shape. Themes, zoom,
keyboard/accessibility and validation guidance remain accepted as reported in
[the v1.2.10 record](UI-UAT-1.2.10.md). This follow-up uses the supplied
`skyview_logo_rounded_square.svg` for a white rounded tile with transparent
corners. Only installation and the revised native icon need focused UAT.

## Published candidate installation reference

Save work and close SDE normally. Wait for maintenance/install/package work to
finish. Record the current app version, tool baseline, schedule and application-
update pause setting. Keep that policy as configured. Download these five assets
from the exact v1.2.11 prerelease into one new folder:

- `Skyview-Dev-Setup-Windows-x64.exe`
- `Skyview-Dev-Setup-LinuxMint-amd64.deb`
- `SHA256SUMS.txt`
- `sde-update.json`
- `sde-update.json.minisig`

On an existing trusted Windows installation, open PowerShell in that folder:

```powershell
$worker = 'C:\Program Files\Skyview Dev Setup\backend\windows\self-update\sde-update-trust.exe'
& $worker verify (Get-Location).Path v1.2.11
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
"$worker" verify "$PWD" v1.2.11
```

Stop on any nonzero result or missing trusted verifier. After successful verification:

```bash
sudo env DEBIAN_FRONTEND=noninteractive apt-get -y --no-remove --no-install-recommends \
  -o DPkg::Lock::Timeout=30 -o Dpkg::Options::=--force-confdef \
  -o Dpkg::Options::=--force-confold install ./Skyview-Dev-Setup-LinuxMint-amd64.deb
dpkg-query -W skyview-dev-setup
```

Expect successful configuration and version 1.2.11. Stop/report failures without
forcing package transactions. App Install/Repair/Update buttons manage tools;
they do not install this application candidate. Missing trusted-verifier cases
need a separate bootstrap handoff.

## Focused icon UAT

On both Windows 11 and Mint Cinnamon:

1. Confirm installation succeeds and the app displays **1.2.11**. Confirm the
   existing theme/zoom, baseline, pause policy and schedule remain as recorded.
2. Launch the newly installed app normally. Check its taskbar/dock icon at normal
   size against dark and light desktop/taskbar backgrounds. The white tile must
   have rounded corners; the area outside the rounded tile must show the desktop
   background. Confirm the supplied artwork remains recognizable. Also check the
   Start/menu launcher icon.
3. Record any old pinned-shortcut/icon-cache behavior separately and compare with
   the newly launched app and new menu entry. Cached v1.2.10 shortcuts must not be
   mistaken for the new asset or silently counted as a passing new icon.
4. Return Pass/Fail/Blocked with an explicit acceptance of the revised icon shape
   on each desktop. Report other regressions if observed; accepted v1.2.10 UI
   checks do not need a full repeat for this icon-only change.

## Results to return

| Field | Windows 11 | Mint Cinnamon |
| --- | --- | --- |
| Candidate version / source / authentication | Confirmed 1.2.11; package match | Confirmed 1.2.11 after correcting accidental 1.2.10 reinstall |
| Installation / displayed 1.2.11 / settings retained | Installation/version confirmed; prior UI acceptance retained | Installation/version confirmed; prior UI acceptance retained |
| Rounded white icon / transparent corners on dark and light | Caption rounded; taskbar square | Owner reports icon correct; separate background cells not supplied |
| Start/menu icon / pinned-shortcut cache observations | Start square despite unpin/relaunch and fresh reinstall | Revised icon accepted |
| Findings or accepted limitations | Windows Shell cache finding remains open | Initial finding explained by installed 1.2.10 |
| Owner acceptance of revised shape / date | Not accepted | Accepted in owner follow-up; separate local date not supplied |

Keep #63 and the milestone open until the owner accepts the revised icon and
any named limitations. Do not infer native desktop acceptance from asset previews
or automated upgrade probes. Stable promotion and fleet rollout remain separate.
