# v1.2.17 execution ledger — October 25, 2026

The owner reported a genuine v1.2.16 Windows 11 UAT failure: switching Automatic
SDE updates off reports an unavailable setting; Refresh/reopen shows Enabled.
App and protected active engine are 1.2.16. Separate baseline/default identity,
history separation, keyboard/appearance/navigation and preservation rows passed.
[Owner finding](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/103#issuecomment-6392065693).
Mint v1.2.16 UAT is unreported. Both actual Windows 11 and Mint UAT laptops passed
v1.2.15; private device attribution and exact-version confirmation are recorded
[here](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/103#issuecomment-6391809036).
The planned Windows 10 PC was not the completed Windows 11 UAT machine.

## Defect and narrow correction

The frontend invokes `set_self_update_paused`, registered in the native handler,
but v1.2.16 omitted it from build.rs's generated app command permissions and
the main-window capability. The save is therefore not granted to the webview;
the error path marks policy unconfirmed and Refresh reads the unchanged value.
Add only this fixed boolean command to both declarations. No filesystem/shell
plugin grant, remote origin, arbitrary path or privilege expansion is added.
The existing policy writer, strict decoding, file/parent protections, worker
eligibility and installer reset semantics remain unchanged.

The new frontend/handler/generated-permission/capability regression fails on the
old declarations for the missing command and passes after correction. Native
Tauri IPC tests use the production handler and actual generated context: the
main window reaches strict boolean decoding; an untrusted window is denied.
Invalid/missing arguments stop before policy access, so these tests do not alter
owner machines. Existing native standard-student setter/readback/protected-write
denial fixtures separately test persistence and permissions. Existing browser
tests cover saving/error/focus/history, not native IPC authorization.

## Candidate and immutable evidence

v1.2.17 tag/release was unused before engineering. The protected recipe builds
unpublished same-source 1.2.16/1.2.17 installer fixtures and publishes only17.
The rebuilt16 fixture is not the accepted published16 bytes. App source and
managed-tool baseline remain1.2.1; dependencies and release key stay unchanged.
v1.2.15 and v1.2.16 releases/tags/assets remain immutable. v1.2.16's
[authentication](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/103#issuecomment-6391607168)
remains valid, but it is not accepted for stable. Stable/latest remainsv1.2.14.

Required: reviewable PR; full/native and Chromium/WebKit checks; merged exact-main
CI; audited native pair/input artifacts; new exact-input human signing approval;
independent five-asset authentication; focused17 Windows/Mint UAT; separate exact
stable authorization and immutable promotion/public-link verification. Approval
of16 signing does not authorize17 signing or stable promotion.

After promotion, retained actual14 Windows/Mint installations exercise live#99.
Their allocation is unchanged; no downgrade, install, Repair, maintenance trigger
or policy resume is inferred. #43/milestone2 remain open for a separately scoped
device/action/policy/window pilot or explicit owner disposition. #59 is closed
under its accepted historical affected-PC/native evidence limit; this UI finding
does not reopen that unrelated migration. #101 beta behavior and #72/#73 remain
outside scope. Windows10 support was investigated, not selected for this fix.
