# Unattended Linux Mint application installation (#40)

The existing root maintenance service selects a protected external launcher at
`/usr/local/libexec/skyview-self-update.py`. The stable schema-1 launcher accepts no
arguments and uses fixed paths. It snapshots the current verifier and version
receipt into a private UUID directory before running `maintain-linux`. The native
worker has no production key, repository, package-path or OS-policy overrides.
Linux Mint 22.x amd64 remains the supported production platform.

## Expected behavior

Tool maintenance runs first using the currently applied baseline. An embedded
supervisor acquires #38's shared session and exclusive operation leases before
reading deployed scripts. It snapshots the updater and its helper files and
passes the actual held descriptors to the child. A concurrent mentor Repair
cannot mix baseline generations. A tool failure or contention prevents app
installation in that invocation; an unavailable GitHub check cannot prevent the
earlier tool work. Tool exit and application outcome are reported separately.

The worker uses #37's fixed GitHub discovery, rejects drafts/prereleases and
non-newer versions, stages authenticated assets, then rechecks GitHub eligibility.
Under both installation leases it rechecks pause and installed identity, verifies
the pinned Minisign signature and payload hash/size again, and checks the DEB's
package name, version and architecture. A staged marker is never execution
authority. Only `skyview-dev-setup` for `amd64`, at the signed version, can execute.

APT/DPKG contention is inspected with POSIX record locks, matching the package
manager's locking namespace. Existing contention defers before writing installation
intent. APT itself is responsible for atomic acquisition; its frontend wait is
bounded to 30 seconds if another process races the preflight. An unhealthy DPKG
state requires mentor repair. Locks are never deleted and package processes are
never killed. Once the installer starts, the worker waits for its actual outcome.

The fixed command is `apt-get -y --no-remove --no-install-recommends`, with
`DPkg::Lock::Timeout=30`, `--force-confdef`, `--force-confold`, and `install` of the
protected local DEB. Its clean environment specifies root HOME, fixed system PATH,
C locale and `DEBIAN_FRONTEND=noninteractive`. APT resolves required dependencies
through the machine's configured authenticated repositories. No distribution
upgrade, downgrade, autoremove, unauthenticated-package option, GUI launch or
reboot is requested. This preserves existing configuration on conffile conflicts.
See the [APT command contract](https://manpages.ubuntu.com/manpages/jammy/man8/apt-get.8.html).

A durable #38 transaction and detailed installation receipt precede APT. Exit 0
requires the package to be fully installed at the expected version, required
application resources, and an activated engine whose bytes match the installed
bundle. A nonzero exit, unknown completion or failed postcheck leaves intent and
blocks automatic retry. A lock race that reaches APT and then fails is treated
conservatively as requiring review; the worker does not infer that no package work
occurred by parsing localized APT output. Recovery controls belong to #41.

## Application, engine and baseline separation

The DEB postinst initializes coordination and activates a protected immutable
engine generation. It does not provision tools, apply Node/Python policies,
configure users, enable/start a timer, or launch maintenance. Running invocations
use private copies outside the package's replaced files. Atomic receipt publication
selects the next engine; current and previous engine generations are retained.
The schema-1 launcher is installed once; incompatible launcher changes need an
explicit migration. A killed worker's snapshot is retained for diagnosis.

For an already provisioned coordinated service, a fixed systemd drop-in changes
only ExecStart. It preserves the existing timer, enabled/disabled state, custom
schedules and unrelated unit settings. The hook only reloads unit definitions when
systemd is actually running; it never restarts the service. An app-only install
creates neither a service nor a timer. An older uncoordinated deployed baseline
still requires #38's one-time mentor Repair migration. Explicit baseline
Install/Repair selects the external host when available; unpacked-script installs
without a packaged app retain the previous direct service entry point.

Home files, projects, credentials, editor settings and applied baseline policy
remain outside application installation. The worker reports the protected applied
baseline version separately from application/engine versions; it never substitutes
a new app version for an unknown baseline. #33's full proposal/version UI remains
separate work.

## Pause, recovery and status

Bootstrap defaults `policy.json` to schema 1 and `paused=true`, preserving an
existing administrator-controlled policy. Pause blocks app self-installation while
allowing earlier tool maintenance. Production stays paused until #41 controls,
#42 integration and #43 owner acceptance are complete. Signing a candidate never
approves promotion of its GitHub prerelease.

The worker attempts to retain the exact currently installed stable signed DEB.
An older unsigned or unavailable release reports reduced previous-version
recovery capability. Successful installation retains the new DEB, manifest and
signature, plus the previous authenticated recovery set when available. Cleanup
under the operation lease removes only known files in non-retained UUID staging
directories; unknown state, links and unsafe ownership fail closed. An interrupted
transaction blocks cleanup. There is no automated rollback.

The root-owned state directory is traversable for sanitized `status.json` read
access; engines, runs, staging, logs and receipts remain private. Status contains
separate application, engine and baseline versions, tool exit, native exit,
candidate, outcome, timestamp, sanitized detail and private log reference. The
launcher retains eight completed logs plus active/crashed invocation logs.

## Verification and remaining owner UAT

Required CI extracts the actual Mint 22.3 XFCE userland from the official ISO.
It verifies Mint's signed checksum list using the public ISO signing key with
fingerprint `27DEB15644C6B3CF3BD7D291300F846BA25BAE09` and checks a pinned ISO SHA256
before extraction, following [Mint's verification guide](https://linuxmint-installation-guide.readthedocs.io/en/latest/verify.html).
It checks `/etc/os-release` and exercises the production Mint eligibility gate;
it never relabels Ubuntu as Mint. On that actual Mint userland it installs the
real 1.2.1 DEB, then invokes the same protected installation function as root to
upgrade to an unpublished 1.2.2 DEB. A disposable in-memory test key authenticates
fixture metadata; production's pinned key rejects it, and no production override
exists. The test rejects metadata/payload tampering, exercises pause, GUI leases
and a real other-process DPKG lock, checks package/resources/engine activation,
preserves a student home sentinel, baseline and custom timer, then executes the
real packaged launcher and confirms the next engine with an applied policy
snapshot. A real failing postinst leaves partial DPKG state and blocks retry.
The disposable container is discarded without deleting package locks or pretending
to repair its deliberately partial package state.

Ubuntu package bootstrap/build and cross-platform signature/coordination tests
are supporting evidence. Mint container evidence proves native APT/DPKG and
userland execution, not a booted school desktop or live systemd timer. #42/#43
retain representative booted Mint laptops, real timers/missed runs, school network
conditions, full student profiles, live GUI deferral, approved stable-release
selection and mentor pause/interruption/recovery acceptance. Codex owns engineering
and these automated/native checks; the owner performs UAT only.
