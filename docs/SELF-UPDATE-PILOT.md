# Controlled self-update pilot template — historical v1.2.14 → v1.2.17 proposal

**Not authorized and not run.** The owner [accepted native/manual evidence for
#43/milestone2 closeout](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/43#issuecomment-6409138390) and deferred the real automatic pilot to
[#106](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/106) for the next independently accepted stable transition.
The historical14→17 proposal below preserves the reviewed sequence; prepare a
fresh exact target/source/assets/actual starting-version packet before requesting
future device/action/policy/window approval. Do not reuse17 as a same-version
installation test on current17 machines.

The proposed retained14 starting roles both
[passed live discovery and manually upgraded17](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/99#issuecomment-6407709158); all four known tested
desktops now run17. No actual14 starting role remains in that inventory. The
owner selected the next accepted stable transition for the real pilot in #106.
Do not downgrade or create a release solely to manufacture evidence. A same-version
check is not an install pass.

Stable promotion is a repository action; it does
not authorize any device change. No fleet expansion is included. Complete the
private allowlist and obtain owner approval of the concrete packet below before
any resume, schedule change or maintenance trigger. Public evidence uses device
roles, not personal hostnames. Inventory information alone is not authorization.

| Approval field | Proposed scope / value to fill before request |
| --- | --- |
| Target | Accepted stable v1.2.17, release423797225/source7de6d29cfb0b8ba1677a20bc94a746ecfa4e838d; five immutable assets in [promotion receipt](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/104#issuecomment-6407525155) |
| Device allowlist | Historical proposal only: former14 Windows/Mint roles now17 after manual upgrades. For #106, select representative roles with actual older versions relative to the next accepted stable target; private aliases remain local |
| Evidence type | Physical or already approved desktop VM; booted OS/desktop/version to confirm |
| Maintenance window | Owner-selected local start/end/timezone; allow all package work to finish even if over window |
| Starting baseline/route | Compatible protected maintenance baseline, expected applied 1.2.1; trusted launcher/SYSTEM or root; actual enabled schedule/custom timing recorded |
| Intended changes | Inspect actual policy and apply only the separately approved pause/resume change; two invocations of its existing maintenance task/service; real tool maintenance each time; authenticated app 1.2.14 → 1.2.17 only on idle invocation |
| Final policy | Proposed paused after completion/finding; owner must approve desired final state and stop-response pause |
| Other changes | No Repair, provisioning, schedule enablement/default reset, package fault injection, downgrade or new host/VM/media access; prepare a separate decision if prerequisite missing |
| Owner wording/date | Pending exact allowlist, target, actions, window and final/stop policy authorization |

## Preconditions and before capture

1. New target independently authenticated, owner-accepted and stable/latest;
   exact source/CI/asset receipt current. Older retained app must truly be 1.2.14.
   Do not downgrade or reinstall it to fabricate state. Keep one complete signed
   accepted asset set under mentor control for assessed repair.
2. Before changing policy, finish #99 read-only older-GUI launch/About/official
   browser/dismiss/restart/offline/retry checks. Capture actual Windows and Mint
   observations separately; no discovery action may install automatically.
3. Save student work and privately capture sample file hashes/Git state, editor
   settings, app/engine/baseline version **and baseline bytes**, existing relevant
   logs/private ACLs, policy bytes/value, schedule triggers/enabled/custom timing,
   trusted launcher/principal, coordination, package health/activity and existing
   status/recovery. Sanitize submitted paths/account data. Old legacy logs are
   diagnostic evidence; protected receipts establish authenticated attempt state.
4. A missing/disabled schedule or incompatible `needs_repair` baseline stops this
   packet. Do not enable, Repair, copy scripts or alter markers by assumption.
   Missing automatic history after manual installation is allowed; record it.
   Read-only idle status alone does not grant installation permission.

## Approved open-SDE invocation

Keep SDE open normally, then perform only the approved policy change using the
**installed** worker in an administrator terminal. Check every exit; stop on any
unexpected value. Windows:

```powershell
$worker = 'C:\Program Files\Skyview Dev Setup\backend\windows\self-update\sde-update-trust.exe'
& $worker resume
if ($LASTEXITCODE -ne 0) { throw 'Resume failed; stop.' }
& $worker self-update-status
Get-ScheduledTask -TaskName 'Skyview Robotics - Dev Tool Updates' |
    Select-Object State,Actions,Principal,Triggers,Settings
Start-ScheduledTask -TaskName 'Skyview Robotics - Dev Tool Updates'
Get-ScheduledTaskInfo -TaskName 'Skyview Robotics - Dev Tool Updates'
```

Mint:

```sh
worker='/usr/lib/Skyview Dev Setup/backend/linux/self-update/sde-update-trust'
sudo "$worker" resume && "$worker" self-update-status
# Only continue after successful resume and confirmed approved existing route.
systemctl status skyview-student-dev-update.timer --no-pager
sudo systemctl start skyview-student-dev-update.service
systemctl status skyview-student-dev-update.service --no-pager
```

These triggers really update development tools. The open SDE session must remain
open and app installation must defer. Capture a fresh completed worker receipt,
independent tool exit/validation outcome, app outcome/phase/times and task/service
result. A task-start success is not completed maintenance success. Existing tool
or package activity may defer maintenance earlier; record what actually happened
rather than claiming the application lease gate ran. Let work finish normally.
Do not force-close SDE, kill children or clear locks/journals to obtain the path.

## Approved idle invocation

Close SDE normally. Confirm tool/native/package work from the previous invocation
has ended. Within the same authorization/window, run **only the existing trigger**
above again; do not repeat `resume` or change schedule. Wait for completion.
Expect a real silent pinned-authenticated app installation, native outcome and
postchecks for app/engine 1.2.17, retained verification/recovery evidence, separate
tool result and preserved applied baseline/files/preferences/log/private ACLs and
schedule. Record exact new signed recovery versions with `verify-recovery`; a
flag alone does not prove there is a previous signed installer.

Windows elevated read-only follow-up:

```powershell
& $worker self-update-status
& $worker verify-recovery
if ($LASTEXITCODE -ne 0) { throw 'Recovery verification failed; retain evidence.' }
Get-ScheduledTaskInfo -TaskName 'Skyview Robotics - Dev Tool Updates'
```

Mint:

```sh
"$worker" self-update-status
sudo "$worker" verify-recovery
systemctl status skyview-student-dev-update.service --no-pager
dpkg-query -W '-f=${Status}\n${Version}\n${Architecture}\n' skyview-dev-setup
```

Reopen as the student. Compare all before state. Report native exit, app/engine,
applied baseline, tool outcome, fresh times/log reference, recovery verification
and preservation independently. An equal/current check or manual install is not
an automatic-install pass. Immediate invocation is not natural weekly firing;
reboot/school-network/natural schedule observations need evidence or explicit
owner limits.

## Final policy, stop conditions and recovery

Resume intentionally changes policy; never claim policy bytes remained unchanged.
For the proposed **approved paused final state**, run installed worker `pause`
(Windows elevated `& $worker pause`; Mint `sudo "$worker" pause`), verify success
and `self-update-status`, refresh Schedule and record actual final value/time.
Use a different final state only if explicitly approved in the completed packet.

Stop subsequent attempts on unexpected identity/policy, student-data or schedule
change, failed validation/authentication, unsupported permissions, interrupted
package state or uncertain native completion. Preserve private logs/receipts and
pause subsequent app installation as approved in the packet. Pause does not cancel
already running work: wait for all children, even beyond the window. Do not
remove locks/journals, force reboot, uninstall tools or synthesize successful
receipts. [Mentor recovery](SELF-UPDATE-MENTOR.md) requires native assessment and
separate approval for any repair; there is no universal automatic rollback.

## Result and expansion disposition

For each role record date/window, exact authorization, starting/target versions,
actual policy changes, open/idle receipts, tool/app/native outcomes, baseline/data/
ACL/schedule comparisons, recovery version proof, final policy and findings. Owner
reviews results before any expansion. #43 and milestone 2 remain open if required
pilot work is unavailable, unless the owner explicitly revises that scope and
tracks remaining work. Release success is preserved even if the pilot is blocked.

## v1.2.17 policy change

Installation/upgrade enables SDE updates even when the starting policy is paused.
A final paused policy must be deliberately reapplied and verified after the idle
upgrade; do not claim pause preservation. Students can also toggle this setting.
This affects observation and stop-response planning, not release authentication
or the need for exact-device/action/window pilot authorization.
