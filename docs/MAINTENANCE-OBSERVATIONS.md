# Maintenance observations and tool readiness

Part of [#161](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161).

A maintenance schedule answers when automatic updates can start. It does not tell us whether the development tools work now. Windows and Linux validation now report scheduling as **information**, outside the required-tool failure and warning counts. A missing, disabled or unreadable schedule remains visible. It cannot make a failed tool check pass or clear a safety finding.

| Observation | Meaning |
| --- | --- |
| Enabled | The task or timer is enabled. Read Schedule for its next run and earlier results. This is not proof of a running installer. |
| Disabled | Future automatic maintenance is disabled. SDE does not guess why. A disabled Linux timer can remain active in the current session; the message explains that possibility. |
| Enabled Linux timer is inactive | The timer is enabled but is not active. Review Schedule. |
| Missing | The fixed task or timer was not found. Review the schedule before choosing setup changes. |
| Unreadable | The schedule check did not finish. This is not proof that the task or timer is missing. |

Windows still queries the exact task through Task Scheduler, with standard-user read access only. Access-denied and missing-task errors remain distinct. Native CI verifies both cases, the disabled state and the existing restriction against running or changing the SYSTEM task. Reading the disabled task must leave it disabled.

Linux validation uses the existing read-only `schedule.py` inspector with the fixed timer and service names. Its new `--validation` output is an informational event. Its existing JSON output is unchanged. Helper failure produces an incomplete-schedule information message, rather than a tool failure or a successful schedule claim. The inspector never enables, starts, disables or edits a unit.

The Schedule page continues to show the actual schedule and earlier results separately from automatic SDE application updates. An earlier successful run is not a fresh tool check. An earlier failure does not override fresh successful tool checks by itself. Native activity, uncertain operations, package safety and retained interruptions keep their existing authority.

Older retained validation failures stay failures until a fresh check replaces them. Their review guidance requests a fresh schedule inspection; it does not infer that Repair is safe or necessary. New informational validation rows offer the same read-only Schedule review route.

This is an observation increment. Explicit leave-disabled persistence, supported full-scope restoration review, its automatic follow-up checks and the accepted connected Overview cards remain follow-up work. There is no new Enable endpoint, policy resumption, automatic retry, task invocation or permission to change packages. Existing Install/Repair effects are unchanged and still need their accepted preservation audit before the new restoration flow is offered.

Full Windows/Mint native, trust, integrity and acceptance checks remain required. Human signing approval, owner UAT of the exact authenticated candidate and separate stable-promotion authorization remain required.
