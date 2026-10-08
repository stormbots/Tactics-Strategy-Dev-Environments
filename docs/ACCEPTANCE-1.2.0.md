# Mentor acceptance — 1.2 UI features

All features below are **Accepted for version 1.2.1 on both platforms**, based on the project owner's explicit release sign-off on **2026-10-08**. See the [1.2.1 acceptance record](ACCEPTANCE-1.2.1.md) for evidence and the accepted PowerShell reporting limitation. This records acceptance of the features introduced in 1.2.0 as shipped in 1.2.1; the earlier 1.2.0 candidate remains historical.

| Feature check | Windows | Linux Mint |
|---|---|---|
| Launch normally; all required checks pass independently of updates | Accepted | Accepted |
| Ready tools display installed versions; updates display current → target | Accepted | Accepted |
| No updates, available updates, skipped check, and offline/unavailable check are clear | Accepted | Accepted |
| Node candidates remain 24.x; Python candidates remain 3.14.x | Accepted | Accepted |
| Schedule agrees with system task/timer; Refresh does not trigger a run or elevation | Accepted | Accepted |
| Local next/last timestamps, never-run, success, failure, and unavailable history are accurate | Accepted | Accepted |
| Disabled/missing task and permissions failure show actionable information | Accepted | Accepted |
| Maintenance log folder opens separately from GUI operation logs | Accepted | Accepted |
| About version/platform are correct; both external links open in the system browser | Accepted | Accepted |
| Tab/Shift+Tab/Enter, visible focus, 200% scaling, narrow layout, reduced motion | Accepted | Accepted |
| Narrator/Orca headings, new-page focus, loading, refresh, and status announcements | Accepted | Accepted |

Record OS version, release commit, downloaded checksums, and results. A mentor can use a disposable snapshot to exercise failed/disabled maintenance; the Schedule page itself provides no run or edit control. On Linux, systemd can discard service results across restart: a known previous trigger with no result must show **Unavailable**, rather than **Succeeded** or **Never run**.
