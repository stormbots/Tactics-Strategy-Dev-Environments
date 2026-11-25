# Project working-folder verification

Part of [#161](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161)
and its accepted project-location plan. This increment verifies a working folder;
saving locations and confirming a course project's identity remain later steps.

## What the current check establishes

Windows and Mint configured-project validation now ask Git whether the exact
folder is a working-tree root. Ordinary repositories and valid linked worktrees
can pass. A worktree's `.git` entry may be a file. A `.git` file or directory alone
cannot establish a pass, and finding a repository in a parent folder cannot
certify the selected child folder.

The fixed command uses `--no-pager`, `--no-optional-locks`, `core.fsmonitor=false`
and `rev-parse --show-toplevel --is-inside-work-tree`. The returned root must
match the inspected folder. There is no status refresh, hook, remote command,
fetch, clone, checkout, branch change, project write or Git trust override.
Fork remotes and uncommitted work are kept. A verified working folder does not
establish that its remote matches a required course project.

The helpers run only for an ordinary user. They use the existing bounded
[Linux](../linux/lib/editor_location.py) and
[Windows](../windows/chocolatey/tools/EditorLocation.ps1) diagnostic runners:
six seconds for this query and 32 KiB per output stream. Only the diagnostic
child can be terminated at its deadline. Filesystem access itself is not a hard
wall-clock guarantee. Windows currently supports local-drive directories without
reparse points; unsupported layouts remain incomplete.

Child-process Git environment variables that could select another repository,
write trace/output files or inject command-line configuration are removed.
`GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM` and `GIT_CONFIG_NOSYSTEM` retain the
ordinary user's trust-configuration context. Normal global/system Git rules
still apply; SDE adds no `safe.directory` exemption. The parent environment and
configuration files are unchanged.

Unavailable paths, missing Git, ownership/trust refusal, timeouts, malformed
output and other inspection failures cannot become Passed. They remain an
incomplete project check; they do not prove that a project was deleted. The
configured-project check still contributes its existing required validation
result. This increment does not change which configured projects are required.
Missing optional versus explicitly required projects still need their accepted
policy/UI implementation.

## Integration and remaining work

[Windows validation](../windows/chocolatey/tools/Validate-SkyviewEnvironment.ps1)
and [Mint validation](../linux/Validate-SkyviewStudentDev.sh) use the new working-
folder helpers. Native deployment includes the helpers and the Linux integrity
manifest covers shipped sources. Default workspace roots remain unchanged.

No Save/Open endpoint or new IPC authority is added. The remaining flow must
review an explicitly selected existing location, save only after an explicit
choice, and use that same reference in validation, Open workspace and later
approved setup. It must distinguish unavailable access from confirmed absence,
retain multiple-clone/fork identity, and prevent duplicate setup at an old
location. This check alone does not complete that flow or change provisioning.

## Validation

Eleven new Python cases exercise real repositories/worktrees, dirty-file and Git
configuration byte preservation, fork remotes, fake Git entries, parent roots,
environment injection/tracing, hooks/fsmonitor, elevation/path refusal, failed
or malformed queries, missing Git and single-result validation. Metadata coverage
is now 87 cases. Windows tests exercise the production helper and diagnostic
runner in existing backend contracts. Existing standard-user Windows/Mint profile
fixtures additionally require real repository/worktree verification, refusal of
a foreign-owned repository and retained student/configuration bytes. Native
migration checks require the deployed Windows helper.

All earlier tests remain in force. Full Windows/Mint, trust, integrity, acceptance
and exact-main validation are required. Native fixtures are implementation
evidence, not owner UAT. Human signing, exact authenticated-candidate owner UAT
and separately authorized promotion remain mandatory.

Local evidence: all 87 metadata cases, backend contracts 35, CI-policy 35, Bash
syntax/ShellCheck, the complete Linux integrity manifest and offline docs/diff
checks pass. Windows helper execution and protected standard-user/native fixtures
remain CI requirements. Frontend sources and their 415 unit / 148 browser inventory
are unchanged by this increment.

## Fixture trust isolation

The first native attempt found two fixture setup assumptions. Windows test cleanup
must preserve whether Git environment variables were absent, rather than leaving
an empty `GIT_DIR` that Git rejects. The project fixture now isolates and restores
its Git environment and uses a controlled global configuration with system config
disabled. The earlier preference test asserts restoration of both presence and
value.

The Linux foreign-owner negative fixture also disables system Git configuration,
checks the fixture's actual root ownership and requires Git itself to refuse the
folder before checking SDE's result. A system `safe.directory` policy can
legitimately allow foreign repositories; that is not a bypass added by SDE. A new
local control demonstrates Git's refusal with an empty trust policy and acceptance
under an explicit system exemption. Production continues to respect the ordinary
user's trust context; no production `safe.directory` override or weaker assertion
was introduced. Actual Windows/protected native execution remains required CI
evidence after these fixture changes.
