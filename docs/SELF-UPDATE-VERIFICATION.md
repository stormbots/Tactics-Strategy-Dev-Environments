# Issue #35 verification record

Date: 2026-10-10 (America/Los_Angeles).
Source inspected: `d4df8ac022e6de61520e0942baac9ac8947bcdfe`.
Initial probe implementation: `f1f4b7715261cb748d83af2d1fb23fb56d6ce098`.

## Executed native checks

[Native upgrade run 38116688114](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38116688114)
completed successfully. It downloaded the published v1.2.0 and v1.2.1 installers
and checked the corresponding published SHA256SUMS before executing them on
disposable GitHub-hosted runners. No student workstation was modified.

### Windows SYSTEM

[Windows job and transcript](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38116688114/job/114402849063)
used Windows Server 2022, an actual scheduled task, and `NT AUTHORITY\SYSTEM`.

| Check | Observed result |
| --- | --- |
| Fresh v1.2.0 installer `/S` | Exit 0 |
| Upgrade to v1.2.1 `/S /UPDATE` | Exit 0 |
| Installed executable | `C:\Program Files\Skyview Dev Setup\skyview-dev-setup.exe` |
| Product versions after each transaction | Exactly 1.2.0, then 1.2.1 |
| Bundled maintenance file | Present after both installations |
| External `C:\ProgramData\SkyviewRobotics\AutoUpdate-SkyviewTools.ps1` | Absent after both; app installation did not provision it |
| GUI process after installation | Absent; no `/R` supplied |
| Student-file sentinel | Preserved after both |

The worker finished without interaction or reboot in this scenario. This does not
establish behavior when WebView2 is missing, files are locked, a reboot is already
pending, or Windows 11 operating-system protections interact with an unsigned
installer. Do not generalize exit zero into a complete reboot-code contract.

### Linux root

[Linux job and log](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38116688114/job/114402849457)
used Ubuntu 24.04.5 LTS with actual root APT installation, supporting evidence for
the DEB path on Mint's Ubuntu base.

| Check | Observed result |
| --- | --- |
| DEB identity | `skyview-dev-setup`, `amd64`, expected versions |
| Package control contents | `control` and `md5sums`; no maintainer scripts in these archived releases |
| Fresh 1.2.0 installation | APT succeeded; `install ok installed` |
| Upgrade 1.2.0 → 1.2.1 | APT succeeded; exact 1.2.1 configured |
| Executable | `/usr/bin/skyview-dev-setup` |
| Bundled backend | `/usr/lib/Skyview Dev Setup/backend/linux/Update-SkyviewStudentDev.sh` present |
| Deployed `/usr/local/sbin/skyview-student-dev-update` | Absent; app installation did not provision it |
| Student-file sentinel | Preserved |

This is not Mint Cinnamon or PolicyKit UAT. Neither probe applies the development
baseline or tests the not-yet-implemented bootstrap hooks. GUI absence was also
checked; the follow-up probe uses full command-line matching because Linux process
names can be truncated to 15 characters.

## Local verification

- Bash syntax and ShellCheck (warning level): passed for the Linux probe.
- PowerShell parser: passed for the Windows probe.
- Backend contract checks: 6 tests passed.
- Metadata checks: 8 tests passed.
- Linux runtime checks: 3 tests passed.

The existing PR build workflow additionally runs frontend tests/build/audit,
browser accessibility checks, actionlint, platform backend checks, Rust tests,
and native NSIS/DEB builds. Its results are available on PR #44; these checks
validate packaging/source quality and do not replace installation evidence.

## Required downstream verification

| Owner issue | Remaining evidence |
| --- | --- |
| #36 | Signed metadata round trip, bad signature/hash/identity rejection, signing-secret handling, key lifecycle |
| #37 | Stable selection, real redirects, limits/timeouts, offline/rate-limit outcomes, protected staging |
| #38 | Cross-session/helper gates, inheritance, activity races, stale-state recovery, manual-entry coordination |
| #39 | New Windows bootstrap hook, custom task preservation, engine switch, locked files, relevant exits/reboot behavior |
| #40 | New DEB hooks, unit refresh without active-service restart, APT contention, engine switch |
| #41 | Pause isolation, separate tool/app results, retained-installer recovery, read-only status |
| #42 | Full authenticated unattended flow, interruption/failure scenarios, next-run maintenance, applied-baseline preservation |
| #43 | Windows 11 and Mint 22.x acceptance, controlled two-version UAT, initial migration and representative rollout |

Issue #35 establishes the design and verifies existing native silent upgrade
mechanics on available runners. It does not claim production self-update,
automatic rollback, supported-desktop UAT, or permission to promote a stable
release. Review the architecture contract before implementing its dependent
stories.
