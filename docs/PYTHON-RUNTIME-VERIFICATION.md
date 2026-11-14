# Python verification: first runtime increment for #161

## Problem and scope

The Windows validator previously ran bare `python --version` and then bare `python -m pip --version`. A newer or older default could hide a working Python 3.14 installation. Separate resolution also did not establish an explicit shared interpreter identity.

Windows now discovers and checks the required interpreter directly. A single Python pass requires both the explicit 3.14 interpreter and its pip to pass. Other versions/defaults do not generate warnings when that requirement passes. The helper changes no registrations, PATH, installations, preferences or projects.

This is one implementation increment. It does not complete #161, introduce a Python-only installer, offer a version exception or establish owner UAT acceptance. Node/npm, Linux resolved-identity verification, preference preservation, locations, maintenance and the accepted connected cards remain later increments. Windows retains its existing required Python/pip capability scope; this increment does not claim that a Windows venv was tested.

## Discovery and verification

`windows/chocolatey/tools/PythonRuntime.ps1` is loaded by the real validator and copied into the protected maintenance deployment by the existing package configuration.

Supported discovery reads:

- The launcher's `py -0p` registration listing, recognizing 3.14 and legacy 3.14-32/64 paths.
- PythonCore 3.14 installation records in user/machine registry views.
- The explicit application path currently resolved for `python.exe`, as a fallback candidate.

It does not scan arbitrary folders or switch a runtime manager. It lists launcher registrations rather than asking the launcher to execute/install a missing family. Recognized paths must be absolute local executable files; zero-length Windows execution aliases are not invoked as Python candidates. Unsupported/incomplete registration discovery is not proof of absence. A usable fully checked candidate can pass despite a failure to inspect another source.

The selected candidate runs a fixed isolated identity probe. Its reported executable is checked directly again, and the confirmed executable runs `-I -B -m pip --version`. The identity probes also use `-I -B`: they do not import project/environment Python paths or write bytecode. pip must exit successfully and report Python 3.14. Another installation's bare pip cannot supply a pass.

Each fixed read-only process has at most a 2.5-second wait, within a 12-second probe budget for this discovery sequence. Registry enumeration and candidate counts are capped; truncation remains incomplete. A deadline can terminate only the helper's own fixed diagnostic process, never an installer. Neither stream is treated as shell text or a repair command. The native validator's existing coordination and safety behavior remains authoritative.

## Structured evidence

The report includes `SKYVIEW_EVENT|runtime|Python|{...}` with schema 1, component, required family, status/reason, verified version, explicit executable and pip version when established.

| State | Meaning |
| --- | --- |
| `passed` / `verified` | Explicit Python 3.14 and its pip passed |
| `notFound` / `notDiscovered` | The completed supported search did not find the required interpreter; not an exhaustive disk search |
| `unusable` | A registered/identified candidate or its required pip check failed |
| `incomplete` | Discovery or a required check could not finish; includes pip timeout |

All non-passing states remain a failed required validation check and prevent false Ready. They have different explanations; incomplete is not labeled missing. No state acknowledges an incident or permits package execution. A valid interpreter's version and a missing/broken pip are distinct facts; the aggregate Python requirement passes only when both checks pass.

The frontend has a narrow typed decoder for this evidence, with length, shape, component, family, path and pass-completeness checks. Current generic validation rows still render the check messages. The accepted evidence-driven cards/continuations will consume this contract in their later integration increment. This decoder supplies no native execution capability and persists no user location or exception.

## Verification and evidence limits

- Local PowerShell contracts exercise newer/older defaults, no launcher, registry fallback, missing versus incomplete discovery, unusable registration, invalid output, broken/mismatched pip, pip timeout, same-interpreter pairing, isolated probes and unchanged PATH.
- The actual process adapter is exercised for argument quoting, exit-code preservation and timeout. Fixtures supply interpreter/discovery observations; they are not installed Windows Python versions.
- The existing Windows backend contract runner now requires one structured observation from the real packaged-entry validator, checks aggregate pass/fail consistency and runs the new contracts. Its Windows smoke also queries real runner registrations and verifies complete evidence for any live pass. It does not require the runner to have the owner's exact side-by-side arrangement.
- Local frontend: 279 tests passed, including decoder rejection of partial/wrong-family/invalid evidence. Production build and formatting passed. Existing Python backend contracts (35) and CI-scope policy tests (26) passed.
- Local PowerShell runs use PowerShell 7 on Linux. Required Windows CI must establish Windows PowerShell 5.1 behavior, registry/native smoke, packaging/deployment and full safety/trust/acceptance results. Actual supported side-by-side installation fixtures, Mint checks and exact-candidate owner UAT remain required before claiming the complete Python proposal accepted.

Startup baseline: #162 is merged at `9f1c316b13edfcbc221eef9eb6ffccfae125b399`; its exact-main [run 43583833987](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/43583833987) passed checks, both native jobs, both trust jobs and acceptance. The startup issue still needs its remaining packaged/owner evidence.

No workflow scope, safety, signing or release identity changed. Preserve published v1.2.23 assets and existing evidence. Human signing, exact-candidate owner UAT and separate promotion approval remain mandatory.
