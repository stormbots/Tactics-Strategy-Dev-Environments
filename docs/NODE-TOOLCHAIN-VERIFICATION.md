# Node.js and npm verification increments for #161

## Problem and result

The Windows validator independently ran bare `node --version` and bare `npm --version`. It could reject a required Node 24 installation when another version was the default, or check npm through another Node.

It now discovers a supported Node 24 executable, resolves and reverifies its actual identity, checks its associated npm package and supported Node range, then invokes that npm CLI with the selected Node. A complete pair produces one required Node.js pass and supplies both actual versions to the existing tool metadata. Missing search results, unusable candidates and unfinished checks remain different non-passing results.

Other installations, PATH, runtime-manager selection, project settings and global defaults are preserved. This is read-only observation work. Complete real side-by-side fixtures, maintenance eligibility/review, preservation gaps in provisioning and the accepted connected UI remain outstanding. These increments do not complete #161 or create a Node-only repair engine.

## Supported discovery

`NodeRuntime.ps1` reads bounded known Windows sources:

- Cached Node 24 directories under configured/default nvm-windows, Volta and fnm stores.
- Node.js install-path and bounded uninstall registry records, including supported per-user/machine views.
- Conventional Program Files and nvm symlink locations.
- The resolved `node.exe` application as a fallback.

No manager command is run and no drive is scanned. The known Volta launcher path is excluded because launching it could acquire a missing runtime; only cached version-store executables are considered there. Shell `.cmd`/PowerShell shims are not executed for discovery. Executable shims that return an actual interpreter are followed only through fresh identity verification. Missing/unreadable/truncated sources remain incomplete unless another complete pair passes.

Version-store lists and final candidates are capped. Each fixed process has at most a 2.5-second wait within a 15-second probe budget. Only the helper's own diagnostic process can be stopped on timeout. Nothing targets an existing installer or removes a native gate.

## Pair verification

The fixed `NodeRuntimeProbe.cjs` uses Node's actual version and resolved executable path. Its npm mode derives `node_modules/npm/bin/npm-cli.js` beside that executable, reads npm's package metadata and uses npm's own semver dependency to check its declared Node engine range. npm must be the named package with a valid version and compatible engine range. Merely finding an npm file is not a pass.

The wrapper then invokes that exact CLI through the verified Node and requires successful exit plus a version matching the checked package. It never resolves bare npm or executes diagnostic text as a command. Supported npm prerelease versions remain evidence, not a newly imposed npm family restriction.

For each child process, Node injection/cache/coverage environment variables are removed and npm notification/script/audit settings are disabled. The working directory is temporary. Parent environment values are unchanged. No project package script, installation, manager switch or network lookup is requested by the fixed probes.

## Evidence and maintenance boundary

The validator emits `SKYVIEW_EVENT|runtime|Node.js|{...}` with schema 1, required family, status/reason, verified Node version/path, npm version/CLI path when established, and `maintenanceEligibility: notEvaluated`.

The frontend decoder rejects incomplete passes, another installation's npm path, malformed records and injected maintenance permission. It is an evidence foundation for later cards, not a native execution API. Existing generic rows still display the new check messages; the accepted card/continuation work remains a later increment.

Validation success does not prove that Chocolatey can maintain a selected version-store installation. Managed update metadata now withholds a candidate when the selected Node version differs from Chocolatey's tracked version, rather than treating executable/package version differences as one update comparison. That difference is informational and does not create a readiness warning or an update-retry task. It does not prove there are two installations; package drift is also possible. A matching version still supplies advisory package metadata, not proof of path ownership or execution authority. Actual eligibility/conflict review remains required before claiming the accepted maintenance workflow complete.

`Node24.ps1`, its migration/ownership rules, updater execution, coordination and all native admission checks are unchanged. Their existing preservation limitations must be resolved in the accepted follow-up work before promising a safe full Install/Repair remedy for every coexistence arrangement.

## Deployment and verification

The managed maintenance copy includes both new helpers under its existing protected file rules. The native application bundle already includes the backend resource directory. Required installed Windows recovery verification now checks that both helpers exist; original journal/privilege/summary assertions stay intact.

Windows increment's local evidence:

