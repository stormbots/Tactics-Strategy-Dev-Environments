# Recovery bootstrap integration: engineering handoff

Branch: `codex/recovery-bootstrap-integration`, stacked on accepted #116 head
`c0a3ecd282409af436cac12a32ed8a771707ff06` (Build `40821734101`). Includes
still-unmerged #113–#116. This is one bounded T1 deployment task, not completion
of the T4 platform adapters, the full redesign or a UAT/release candidate.

## Acceptance criteria and implementation

The existing `sde_coordination::initialize()` entry point now initializes the
trusted layout and attempts incident preparation under the exclusive operation
gate. Both the installed application's `--coordination-init` (used by NSIS and
Debian post-install hooks) and the narrow coordinator `init` command use it.
No new CLI argument, path override, environment bypass or elevation route exists.

- Clean initialization creates only gates, not a phantom incident or consent.
- An inactive legacy journal receives a sanitized public incident, private
  generation binding, fixed writable intent slot and protected restart context.
  Its original bytes/object remain intact and ordinary execution still blocks.
- Repeat installation/preparation preserves incident identity, captured restart
  context and any submitted intent. It does not reconcile that intent into an
  acknowledgment, archive or retired journal. A replacement generation gets a
  new identity and requires fresh consent.
- A live supervisor holding the gate defers metadata preparation but does not
  fail initialization. This matters during signed upgrades: the updater owns the
  gate while package hooks run. Do not label its live journal as an interruption,
  replace a held gate or deadlock/fail its own install. Other trust/I/O failures
  still fail initialization; Busy is the only deferred preparation result.
- Malformed/untrusted recovery metadata fails closed without repairing it or
  discarding original evidence. Bootstrap never clears a journal on restart,
  Validation success, installer success or presence of a submitted intent.

No GUI acknowledgment/continue action is enabled. Automatic reports, final
history/Recovery UI, script/scheduled/updater execution adapters, read-only
diagnostic parity, actual reboot/resumption and consolidation remain dependent
work. Preparation captures provenance only; it does not inspect or certify
package inactivity/health. The safe transition rechecks those independently.

## Tests and native proof required

Targeted local checks: coordinator library harness 52 successful entries;
protected fixture cases return early at non-root UID and are not native proof.
Linux and Windows GNU all-target Clippy with warnings denied passed. CI-scope
contracts 17/17 passed; Python compilation, Bash syntax and diff checks passed.
PowerShell and actual package execution are deferred to the existing workflows.

New `bootstrap_*` native coordinator tests cover clean/idempotent initialization,
legacy evidence identity, submitted-intent retention, changed generations, corrupt
metadata, and live installation leases. The existing real standard-user storage
probe now obtains its fixture through production bootstrap, then demonstrates
prompt-free submission and no private evidence/mutation access.

Existing Build Skyview Dev Setup gains two required installed-package probes:

- **Required Windows installed recovery bootstrap**, after clean NSIS installation
  and before signed SYSTEM-upgrade testing. Runs `Test-RecoveryBootstrapCI.ps1`
  through in-box Windows PowerShell and requires exit zero plus the exact marker
  `SDE_RECOVERY_WINDOWS_INSTALLED_BOOTSTRAP_OK`.
- **Required Linux installed recovery bootstrap**, after clean Debian installation.
  Runs `verify_recovery_bootstrap_native.py` as root; pipefail and exact marker
  `SDE_RECOVERY_LINUX_INSTALLED_BOOTSTRAP_OK` are mandatory. The same helper is
  also required inside the actual Mint 22.3 container before applied-baseline
  setup in the existing signed-upgrade step. Ubuntu host results alone are not
  Mint proof.

Both helpers create a private synthetic legacy journal on a disposable runner,
exercise the installed executable while a synthetic supervisor gate is held,
then reinstall the real package to exercise its actual hook. Repeat installed
initialization must preserve context/intent and keep script mutations blocked.
Neither helper launches development-tool provisioning or package corruption.
Successful cleanup removes only verified synthetic fixture records. On failure,
leave CI evidence intact rather than clearing unexpected/partial state.
Existing trust, permission, durable crash/replay, mutation, native build,
feasibility marker and signed-upgrade checks remain mandatory and unchanged.

## DevOps handoff and boundary

Validate the exact new head with the existing Build workflow. Require all
applicable checks, native Windows and root-required Linux coordinator commands,
both installed markers, and the marker inside actual Mint. Return run/job URLs,
counts and exact failing commands/assertions. Do not accept local skips or older
accepted heads as proof. Inspect initial/final results without continuous polling.

Do not merge partial work, version, sign, publish, resume automation, prepare a
candidate or request UAT. Owner Windows interruption evidence and Mint v1.2.18
Install/Validate acceptance (35/0/0) remain unchanged. This work executes only in
isolated native fixtures, not owner machines. After acceptance, return to
engineering for the remaining normally privileged execution adapters and the
approved reports/history/Recovery experience.
