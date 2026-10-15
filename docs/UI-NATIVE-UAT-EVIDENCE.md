# Native fixture verification evidence — 2026-10-15

## Outcome

**Native verification is blocked on both requested platforms.** No disposable
Windows or Mint desktop is attached or configured for remote access in this
session. Local regression checks passed; they do not establish native acceptance.
No platform defect was reproduced, so no speculative helper changes were made.

The helpers remain uncommitted local changes based on source
`b6cbf6548e8ec09522a7d61bf29d8101826dda69` (merged PR #66).

| File tested | SHA-256 |
| --- | --- |
| `tests/native_uat_fixtures.py` | `5749cfd7f9523c46e3974faef366148008fc5331b7fc44f68c69c9b72673e6c1` |
| `tests/test_native_uat_fixtures.py` | `73e7951e280044c73b2de1c718b099fcb699d309885b6b70d4dd17d712b81481` |

## Available execution environment

- Debian GNU/Linux 13 (trixie), x86_64; Linux kernel 6.18.44.
- Python 3.12.14; Git 2.52.0.
- No `/dev/kvm`, QEMU, VirtualBox, libvirt CLI, PowerShell or Tailscale CLI.
- Managed runtime observations were current: no remote-access secrets, runtime
  variables or outbound identities were configured. The supported policy reports
  no VPN configuration and zero TCP destination grants.
- No connected Windows or Mint desktop tool was available. Docker availability
  does not supply either of the requested desktop environments.

No remote host was guessed, scanned, provisioned, or accessed. The user was asked
whether disposable Windows 11 and Mint Cinnamon VMs can be connected, with access
credentials configured through secure environment settings rather than chat.

## Local verification actually executed

| Check | Result | Scope |
| --- | --- | --- |
| `python -m unittest discover -s tests -p test_native_uat_fixtures.py -v` | **17 passed** | Temporary filesystem roots and real Git; native identity/target paths substituted |
| `python -m py_compile tests/native_uat_fixtures.py tests/test_native_uat_fixtures.py` | Pass | Python syntax/compilation only |
| Actual CLI `enroll --acknowledge-disposable-vm` on Debian, temporary state path | Pass | Nonzero exit with `Native fixtures require Windows or Linux Mint`; verified no state directory created |
| `git diff --check` | Pass | Tracked diff whitespace check |

The 17 tests cover exact-byte Git restoration, both repository CSV schemas,
empty workspace restoration and repeated restore, preservation of student work,
drift/deleted-file refusal, active-case exclusion, wrong-host/acknowledgement
checks, pending-intent recovery, permission-denied recovery, linked targets,
state-directory location, exclusive locking, and PowerShell command construction.
The Windows ACL command is mocked in its construction test; it was **not executed
on Windows**. Real Git/file operations in this suite still run on Debian, not Mint.
The local verbose test log is `work/native-uat-tests.log`; it is temporary evidence,
not a native acceptance report.

## Native execution record

| Required check | Windows 11 | Mint Cinnamon 22.x |
| --- | --- | --- |
| Desktop/OS, dedicated account, snapshot and access verified | Blocked — no connected host | Blocked — no connected host |
| Enrollment and private backup directory permissions | Not run | Not run |
| Actual CLI workspace apply/restore | Not run | Not run |
| Actual CLI Git-default apply/restore and effective setting | Not run | Not run |
| Installed repository CSV apply/restore | Not run | Not run |
| Native Validate observes expected diagnostics and guidance | Not run | Not run |
| Post-restore Validate matches baseline | Not run | Not run |
| Drift/interruption handling and snapshot recovery | Not run | Not run |
| Elevated Repair continuity and full snapshot recovery | Not run | Not run |

## Resume procedure

Once Codex has secure access to disposable desktops, verify host identity and
snapshot recovery first, then follow [fixture commands](UI-NATIVE-UAT-FIXTURES.md).
Record the exact helper hashes above (or new hashes after reviewed fixes), OS,
Python/Git, account type, current installed SDE version, snapshot identity, command
exit codes, permission checks, original native diagnostics, restoration results
and the post-restoration report. Keep private Git backup contents out of evidence.

Helper-only verification can use a suitable existing installation to establish
setup/restore behavior. Such a run on v1.2.7 cannot accept the newer theme/zoom/
guidance UI: combined milestone UI UAT still requires a separately authorized test
build. If no suitable installed baseline exists, record the native backend case
Blocked rather than building/installing SDE under this task.

Application versions, workflows, tags, build dispatch, signing, releases and
application-update policy were not changed. No push or PR was opened that could
trigger application builds. Release preparation remains deferred.
