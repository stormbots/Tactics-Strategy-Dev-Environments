# PyCharm checks in supported alternate locations

Part of [issue #161](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161).

SDE checks the selected PyCharm installation instead of requiring it to live in one folder. A supported per-user installation can pass without a managed `/opt/pycharm` link or a Program Files installation. Existing launchers, shortcuts, settings and projects are preserved.

## What gets checked

The read-only collectors inspect PyCharm's `product-info.json`. It must name PyCharm or PyCharm Community Edition, identify the `PY` or `PC` product, and report a numeric release version. Its launch record must match the current platform and supported bundled layout. If the product record supplies `minRequiredJavaVersion`, the bundled runtime must meet it. Older records without that optional field still require a successful bundled-runtime check.

The metadata fields follow JetBrains' [product-info schema](https://github.com/JetBrains/intellij-community/blob/master/platform/buildData/src/productInfo/ProductInfoData.kt) and [product-info generator](https://github.com/JetBrains/intellij-community/blob/master/platform/build-scripts/src/org/jetbrains/intellij/build/impl/productInfo/ProductInfoGenerator.kt). The minimum Java requirement comes from that product record, without changing the computer's default Java.

The collector checks that the declared launcher and fixed bundled Java files exist, stay inside the installation and have the expected executable format. It then runs only that bundle's Java with `--version`, from a temporary working folder. The command must succeed and identify JetBrains Runtime. Java agent injection variables are removed before the probe. The IDE launcher and project code are never run by these checks.

These checks establish the product record, launcher files and a working bundled runtime at collection time. They do not establish that every IDE feature works, authenticate the publisher, inspect the whole runtime, or replace a real desktop launch during owner UAT. Installs that require an external Java runtime or an unsupported launcher layout stay incomplete; they are not reported missing.

The observation records the checked version, product code, launcher and runtime paths, runtime version and a fingerprint of the three inspected files. It is data only. It cannot count as completion of an operation, clear an interruption, authorize a command or grant update permission. SDE currently has no PyCharm Open destination; this increment adds no frontend path-execution endpoint. VSCodium's independently verified Open contract is unchanged.

## Supported discovery

Linux reads the `pycharm` PATH target, supported XDG desktop records, `/opt/pycharm`, and bounded PyCharm folders under `/opt`, the user's local application folders and the current JetBrains Toolbox app folder. Symlink launchers can identify the canonical installation root. Resource files and the bundled runtime cannot escape that root.

Windows reads a supported `pycharm64.exe` PATH location, PyCharm uninstall records and bounded PyCharm folders under system JetBrains, per-user Programs and the current JetBrains Toolbox apps folder. It reads install locations as data. It does not run uninstall strings, `Win32_Product`, shell wrappers or registry commands. Reparse-point and UNC layouts remain unsupported by this increment.

Both collectors refuse elevated use before probing external software. Discovery does not scan the whole disk. It checks at most twelve candidates, eight launch records per product file, and bounded registered/known-location entries. The first fully verified installation wins consistently; explicit multi-installation choice and older Toolbox directory layouts remain follow-up work.

A product file is limited to 1 MiB, the launcher to 16 MiB and the runtime executable to 512 MiB. Diagnostic output is bounded to 32 KiB per stream. Each runtime query has at most four seconds inside a shared fifteen-second collection budget. Filesystem latency is not a hard wall-clock guarantee. Timeouts may stop only the diagnostic child started by this collector, never an installer or package worker.

## Missing and incomplete are different

A complete supported search with no installation reports **not found**. Access denial, stale registration, unsupported layout, discovery limits, or missing files within an installation report **check incomplete**. An identified wrong product or a runtime command that fails reports an unusable candidate. A later fully verified candidate can still pass. Partial command output cannot turn a failed runtime query into a pass.

Older retained failures about the managed PyCharm symlink now request a fresh check. They do not by themselves recommend reinstalling or moving PyCharm. Original failed evidence is not converted into a pass; only a new successful check can resolve it.

## Maintenance and release limits

The checked application version is separate from APT, JetBrains or Chocolatey maintenance ownership. SDE does not offer an update candidate for this selected installation until that separate contract is established. This does not prove the installation is externally managed.

This increment does not change the effects of full Install/Repair, the privileged updater or scheduled maintenance. Their preservation of alternate installations still needs review before the accepted UI can promise it. Other application discovery and connected workflows also remain open in #161.

Windows/Mint native, trust, integrity and acceptance checks remain required. Human signing, owner UAT of the exact authenticated candidate and separate stable-promotion authorization remain in force.
