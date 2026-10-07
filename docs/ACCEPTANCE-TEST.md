# Mentor laptop acceptance test — 1.1.5

Use one expendable/test Windows 11 x64 laptop and one Linux Mint Cinnamon 22.x amd64 laptop. Back up student projects first. Record laptop model, OS version, release commit, checksums and results. Do not test provisioning on a mentor's primary workstation.

## Recorded accessibility results

Windows results reported by the user on **2026-10-07** for **v1.1.5** (release commit `ec58ad147a938f6f596632691b3b3ce46724425b`):

| Check | Windows result | Evidence |
|---|---|---|
| Keyboard navigation | **PASS** | User-reported manual test |
| 200% scaling | **PASS** | User-reported manual test |
| Narrator | **PASS** | User-reported manual test |

These results record the reported accessibility portions of step 2. Its other conditions and the remaining acceptance steps still require separate sign-off. Linux Mint keyboard navigation, scaling and Orca testing remain pending.

## Acceptance procedure

1. Download the EXE/DEB and verify against `SHA256SUMS.txt`. Open the downloaded package graphically. Windows publisher/SmartScreen behavior must be evaluated because the initial build is unsigned; do not disable UAC or other security protections. Mint should use Software Installer, then show a working application menu entry and logo.
2. Launch as a normal student user. Confirm the detected OS and real tool statuses. Use Tab/Shift+Tab/Enter to reach every operation and Show details/Advanced. Confirm visible focus, readable text at 200% scaling, and no content loss at narrow window sizes. Check headings, buttons, validation table, progress and result announcements with Narrator or Orca.
3. Click Install. Approve UAC/PolicyKit graphically. On Windows also test a standard user supplying a separate administrator's credentials. Verify no terminal window or terminal input is required and the GUI stays unelevated. Keep the window open until final validation. Logs and progress should continue during long package phases.
4. Confirm required tools, Node 24.x, Python 3.14.x, standard extensions and weekly maintenance pass. Git identity and GitHub authentication may be INFORMATION. Open VSCodium and Development using the success actions. Confirm the correct student's editor, Git defaults, settings and workspace ownership/access; no profile changes should land in the credentialed administrator/root account.
5. Add a sentinel file in an existing project and a custom editor setting. Run Install a second time, then Repair. Confirm sentinel files, repositories, custom settings and local identity/authentication are retained. Optional CSV repositories must be cloned only when their destination is absent.
6. Run Validate. No administrative prompt or software installation should occur. Confirm a zero-failure summary only when all required checks pass. Temporarily disable the maintenance task/timer: Validate must fail graphically; Repair must restore it.
7. Run Update. Verify only managed packages change, Node remains 24.x and Python 3.14.x, no Linux distribution upgrade or Snap enablement occurs, and `/usr/bin/python3` retains its original target/version. Optional update detection should use managed packages only.
8. Reboot and relaunch. Confirm Ready status, application launchers, and weekly maintenance remain configured. Windows task must run as SYSTEM, weekly Sunday at 03:00 with catch-up enabled. Mint timer must be enabled/active with its existing persistent catch-up behavior. Have a mentor trigger maintenance once and review its log/exit status.
9. On a fresh test snapshot, deny the privilege prompt. Confirm actionable failure and Retry, then grant approval and finish. If practical, disconnect networking during a package download; setup must stop on critical failure, retain earlier installed tools/projects, expose the package error, and recover on Retry. Do not interrupt a package transaction by powering off.
10. Verify normal close is prevented during active setup, succeeds after completion, and no hidden helper continues after a reported result. Inspect GUI and native logs for unexpected credentials before sharing. Test an intentionally malformed/unapproved privileged operation in a mentor development harness: it must be rejected.

Sign off both laptops before promoting the prerelease to general fleet deployment. CI proves builds and automated contracts, not real UAC/PolicyKit, package sources, desktop integration, signing behavior, or heterogeneous laptop compatibility.
