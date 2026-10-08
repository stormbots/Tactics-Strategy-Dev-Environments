# Mentor acceptance — 1.2.1 candidate

Manual results remain pending. The supplied Linux Mint 22.3 logs for 1.2.0 showed Install/Repair stopping with exit 141 and validation reporting 17 passed, 14 failed. The 1.2.1 candidate corrects the shared Node.js selector; these logs do not sign off the corrected version.

Use the full [acceptance procedure](ACCEPTANCE-TEST.md) and repeat the [1.2 UI feature checks](ACCEPTANCE-1.2.0.md) on this candidate. Record the release commit, OS version, installer checksum, and results.

| Check | Windows | Linux Mint |
|---|---|---|
| Install and Repair complete; all required validation checks pass | Pending | Pending |
| Large APT listing does not stop Node.js 24.x selection with exit 141 | Not applicable | Pending |
| Scheduled maintenance completes using the corrected selector | Not applicable | Pending |
| Node remains 24.x and Python remains 3.14.x | Pending | Pending |
| Tool versions/update counts, Schedule, Refresh, log folder, and About | Pending | Pending |
| Keyboard navigation, 200% scaling, Narrator/Orca, reduced motion | Pending | Pending |

The automated selector regression uses synthetic data and does not install packages. A mentor must confirm full provisioning and maintenance on a disposable Mint machine. Prior 1.1.5 manual sign-off remains historical evidence for that version; 1.1.5 remains stable.
