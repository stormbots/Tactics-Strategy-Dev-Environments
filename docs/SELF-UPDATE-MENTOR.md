# Mentor controls and recovery (#41)

SDE application installation and development-tool maintenance are separate phases.
Every workstation starts with **SDE installation paused**. Pausing or resuming
changes only this workstation's app-installation policy; it does not disable the
weekly task/timer, change its schedule, provision tools or clear an interrupted
transaction. Keep production paused through #42 integration and #43 owner UAT.
Candidate releases remain GitHub prereleases until the owner explicitly approves
promotion. A valid signature by itself does not approve a candidate for rollout.

## Pause and resume

Use the installed worker from an **administrator terminal**, not a downloaded
binary, an engine snapshot, or the GUI. Commands accept no paths or configuration
arguments. They require an existing trusted installation/policy and fail closed
on missing, linked, malformed, unknown-schema or student-writable policy state.
Do not run a development build on a school workstation.

Windows: open Windows PowerShell **as Administrator**, then run:

```powershell
$worker = 'C:\Program Files\Skyview Dev Setup\backend\windows\self-update\sde-update-trust.exe'
& $worker pause
if ($LASTEXITCODE -ne 0) { throw 'Pause failed; inspect the error before proceeding.' }
& $worker self-update-status
```

Linux Mint: open a terminal, then run:

```sh
sudo '/usr/lib/Skyview Dev Setup/backend/linux/self-update/sde-update-trust' pause
'/usr/lib/Skyview Dev Setup/backend/linux/self-update/sde-update-trust' self-update-status
```

Refresh **Schedule → SDE application updates**. Confirm the installation setting
says **Paused by administrator**. To resume after owner approval and successful
recovery/UAT, run the same administrator command with `resume` instead of `pause`,
check its exit code, and refresh. Resume does not immediately start maintenance or
install an app; the existing task/timer makes the next attempt. Repeat per laptop.
Do not enable a disabled/missing schedule merely to resume app installation.

Pause is atomic and is checked before discovery and again before native launch.
It does not cancel an installer that has already started, nor guarantee a pause
will beat an installer crossing its last policy check. Wait for running work to
finish. Do not kill APT, DPKG, NSIS, Chocolatey or their supervising worker.
Concurrent administrator commands use the last successfully saved value.

The boolean policy is administrator-writable and student-readable: Linux
`policy.json` is root-owned `0644`; Windows gives Users only file read access.
Engine selectors, installer staging, installation/recovery receipts, run snapshots
and native logs remain protected. Upgrades preserve the pause value. The GUI has
only a fixed, read-only status command; it cannot pause/resume, elevate, select a
path, clear a journal, download or launch an installer through this view.

## Interpreting the maintenance page

The current installation setting is separate from the **last completed attempt**:
resuming does not erase a previous paused result; pausing does not erase a failure.
Missing/unreadable/invalid history is **Unavailable**, never “current” or success.
Results distinguish **Current at last check**, **Paused at last attempt**,
**Deferred**, **Unavailable**, **Failed**, and **Successfully updated**. A check
failure while offline does not prove the installed app is current. “Deferred”
means active SDE/tool/package-manager work prevented installation; normal
contention can retry next time without removing locks.

The page shows check-start/completion and policy-change times in local time,
observed installed/candidate app versions, native exit code, independent tool
phase result, engine version and applied tool-baseline version. The app version
in the open window may differ from a newly installed version until reopened.
It is not a tool baseline version or scheduler execution result. The recovery
availability flag means a signed installer was retained at that attempt; when
no upgrade occurred it can refer to the current version, not an older version.
Use `verify-recovery` to establish the exact current/previous retained versions. No new release
notifications are supplied here; #11 owns those. #10 owns broader Overview
maintenance notices. A successful app update must never conceal failed tools.