- 286 frontend tests, production build/type checks and formatting passed.
- The real JavaScript probe passed 11 compatibility/metadata cases using npm's actual semver dependency. Controlled identities are not actual Windows side-by-side installations.
- PowerShell contracts passed 86 local assertions for pairing, newer/older defaults, fallback, executable shims, missing versus incomplete discovery, invalid output, npm failure/timeout/mismatch and unchanged defaults. Actual process quoting, Unicode output, exit/deadline behavior and child-environment isolation were exercised separately.
- The platform-independent metadata fixtures passed the new cross-installation update guard. The full metadata suite includes Windows native disk/COM assertions and cannot pass on this Linux host; those assertions are unchanged and remain required in Windows CI.
- Source PowerShell parsing and the existing 35 backend contracts and 35 CI-scope tests passed. No application safety or CI classification exception was added.

Required Windows CI additionally exercises real directory discovery for nvm/Volta/fnm fixture stores, the prepared real Node 24/npm pair, production-validator observation consistency and packaged helper presence. Windows PowerShell 5.1 and installed/native assertions have not run locally. Full native/trust/acceptance CI remains mandatory for this platform change. A runner pass does not replace exact-candidate owner UAT or a complete supported coexistence fixture.

The Windows increment merged through #166 at `fa14774feaa4fac3122f2dc57fb0cd987d774aee`. Its PR and exact-main CI passed, including both native platforms, trust and acceptance. Windows CI observed the production validator and passed 91 Node runtime assertions. This is the Linux increment's green baseline.

## Linux counterpart

`node_runtime.py` replaces bare Node/npm and default-family checks with one selected pair. It searches bounded cached nvm, Volta and fnm version stores, `/usr/bin/node`, `/usr/local/bin/node` and the resolved Node application. It reads at most 64 entries per store, considers at most eight required-family versions per store and probes at most 12 distinct executables. Unreadable or truncated discovery stays incomplete unless a complete pair passes. Known Volta launchers, shim directories and shell wrappers are excluded; no manager initialization or acquisition command runs.

The selected native executable is resolved and its identity checked again. The fixed `node_runtime_probe.cjs` checks npm under that installation's `lib/node_modules/npm`. Only `/usr/bin/node` may also use Debian's `/usr/share/nodejs/npm` layout. npm's identity, version, engine range and CLI location must pass before that exact Node invokes the CLI. An unrelated npm or escaping CLI symlink cannot supply a pass. Unsupported layouts remain non-passing rather than borrowing bare npm.

Every process uses a temporary working directory, separate empty npm user/global configurations and a temporary npm cache. Injection variables and inherited npm configuration overrides are removed from the child; parent settings are preserved. A probe waits at most 2.5 seconds within a 15-second process budget. Each output pipe is capped while reading. Only the diagnostic's own process group can be stopped after a timeout or excess output. No installer is targeted and no package action or network lookup is requested.

The validator emits the same schema-1 observation and one required Node.js result. It passes that observation to tool metadata without executing Node/npm again. Metadata and the advisory update preview use the selected versions. A difference from the separately read APT package version withholds the candidate and stays informational. A matching version permits only advisory package comparison; it proves neither installation ownership nor permission to change it.

The frontend decoder now accepts the bounded Linux layouts while retaining the Windows checks and `maintenanceEligibility: notEvaluated`. This is still observation data for the later connected UI. Existing Install/Update package policy, supervisor snapshots, coordination and native admission are unchanged. Provisioning preservation and maintenance review must be completed before promising a full coexistence-safe remedy.

Both Linux helpers are included in the integrity manifest, application backend and protected baseline installation copy. Installed recovery CI checks their package presence without weakening its original evidence assertions. The consumer audit found no remaining bare Node/npm probes in Linux validation or tool metadata; package operations still use their existing approved APT family selector.

Linux increment's local evidence: 287 frontend tests, production build/type checks, 28 Linux runtime tests, 13 metadata tests and 35 backend contracts passed. The runtime suite includes the actual prepared Node 24/npm pair, the validator fragment, temporary-config isolation, bounded process output and simulated older/newer defaults. The JavaScript suite exercises 13 Linux cases, including the mapped Debian layout and an escaping CLI symlink; the existing 11 Windows probe cases still pass. Simulated identities and cached-store files are not real side-by-side installations or Mint owner-device evidence. Full native/trust/acceptance CI and exact-candidate owner UAT remain required.

#160 is currently closed; remaining packaged startup/owner evidence must be reconciled in the release ledger rather than inferred from issue closure. No release version, signing approval, owner acceptance or stable promotion is created by these increments.
