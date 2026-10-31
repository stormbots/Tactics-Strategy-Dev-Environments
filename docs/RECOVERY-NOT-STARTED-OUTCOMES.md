# Native proven-not-started outcomes

Branch: `codex/recovery-not-started-outcomes`.
Base: #131 at `175004d8a189e8d2dd2ec0a934da6f553ce5c784`, accepted in
[Build 41214719832](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41214719832).
Windows trust passed 100/100, root Linux 115/115; both native jobs, user-journal
lifecycle tests, actual Mint 22.3 and Windows SYSTEM signed upgrades and inherited
recovery gates passed. Stack stays draft/unmerged, not an owner UAT candidate.

## Bounded native outcome contract

- Run ordinary read-only preflight before creating/replacing the GUI journal.
  A local preflight denial leaves an earlier incident untouched and creates no
  new interruption or restart requirement. Acquire the account lock and validate
  preserved prior decisions/restart normally before any actual launch.
- Elevation failures are typed `NotStarted` or `Uncertain`, never deserialized
  from the frontend. Generic errors default to uncertain. Only the live native
  no-start branch may retire its own exact current GUI journal; prior preserved
  evidence/decisions and every protected machine transaction remain untouched.
  The generation checks still reject an externally replaced source.
- Return `mutation_outcome`: `not_requested` for read-only Validation,
  `not_started` for a native proven non-start, `completed` only after the existing
  known-success finish, otherwise `uncertain`. This describes the current request,
  not earlier incidents, and is not authority to delete arbitrary evidence or
  automatically replay work. Storage failures may still leave a retained journal
  even when this request never launched provisioning.

## Linux / polkit

The official pkexec contract returns the program's exit status on execution,
126 for a dismissed authentication dialog, and 127 for denied/unavailable
authentication or errors. Thus 126/127 alone cannot prove a cancellation: an
executed helper/backend can return those values too.

The installed helper now flushes a session-matching `SDE_HELPER_ENTERED` marker
before entering any backend/session work; inability to report entry stops the
helper before that work. The parent drains stdout and stderr, tracks read/UTF-8/
reader completion, and waits for the actual process. Normal 126/127 exit plus
reliable complete capture plus no helper entry establishes a non-start under this
fixed installed-helper contract. A wrong-session marker, missing reliable capture,
signal/wait failure, or entered helper stays uncertain. An arbitrary missing
marker on a different program is not this contract. An actual Rust spawn failure
is separately typed before a child exists; it is not inferred from error text.
Existing streaming exit status and redaction remain in place for other consumers.

## Windows / native RunAs

Replace the PowerShell launcher whose broad catch reported every error as 1223
with direct `ShellExecuteExW` RunAs on a dedicated STA thread. Use a fixed executable
and validated operation/session arguments, `SEE_MASK_NOCLOSEPROCESS` and
`SEE_MASK_NOASYNC`. Own the returned process handle and close it normally; do not
terminate a process or impose an installation timeout. A native FALSE result with
`ERROR_CANCELLED` and no process handle is a non-start. A returned process whose
exit code is 1223 is not cancellation evidence. Unknown launch failures or missing
handles stay uncertain. A contradictory error with a handle is uncertain and the
handle is closed without killing the process.

Reject an existing/unreadable protected session log before launch. After a real
helper is launched, continue tailing its protected log, wait for the tracked
process, drain final data, and require the process exit to match the helper's
completion record. No final record, mismatch, or failed wait is uncertain; a stale
or partial log cannot establish successful helper completion. Backend scripts,
system-only environment, native mutation coordination and trust checks remain.
There is still one ordinary OS authorization prompt; no acknowledgment elevation.

The implementation follows current official references, retrieved during this
increment with the documentation skill:

- [pkexec reference / return values](https://polkit.pages.freedesktop.org/polkit/pkexec.1.html)
- [ShellExecuteExW / return and cancellation semantics](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shellexecuteexw)
- [SHELLEXECUTEINFOW / handle and synchronous launch flags](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/ns-shellapi-shellexecuteinfow)

## Verification and limits

Four portable launch-policy tests and the new no-start journal regression passed
locally. The latter retires only this attempt, permits explicit same-session retry,
preserves an evidence stand-in and refuses deletion after generation replacement.
Existing user-journal tests passed. Linux and Windows-GNU coordinator clippy,
28 backend contracts, four command/module wiring tests, locked offline Tauri
metadata, frontend production build, formatting and diff checks passed.

Native Tauri adds a real child-capture fixture covering cancellation, entered
helper with the same exit status, wrong-session marker and incomplete/non-UTF-8
capture, plus a typed spawn-failure test. Windows also tests a real tracked child
exiting 1223 without treating it as a native launch failure. The Windows API source
and policy compile in the coordinator's native trust path as well as Tauri; local
GNU cross-compilation is not Windows runtime evidence. These native tests and all
inherited coordination/trust/Windows/Mint 22.3 signed-upgrade gates require CI.
No actual polkit or UAC cancellation UI has been exercised locally or claimed;
ordinary owner cancellation/retry remains focused UAT. No signing approval here.

Only explicit native proof is covered. Privilege-side preflight refusal, an
entered helper failing before package execution, a genuine backend returning a
cancellation-shaped exit, and interrupted capture remain conservative. Do not
turn those exit codes into clearance without a separately reviewed reliable
control contract. Existing protected machine journals are never cleared by this
user-attempt cleanup. The same installed-helper/source contract and normal session
leases are required; arbitrary mixed/foreign binaries are not a cancellation API.

## Durable continuation

On completed CI, verify exact source/results once, fix actual failures without
waivers, then continue final T7/T8 Recovery safety-observation, acknowledgment and
explicit resume/history interaction. Use native outcome metadata to distinguish
current non-start from earlier evidence, never to delete an older incident.
Do not auto-retry after cancellation or app restart. Keep original decisions and
ordinary preflight/confirmation/OS approval; retain uncertain execution evidence.
Finish retained-history navigation, safe export/view/delete and user/machine
identity handling before consolidated review/UAT. Native cancellation accessibility
and real reboot behavior remain external validation/owner UAT items.

No partial-stack merge, release, publication, fleet rollout, milestone closure or
scheduler. PR checkpoint records exact SHA, initial Build URL and pending tests.
Owner Windows interruption evidence and Mint v1.2.18 Install/Validate 35/0/0 intact.
