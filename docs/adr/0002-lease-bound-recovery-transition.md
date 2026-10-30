# ADR 0002: Fresh safety and a lease-bound recovery transition

Status: foundation accepted at `c0a3ecd` in Build `40821734101` (Windows 44/44,
root-required Linux 47/47). Native sources were readable/stable; this is not an
actual reboot test. Existing execution consumers are not connected. The next
[bootstrap increment](../RECOVERY-BOOTSTRAP-INTEGRATION.md) connects only incident
preparation during normally authorized installation. Depends on accepted
[ADR 0001](0001-interruption-acknowledgment-boundary.md).

Current integration note: the [application-updater increment](../RECOVERY-APPLICATION-UPDATER.md)
adds a non-authoritative preparation lease for eligibility/signature/staging work.
It can hold ordinary locks while old evidence remains, but cannot grant mutation
permission or consume acknowledgment. Its begin operation transfers the same
handles into this ADR's existing transition; no locks are released between
authentication and fresh native/incident checks. Interrupted staging preserves
old inputs and recovery receipts. The historical foundation scope below remains
unchanged; native integration validation is a separate gate.

## Decision

An unlocked SDE operation gate cannot establish that a previous installer or its
detached child terminated. A retained unknown journal therefore remains activity
unknown until independent restart provenance establishes that its earlier process
lifetime ended. Current native package activity is checked separately: a restart
does not certify package health, imply acknowledgment, or release a journal.

Capture protected provenance once per incident during normally privileged
preparation. Linux uses the kernel boot UUID. Windows requires both a changed
primary SMSS PID/creation identity and a changed Kernel-General OS-start event
12 record/time. Missing or only partially changed evidence stays unknown. Do not
use elapsed time, PID absence/reuse, an unlocked gate, or a BCD loader identifier
as restart proof. A legacy incident first encountered after a restart may need
one further normal Restart after provenance is captured; explain this limitation
in the later UI. If provenance cannot be read, no override is inferred.

The Windows sources are documented but their availability under supported native
privilege contexts must be demonstrated by CI. Simulated comparisons do not
prove a real reboot. Relevant Microsoft documentation:

- [Win32_Process CreationDate and PID reuse](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-process)
- [OS-start event 12](https://learn.microsoft.com/en-us/troubleshoot/windows-server/performance/troubleshoot-unexpected-reboots-system-event-logs)
- [Primary SMSS during boot](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/windows-boot-issues-troubleshooting)

Fresh native inspection is read-only and bounded. Windows uses fixed in-box
PowerShell/CIM/event/registry queries with in-box module paths, never caller
commands or raw command-line output. Known package processes block; an Installer
InProgress marker is incomplete; its absence is only unknown health, not healthy.
Linux inspects native dpkg/apt lock identities and `/proc/locks`, plus a fixed
read-only `dpkg --audit`. Failed diagnostics are unknown, not package damage.
Unknown health alone warns/allows once inactivity is established. Package-native
locking and all other execution eligibility checks remain required.

Only `mutation::begin` can mint a non-serializable retirement permit, borrowing
its operation lease. It owns the necessary session lease, revalidates protected
incident binding and durable acknowledgment, and rechecks safety after persistence.
It moves the original journal object without replacement into the protected
archive and creates a distinct new private transaction. A public observation or
student-writable intent is never an execution permit. Original bytes, receipt,
and the retired journal remain retained; a destination collision blocks.

The guard supervises one trusted command, checks current native activity again,
and passes existing nesting coordination to the child. Unix clears CLOEXEC only
in the spawned child, preserving parent flags; Windows passes the private nesting
token without logging it. The caller still must perform its normal identity,
signature, policy, and privilege checks. Child exit, passing Validation, or guard
drop never clears intent. Only an explicit known-outcome finish clears that
guard's own matching new journal. No installer process is timed out or killed.

## Consequences and boundaries

Restart is conservative, not a general repair instruction. External package work
can race a snapshot, so package-native safeguards remain mandatory. Earlier
non-package children cannot be dismissed on package-process absence alone.
Public diagnostics contain only source categories and numeric error codes;
restart keys are local operational metadata, not report content or authority.

Existing `operation`/`installation`, scripts, GUI, updater and scheduling flows
remain unchanged in this increment. Future platform integration must verify
nesting, completion and bootstrap behavior before connecting the new primitive.
No report/history UI, automatic restart, production bypass or owner-state mutation
is introduced here. Native CI is a gate before the next integration task.
