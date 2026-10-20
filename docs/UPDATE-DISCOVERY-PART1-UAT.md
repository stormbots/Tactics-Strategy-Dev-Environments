# Part 1 — Windows 11 and Mint Cinnamon UAT, candidate 1.2.13

## Status and candidate identity

**Preparation only. Do not install until the chat/PR confirms publication,
protected signing and independent authentication of all five published assets.**
Expected release: https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/v1.2.13 .
CI artifacts and this document alone do not establish that handoff. Source SHA,
full-main/native run URLs and downloaded asset hashes will be recorded in the PR.

This candidate covers #11, #12, #30, #87, #90 and #91. Tool baseline remains 1.2.1.
Keep your current application-update pause policy and schedule. Do not resume the
fleet or run Repair to test an SDE application upgrade. Save work, close SDE
normally, and let other maintenance/package work finish before installation.
Record prior app version, baseline, schedule, pause and appearance preferences.

## Download and authenticate after the confirmed handoff

Download all five assets into a new folder on each test PC:

- Skyview-Dev-Setup-Windows-x64.exe
- Skyview-Dev-Setup-LinuxMint-amd64.deb
- SHA256SUMS.txt
- sde-update.json
- sde-update.json.minisig

Use the already trusted installed pinned verifier; never a verifier downloaded
from an untrusted folder. Stop if it is missing or authentication fails.

Windows PowerShell in the download folder:

```powershell
$worker = 'C:\Program Files\Skyview Dev Setup\backend\windows\self-update\sde-update-trust.exe'
& $worker verify (Get-Location).Path v1.2.13
if ($LASTEXITCODE -ne 0) { throw 'Stop: candidate authentication failed.' }
```

Then, in Administrator PowerShell in that folder:

```powershell
$package = (Resolve-Path '.\Skyview-Dev-Setup-Windows-x64.exe').Path
$p = Start-Process $package -ArgumentList '/S','/UPDATE' -Wait -PassThru
$p.ExitCode
```

Expect exit 0. Report another result; a reboot-required result needs its own
assessment. Open SDE from Start as the ordinary student/shared user afterwards.

Mint terminal in the download folder:

```bash
'/usr/lib/Skyview Dev Setup/backend/linux/self-update/sde-update-trust' verify "$PWD" v1.2.13 &&
sha256sum --check SHA256SUMS.txt
```

Only after successful authentication:

```bash
sudo apt-get install --no-install-recommends ./Skyview-Dev-Setup-LinuxMint-amd64.deb
```

Open SDE from the normal desktop menu, never as root. These install SDE only;
Install Development Environment, Repair and Update Development Tools are
separate tool/configuration operations.

## Focused acceptance

1. Confirm 1.2.13 in the app and preserved baseline, pause, schedule, theme/zoom and
   sample project/editor preferences. Existing rounded icons retain their
   previously accepted appearance.
2. On launch, local validation completes and displays readiness separately from
   managed-tool update status. While update checks are pending, navigation and
   safe Open VSCodium/Open Development actions remain usable. An available update
   alone does not make validation fail; actual warnings/failures remain visible.
3. About offers Check for SDE updates. Against a stable release older than/equal
   to this candidate, it reports no newer stable release. Disconnect the test PC
   from the network temporarily and check again: failure is non-blocking, never
   up to date, and the last successful session timestamp is retained. Reconnect
   and retry. No installer is automatically downloaded or launched.
4. Review managed-tool updates, or choose Update then Update Development Tools.
   A read-only preview appears before elevation or changes. Check installed and
   available versions, per-tool source/current/unknown/native states, collection
   time, Node 24.x/Python 3.14.x and configuration/extension scope. Mint's local
   APT metadata is explicitly described as potentially stale. Refresh preview
   does not refresh APT or install anything. Cancel starts no operation.
5. Preflight shows disk budgets, package activity, coordination, restart and
   source observations. A known blocker disables Continue; unavailable/warning
   results require review/acknowledgement. Check again refreshes them. Do not
   alter system permissions, delete locks, force-close installers or deliberately
   corrupt package state to create a test. Unsafe fault cases belong on CI.
6. On Windows, compare PowerShell's executable version and shown availability.
   Equal/older available versions must not be offered as an update. A real
   metadata disagreement is explained without rewriting Chocolatey ownership.
   If this PC has no drift, report that scenario as unavailable on this PC;
   regression fixtures separately cover exact equal/ahead/newer/unknown cases.
7. On a suitable test PC, use Continue with Update to run the existing full
   managed-tool operation. This intentionally changes tools/configuration and
   extensions. Confirm real administrator approval, live results, actual updated
   versions/final validation and retained projects/preferences. Native package
   failures or unavailable-source results must be reported accurately; no per-tool
   selection or automatic rollback is promised. If not appropriate on this PC,
   explicitly report the limitation rather than marking the operation passed.
8. Check keyboard operation/focus, light/dark themes, all five zoom levels and
   supported minimum window size. Check Narrator/Orca announcements as available:
   state changes should be understandable without repetitive speech or focus
   theft. Cancel closes the preview without launching changes.
9. Follow the README's current stable link: expect the current accepted stable,
   which may still be 1.2.12 while 1.2.13 is a prerelease. Both supported package
   names and the verification instructions must be easy to identify.

## Coverage limits to disposition explicitly

While 1.2.13 is an unaccepted prerelease, it must not advertise itself as a newer
stable release. Automated selector fixtures cover newer/current/equal/older,
prerelease/draft filtering, missing assets, semantic ordering and offline/rate
limit. UI fixtures cover download actions, per-version dismissal and a later
version being announced; these are not claims of an actual newer stable release
observed in the native candidate. Record acceptance of that evidence boundary
or request a controlled follow-up; do not promote an unaccepted version merely
to manufacture an available-update state. Signing and native package upgrade
CI also do not establish supported-desktop assistive-technology behavior.

## Return results

Use Pass, Fail, Not run or Accepted limitation, with details where applicable.

| Check | Windows 11 | Mint Cinnamon |
| --- | --- | --- |
| Candidate authentication / installation / displayed version | Pending | Pending |
| App baseline, schedule, pause, project/settings preserved | Pending | Pending |
| Local readiness independent of update checks / navigation | Pending | Pending |
| About current check / offline / retry / timestamp | Pending | Pending |
| Tool preview / versions / partial results / refresh / Cancel | Pending | Pending |
| Update preflight / blockers or unknowns / acknowledgement | Pending | Pending |
| PowerShell consistency or explicit unavailable drift case | Pending | Not applicable |
| Confirmed managed-tool Update / actual results | Pending | Pending |
| Themes / five zoom levels / keyboard / speech | Pending | Pending |
| Public stable download instructions | Pending | Pending |
| Findings / accepted evidence limits / owner acceptance/date | Pending | Pending |

Do not close issues/milestone or promote until actual results and any accepted
limitations are recorded for this exact candidate. Changed binaries require a
fresh immutable candidate version. Stable/latest promotion preserves the same
accepted tag/assets; it never authorizes fleet rollout or policy resume.
