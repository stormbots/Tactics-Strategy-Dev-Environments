# VSCodium application locations: Linux increment

Part of [issue #161](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161).
This increment connects Linux VSCodium validation and the ordinary **Open VSCodium** action to the same checked installation. It does not complete the application-location proposal for Windows or other applications.

## What the student sees

VSCodium can be installed in a supported location outside the usual system folder. That difference alone does not make the check fail or call for Repair. SDE checks the selected installation and its required extensions. **Open VSCodium** checks that installation again before opening it.

If the installation moved, changed, or disappeared after the check, Open reports the problem. The student can check again or open VSCodium from their desktop. SDE does not silently open a different installation using an old selection.

## Discovery and selection

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

Windows discovery, other applications, explicit choice between multiple verified installations, maintenance ownership, and preservation of alternate installations during full Install/Repair or scheduled maintenance remain follow-up work. This increment does not establish that those modifying operations preserve every alternate installation. It does not authorize them. Owner UAT must exercise the final authenticated candidate; source fixtures and CI alone do not close #161.

## Source references

- [VSCodium product preparation](https://github.com/VSCodium/vscodium/blob/master/prepare_vscode.sh) sets stable product names and the release version.
- [VS Code's Linux launcher](https://github.com/microsoft/vscode/blob/main/resources/linux/bin/code.sh) runs the bundled executable and fixed CLI with `ELECTRON_RUN_AS_NODE=1`.

Local fixtures cover alternate paths with spaces, product mismatch, failed commands, resource escapes, stale selections, and ordinary-user enforcement without launching fixture applications. Existing Windows/Mint native, signing, integrity, recovery, and acceptance gates remain required.
