# v1.2.8 testing prerelease: installation and owner UAT

This guide becomes actionable only after Codex confirms the protected workflow
has published and authenticated all five v1.2.8 assets. Until then, do not install
unsigned Actions artifacts or an unpublished 1.2.7 fixture. The owner performs UAT;
Codex owns build checks, authentication evidence, diagnosis and follow-up fixes.

## Candidate and authentication

Expected release: https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/v1.2.8

It must display **Pre-release**. Stable promotion, fleet rollout and policy resume
remain deferred. Do not use `/releases/latest`; that points to the stable channel.
Codex supplies the reviewed source SHA, successful workflow run and published
asset evidence with the handoff. Existing v1.2.7 assets must remain unchanged.

Download these five files to one new local folder, keeping the names unchanged:

- `Skyview-Dev-Setup-Windows-x64.exe`
- `Skyview-Dev-Setup-LinuxMint-amd64.deb`
- `SHA256SUMS.txt`
- `sde-update.json`
- `sde-update.json.minisig`

On the existing trusted Windows v1.2.7 installation, open PowerShell in that
folder and authenticate before starting the installer:

```powershell
$assets = (Get-Location).Path
$worker = 'C:\Program Files\Skyview Dev Setup\backend\windows\self-update\sde-update-trust.exe'
& $worker verify $assets v1.2.8
if ($LASTEXITCODE -ne 0) { throw 'Stop: candidate authentication failed.' }
```

On an existing trusted Mint installation, from the asset folder:

```bash
worker='/usr/lib/Skyview Dev Setup/backend/linux/self-update/sde-update-trust'
"$worker" verify "$PWD" v1.2.8
```

Stop on any nonzero result, missing verifier, unexpected version or missing asset;
report the output to Codex. Do not bypass verification or copy a verifier from an
untrusted build. A machine without a trusted installed verifier needs a separate
Codex bootstrap handoff; this guide assumes an existing trusted installation.

## Before installation

Save normal work. Record the current app version, applied tool baseline, schedule
and app-installation pause setting. Keep the current pause policy; do not resume
SDE automatic installation for this UI test. Close SDE normally and wait until
maintenance, installers and package-manager work are idle. Manual installation
is not protected by the automatic update gates.

Install SDE itself using the native installer. The UI's Install, Repair and Update
operations manage development tools; they do not install this application update.

### Windows

Use an Administrator PowerShell terminal in the authenticated asset folder:

```powershell
$package = (Resolve-Path '.\Skyview-Dev-Setup-Windows-x64.exe').Path
$p = Start-Process $package -ArgumentList '/S','/UPDATE' -Wait -PassThru
$p.ExitCode
```

Expect exit 0, no forced reboot and no automatically launched SDE window. Record
any other exit code; 3010 needs mentor assessment rather than a clean pass. If
elevating with a different account, navigate to the actual downloaded folder,
not that administrator account's default Downloads folder.

### Mint

In the authenticated asset folder, with package-manager work idle:

```bash
sudo env DEBIAN_FRONTEND=noninteractive apt-get -y --no-remove --no-install-recommends \
  -o DPkg::Lock::Timeout=30 -o Dpkg::Options::=--force-confdef \
  -o Dpkg::Options::=--force-confold install ./Skyview-Dev-Setup-LinuxMint-amd64.deb
```

Expect successful package configuration, no GUI launch and no forced reboot.
Record `dpkg-query -W skyview-dev-setup`; it should show 1.2.8. Do not force-remove
packages or interrupt package transactions to get past an error.

## First UAT pass on the owner's existing Windows workstation

1. Open SDE as the normal desktop user. Confirm About and Schedule's **App version
   in this window** show **1.2.8**. Existing selections/preferences should survive
   the upgrade. The decorative banner stays absent and the heading asks “Are you
   ready to build?”; readiness comes from its status card.
2. Try System, Light and Dark. With System selected, change OS appearance while
   SDE stays open. With Light/Dark selected, OS changes should not override it.
   Relaunch between explicit choices to verify persistence when no work is active.
3. Try all five zoom levels; check Overview, Validation, Schedule and About in both
   themes at 1040×820 and 640×600. Text/icons/logs scale together; controls remain
   reachable and there is no page overflow, overlap or lost content. Check 150%
   with normal OS display scaling. Relaunch at a non-default zoom.
4. Use keyboard navigation and the platform screen reader. Check visible focus,
   names, zoom value, statuses and understandable phase/result announcements.
   Check reduced motion. Record duplicate or missing announcements.
5. Run Validate and change theme/zoom while it runs. Logs and progress must
   continue, and completion must occur once. Preserve/export its log. Inspect
   existing failures/warnings and their technical details; Review actions must
   select a mode without starting work or elevation.
6. Confirm schedule, tool baseline and application-update pause policy are retained.
   Previous maintenance-version fields may describe an earlier completed attempt;
   use their timestamps and **App version in this window** for the current UI.

Do not damage tools or change student configuration to manufacture failures.
Known Repair/manual/mentor cases and actual elevated operations belong on the
controlled disposable fixtures prepared by Codex. A genuine update candidate may
not be available; record unexercised cases as Not run.

## Complete milestone acceptance

Continue with [the consolidated matrix](UI-MILESTONE-UAT.md) and
[controlled fixtures](UI-NATIVE-UAT-FIXTURES.md), recording Windows and booted Mint
separately. No personal Mint machine/VM is currently available: record its desktop
UAT as **Blocked**, not as passed based on CI. Windows Server/container automation
supports engineering evidence but does not certify Cinnamon, WebKitGTK, Narrator
or Orca UI acceptance. No VM provisioning is required from the owner just to
repeat automated helper/package tests; Codex uses native CI for those.

Report Pass / Fail / Blocked / Not run, OS/webview, source/app version, page, theme,
zoom, window size, OS scale, expected versus observed behavior, and useful logs or
screenshots. Codex interprets the evidence and fixes reproducible failures. Keep
#4/#5/#6 and the milestone open until acceptance and any limitations/deferrals are
explicitly agreed. A new candidate is required for changed published binaries;
never replace assets in v1.2.8. Stable promotion remains a later decision.
