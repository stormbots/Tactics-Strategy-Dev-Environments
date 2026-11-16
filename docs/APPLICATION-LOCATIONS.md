# DBeaver and browser location checks

Part of [issue #161](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161). These checks follow the [VSCodium](EDITOR-LOCATIONS.md) and [PyCharm](PYCHARM-LOCATIONS.md) location increments.

SDE no longer uses a familiar filename or one installation folder as enough evidence for DBeaver, Chrome or Firefox. It looks through supported installation records, launchers and known locations. The first fully verified candidate wins consistently. A supported alternate location does not by itself cause a warning, Repair suggestion, duplicate installation or relocation.

## What each check establishes

| App | Evidence |
| --- | --- |
| DBeaver | Expected `.eclipseproduct` name, product ID and numeric version; native launcher; bounded startup JAR with the expected bundle identity; selected bundled Java and a successful version query meeting the minimum in `dbeaver.ini` when supplied |
| Chrome on Linux | Canonical native executable and a successful `--version` query identifying Google Chrome |
| Firefox on Linux | Expected `application.ini` name/product ID/version, canonical native executable and a successful matching Mozilla Firefox version query; an ESR suffix is accepted |
| Chrome on Windows | Supported PE executable format, Google Chrome product name and numeric product version from the executable's version resource |
| Firefox on Windows | Supported PE executable format and product version, plus matching Firefox product ID/version in `application.ini`; an ESR suffix is accepted |

Windows browser checks inspect files. They do not run browser executables to ask for a version. Linux browser queries pass only `--version`; they do not request a browser window or profile change. DBeaver checks run only the selected Java with `--version`, never the IDE, startup JAR or a project. Java agent injection variables are removed for diagnostic children.

DBeaver's marker and minimum-Java conventions follow the upstream [product marker](https://github.com/dbeaver/dbeaver/blob/devel/features/org.jkiss.dbeaver.ce.feature/root/.eclipseproduct), [community product definition](https://github.com/dbeaver/dbeaver/blob/devel/product/community/DBeaver.product) and [product-name property](https://github.com/dbeaver/dbeaver/blob/devel/pom.xml). Its `-startup` and `-vm` values are read as data. Startup must identify a supported launcher JAR within the selected bundle. The configured Java must also remain within it; an absolute path inside the bundle is supported. A missing explicit VM uses the standard bundled `jre/bin` layout. External/system Java layouts stay incomplete rather than being called missing.

These are bounded product, file and runtime checks, not publisher authentication or a test of every browser/IDE feature. Owner UAT must still launch real applications and exercise their required functions on the exact authenticated release candidate. A fingerprint covers inspected files, not the whole installation or profile.

## Discovery and limits

Linux reads supported PATH targets, fixed XDG desktop records and known system/user folders. Desktop command text is never evaluated. Symlinks can identify the canonical installation root, but checked resources and runtime files cannot escape it. Unsupported shell wrappers or layouts remain incomplete. Discovery considers at most eight XDG folders and twelve candidate roots per app, without a drive scan.

Windows reads supported PATH executables, App Paths and uninstall records, then known Program Files and per-user folders. It reads up to 512 uninstall keys per branch and checks at most twelve candidate paths per app. It never runs uninstall strings, registry command text or `Win32_Product`. Local-drive layouts are supported; UNC and reparse-point layouts remain incomplete. Both x86 and x64 browser images can qualify on the supported x64 Windows platform. DBeaver's launcher and selected Java must have matching architecture.

Collectors refuse elevated use before inspecting candidates or starting diagnostic children. Discovery grants no elevated execution permission. The existing Chrome-on-Linux policy is retained: automated Chrome parity is required on amd64, while other architectures receive a warning rather than a new failed requirement.

Metadata and manifest reads have explicit byte limits. A startup JAR is limited to 64 MiB; its manifest to 64 KiB. Native files are limited to 512 MiB, with a smaller 64 MiB DBeaver launcher limit. Output is bounded to 32 KiB per stream. Each diagnostic query receives at most four seconds inside a fifteen-second budget per app. Filesystem latency is not a hard wall-clock guarantee. Timeout handling can stop only the diagnostic process started by the collector; package/installer workers are never stopped.

## Findings and maintenance

A complete supported search with no installation reports **not found**. Stale records, access errors, missing files inside an installation, unsupported layouts, exceeded limits or interrupted collection remain **check incomplete**. Wrong products and failed required runtime/version checks cannot pass. Changed inspected files invalidate the observation. A later fully verified candidate can still pass without a warning about another failed source.

The `application` event contains observation data only. It cannot substitute for a required validation row, operation completion, interruption acknowledgment or native execution permission. The shell collector rejects missing/duplicate result records and empty helper output. Retained failures from older location-only checks request a new check instead of recommending Repair from that old evidence alone.

Reported application versions are separate from APT or Chocolatey ownership. SDE offers no update candidate for these selected installations until maintenance eligibility is established. An unknown maintenance relationship does not prove that an external manager owns the installation.

This increment adds no DBeaver or browser Open endpoint, and sends no application path to native launch or elevation. It does not edit profiles, shortcuts, preferences, project settings, default commands or installed locations. Explicit multi-installation choice, any additional Open contracts, external Java layouts and modifying-operation preservation/maintenance remain follow-up work before closing #161. Existing Install/Repair and scheduled-update effects are not redefined by these observations.

All Windows/Mint native, trust, integrity and acceptance gates remain required. Human signing, exact authenticated-candidate owner UAT and separate stable-promotion authorization remain mandatory.

Windows test fixtures use the operating system's .NET Framework compiler to emit native `VERSIONINFO` resources. The tests assert that the PE resource directory and expected product/version values exist before invoking discovery. Unix .NET can read managed assembly attributes even without native version resources, so the portable fixture checks alone do not establish Windows resource behavior. Generated application files are inspected as data and never executed.
