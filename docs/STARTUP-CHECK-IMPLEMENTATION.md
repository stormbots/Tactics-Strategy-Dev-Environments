# Startup checks: first implementation increment for #160

## What changed

Startup now waits for fresh safety information before asking for tool validation. One same-window read sequence owns both phases. Checks in that window that need the same native operation gate wait until the sequence finishes.

An explicit Check my setup uses the same sequence, including the post-validation safety refresh. Its pending state covers queue admission as well as execution, so a queued request does not look ignored or allow duplicate submissions.

The queue is frontend scheduling only. Its opaque ReadSequence identity is not a native lease, acknowledgment, saved safety result or execution permit. Native locking, trust, package checks, incident binding and privilege rules are unchanged. Install/Repair/Update are not put into a read-only queue. Their existing explicit review and fresh native admission stay authoritative.

## Source findings and evidence limits

The former production App starts `inspect_system` and `inspect_recovery_state` in independent mount effects. The recovery observation takes `operations.gate`; the Linux read-only validator also needs it. A new production-App test fails on the original source because validation is submitted before its delayed safety observation returns. The same test passes after ordering those calls.

This confirms the code-level overlap. It does not prove that self-contention caused the owner's specific Mint startup report. Initial owner-device logs and safe packaged-launch evidence are still needed. No faults were induced on an owner's computer.

## Reader classification

| Caller | Native gate use | Treatment |
| --- | --- | --- |
| `inspect` / `inspect_system` | Read-only validation takes the operation gate | Queue; startup passes its current sequence identity |
| `operate(validate)` | Read-only operation runs through the normal validator/gate | Queue inside the explicit check's owning sequence |
| `inspectRecovery` | Recovery state calls native observations and public recovery state | Queue; startup/explicit-check phase passes the owning identity |
| `inspectSelfUpdate` | `observation::inspect` calls coordination status | Queue |
| `supportContext` | Collects native observations and public recovery state | Queue |
| `inspectOperationIncident` | Journal inspection calls native operation status | Queue |
| Machine incident history | History list acquires `operations.gate` | Queue |
| Saved report details | Machine acknowledgment observation acquires the gate | Queue; source is known only after loading the report |
| Schedule inspection | Separate task/systemd query | Keep independent |
| Application/tool update discovery | No shared operation gate on this path; may use network | Keep independent; no network wait holds this queue |
| User-only history / report listing / export | Bounded per-user storage or export dialog; no machine operation gate on these read paths | Keep independent |
| Install/update preflight | Explicit operation review; may include gate-taking safety and network checks | Not background startup collection. Startup busy state prevents review submission. Existing fresh native checks remain required. No blanket queue around network preflight |
| Acknowledgment, report creation, setting policy, file/history deletion and package operations | Explicit state-changing requests; some collect their own observations | Not silently queued or replayed as reads. Existing busy/review/consent and native protections remain unchanged |

Do not use the queue to change the scope or authority of a command. No Tauri command or permission was added. ReadSequence is never sent in an IPC payload.

## Loading, errors and lifecycle

- Startup stays Checking across both phases and while its own earlier reader finishes.
- A known active operation defers startup validation. Unavailable safety also defers it. Both settle the initial loading state without inventing a failed tool check, a successful report or a timestamp.
- Other uncertain/incident states retain their existing precedence. Any allowed read-only diagnosis still goes through the real backend and cannot authorize changes.
- Failed reads still reject to their caller. Failure does not poison the next queued request or start a retry.
- Repeated effects/clicks do not duplicate the startup/check request. StrictMode effect replay is covered.
- A sequence identity is usable only by its current owner. Expired identities are rejected; internal calls use the current identity rather than recursively queueing themselves.
- Unmounted or outdated startup work is ignored before unsubmitted validation. Already submitted native work is not killed or falsely canceled.
- A late startup result does not redirect navigation or steal focus.
- Genuine external work still holds the native gate. Same-window scheduling does not release or bypass it.

## Regression coverage

New production-App cases cover delayed safety and validation, continuous checking, one StrictMode sequence, known activity, unavailable safety, delayed completion during navigation, unmount before validation and visibly pending queue admission with duplicate clicks.

Queue and real bridge-adapter tests cover both phases, FIFO diagnostic reads, gate-free schedule/release discovery, explicit validation without recursive enqueue, unchanged mutation RPC fields, failed-read recovery and stale scheduling identity rejection.

The existing combined-browser fixture now collects its tool report while safety permits it, then requests a read-only check to introduce the blocker. This represents a real combined state after a prior check. It keeps every original assertion: retained Git diagnostics, no mutation, no false Ready, recovery routes, accessibility, all themes, widths and zoom levels. A cold launch with active work intentionally defers the validator and cannot invent those tool rows.

A coordination regression uses the real native gate to prove overlap returns Busy, ordered reads can acquire it, and another process's live lease still blocks observations/validation acquisition. The probe exits normally; no installer is killed and no transaction is created.

On non-root Unix, the existing Fixture guard returns before protected filesystem work. A local compile/test invocation is not proof that its privileged assertions ran. The existing required root/Linux and Windows CI jobs must execute this test with their normal enforcement. Native fixture/packaged UI evidence remains separate.

## Local validation checkpoint

- Frontend: 275 tests across 19 files passed; TypeScript, formatting and production build passed.
- Python backend contracts: 35 passed; CI scope policy: 26 passed; CI timing policy: 4 passed.
- Rust: formatting and coordination clippy passed. The new native regression compiled, but its protected assertions require the privileged CI jobs described above.
- System-Chromium browser suite: the original run passed 114 cases. Four combined-state cases needed a fixture update for the new startup order; all four passed their focused rerun, retaining every original assertion. CI remains authoritative for its configured Chromium/WebKit coverage and native operating systems.

## First CI result and probe correction

[Run 371](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/43568067928), for PR head `88b344e798e8e52eba3bb2d1a906aef10c70a302`, passed application/browser checks and both Windows and Linux/Mint native build/installed verification jobs. Both update-trust jobs failed the new regression at its final successful-exit assertion, so acceptance correctly failed and the PR remained blocked.

The shared probe helper dropped the child's stdout pipe after reading its ready signal. When the child exited normally, Rust's test harness wrote its result to that closed pipe and failed with BrokenPipe. Earlier tests killed their probes and did not assert normal exit, so this fixture defect had not surfaced there.

The helper now retains the pipe, and the new test drains it with `wait_with_output` after closing stdin. All gate, activity, decision, normal-exit and no-transaction assertions remain. A local unprivileged Rust harness experiment reproduced failure when dropping the pipe and passed when retaining/draining it. Formatting and coordination clippy passed; the protected regression still requires Windows/root-Linux CI. No application or workflow code changed in this correction. Preserve run 371's useful evidence, but require green results at the corrected head before merge.

## Scope and remaining release work

This is the first code increment, not completion of #160/#161 or release acceptance. Required Windows/Mint/native/trust checks, exact-main evidence and packaged ordinary-launch checks remain. No production locking semantics, release identity, workflow policy, signing or published assets changed.

Next: inspect exact-head CI and required native assertions, integrate only through normal protected merge, then continue the accepted #161 observation/discovery/preservation and connected UI work. Do not claim a packaged fix from unit/browser/native-component tests. Stop for human signing approval and exact-candidate owner UAT; stable promotion still needs separate authorization.
