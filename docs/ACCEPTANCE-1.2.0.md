# Mentor acceptance — 1.2.0 candidate

Manual results are **pending on Windows 11 x64 and Linux Mint Cinnamon 22.x amd64**. Use test machines and retain the full [acceptance procedure](ACCEPTANCE-TEST.md); its recorded 1.1.5 results do not sign off this candidate.

| Feature check | Windows | Linux Mint |
|---|---|---|
| Launch normally; all required checks pass independently of updates | Pending | Pending |
| Ready tools display installed versions; updates display current → target | Pending | Pending |
| No updates, available updates, skipped check, and offline/unavailable check are clear | Pending | Pending |
| Node candidates remain 24.x; Python candidates remain 3.14.x | Pending | Pending |
| Schedule agrees with system task/timer; Refresh does not trigger a run or elevation | Pending | Pending |
| Local next/last timestamps, never-run, success, failure, and unavailable history are accurate | Pending | Pending |
| Disabled/missing task and permissions failure show actionable information | Pending | Pending |
| Maintenance log folder opens separately from GUI operation logs | Pending | Pending |
| About version/platform are correct; both external links open in the system browser | Pending | Pending |
| Tab/Shift+Tab/Enter, visible focus, 200% scaling, narrow layout, reduced motion | Pending | Pending |
| Narrator/Orca headings, new-page focus, loading, refresh, and status announcements | Pending | Pending |

Record OS version, release commit, downloaded checksums, and results. A mentor can use a disposable snapshot to exercise failed/disabled maintenance; the Schedule page itself provides no run or edit control. On Linux, systemd can discard service results across restart: a known previous trigger with no result must show **Unavailable**, rather than **Succeeded** or **Never run**.