Current coordination is also shown. An open SDE window contributes to “SDE or
maintenance is active”; that label does not claim a timer is running. Interrupted,
untrusted or incompatible-baseline state requires mentor assessment even if the
last receipt says success. A killed worker may leave its older receipt in place.
Do not interpret absence of a fresh receipt as successful installation.

## Immediate failure checks

On Linux, Schedule also reads a protected, non-secret service-attempt receipt
when systemd no longer retains execution timestamps. New attempts clear previous
success before the launcher starts; completion records include startup failures.
An incomplete receipt remains Unavailable after an interruption. A newer service
invocation or timer trigger prevents an older receipt from concealing missing
results. Existing history is not fabricated during an app upgrade: run the
provisioned maintenance service to establish the first receipt. See the
[1.2.4 focused UAT procedure](SELF-UPDATE-UAT-1.2.4.md).

1. Pause SDE installation using the administrator command. Preserve the tool
   schedule unless its own package work requires a mentor-controlled maintenance
   window. Check Schedule for the independent tool result and current coordination.
2. Record both app versions, candidate, times, phase and native exit. Keep logs
   private; remove tokens, account details and personal paths before sharing.
3. Establish whether any native installer or package-manager children are still
   running. Wait for them. Idle coordination gates or absence of the original
   worker alone do not prove package children completed. Never delete package
   locks or gate files, force-close SDE, force a reboot, or blindly clear intent.
4. Inspect the protected native log and `installation.json`, plus the native
   package state below. Distinguish the phase that failed before choosing repair.

Locations (mentor/admin access required for private files):

| Item | Windows | Linux Mint |
| --- | --- | --- |
| Read-only policy/status | `C:\ProgramData\SkyviewRobotics\SelfUpdate\policy.json` / `status.json` | `/var/lib/skyview-robotics/self-update/policy.json` / `status.json` |
| Native logs (eight completed runs plus active/crashed logs) | `C:\ProgramData\SkyviewRobotics\SelfUpdate\logs` | `/var/lib/skyview-robotics/self-update/logs` |
| Installation and recovery receipts | Same root: `installation.json`, `recovery.json`, `previous-recovery.json` | Same root, same names |
| Retained installers and signed metadata | Same root: `staging\<transaction UUID>` | Same root: `staging/<transaction UUID>` |
| Interrupted-operation journal | `C:\ProgramData\SkyviewRoboticsCoordination\transaction.json` | `/var/lib/skyview-robotics-coordination/transaction.json` |

The status log reference is a validated relative UUID filename, never a caller
supplied path. UI actions are fixed summaries; raw native output/detail strings
are not sent to the UI. Production logs contain fixed failure classifications,
versions/timestamps and native package output, not signing credentials. Release
signing stays in its protected workflow; recovery never needs the private key.

### Download/staging failure

The Download phase has not launched a native installer. A failed or interrupted
transfer cannot authorize installation. Check connectivity to the official GitHub
repository, free disk space and protected-file permissions. Authentication,
truncation and length/hash failures must not be bypassed. Eligible future attempts
re-download and authenticate. Normal staging cleanup removes only recognized,
unretained transaction directories under the operation gate. Do not manually
remove retained recovery assets or unknown files. An unrelated interrupted tool
transaction can still block retry and needs separate assessment.

### Windows native failure or uncertain completion

Read the log and installation receipt. In an elevated terminal, inspect the
64-bit uninstall registration and installed file product version:

```powershell
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Skyview Dev Setup' |
    Select-Object DisplayVersion, InstallLocation
(Get-Item 'C:\Program Files\Skyview Dev Setup\skyview-dev-setup.exe').VersionInfo.ProductVersion
```

An NSIS exit of zero is successful only after app/resource/active-engine checks.
Exit 3010 is recorded as reboot indicated, not assumed successful; other nonzero
or unknown completion and postcheck mismatch retain intent and block automatic
retry. Inspect task history and private logs. If reboot is appropriate, arrange
it with the student after saving work; reboot does not automatically clear intent.
Repair/reinstall the authenticated app package only in a controlled maintenance
window after all native children finish. Do not uninstall development tools or
remove student projects to repair the application.

