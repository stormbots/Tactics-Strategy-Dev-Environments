# #72 disabled Schedule/backend integration

The owner authorized parallel UI work on 2026-10-18. No update enablement or native
execution is included. PR #73 remains draft and unmerged.

## First integrated slice (historical b8b85db)

- Schedule shows an explicitly unavailable Update Now control, distinct from
  scheduled-maintenance history/policy. Existing results are not eligibility.
- New argument-free Tauri commands inspect_app_update/request_app_update have a
  side-effect-free backend. Inspection always returns disabled/native-validation-
  pending; requests always reject. No filesystem, network, policy, marker, process,
  lock or privilege operation can be reached through this boundary.
- Frontend parsing rejects even an enabled=true reply until a future native
  contract is reviewed. Browser preview remains disabled; no URL, storage, build
  flag or mock-preview switch enables it.
- Consent interaction is exercised through test mocks only: explicit checkbox,
  ordinary-close/crash consent, no immediate cancellation, 15-minute/2-minute
  deadlines and pause commitment boundary. Back exists only before authorization.
  Focus enters confirmation and returns on Back. A synchronous guard prevents
  duplicate submissions. Errors/unexpected success never imply worker creation,
  preparation, cancellation or completion; no automatic retry.

## Read-only discovery/progress slice — 2026-10-18

- Explicit Check SDE release calls a fixed notification-only adapter with the
  running app version and fixed artifact platform. It enumerates official stable
  listings, fetches only bounded manifest/signature bytes and authenticates exact
  bytes through the existing pinned-key/manifest contract. It binds version/tag,
  platform filename and installer size to the selected listing. No installer is
  transferred, staged, run or declared verified. A signed metadata digest is not
  proof of downloaded installer bytes, installed identity or native compatibility.
- No-newer-listing is deliberately distinct from verified/current installation or
  an authenticated guarantee of latest release. Offline, incomplete, untrusted,
  rate-limited and malformed paths cannot show a verified candidate or fall back
  to a lower release. No UI result changes the independent disabled request gate.
- The existing scheduled discovery/installation path is unchanged. Notification
  transport has a separate 15-second total network budget; one process-wide check
  holds a try-lock and starts at most once per 30 seconds, including failures.
  UI has a 20-second watchdog and discards late replies without a background retry.
- Linux progress uses the existing fixed protected runs path and canonical UUID,
  root-owned/non-writable ancestor/file checks, requesting real UID and current
  boot. Its bounded typed projection strips arbitrary detail/path text and always
  sets closeAllowed=false. Windows progress remains explicitly unsupported.
- A request-correlated view polls serially every two seconds, at most 450 reads
  over 15 minutes, with a five-second read watchdog. Timeout halts observation,
  not an independent worker; no retry/worker cancellation or intent clearing is
  inferred. Cleanup removes timers, drops late/foreign results and never signals
  a process. No URL/storage ID or maintenance outcome auto-attaches a request.
- Within a watcher, sequence/state regression, mutation of the same publication, boot/request changes,
  candidate changes and terminal resurrection halt observation. Same-publication
  polls do not refresh reported age. A 10-second presentation freshness bound is
  advisory only, distinct from worker consent/deadline policy. Long-running phases
  may legitimately have an old report; stale does not mean cancelled or failed.
- Preparation is indeterminate; no invented byte percentage. Ready shows a disabled
  Close SDE & install button, including on fresh reports. A separately registered,
  argument-limited backend close command independently refuses every call and
  never exits the app/releases its S lease. Reported outcomes never clear startup
  or recovery barriers. Update and close execution remain hard-disabled.

## Remaining native and integration gates

Deployed capability migration, actual OS-authorized submission/receipt correlation,
attaching that receipt to the normal Schedule/restricted-startup route, actual
Close SDE behavior and Windows privilege/progress implementation remain unfinished.
The ordinary Schedule renders no request watcher because no request can be accepted;
ready/progress views are exercised with isolated correlated fixtures. Do not infer
an end-to-end handoff from these tests or enable it using a marker/mock/URL switch.

