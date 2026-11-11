# Guided Overview v1.2.23 — owner UAT

Status: **Not run; candidate not yet authenticated or supplied.** Begin only after
Codex fills the candidate record below and supplies verified installation steps.
Do not install unsigned PR/Actions artifacts or the unpublished rebuilt baseline.
This sheet does not approve signing, accept UAT or authorize stable promotion.

## Candidate record — Codex fills before owner testing

| Item | Record |
| --- | --- |
| Candidate | **1.2.23**; tag v1.2.23, pending publication after human signing approval |
| Automated/native implementation source | `8e3c4463a475ed9fc7f89c88669fb12c129cf618`; [final-main Build 42959957444](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/42959957444) passed |
| Candidate preparation PR and exact source/tag SHA | Pending; must include preparation changes and successful exact-main CI |
| Candidate pair Windows SYSTEM / actual Mint evidence | Pending new 1.2.22 → 1.2.23 same-source rebuilt pair; not historical released-binary coverage |
| Human signing approval / protected run | Pending; `sde-release-signing` currently requires reviewer `rdpollard`; Codex must not approve through tools |
| Prerelease URL / exact tag source | Pending |
| Five immutable asset IDs, sizes, SHA-256 digests | Pending; see table below |
| Independent pinned-key metadata signature and both payload checks | Pending; download and verify published assets before installation instructions |
| Owner devices/accounts and installed candidate version | Not run; supported Windows 11 x64 and Linux Mint 22.x amd64 |

| Asset | Release asset ID | Bytes | SHA-256 |
| --- | --- | --- | --- |
| Skyview-Dev-Setup-Windows-x64.exe | Pending | Pending | Pending |
| Skyview-Dev-Setup-LinuxMint-amd64.deb | Pending | Pending | Pending |
| SHA256SUMS.txt | Pending | Pending | Pending |
| sde-update.json | Pending | Pending | Pending |
| sde-update.json.minisig | Pending | Pending | Pending |

A replacement asset/source is a new candidate with affected verification and
scoped owner retesting. Keep the accepted assets unchanged throughout UAT.

## Safe setup

Codex will provide the exact authenticated app installer for each platform.
Record existing projects/editor choices and the current Schedule/About/update
state before installing. This is an app candidate; do not run tool Install/Repair,
downgrade tools, clear journals, remove locks, kill package processes or introduce
an interruption just for coverage. If automation/updates are deliberately paused,
report that before installation: UAT grants no policy-resumption authorization.
Normal installer policy semantics have not changed in this candidate.

Preserve the original Windows interruption evidence and Mint v1.2.18 **35/0/0**
record. Neither historical result accepts this candidate. Stop and report any
unexpected mutation, repeated elevation, inaccessible controls or lost data;
Codex handles diagnosis and fixture reproduction.

## Ordinary owner walkthrough

Run the naturally available paths on Windows and Mint. Mark a state you did not
encounter **Not observed**; do not manufacture it. Difficult failure/permission/
interruption cases belong to the automated/native ledger, not owner fault injection.

1. After the verified app install/upgrade, confirm About shows **1.2.23**. Open
   Overview: startup checks should be read-only, with one understandable next step.
   A healthy setup should become Ready; genuine current blockers should remain
   explained, with no automatic install, repair, acknowledgment or OS prompt.
2. If Ready, open VSCodium and your usual workspace using the primary/Other
   actions routes. Confirm normal destinations and existing projects/settings.
   Do not run setup merely because the interface offers a review path.
3. If tool updates are naturally available, expect **Ready!**, **Install updates**,
   the exact sentence “Your setup works, but there are updates available if you
   would like to install them.” and one **Review updates** primary. Review then
   Back/Cancel: no update or privilege prompt should start. Editor access remains
   under Other actions; tool and app updates should be clearly distinct.
4. Review a naturally relevant setup/repair action, or an explicit Other actions
   review if useful, then Back/Cancel. The real full scope should be understandable;
   cancel must return usefully and start nothing. No tool mutation is required.
5. Visit Validation, Recovery, Schedule and About, then return. Open Details and
   inspect available findings/log/report routes. No navigation should start a
   change or discard evidence. When Recovery has nothing to handle, retain the
   accepted neutral “There is nothing to recover from right now” card with its
   single Create support report button. Otherwise retain the real safety guidance.
6. Optionally open a support preview and cancel. Sharing/export remains optional;
   no private logs should be included or uploaded without your choice. Do not
   delete history/evidence to pass this step. Retained warnings must stay visible.
7. While idle, close and reopen the app. It should query fresh findings and forget
   an unstarted review, with no replay or success derived from old UI state. If
   work is naturally running, follow the existing close guard; navigate normally
   and return to the supported progress/status cue without another operation.
8. Check your usual light/dark theme, zoom and keyboard navigation. Try review
   Cancel and modal Escape, readable status/actions, useful focus and no horizontal
   scrolling. Check assistive-technology announcements if you normally use them.
   No real OS reboot, synthetic failure or device reprovisioning is requested.

## Owner result record

For each platform record device/account context, installed version, exact candidate
source/assets, step, expected versus observed result, and **Pass / Fail / Blocked /
Not observed**. All steps currently remain **Not run**. A screenshot or sanitized
finding is enough; do not send private journal bytes, credentials or personal logs.

| Platform | Candidate identity confirmed | Steps / results / evidence | Defects or retest | Owner decision |
| --- | --- | --- | --- | --- |
| Windows 11 | Not run | Not run | Not run | Pending |
| Linux Mint | Not run | Not run | Not run | Pending |

Codex records your explicit decision against this exact candidate. Prototype
approval, a green CI job or prior v1.2.22 acceptance cannot supply that decision.
Stable/latest promotion and any fleet or automation/policy action require separate
authorization even after owner acceptance.
