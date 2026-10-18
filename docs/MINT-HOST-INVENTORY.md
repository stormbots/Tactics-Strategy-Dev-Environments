# Spare Mint host inventory: disabled infrastructure only

This workflow registers its name on main so an organization administrator can
select it in a restricted runner group. It does not enable or deploy #72, merge
#73, register/start runners, provision guests or install application packages.

## Activation is a separate approval step

Leave these repository Actions variables absent during PR review and merge:

- MINT_RUNNER_ENABLED (must later equal exactly `true`)
- MINT_RUNNER_ACCESS_READY (must later equal exactly `verified`)
- MINT_RUNNER_APPROVED_SHA (must later equal the full reviewed main commit SHA)

Missing flags or mismatched SHA skip the sole job before scheduling. There are
no dispatch inputs, PR/push triggers or reusable-workflow entry points for the
inventory. It is manual-only and main-only. Later main commits disable it until
reviewed and approved explicitly. Do not set the variables during this PR.

Before setting ACCESS_READY, an organization administrator must verify:

1. Group `sde-mint-isolated` is not Default, uses Selected repositories containing
   only stormbots/Tactics-Strategy-Dev-Environments (explicit public-repo opt-in),
   and Selected workflows containing exactly:

   stormbots/Tactics-Strategy-Dev-Environments/.github/workflows/mint-host-inventory.yml@refs/heads/main

2. Main is protected against unreviewed/direct/force changes and deletion,
   including workflow code-owner review and no routine administrator bypass.
3. Environment `mint-host-access` already exists, has an independent required
   reviewer, prevents self-review, permits main only, has no secrets, and disables
   administrator bypass where supported. GitHub can create unprotected environments
   automatically: naming an environment in YAML does NOT establish these settings.
4. The exact SHA and live settings have been reviewed. Only then set ACCESS_READY,
   APPROVED_SHA, and ENABLED last. This is an administrator attestation; the job
   does not claim to inspect organization settings through its empty-permission
   token. A trusted administrator can alter policy; labels/flags are not a
   substitute for scheduler-side repository/workflow restrictions.

No runner should be registered until these controls are verified. Repository
admin permission alone did not let Codex inspect org runner groups: that API
returned 403. If any protection cannot be applied, stop without broadening access.

The group cannot be configured with this workflow until it exists on main.
Merge this separate infrastructure PR only after its checks/review pass and
merge authorization is given; keep #73 draft/unmerged. Then create/verify the
restricted group and approval environment. Registration, start, dispatch and
guest testing remain separately authorized later steps, not consequences of merge.

## Fixed inventory boundary

The job uses `org/sde-mint-isolated` and routing label `sde-mint-inventory`, runs
as a non-root dedicated account, has no GitHub token permissions, secrets,
checkout, third-party action or arbitrary command/ref input. Its fixed inline
Python only queries KVM_GET_API_VERSION (no VM created), checks Mint release,
and calls QEMU --version. It prints bounded facts with guestExecuted=false,
mediaAuthenticated=false, consolePrepared=false and productionReady=false.
The five-minute job timeout is not a guest-worker kill/cleanup mechanism. No
registration, VM boot, privileged change, media download, service, application
build, package operation, signing or release step is present.

The account needs existing KVM access; neither account creation nor dependency
installation happens here. The reviewed temporary-runner setup remains on #73's
branch for later approval; it is deliberately not imported into this PR.

## Focused CI and review evidence

mint-host-inventory-checks.yml runs static/unit policy checks and actionlint on
GitHub-hosted Ubuntu only. It cannot select the spare runner or its environment.
Tests parse inline Python without executing it, exercise missing/partial flags,
wrong events/repos/refs/SHAs, and assert a fixed read-only subprocess command.
They also verify installer CI is skipped only for exact infrastructure paths.

main's existing CI otherwise builds installers automatically, so the existing
scope classifier gains an exact seven-file infrastructure allowlist. PRs containing
any application/unknown path still require normal CI. A main push skips application
CI only when its complete before/after diff contains exclusively these exact
infrastructure files. Missing/malformed/deleted/mismatched push metadata or failed
diff cannot skip. Release refs and manual application dispatch are unchanged.
No application workflow steps/triggers or package policies were transplanted
from #73. This narrowly avoids installer preparation both for this PR and a
future authorized infrastructure-only merge.

No native runner enforcement, host execution, authentication or cleanup has been
validated by these static checks. Historical #72 research failures remain intact.

References:
- https://docs.github.com/en/enterprise-cloud@latest/actions/how-tos/manage-runners/self-hosted-runners/manage-access
- https://docs.github.com/en/rest/actions/self-hosted-runner-groups
