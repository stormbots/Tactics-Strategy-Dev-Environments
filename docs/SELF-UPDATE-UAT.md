# Owner UAT for SDE self-updates (#43)

Use one representative Windows 11 x64 laptop and one booted Linux Mint 22.x amd64
laptop with a mentor administrator account and ordinary student account. Save
student work first. Keep app updates paused on all classroom laptops. Codex owns
builds, authentication, automated tests and diagnosis; the owner owns acceptance.
Do not use CI test scripts or ephemeral signing keys on a laptop.

## Before testing

Have Codex complete the [candidate preparation](SELF-UPDATE-ROLLOUT.md), verify the
published signatures and both installers, and supply the exact release URLs,
source commit, Actions run and SHA-256 values. Both v1.2.2 and v1.2.3 must still
show **Pre-release**. Do not use GitHub's `/releases/latest` link for these tests.
Unsigned archived 1.2.1 does not establish the new trust contract.

Download **all five assets for each version** into separate local folders:
both installers, SHA256SUMS.txt, sde-update.json and sde-update.json.minisig.
Never mix versions or overwrite assets. The first bootstrap relies on mentor
approval of the reviewed source and Codex's signature/hash evidence. Once the
trusted candidate is installed, its pinned verifier can authenticate both full
folders before the second installation. Checksums alone are not authentication.

Record the starting app version; project/Git status; editor settings; Node and
Python versions; applied tool-baseline version; and task/timer schedule, enabled
state and last result. Use an ordinary sample project with saved edits. Ask Codex
to help collect a sanitized before/after record without posting personal data.

## Two-version manual installation

Close SDE normally and wait for maintenance/native package work to finish. This
manual test does not use automatic installation gates: never launch it while SDE
or tool maintenance is active. Do not select GUI Install/Repair/Update to install
the application; those are development-baseline actions.

Windows: in Windows PowerShell **as Administrator**, change to the v1.2.2 folder:

```powershell
$package = (Resolve-Path '.\Skyview-Dev-Setup-Windows-x64.exe').Path
$p = Start-Process $package -ArgumentList '/S','/UPDATE' -Wait -PassThru
$p.ExitCode
```

Expect exit 0 and no installer/GUI window or forced reboot. Exit 3010 indicates a
reboot requirement and needs mentor assessment; do not count it as a clean pass.
Then reopen SDE as the student, check About 1.2.2 and Schedule's **Paused by
administrator**, and close SDE again. Installed worker path:

```powershell
$worker = 'C:\Program Files\Skyview Dev Setup\backend\windows\self-update\sde-update-trust.exe'
& $worker verify 'C:\full\path\to\v1.2.2-assets' v1.2.2
if ($LASTEXITCODE -ne 0) { throw 'Starting assets failed authentication.' }
& $worker verify 'C:\full\path\to\v1.2.3-assets' v1.2.3
if ($LASTEXITCODE -ne 0) { throw 'Upgrade assets failed authentication.' }
```

Replace the example asset-folder paths. After both checks succeed, change to the
v1.2.3 folder and repeat the installer command, then check About 1.2.3.

Mint: in the v1.2.2 folder, after checking package-manager work is idle:

```sh
sudo env DEBIAN_FRONTEND=noninteractive apt-get -y --no-remove --no-install-recommends \
  -o DPkg::Lock::Timeout=30 -o Dpkg::Options::=--force-confdef \
  -o Dpkg::Options::=--force-confold install ./Skyview-Dev-Setup-LinuxMint-amd64.deb
```

Expect a configured package at 1.2.2, no GUI launch or forced reboot. Reopen as
student, inspect About and paused status, then close it normally. Authenticate:

```sh
worker='/usr/lib/Skyview Dev Setup/backend/linux/self-update/sde-update-trust'
"$worker" verify '/full/path/to/v1.2.2-assets' v1.2.2
"$worker" verify '/full/path/to/v1.2.3-assets' v1.2.3
```

Stop if either exits nonzero. Repeat the installation command from the v1.2.3
folder. Check `dpkg-query -W skyview-dev-setup` and About show 1.2.3.

## Legacy maintenance prerequisite

An app upgrade preserves an older uncoordinated deployed baseline. With SDE
closed, coordination can therefore show **Needs repair** rather than idle; its old
schedule is not silently changed to the new launcher. This is expected and blocks
automatic installation. Follow the separately authorized mentor baseline Repair
in [the migration guide](SELF-UPDATE-ROLLOUT.md) before testing continued maintenance
through the new host. Record before/after tool versions and schedule settings:
Repair is a real baseline action and can change tools/default schedules. Do not
mark the maintenance/deferral tests passed while this prerequisite is unresolved.
An app-only machine with no deployed baseline needs no compatibility migration.