### Mint installer failure versus damaged package-manager state

These read-only checks work while assessing a stopped attempt:

```sh
sudo dpkg --audit
dpkg-query -W '-f=${db:Status-Status}\n${Version}\n${Architecture}\n' skyview-dev-setup
sudo tail -n 100 /var/log/apt/term.log
sudo tail -n 100 /var/log/dpkg.log
```

A **Packagehealth** failure occurs before SDE's installer launch: the pre-existing
DPKG state requires repair. An **Installer** failure may itself leave a package
unconfigured; a zero exit followed by a **Postcheck** failure can mean inconsistent
app/resources/engine activation. Busy locks are contention, not proof of a damaged
database. Never remove lock files, use database-force options, or start a second
APT while one is active. If all package children have completed, assess the normal
native recovery proposal (`sudo apt-get --simulate --fix-broken install`), review
its proposed package changes, then have a mentor perform the appropriate native
repair (for example `sudo dpkg --configure -a`). Those are system-wide operations,
not a universal SDE recovery script. Recheck `dpkg --audit`, app package version,
resources and engine receipt. Keep app updates paused during repair.

## Retained-installer recovery

Run the fixed verification command as administrator/root:

```powershell
& 'C:\Program Files\Skyview Dev Setup\backend\windows\self-update\sde-update-trust.exe' verify-recovery
if ($LASTEXITCODE -ne 0) { throw 'Recovery assets could not be verified.' }
```

```sh
sudo '/usr/lib/Skyview Dev Setup/backend/linux/self-update/sde-update-trust' verify-recovery
```

It validates the private receipts, canonical versions/UUIDs, trusted paths, pinned
Minisign signature, official repository/channel/tag, platform asset, length and
hash. It prints the current and previous retained package locations without
executing them or clearing intent. A verification failure means stop; a partial
printed result followed by a nonzero exit is not approval. Missing previous signed
assets (common for old unsigned releases) mean reduced recovery capability, not a
promise that a previous version exists.

Use the authenticated current installer for app repair when native assessment
supports it. A previous installer is an emergency option after checking native
downgrade behavior and compatibility with the existing engine, baseline and
student data. Linux downgrades may need explicitly reviewed native options;
Windows installer behavior may reject older packages. This project supplies **no
automatic rollback**, automatic downgrade, or universal rollback guarantee.
Signature verification is necessary but does not prove a downgrade is safe.
If the installed worker is damaged, obtain the trusted verifier and the exact
signed assets from the official repository's approved stable release through a
mentor-controlled repair procedure; never trust an arbitrary local executable.

After native repair, a mentor must establish all package children ended and
verify the app, resources, active engine, applied baseline, package health and
student workspace before addressing the interruption journal. Retain logs and
receipts first. Follow the gate-held recovery requirements in
[SELF-UPDATE-COORDINATION.md](SELF-UPDATE-COORDINATION.md); there is deliberately no
GUI or blind CLI “clear journal” action. Ask Codex to prepare/review the specific
repair and gate-held journal removal from that workstation's evidence. If
completion cannot be established, leave intent intact and stop. Then reopen SDE,
validate tools, check the schedule, confirm pause remained set, and perform owner
UAT before a mentor resumes installation.

## Verification responsibility

Codex tests strict status interpretation/redaction and all six UI outcomes,
separate tool failure, current pause versus old result, read-only capability,
root/SYSTEM pause/resume, real standard-user read/denied writes, retained fixture
key rejection, and pause isolation through the packaged maintenance launchers.
Required CI retains real Windows NSIS and Mint APT/DPKG upgrade/failure tests.
Mint ISO userland in a container proves package execution, not a booted desktop
with a live timer; Windows Server native CI is not Windows 11 UAT. #42 expands
integration; #43 retains the owner's school-laptop UAT and release-promotion
approval. No production policy, secret or release is changed by this issue.
