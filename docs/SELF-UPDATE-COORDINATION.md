# Shared SDE coordination (#38)

SDE now uses two administrator-created, read-only gate files shared by the GUI,
privileged helpers, tool maintenance, supported manual scripts, and future native
self-installers. `sde-coordination` is a small native library used by the GUI and
updater. Linux script supervision uses the same files with `flock`; Windows uses
read-only file handles and Windows sharing restrictions. No lock grants elevation,
selects a script, or contains commands. The privileged helper still accepts only
its existing enumerated operations, validates installed resources, and clears the
caller environment.

## Lifetime and ordering

* The GUI acquires a shared `sessions.gate` lease **before creating a webview** and
  retains it until exit. Multiple GUI windows can coexist. A helper also holds a
  session lease, so GUI exit does not leave a running backend invisible.
* Backend wrappers acquire a shared session lease and an exclusive
  `operations.gate` lease before setup, repair, validation, profile setup, tool
  maintenance, or snapshot generation. Acquisitions never wait. Process-local
  `Busy` still prevents overlapping requests within one window.
* Future #39/#40 installers must retain `sde_coordination::installation()` for the
  entire verification/replacement transaction. It first acquires the operation
  gate, rejects an interrupted record, then takes the session gate exclusively.
  Failure drops the first gate. Before launching a native installer, call
  `Installation::begin_transaction()` and retain its durable transaction guard;
  call `Transaction::complete()` only after all package children end with a known
  outcome. Dropping it retains the interrupted record, including on reboot. New GUI sessions cannot slip in after the
  inactivity decision because the successful installer retains both handles.
* GUI operations do not acquire the operation gate before elevating a helper.
  The backend wrapper owns it. Linux children inherit validated descriptors;
  environment booleans do not bypass acquisition. Windows scripts within the same
  PowerShell process retain the actual FileStream; elevated Chocolatey children
  reuse a random transaction token matched against the private administrator-owned
  record and require the supervising exclusive handle to remain held.
* Wrappers await their supported script/child chains. They never kill package
  children, forcibly close a GUI, delete APT/DPKG locks, or force package databases.
  Linux inherited leases remain held by children if their wrapper dies. Because
  package tools may close inherited handles and Windows child processes do not
  necessarily inherit them, the protected system journal also blocks replacement
  after a supervising process crashes. Mere absence of a process is not proof
  that its package children completed.

The operation gate covers maintenance reads of the applied baseline as well as
its package work. Release it before attempting self-installation as a separate
transaction. Download/staging remains separate from installation; #37 does not
replace application files. This PR introduces no scheduling of self-installation.

## Storage, bootstrap, and compatibility

Windows: `C:\ProgramData\SkyviewRoboticsCoordination`; Linux:
`/var/lib/skyview-robotics-coordination`. Paths are fixed and cannot be overridden
by an environment variable or UI input. Native validation rejects untrusted
owners/writers, links/reparse points, nonempty/nonregular gates, and hard links.
Linux gate files are root-owned `0444` in a `0755` directory. Windows allows
Administrators/SYSTEM ownership and modification, with Users receiving read-only
access. System ancestors are validated before native acquisition. Students can
hold leases and defer maintenance, but cannot replace gates or author a privileged
transaction record. Explicit Windows baseline Repair also protects deployed
maintenance scripts and their policy directory with administrator ownership and
read-only student access.

Application package post-install hooks run the narrow
`skyview-dev-setup --coordination-init` entry point to create this storage. They do
not provision tools, apply a new development baseline, schedule self-installation,
reset interrupted state, or replace an existing gate inode. Existing machines need
one explicit application upgrade before using this coordination contract. Missing
or unsafe storage fails closed with an installation/repair message; there is no
unguarded fallback for an old script. Supported manual scripts now require this
application bootstrap. Older deployed maintenance does not acquire these gates:
the installation API fails closed with `needs_repair` until a mentor explicitly
migrates that baseline's maintenance entry point with Repair. Disable the old
schedule and wait for its package work to finish before this one-time migration;
never kill an existing transaction. Application installation does not silently
apply this baseline migration. The Linux manual installer elevates its system phase
separately and keeps profile configuration unelevated.

## Deferral, interrupted state, and recovery

Contention emits `SKYVIEW_EVENT|warning|deferred|…` and returns exit **75** from
maintenance scripts. The existing Windows Task Scheduler/Linux systemd schedule
tries again at its next invocation. Schedule readers and the Maintenance page
recognize `deferred` independently of success/failure. No new scheduler or busy
polling is introduced.

A root/administrator-owned private `transaction.json` is flushed before any system
mutation. Its presence blocks new operations and installation once the kernel
operation gate is free. Normal Linux child completion (including a reported
failure) clears the record after waiting; a signal or supervisor crash retains
it. Windows clears it only after a normally completed script; an exception,
cancellation, crash, or reboot retains it conservatively. Initialization never
clears this record. A stale or malformed record is also a reason to stop, never an
instruction to execute or blindly resume work.

`sde-update-trust coordination-status` / `sde-coordination status` return `idle`, `busy`,
`interrupted`, `needs_repair`, `unavailable`, or `untrusted`. Status is diagnostic only; installers
must acquire and retain the real installation lease. `idle` is not an installation
permission. The native status probe never clears state.

Mentor recovery controls belong to #41; interrupted-operation UI belongs to #8
and status presentation integrates with #10. Until then, mentor recovery requires
reviewing logs and confirming that **all package children and native package
transactions have completed**, fixing the underlying failure using normal package
manager procedures, and clearing only SDE's transaction record while holding its
operation gate. Do not remove either gate file, any package-manager lock, or an
unknown active transaction. If completion cannot be established, defer and seek
mentor intervention. There is no automatic retry of an unknown interrupted
mutation and no universal rollback promise.

## Verification and remaining UAT

CI runs real Windows/Linux cross-process session/operation/exclusive installation
contention, failed second-gate cleanup, abrupt process exit, protected storage and
stale-record tests. Required Linux tests run as root, never as silently skipped
unprivileged checks. Synthetic Linux supervision verifies child-retained leases,
wrapper-crash journaling, bad inherited descriptors, and signalled/failed child
behavior. Synthetic Windows PowerShell tests exercise same-process nesting,
elevated child reuse, contention, crash journaling and blocked repetition. A real
standard-user fixture verifies read-only leases and denied state mutation. Fixtures
never run package managers; the separate existing native application regression
suite still exercises the real Windows provisioning chain.

Server/Ubuntu runners validate operating-system behavior; they are not Windows 11
or Linux Mint desktop UAT. #42 will exercise the completed installers under these
locks, and #43 retains owner acceptance on school laptops. No candidate release
is promoted by this work.