Native validation still must prove cross-user ACL behavior, real polkit/UAC and
worker lifetime, installed compatibility, deadlines/suspend, admission/reopen,
package preservation and recovery. No runner/media/VM work or native guest tests
were needed for this slice. W2h's counterexample and W2m's failure remain unchanged.

## Integration and CI boundary

Main was merged into the PR branch, retaining its exact Mint infrastructure
allowlist and manual legacy fixture dispatch rules. Conflict resolution retains
PR #73's checks/update-trust/desktop-check validation jobs; installer/native-package
and release gates are unchanged. Changes to this UI/backend require application
validation, not an infrastructure-only exception. Native package tests remain
ignored unless explicitly selected by the separately dispatched package workflow.

This is implementation/automated-QA evidence only, not desktop UAT, native
privilege proof, authentication safety or release readiness. W2h and W2m results
remain preserved. Optional archival/runner/VM work is paused.

## Local review evidence (first slice)

- UI: 114 unit/component checks pass, including 11 focused disabled-contract,
  consent, duplicate-submit and ambiguous-result checks; TypeScript and Prettier pass.
- Chromium: five accessibility/interaction cases pass. Three affected Schedule
  cases rerun after review pass, including compact/wide reflow and axe audits.
- Linux desktop: all-target cargo check passes; two focused backend refusal/ABI
  tests pass. The full ordinary Linux desktop suite also passes (13 checks).
  Rustfmt and desktop all-target Clippy pass. Existing stream-reader lint was
  resolved with equivalent error-skipping iteration, and the unchanged test
  module moved below production items; no privilege boundary changed. These
  tests do not launch the application or any updater.
- Policy/backend QA: scope, dispatch boundaries, Mint workflow/static fixtures,
  app-only request/package-hook mocks, command permission agreement and actionlint
  pass. Review fixed a stale main-branch job-layout assertion; no workflow gate was
  relaxed. The main-window handler/manifest/permission sets agree.
- Windows native compilation remains an automatic CI obligation, not a local
  proof. Cross-user OS authorization, installed updates, package preservation,
  protected progress and desktop UAT remain unvalidated by this slice.

All files under permissions/autogenerated are build outputs, ignored rather than
hand-edited. Runtime command permission grants remain explicit in main.json.

## Current slice review evidence

- Signed metadata tests exercise real ephemeral signatures, production-key rejection,
  byte tampering and listing/manifest size mismatch. Mock transports assert no
  installer request. No external discovery or installed update ran during local QA.
- Pure Linux projection cases cover identity/boot/future time, stale/expired ready,
  malformed/incomplete candidates and no close authority. POSIX ACL native gate
  remains ignored; these checks do not certify cross-user filesystem access.
- UI cases cover unknown fields, bad identity, replay/state regression, candidate
  changes, terminal outcomes, timeout/late replies, request switch, cleanup and
  bounded polling. Review found and fixed same-age cached replies restarting the
  UI freshness window; conservative carried age/remaining time now survives polls.
- Ready/preparation views have mocked axe checks; compact/wide real-browser checks
  cover disabled controls, preview discovery failure, keyboard/reflow and contrast.
  Live ready/close behavior still requires native validation and owner desktop UAT.
- Backend single-flight/cooldown tests use injected providers without network or
  package operations. Direct request/close calls always fail. Command handler,
  build manifest and local permission sets match; no shell/filesystem permissions
  or update capability are granted by the new commands.

Current local results: 138 UI checks; 16 ordinary Linux desktop Rust checks;
four signed-notification cases; eight selected Linux progress/request cases
(one native ACL case ignored); three affected browser cases; backend permission,
scope, dispatch and request/hook policy checks pass. The ordinary updater library
run reported 58 passed/one ignored before the added standalone notification-budget
regression also passed. Both crates pass all-target Clippy and Rustfmt; TypeScript,
Prettier and actionlint pass. No installed native update, external release discovery,
root fixture provisioning or desktop UAT was executed by these local checks.

