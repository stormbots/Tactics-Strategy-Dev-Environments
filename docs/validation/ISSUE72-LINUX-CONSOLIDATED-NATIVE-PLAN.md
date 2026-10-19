# Linux-first consolidated native session — proposal, not execution authority

The owner approved Linux-first engineering behind disabled gates and preparation
of this session. Package operations, enablement, installer dispatch and releases
still require separate authorization. PR #73 remains draft/unmerged. Windows,
runner/VM/media work and custom-protocol research are paused.

## Current evidence and practical boundary

[Spare-host evidence](../design/evidence/ISSUE72-SPARE-MINT-DISABLED-BROKER.json)
records the user-reported attempt at dc078e3. Existing SDE/state stopped the clean-
host packet. A narrower two-file deployment was authorized and performed; the
policy registered but pkexec returned 127 without a GUI prompt. No cancellation
or approved entry was proved. A process-name search found no matching agent and
journal output was empty; the root cause remains unknown. Both temporary files
were removed after root-owner/hash/inode/mode checks. Sources and journal remain.
This is blocked diagnostic evidence, bounded cleanup evidence and unproven
authentication safety. It does not supersede W2h/W2m or earlier ACL limitations.

Do not repeat the original clean-host bootstrap packet on this installed host.
Use the spare PC as an explicitly disposable **installed** baseline only after
recording its actual package version, installed-file hashes, policy, service/timer
configuration and recovery state. Do not uninstall SDE just to pass preflight.

## Efficient sequence and stop gates

One engineering review and one artifact review precede one scheduled native
session. Run the already-existing automated fixtures rather than constructing
another runner/VM system. Execute cases sequentially, stop at the first unexpected
result, and rerun only an affected case after a reviewed fix. User desktop UAT is
separate from native process/package proof and may share the same final session.

| Stage | Work | Pass / stop condition |
| --- | --- | --- |
| 0. Artifact and host pin | Pin source commit, trusted baseline/candidate package versions and hashes, signatures, deployment files and evidence directory. Read installed state and verify no unresolved transaction. | Stop if pins, recovery, disk or ownership are unknown, or a native fixture cannot use the existing installed baseline safely. |
| 1. Desktop authorization | Targeted read-only inspection of existing session/agent executable/autostart and polkit action mapping. If an existing packaged agent is absent from the session, propose its exact non-root launch for approval; no new package, service or settings change by assumption. Then one cancelled and one approved disabled-broker check using the bounded two-file deployment and checked removal. | Stop if a GUI prompt cannot be established, consent does not map to the original UID, denial creates a request, or approved entry is not disabled exit 78. No sudo fallback for the real app request. |
| 2. Package-free process proof | Select existing isolated coordination tests and bounded root-owned fixtures for same-UID receipt access, denial to another existing UID, malformed/missing records, retained worker, O/A/S ownership, multiple windows and rapid reopen; simulate pause/deadlines/interruption via test-only fixtures. | Wrong UID access/write, second admission, unexpected child/lock retention, duplicate action, cleared uncertain intent, unaccounted residue or deadline extension stops. Synthetic outcomes are labeled and never certified as a real installer result. |
| 3. One controlled package upgrade | Once explicitly authorized, install the pinned prerequisite testing baseline and run one strictly app-only upgrade to the pinned compatible candidate through the reviewed shared native installation core. Include real package hooks, retained S until close, admission during commit, postchecks and tool/schedule preservation. | A tool operation, incompatible hook, reacquired lease, unverified bytes, wrong package, unknown descendant, unsafe reopen or lost recovery evidence stops. Do not replay after uncertain commitment. |
| 4. Feature/UAT proof | With separately authorized testing enablement and installer build, exercise real Schedule consent/request/preparation/Ready/close/reopen, ordinary close/crash semantics and keyboard/status behavior on the owned Mint desktop. | Only original OS authorization plus independently held worker authority may lead to installation. Close does not clear recovery intent or grant installation authority. A stale UI must be rejected safely. |
| 5. Closeout | Capture protected receipts, exact action/package exits, ownership/locks/processes, source/artifact pins, unchanged settings and cleanup inventory; restore test-only activation and preserve uncertainty. | Report diagnostic completion, cleanup correctness, native safety evidence and desktop acceptance independently. No stable promotion or rollout. |

## Important artifact dependency — do not bypass release trust for speed

The product worker selects only an authenticated **official stable** eligible
release, and capabilities bind the exact candidate package bytes. An arbitrary
locally built or prerelease installer cannot be substituted. The native session
therefore needs a verified baseline/candidate pair with compatible app-only hooks.
Existing stable binaries must not be assumed compatible with the new hooks.

A package-fixture invocation of the shared installation core can prove package
operations with review-pinned test artifacts; it does not prove the public stable
worker discovery path. Its exact driver/inputs must be reviewed before package
authorization. Full worker end-to-end proof needs either a qualifying authenticated
stable candidate or a separately reviewed, isolated test-only signed-discovery
fixture that cannot affect product trust or production enablement. Neither exists
merely because local tests passed. Do not publish a stable release to manufacture
a candidate, fake a capability marker, change the production key/feed/version
rules or promise one upgrade establishes both paths without checking this gate.

Before requesting execution, fill the artifact pins and executable driver commands.
These are engineering inputs to prepare; no additional product decision is needed
unless the available artifacts require a change to the approved trust contract.

## Exact additional operation classes requiring authorization

The following is a bounded preparation list, **not yet an executable packet**:

* Root-owned fixture creation/deletion under a single new
  `/var/lib/coordination-test-<run-id>` directory with inode/owner journal checks;
  use an existing second unprivileged UID, no account creation by assumption.
* Temporary deployment/removal of the fixed disabled broker and polkit action,
  with source hashes and existing-state preservation. This is polkit registration;
  the original two-file deployment permission was consumed by the stopped attempt.
* Any launch of an existing desktop authentication agent must name its verified
  packaged path, session/UID and stop/cleanup procedure; no installation or settings
  repair is currently authorized.
* Installation of the reviewed testing baseline and **one** controlled native
  app-only upgrade, using exact package hashes/versions and the reviewed fixed
  driver. State explicitly which current SDE files/package metadata change, the
  expected package-hook effects, child supervision and recovery/rollback boundary.
  Retain the administrator pause and unrelated scheduled-maintenance settings.
* Any test-only capability receipt/activation must be separately approved, backed
  by the relevant real native file/hook evidence, scoped to the exact artifacts,
  and removed/restored at closeout. It is not permission for production enablement.
* Installer/application-build dispatch remains separate from these native steps;
  signing/publication/release preparation is not implied by package authorization.

Maximum proposed operator session: 90 minutes, one controlled upgrade, bounded
16 MiB evidence directory (installer artifacts separately size-pinned), no media
or guest download, no runner registration, no new task/service, no fleet action.
Do not kill an uncertain committed installer/worker as a cleanup shortcut. Stop and
preserve evidence on any unsupported prerequisite, unexpected outcome, resource
limit or failed ownership/cleanup check. Unknown state is not automatically repaired.
