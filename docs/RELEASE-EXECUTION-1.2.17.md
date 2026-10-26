# v1.2.17 execution ledger — October 25, 2026

## Completed stable release — October 25, 2026

**v1.2.17 is owner-accepted stable/latest**, release **423797225**, source
`7de6d29cfb0b8ba1677a20bc94a746ecfa4e838d`.
[Both-platform focused UAT](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/104#issuecomment-6407488626) and [promotion/public-link receipt](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/104#issuecomment-6407525155)
record the exact accepted release. The latter contains all five immutable asset
IDs, lengths and SHA-256 values. This documentation follow-up does not change the
released source, tag, signature or packages.

| Gate | Completed evidence / remaining scope |
| --- | --- |
| Reviewed correction | PR104 final head e651899; merged source7de6d29; missing generated/main-window permission fixed without changing the policy writer |
| Final PR verification | Full40252430909, pair40252430879 and native contract40252430883 all passed |
| Exact-main verification | Full40254829440 passed on released7de6d29; actual Windows SYSTEM and Mint root fixtures, IPC grant/denial, trust, 114 frontend and84 browser checks audited |
| Candidate / signing | Protected40256656651 passed; actual human reviewer rdpollard approved17 signing; Codex submitted no approval |
| Independent authentication | Five published assets, pinned signature and both payloads, input match, PE/DEB17 identity, copied-file tamper/wrong-tag rejection all passed |
| Owner desktop UAT | Windows11 and Mint22.3 x86_64: all focused17 rows Pass, including no-elevation off/on persistence across Refresh/reopening, identity, preservation, independent history and keyboard focus |
| Stable authorization | Owner explicitly approved v1.2.17 stable/latest; only existing release prerelease/latest metadata changed |
| Public verification | Exact17 latest API/page and both evergreen installer HTTP200 redirects; unchanged five assets/tag/source; stable_downloads.py passed |
| #102 | Closed as delivered in stable17; every app install/upgrade enables updates, and the student Inline preference saves without triggering maintenance |
| #59 | Closed under explicit historical affected-PC/native evidence limit; additional affected-PC/private-ACL inventories remain unreported and accepted |
| #99 | Open: actual retained14 Windows/Mint live discovery now possible; owner observations pending; no downgrade or installation implied |
| #43 / milestone2 | Open: exact-device/action/policy/window pilot authorization and real automatic-install/tool/preservation/recovery results, or explicit owner scope disposition, still required |

Retained actual14 device roles are distinct from the two accepted17 UAT roles.
No policy resume, task/service trigger, device install or fleet action was performed
by Codex. School-network/student-account and reboot/natural-weekly claims remain
limited to the evidence actually reported; immediate triggers are not natural
weekly firing. Earlier15 desktop and five-zoom evidence is reused within scope;
the16 failure and unreported Mint16 result are not relabeled as passes. #101 beta
behavior and #72/#73 remain outside scope. Windows10 support was not implemented.

Everything below is the historical engineering checkpoint before publication;
pending statements describe that checkpoint and are superseded only as above.

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
