# Native fixture verification evidence — 2026-10-15

## Scope

The helper verification uses the same automation approach as earlier native
checks: a disposable GitHub Windows runner and genuine Linux Mint userland
extracted from the signed official ISO. User-provided VMs are not required for
these helper checks. The earlier Debian-only access assessment was incomplete:
GitHub Actions supplies the disposable native environments remotely.

This is fixture automation, not desktop UI UAT. The Windows job uses Windows
Server 2022, not Windows 11. Mint runs in a container from the 22.3 Xfce ISO, not a
booted Cinnamon desktop. No SDE package is built/installed; no application Validate,
Repair, elevation-dialog, screen-reader or appearance acceptance is inferred.

## Reviewed and tested source

- Branch: `qa/native-uat-fixtures`.
- Tested source: `f2689bb36084c42745cbc41e482bc85a4bf485f0`.
- [Fixture-only CI run](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38738469312).
- Later documentation-only commits do not alter the tested helper/workflow files.

| File tested | SHA-256 |
| --- | --- |
| `tests/native_uat_fixtures.py` | `8144b017083b91e7625ba51e44f8a250d8028910f3c7b61ddb97a89e1a70498c` |
| `tests/test_native_uat_fixtures.py` | `1fd78b1425214bb32c98b70ad18c7ed4008b905e2c490d54ec9364c0ab88690e` |
| `tests/verify_native_uat_cli.py` | `daff537d416a96938109755fb177c4956ff21003fd7c1e24c355e6226729ae62` |

## Platform results

**Both fixture jobs passed** on the exact source above. Windows completed in
38 seconds; Mint completed in 5 minutes 18 seconds.


| Check | Windows runner | Mint non-root container |
| --- | --- | --- |
| Regression suite | Pass: 16 passed, one POSIX-only test skipped | Pass: all 17 passed |
| Actual CLI enrollment and private backup permissions | Pass | Pass |
| Actual workspace apply/restore, repeated restore | Pass | Pass |
| Actual Git-default apply/restore, exact original bytes | Pass | Pass |
| Actual installed-location repository CSV apply/restore | Pass | Pass |
| Actual changed-file refusal preserves the edit | Pass | Pass |
| Evidence artifact retained | `native-fixture-Windows` | `native-fixture-Mint` |

The CLI smoke test uses actual platform identity, account/profile and target paths;
it does not mock the OS, Git command, filesystem or Windows ACL API. Windows uses
a dedicated synthetic HOME/USERPROFILE on the disposable runner. Mint uses an
actual non-root account with a dedicated home. Neither contains student data.
Machine-wide fixture locations start absent; the harness refuses existing data.
The test-owned CSV location is prepared writable without weakening the helper.

The Windows native smoke checks a protected current-user-only DACL. Mint checks
0700 and account ownership. Native commands apply/restore all three supported
cases and compare exact original bytes, then deliberately edit the Git fixture
and verify restoration refuses to overwrite it. Tests never export the private
ledger or backup configuration. JSON records and regression output are retained
as Actions artifacts; retention is finite, so preserve them before expiry if
needed for long-term acceptance.

### Retained artifacts

Both artifacts were present and unexpired when recorded:

| Artifact | Archive SHA-256 |
| --- | --- |
| [Windows evidence](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38738469312/artifacts/11973744215) | `18fdb1ecc380cae8ad9d9089e9ab420a69fca1ae798051e12b70615dcc6185d5` |
| [Mint evidence](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38738469312/artifacts/11974870791) | `acb372fd28345f8aca1e8b6568d249f1dc5d87a528dec0d6f1cb58e7b6f3394e` |

Each contains its platform JSON smoke record and `unit-tests.txt`. Archive
hashes are from the GitHub artifacts API; helper hashes above identify the
source actually exercised. These artifacts are test evidence, not installers.

## Defects and verification improvements

1. Windows failed while loading `Set-Acl` from `Microsoft.PowerShell.Security`.
   The captured native error reported that the command's module could not load.
   Replaced that module-dependent operation with Windows .NET
   `System.IO.Directory.SetAccessControl`; the actual Windows CLI and DACL check
   then passed. Command paths remain environment data, not interpolated script.
2. Made Python/Git test prerequisites explicit in the minimal Mint image after
   its first CLI step stopped before producing smoke evidence. Only test
   dependencies are installed, not SDE or its development-tool baseline.
3. Preserve unit failures as bounded Actions annotations and text artifacts,
   including when the job fails. Direct log downloads were unavailable from the
   local restricted network, so annotations supplied the Windows diagnosis.

Superseded failed/cancelled runs are not acceptance evidence. The final source
run linked above supplies the platform result. No failure was hidden by disabling
ACL checks or bypassing the non-root Mint guard.

## Local checks

Debian 13 x86_64, Python 3.12.14, Git 2.52.0:

- All 17 regression tests passed, using temporary paths and substituted platform
  identity. These are local tests, separately labeled from actual native CLI runs.
- Python compilation of all four helper/test entry points passed.
- Workflow YAML parsed with the expected isolated push branch and two fixture jobs.
- Actual unsupported-host enrollment rejected Debian with nonzero exit and no
  state directory created.
- `git diff --check` passed.

## Deferred acceptance and delivery

Actual Windows 11 and booted Mint Cinnamon UI acceptance remains pending under
[the consolidated plan](UI-MILESTONE-UAT.md). Successful helper automation neither
accepts #4/#5/#6 nor closes their issues. Unknown/runtime failures, genuine tool
updates, scheduler changes and full Repair are outside this smoke test.

Application versions, tags, signing, releases and update policy remain unchanged.
The recorded native run above was fixture-specific CI on the isolated branch;
no application build workflow was dispatched. Subsequent PR integration adds a
lightweight scope classifier and gated application jobs, with policy tests. See
[fixture CI scope](UI-NATIVE-UAT-FIXTURES.md#fixture-only-ci). PR scope/native/lint
results must be recorded separately from the earlier source run above. Main and
release state remain unchanged until separately authorized.