## Checklist and expected results

| Owner check | Expected result / boundary |
| --- | --- |
| Silent 1.2.2 → 1.2.3 manual upgrade | Real native install; app and engine update; no launched student GUI or forced reboot |
| Student files/settings | Saved edits, repositories/Git settings and editor preferences unchanged; reopen and work normally |
| Baseline/schedule | Applied tool baseline unchanged; existing customized schedule/enabled state preserved; app-only laptop gains no tool schedule |
| Pause/resume round trip | Use mentor guide `resume`, inspect, then immediately `pause`; policy alone changes; no installation or baseline action starts. Only on these test laptops, while both releases remain prereleases |
| Read-only student view | Student sees status/policy and cannot change them; app/engine and older baseline versions remain distinct |
| Active SDE | Coordination shows active while SDE is open; close normally and refresh fixed worker status. Prereleases cannot supply a real automatic-install deferral on laptops; native CI proves the production lease gate |
| School network | Administrator `check` reaches official GitHub, excludes prereleases; offline gives unavailable rather than current; reconnect and repeat. It does not write the maintenance history |
| Tampered metadata | Copy an asset folder, alter metadata, run `verify`; nonzero exit. Never install the damaged copy. Codex can prepare this harmless fixture |
| Continued tool maintenance | Immediate existing task/service below runs applied tools with new engine and paused app result; tool success/failure remains separate |
| Booted schedule | Observe actual task/timer next-run and one real firing on a booted laptop; missed-run catch-up/custom timing remain correct |
| Recovery | Understand mentor log/receipt paths; missing recovery after a manual bootstrap is allowed. Do not fabricate package failures on student laptops; CI covers native failures |

Do not expect **Successfully updated** or retained automatic-install receipts
from these manual installs. They activate the engine but do not synthesize a
worker attempt. Missing history remains Unavailable until real maintenance runs.

## Immediate checks and maintenance (no weekly wait)

The installed worker's `check` is discovery only: it neither installs nor applies
tools, and does not prove automatic eligibility of a prerelease. Run it from an
administrator terminal on the supported OS, while keeping policy paused:

```powershell
& $worker check
& $worker self-update-status
```

```sh
sudo "$worker" check
"$worker" self-update-status
```

The newer prereleases are ignored. Older unsigned stable releases can produce an
unavailable result on older installations; that is not permission to bypass trust.
On 1.2.3 with no newer stable release, expect no newer candidate when online.

To test the **existing provisioned schedule**, close SDE and choose a maintenance
window; these commands really update development tools. Do not register a new
task/timer or enable a disabled one merely for app UAT. Windows elevated:

```powershell
Get-ScheduledTask -TaskName 'Skyview Robotics - Dev Tool Updates'
Start-ScheduledTask -TaskName 'Skyview Robotics - Dev Tool Updates'
Get-ScheduledTaskInfo -TaskName 'Skyview Robotics - Dev Tool Updates'
```

Mint:

```sh
systemctl status skyview-student-dev-update.timer --no-pager
sudo systemctl start skyview-student-dev-update.service
systemctl status skyview-student-dev-update.service --no-pager
```

Wait for native/package work to finish, reopen SDE and refresh Schedule. Check new
engine, preserved applied baseline, separate tool exit and paused app result.
If no provisioned schedule exists, mark this test not applicable until a separate
mentor-authorized baseline provisioning action; do not count app-only installation
as scheduled-maintenance success.

## Later automatic pilot

After accepting the exact manual UAT target, separately authorize stable promotion
and resume only on a reserved representative Windows/Mint pilot still at 1.2.2.
Use the rollout guide's open-SDE deferral test and closed-SDE automatic upgrade to
accepted stable 1.2.3. This verifies the real discovery-to-installation path on
school laptops without exposing an **unaccepted** stable release. Do not downgrade
the manual UAT laptops, promote 1.2.2, or unpause the classroom fleet for this test.
Record pilot findings before authorizing wider deployment. Promotion and resume
remain pending; these instructions supply no authorization.

## Findings, acceptance and failure response

Stop on unexpected version/policy, changed student data, validation failure or
interrupted native state. Keep app updates paused, preserve logs and use
[mentor recovery](SELF-UPDATE-MENTOR.md). Never kill installers, delete locks or
clear intent to get a green result. Give Codex sanitized OS/version, test step,
expected/actual result, times and native/tool exits; Codex diagnoses and supplies a
new immutable candidate if code changes. Repeat affected UAT on that new build.

Record each result in [the acceptance record](ACCEPTANCE-SELF-UPDATE.md). The owner
must explicitly accept the exact target/source/assets on both systems. Automated
checks, approving signing, merging a PR, or finishing this checklist do not by
themselves authorize stable promotion or classroom resume.
