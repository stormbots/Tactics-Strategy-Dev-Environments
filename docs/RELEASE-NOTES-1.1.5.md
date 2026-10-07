# Skyview Dev Setup 1.1.5

Windows validation now checks the exact maintenance task through Task Scheduler and reports missing, disabled, inaccessible and other query failures separately. Previously, validation suppressed task-query errors and showed a generic "Weekly maintenance enabled" failure even after Repair successfully registered the task.

Install and Repair now set explicit permissions on the Skyview-managed maintenance task: SYSTEM and administrators retain full control; normal users receive read access so the desktop app can validate it without elevation. Read access does not grant permission to run, edit, delete or change the task's security. Other scheduled tasks are unaffected. The weekly SYSTEM schedule is retained.

The Windows backend package is 1.1.5 so the task-permission helper and revised validator are installed and copied to the maintenance directory. The Linux baseline is unchanged. The startup spinner and automatic live details from 1.1.4 remain included.

Windows CI reproduces the access-denied failure with a temporary standard account and a harmless task, applies the permission fix, checks enabled/disabled/missing results, and verifies that the account cannot execute the SYSTEM task or change its permissions. Full system provisioning then verifies the real maintenance task from a standard-user process. Machine-changing tests run only on disposable GitHub runners.

Follow the Windows installer's update/reinstall flow, relaunch Skyview Dev Setup, and run **Repair** once to update the existing task's permissions. Then run **Validate**; all installed software can be reused. Updating the application alone does not change the task.

Manual acceptance was completed on fresh Windows and Linux machines on **2026-10-07**, with all checks reported as passing. This includes installation, validation, keyboard navigation, 200% scaling, Narrator/Orca, repair and data preservation, reboot, updates and maintenance. See the [acceptance record](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/main/docs/ACCEPTANCE-TEST.md) for the test procedure and evidence.

Stable promotion retains the existing **v1.1.5** tag at `ec58ad147a938f6f596632691b3b3ce46724425b` and the tested installer assets; no rebuild is required. Verify downloads against the attached `SHA256SUMS.txt`. Windows installers ship unsigned by project decision. Keep operating-system protections enabled.
