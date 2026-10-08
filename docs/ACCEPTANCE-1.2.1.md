# Mentor acceptance — 1.2.1

On **2026-10-08**, the project owner instructed: **"Mark all as accepted, merge, and publish to stable."** All applicable release checklist items, the full [acceptance procedure](ACCEPTANCE-TEST.md), and the [1.2 UI feature checklist](ACCEPTANCE-1.2.0.md) are **Accepted** on Windows 11 x64 and Linux Mint Cinnamon 22.x amd64 on that basis.

**Accepted** records the owner's decision. The agent did not independently repeat every manual test.

| Check | Windows | Linux Mint |
|---|---|---|
| Install and Repair complete; all required validation checks pass | Accepted | Accepted |
| Large APT listing does not stop Node.js 24.x selection with exit 141 | Not applicable | Accepted |
| Scheduled maintenance completes using the corrected selector | Not applicable | Accepted |
| Node remains 24.x and Python remains 3.14.x | Accepted | Accepted |
| Tool versions/update counts, Schedule, Refresh, log folder, and About | Accepted | Accepted |
| Keyboard navigation, 200% scaling, Narrator/Orca, reduced motion | Accepted | Accepted |

## Supporting evidence

- Release source/tag: `v1.2.1`, commit `40c2177c5916002db2e8da45143784b1ac6ad114`.
- [Candidate CI](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/37821916493) and [PR CI](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/37821921095) passed. Coverage includes 27 frontend tests, 16 Windows and 11 Linux Rust tests, 3 runtime selector regressions, 8 Linux metadata fixtures, 6 backend contracts, integrity/static analysis, and 4 browser accessibility checks. Machine-changing Windows tests ran on disposable GitHub runners.
- Supplied Mint 22.3 Cinnamon logs: `install-31204d7c-09d5-49c6-90cf-90ec795e1483.log` and subsequent `validate-7986dd00-5823-4289-af9c-a0a9217a2fab.log` each report **35 PASS, 0 WARN, 0 FAIL**. Node is 24.21.0, Python is 3.14.8, and maintenance is enabled/active.
- Supplied Windows candidate logs reported **31 passed, 0 failed**. Final Windows/Mint release acceptance comes from the owner's instruction above.
- Windows installer SHA-256: `7ac0c568c3fca4c9a941b5261f7ebd16f31b0e9247de9cd19fada25d87b8e71d`.
- Linux Mint installer SHA-256: `516e26b3bd4a24210bfcd4b3fc5300fad62c98caec5375c01f689ab2e377cfbe`.
- Downloaded assets matched the published manifest and GitHub digests. The DEB's corrected installation/updater scripts matched committed source byte for byte. Promotion preserves the existing tag and assets.

## Accepted limitation

The Windows tool list can show identical PowerShell installed/available versions when Chocolatey's installed package record lags behind the executable. The owner accepted the current release with this known reporting limitation; this sign-off does not claim the display defect was corrected. Windows code signing remains excluded from requirements by project decision.

Prior 1.1.5 manual sign-off remains historical evidence for that version. Version **1.2.1** is the accepted stable release.
