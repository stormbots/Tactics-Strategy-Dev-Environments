# Deployment readiness owner UAT — v1.2.17

**Completed October 25, 2026:** exact v1.2.17 is independently authenticated,
owner-accepted on both Windows11/Mint desktops and promoted stable/latest under
separate explicit owner approval. [UAT acceptance](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/104#issuecomment-6407488626); [immutable promotion
and public-download receipt](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/104#issuecomment-6407525155). Release423797225 is source7de6d29.
Accepted downloads: [official stable/latest](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/latest).

The procedure below records the completed candidate acceptance and remains a
reference for authenticated installation. Do not repeat already accepted rows
by default. Publication originally used `prerelease=true`, `latest=false`; promotion changed
metadata only. No device pilot is authorized by this sheet. The next owner step
is the retained14 [live discovery check](#after-independently-accepted-stable-promotion-99),
then a separately authorized [pilot](SELF-UPDATE-PILOT.md).

Owner performs desktop UAT on Windows 11 x64 and **booted Mint Cinnamon 22.x
amd64**. Record physical hardware or approved desktop VM; Windows Server and Mint
userland CI are separate evidence. Keep the existing Windows/Mint v1.2.14 daily
installations unchanged for [#99](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/99).
The actual Windows 11 UAT laptop and replacement Mint laptop both
passed v1.2.15 UAT; reuse those results within their recorded scope. Focus
v1.2.17 owner UAT on the changed defaults and student toggle. The MacBook Air
reports Mint 22.3 x86_64. v1.2.16 failed Windows toggle persistence; its other
focused rows passed. Repeat the fixed toggle/refresh/restart path on v1.2.17;
Mint v1.2.16 acceptance was not reported. Keep private aliases out of public evidence.
A fresh install does not prove upgrade preservation. Never downgrade or recreate
unsafe ACLs to manufacture a starting state. No additional VM/media/host access
is authorized by this checklist.

## Before testing

Record device role privately, OS/desktop, installed app/engine and **applied
baseline separately**, sample project bytes/Git state, editor/appearance settings,
existing log hashes/private ACLs where relevant, schedule/enabled/custom timing,
actual app-update policy and available recovery/status. Save work. Close SDE
normally and let native/package/maintenance work finish before manual install.
Keep the existing schedule. Application installation now intentionally enables
SDE updates, including prior pauses; record this expected change. A deliberate
pause for an approved pilot/recovery procedure must be reapplied afterward. GUI Install/Repair/Update are separate
baseline/tool operations and are not steps for installing this application.

The historical v1.2.6 affected-PC first-attempt pass and controlled SYSTEM
maintenance remain valid for their scope; see the [acceptance matrix](DEPLOYMENT-READINESS-EXECUTION.md).
Reuse accepted v1.2.14/v1.2.15 UAT within its actual scope. The new Inline toggle
is changed UI: test its enabled/paused/saving/error states, keyboard use, refresh
and restart persistence, appearance/compact layout and independent last-attempt
history. No administrator prompt, release fetch, tool maintenance or immediate
installer launch should result from switching it. On a failed save the current
setting is unconfirmed until refreshed; do not infer that the old value remains.

## Download and authenticate

Download **all five assets** from the exact candidate into a new version folder:
`Skyview-Dev-Setup-Windows-x64.exe`,
`Skyview-Dev-Setup-LinuxMint-amd64.deb`, `SHA256SUMS.txt`, `sde-update.json`,
`sde-update.json.minisig`. Do not mix versions. Checksums alone are not authentication.

Use the already trusted installed worker. On a fresh PC with no installed worker,
stop for Codex's separate verifier handoff: a verifier built from reviewed source
in exact-main CI, with run/artifact identity and digest recorded in the PR, stored
outside the selected release folder. Never use a key/verifier from that folder.
The handoff must state its actual path; do not install first merely to obtain it.

Windows PowerShell in the candidate folder, using the trusted installed path
(or the separately authenticated verifier path supplied for the fresh PC):

```powershell
$worker = 'C:\Program Files\Skyview Dev Setup\backend\windows\self-update\sde-update-trust.exe'
if (-not (Test-Path -LiteralPath $worker -PathType Leaf)) { throw 'Obtain the reviewed verifier handoff before installation.' }
& $worker verify (Get-Location).Path v1.2.17
if ($LASTEXITCODE -ne 0) { throw 'Stop: candidate authentication failed.' }
```

Mint, in the candidate folder:

```sh
worker='/usr/lib/Skyview Dev Setup/backend/linux/self-update/sde-update-trust'
"$worker" verify "$PWD" v1.2.17 && sha256sum --check SHA256SUMS.txt
```

Stop on any failure. Codex can prepare harmless metadata/installer tamper cases
in copied asset folders: `verify` must fail; never install damaged copies.

## Native application installation

Only on the owner's selected candidate UAT PC after authentication and normal
administrator consent. In elevated Windows PowerShell in the candidate folder:

```powershell
$package = (Resolve-Path '.\Skyview-Dev-Setup-Windows-x64.exe').Path
# Existing app upgrade: /S /UPDATE. For the selected fresh PC: /S only.
$installerFlags = if (Test-Path 'C:\Program Files\Skyview Dev Setup\skyview-dev-setup.exe') { @('/S','/UPDATE') } else { @('/S') }
$p = Start-Process $package -ArgumentList $installerFlags -Wait -PassThru
$p.ExitCode
```

Expect exit 0, no forced reboot and no GUI launched as SYSTEM/admin. Report other
results; 3010 needs mentor assessment, not a clean-pass label. Open from Start
as the ordinary user after completion.

Mint, after checking other package work is idle, in the candidate folder:

```sh
sudo env DEBIAN_FRONTEND=noninteractive apt-get -y --no-remove --no-install-recommends \
  -o DPkg::Lock::Timeout=30 -o Dpkg::Options::=--force-confdef \
  -o Dpkg::Options::=--force-confold install ./Skyview-Dev-Setup-LinuxMint-amd64.deb
dpkg-query -W '-f=${Status}\n${Version}\n${Architecture}\n' skyview-dev-setup
```

Expect `install ok installed`, `1.2.17`, `amd64`. Open from the ordinary Cinnamon
menu, never as root. Never delete locks, kill installers or force reboot.

## Legacy maintenance prerequisite

App installation preserves an older uncoordinated baseline. `needs_repair` may
therefore be correct and blocks automatic installation; an old schedule is not
silently rerouted. App-only machines gain no baseline/tool schedule. Record this
honestly. [Mentor migration](SELF-UPDATE-ROLLOUT.md) requires separately understood
Repair authorization, before/after capture and restoration of approved custom
schedule timing. Do not paste markers, silently replace scripts or resume to
bypass the compatibility gate.

## Focused acceptance matrix

Record **Pass / Fail / Not run / Accepted limitation**, exact candidate/source,
platform/date/evidence and owner's disposition for each row, separately per OS.
An old pass supports confidence, not a new-candidate desktop pass.

| Area | Required observation / boundary |
| --- | --- |
| Distribution/identity | Complete authenticated candidate; app/active engine 1.2.17; baseline recorded separately, expected existing 1.2.1 if applied |
| Recognized legacy migration | Reuse affected Windows 11 v1.2.6 no-manual-correction pass plus current native fixtures; dispose unreported representative/private-ACL criteria explicitly; no unsafe real-PC fixtures |
| Unsupported layouts/failures | Current disposable native negative evidence only; no owner-PC package failure injection |
| Preservation | Compare saved files/preferences, baseline bytes/version, relevant log bytes/private ACLs and existing schedule/enabled/custom timing; policy intentionally resets to enabled under #102; distinguish fresh install from upgrade |
| Existing maintenance route | Read protected launcher/principal and independent tool/app outcomes; actual trigger only under separately selected device/action/window |
| Active session/package activity | Safe deferral; SDE and existing work finish normally. Real automatic install/deferral belongs to the separately authorized stable pilot |
| Student/school network | Ordinary-user status, pause toggle and protected-state write denial, actual required GitHub access/offline/retry; report unavailable network/account scope |
| Reboot/scheduling | Capture actual observations or accepted limit; immediate trigger is not natural weekly firing |
| Recovery | Understand protected receipts/logs and mentor procedure; missing automatic history/recovery after manual bootstrap is allowed; native failure tests stay separate |
| Focused UI | About/Schedule identity, usable readiness/navigation and preserved appearance/sidebar behavior; retain prior accepted five-zoom evidence |

## Immediate checks and maintenance (no weekly wait)

Installed `check` is discovery only; it does not install, run tools or write a
maintenance success receipt. From the administrator terminal on Windows:

```powershell
& $worker check
& $worker self-update-status
```

Mint:

```sh
sudo "$worker" check
"$worker" self-update-status
```

The prerelease stays ineligible. Equal/older releases do not offer an upgrade;
offline/unavailable does not mean current. An administrator check is separate
from #99's older GUI transition after promotion.

**Actual existing task/service triggers update development tools.** Their exact
commands and open/idle application pilot sequence are in the
[pilot packet](SELF-UPDATE-PILOT.md). Do not run them as read-only inspection or
on a device without a device/action/window authorization. Never enable a disabled
schedule or provision a missing baseline to obtain a pass by assumption.

## After independently accepted stable promotion: #99

On the retained Windows/Mint **v1.2.14** installations, record actual per-platform
results against the real official newer stable release: launch/About discovery,
version and official platform notes/download destinations, readiness/navigation,
keyboard/focus/announcements, explicit browser actions, dismissal and restart.
After a successful offer, test offline/failed refresh and retry, honest history
and stale-offer clearing. Confirm notification checks do not automatically
download, stage, elevate, launch or install. Later-version dismissal behavior
needs a real later release or an explicitly labeled fixture limit; do not invent
one. Keep #99 open until its criteria have actual evidence/disposition.

## Findings and owner decision

Stop on wrong identity/policy, changed student state, validation failure or
uncertain package completion. Preserve sanitized evidence, let package work end,
and follow [mentor recovery](SELF-UPDATE-MENTOR.md). Code changes to published
bytes require a fresh version and authentication, then affected UAT again.

Owner acceptance must name exact target/source/assets and coverage limits on
both desktops. Stable/latest promotion requires explicit exact-target owner
authorization after this concrete result. Signing approval, old v1.2.14 acceptance
and candidate installation do not supply it. The automatic pilot has its own
allowlist/action/window approval. #43/milestone 2 remain open until the required
representative rollout completes or the owner explicitly revises its scope and
tracks the remaining work.

## Focused v1.2.17 policy acceptance

Confirm enabled after installation/upgrade from a paused state; native fixtures
also cover fresh creation and enabled upgrades. As an ordinary student, switch
off and on without an administrator prompt, refresh/reopen and confirm the
saved value. Last-attempt outcome/times, baseline/files/preferences and existing
schedule/enabled/custom timing must remain independent. Administrator pause/resume
commands remain available; a subsequent application installation enables updates
again. No repeated natural-weekly, package-failure or unsafe ACL test is requested
on a real workstation. A controlled automatic pilot remains separately authorized.
