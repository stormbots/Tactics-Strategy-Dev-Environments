# VSCodium application locations: Windows and Linux

Part of [issue #161](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161).
These increments connect Windows and Linux VSCodium validation and the ordinary **Open VSCodium** action to the same checked installation. They do not complete the application-location proposal for other applications or the remaining maintenance and selection work.

## What the student sees

VSCodium can be installed in a supported location outside the usual system folder. That difference alone does not make the check fail or call for Repair. SDE checks the selected installation and its required extensions. **Open VSCodium** checks that installation again before opening it.

If the installation moved, changed, or disappeared after the check, Open reports the problem. The student can check again or open VSCodium from their desktop. SDE does not silently open a different installation using an old selection.

## Linux discovery and selection

The shared read-only collector is `linux/lib/editor_location.py`. Validation and native Open both use it. It examines these sources in order:

1. The `codium` launcher on PATH, resolving its symlink.
2. `codium.desktop` and `vscodium.desktop` in the user's and system's XDG application folders.
3. Known folders: `~/.local/opt/VSCodium`, `~/.local/share/VSCodium`, `/usr/share/codium`, `/usr/lib/codium`, and `/opt/vscodium`.

The first fully verified installation wins. Sources are bounded to eight XDG folders and twelve distinct installation roots. There is no drive scan, shell evaluation, launcher rewrite, or installation step. A desktop record provides a path only. Unsupported commands or profile arguments leave that record incomplete; SDE does not execute them.

The supported layout is stable, bundled VSCodium: a native ELF `codium` executable with `resources/app/product.json`, `resources/app/package.json`, and `resources/app/out/cli.js`. Product metadata must name VSCodium, the `codium` application, and stable quality. The files must remain within the canonical installation. Snap, Flatpak, Insiders, custom profiles, and arbitrary wrapper layouts are not verified by this increment.

Missing software, an incomplete search, an inaccessible file, an unusable launcher, and an installation that changes during a check remain different observations. An incomplete search does not prove that the application is absent. A failed required check remains failed.

## Read-only checks and ordinary Open

The collector runs SDE's fixed identity probe with the selected application's bundled Electron runtime. It then runs that installation's own CLI for its version and extension list. The version must agree with the product files. A failed CLI command cannot contribute partial extension passes. These commands inspect the application; they do not install extensions or change settings.

The probe removes Node injection variables, sets `ELECTRON_RUN_AS_NODE=1`, uses a temporary working folder, limits output to 32 KiB per stream, and bounds each diagnostic subprocess. Identity/version probes share a fifteen-second subprocess budget; extension inspection has a separate six-second limit. File sizes and the number of candidates are bounded too. These limits are not a guarantee about filesystem latency. Only a diagnostic child started by this collector may be stopped on timeout; package workers are never stopped by this code.

The `application` event is observation data. It cannot count as a required validation pass, operation completion, recovery acknowledgment, or maintenance permit. Its selection ID fingerprints the executable and three fixed resource files plus the canonical executable path. This detects a changed selection; it is not a publisher signature or proof of authenticity.

The frontend sends native Open only that ID, never an executable path or command. Open runs fresh discovery and checks the current product files, canonical paths, executable type, and fingerprint independently. A previous ID must still match. Opening without a previous ID still requires a fresh verified selection. Open runs as the ordinary desktop user, without elevation, shell arguments, or a fallback to the old hard-coded path. Concurrent editor Open requests are rejected while one is being checked.

## Maintenance and remaining work

Application usability does not prove that APT owns that installation. Version metadata therefore reports the checked version but does not offer an APT update candidate for it. The UI explains that SDE has not yet confirmed update permission. This is informational and does not request Repair or a retry.

Other applications, explicit choice between multiple verified installations, maintenance ownership, and preservation of alternate installations during full Install/Repair or scheduled maintenance remain follow-up work. These increments do not establish that those modifying operations preserve every alternate installation. They do not authorize them. Owner UAT must exercise the final authenticated candidate; source fixtures and CI alone do not close #161.

## Windows discovery and ordinary Open

Windows uses the shared read-only `EditorLocation.ps1` collector for validation and Open. Discovery reads the PATH `codium.cmd` or `VSCodium.exe` location, Windows App Paths and uninstall records for VSCodium, then the known Program Files and per-user `Programs\VSCodium` folders. It reads up to 512 uninstall keys per registry branch and checks at most twelve distinct executable paths. It never runs registry command text, a `.cmd` launcher, `Win32_Product`, or an installer. The first fully verified installation wins. A stale registered path or an incomplete search cannot establish absence.

The supported layout has a native PE `VSCodium.exe` beside the same three fixed resource files. The product must identify stable VSCodium. UNC paths, reparse-point paths, unsupported wrappers and custom profiles are not verified by this increment. A different supported local-drive location alone does not cause a failure. Discovery neither rewrites PATH nor moves an installation.

The fixed `EditorIdentityProbe.cjs` runs with that application's bundled Electron runtime; ordinary Node cannot supply a successful production identity probe. The selected installation's own CLI must report the matching version and required extensions. The collector removes Node injection variables and bounds both output streams to 32 KiB each. Identity/version subprocesses share a fifteen-second budget; extension inspection has a separate six-second limit. File sizes and candidate counts are also bounded, but filesystem latency is not a hard wall-clock guarantee.

The frontend passes only a selection ID to native Open. Native code calls the same fixed collector through Windows PowerShell, rechecks product files, canonical paths, native executable signature and fingerprint, then opens the checked executable. No command string, registry arguments or frontend path becomes a launch instruction. A previous selection must still match; moved, missing or changed files require another check. The fingerprint detects change and does not authenticate the publisher.

The collector refuses an elevated administrator or SYSTEM token, and native Open independently checks for an ordinary token before starting discovery. Membership in the administrators group with a normal filtered desktop token is not elevation. There is no UAC prompt or elevated fallback. An elevated SDE session must be reopened normally. Collection does not acquire another SDE operation gate or clear retained recovery evidence.

Windows reports the checked VSCodium version separately from Chocolatey ownership. Until the maintenance contract is implemented, it offers no package-update candidate for that selected installation. Neither a compatible installation nor a fingerprint grants modification permission. Existing full Install/Repair and scheduled-maintenance preservation still need their own review.

Local PowerShell tests cover bounded read-only queries and incomplete-result handling. Windows CI also exercises real temporary files and paths with spaces, CJS/PowerShell fingerprint agreement, stale registration, changed resources, failed version and extension commands, strict observation parsing, packaged-helper presence, and native Rust verification. Fixture executable files are never launched. Exact-candidate owner UAT must still cover real installations and desktop Open.

## Source references

- [VSCodium product preparation](https://github.com/VSCodium/vscodium/blob/master/prepare_vscode.sh) sets stable product names and the release version.
- [VS Code's Linux launcher](https://github.com/microsoft/vscode/blob/main/resources/linux/bin/code.sh) runs the bundled executable and fixed CLI with `ELECTRON_RUN_AS_NODE=1`.

Local fixtures cover alternate paths with spaces, product mismatch, failed commands, resource escapes, stale selections, and ordinary-user enforcement without launching fixture applications. Existing Windows/Mint native, signing, integrity, recovery, and acceptance gates remain required.