## Disabled Linux receipt/deployment wiring follow-up

The previously pending receipt correlation now has a protected per-user lookup
and normal Schedule reconnection; the fixed OS launch transport and disabled
broker/policy deployment/removal hooks are wired. This supersedes earlier wording
that these source paths were entirely unwired. It does not establish native
capability migration, restricted-startup presentation, worker lifetime, ACL support,
package behavior or protected close. Both execution source gates and close remain
false. See [the minimum native authorization packet](../validation/ISSUE72-LINUX-DISABLED-REQUEST-GATE.md).

## Linux-first close/admission review and stopped native evidence

The spare Mint attempt did not establish cancellation or approved entry: the
policy registered but no graphical prompt appeared (exit 127). Its two temporary
files were removed after recorded ownership/inode/mode/hash checks. Evidence is
[user-reported and bounded](evidence/ISSUE72-SPARE-MINT-DISABLED-BROKER.json); no
whole-host cleanup, authentication safety or installed update is inferred.

The Linux close path is now prepared behind its independent **false** source gate.
It validates accepted current-UID/current-boot receipt, canonical request ID, Ready
state, complete candidate, matching overall/Ready deadlines, nonfuture/fresh
publication, native capability hashes, candidate allowlist and unresolved recovery.
After potentially slow hashing it rereads protected receipt/progress/time and checks
again. Main holds the common GUI operation exclusion; on success it requests
process exit while retaining exclusion. It never manually releases/reacquires S.
The worker alone retains installation authority. No close grant or receipt lifetime
is extended by these reads; a race after the last read remains subject to the
worker's independent admission, deadline, pause and installation-core checks.

Ready publications refresh at most every five seconds while the worker retains
O/A and waits for S. The original 120-second/15-minute bounds remain; at most 23
additional Ready publications fit the unchanged 32-publication budget. UI progress
and Close remain disabled for execution; enabling is a separately reviewed step.
Read-only compatibility validation now has direct pure coverage for missing,
changed, substituted and external maintenance files and unvalidated candidates.
No test/hook creates a real native-validation marker.

Normal request submission now shares the existing GUI operation exclusion.
Unknown/timed-out protected receipt lookup blocks new consent; after ambiguous
submission, one bounded read-only recovery lookup may reconnect without resubmitting.
Busy startup keeps its native notice and never admits a full webview without S;
if a current protected receipt is readable the notice explains its limited meaning.
A richer live restricted-startup webview is deferred rather than introducing an
unguarded backend surface. Native dialog behavior and actual exit remain unproven.

The [consolidated native plan](../validation/ISSUE72-LINUX-CONSOLIDATED-NATIVE-PLAN.md)
separates authorization/agent repair, package-free ownership/ACL proof, the controlled
package upgrade, and real feature UAT. It is not an executable authorization packet
until source/artifact pins and the exact native driver exist. Stable-only discovery
and candidate-hook proof remain real dependencies; no fixture or prerelease is
silently treated as a stable candidate. Optional infrastructure remains paused.

Focused local QA for this follow-up: 142 UI tests, 18 ordinary Linux desktop Rust
tests, 64 updater library tests (one native POSIX-ACL case intentionally ignored),
three affected real Chromium Schedule/accessibility cases, ten broker mocks,
twelve hook mocks, seven backend contracts, ten CI-boundary and nine CI-scope
checks passed. Both crates pass Rustfmt and all-target Clippy with warnings denied;
TypeScript, affected-file Prettier, actionlint and whitespace checks pass. These
are development/local fixture checks, not native authorization, actual GUI exit,
package installation, receipt cross-user ACL proof or desktop UAT. No source gate,
activation setting, workflow or package-operation selection was enabled/changed.
