# Validation, packaging and publication boundaries

PRs (including drafts), main/release pushes and eligible tag pushes run validation.
They do not build NSIS/DEB installers, execute installed SDE package upgrades or
publish releases. This applies to #72's implementation PR as well as later work.

## Automatic validation

`build-dev-setup.yml` retains UI/unit/browser/accessibility, trust/tampering,
formatting, static analysis, integrity and isolated protected coordination checks.
The new `desktop-check` matrix compiles desktop/test targets and runs Rust unit
tests on Ubuntu and Windows MSVC without Tauri bundling. Windows also runs the
pure package-hook parser checks under Windows PowerShell 5.1; it does not invoke
the packaging main block. The protected Rust coordination fixtures are disposable
`coordination-test-*` directories. These checks do not certify an installed native
upgrade or desktop UAT.

Development dependencies may be installed on disposable runners. Frontend asset
compilation and Rust test/check compilation are validation, not installer creation.
No release-mode verifier artifact is built/uploaded by automatic trust checks.
The existing fixture-only classifier still skips application validation for its
narrow reviewed fixture changes; other/unknown changes fail closed to validation.

`native-uat-fixtures.yml` still tests fixture setup/restoration in disposable
Windows/Mint environments. It does not install SDE packages. Research harnesses
are not activated by these changes.

## Explicit dispatch controls (none dispatched for this change)

The main build workflow exposes three independent boolean choices, all false by
default:

| Inputs | Result |
| --- | --- |
| All false | Validation only. |
| `build_installers` | Build unsigned installer artifacts, inspect package contents and retain checksums; no installed-package execution/publication. |
| Also `run_native_packages` | Opt in to disposable package installation/upgrade, maintenance integration and native failure/recovery tests. Requires installer builds. |
| Also `publish_prerelease` | Separately opt in to signing/publication. Requires both preceding choices, an eligible release ref and the existing `sde-release-signing` environment gate. |

Invalid option combinations fail before packaging. Pushes and PRs cannot enter
the installer or publication jobs even if dispatch inputs were truthy. Release
refs/tags no longer publish automatically; release identity checks, protected
signing environment and historical excluded tags remain in place. The dispatcher
must have separate task authorization for package execution and publication.

`prepare-self-update-uat.yml` is dispatch-only. Its fixed candidate-pair workflow
includes installer builds and native package operations, so dispatch requires
explicit authorization for both. Its new `publish_prerelease` input defaults to
false: building/testing does not sign/publish. Publication retains reviewed-main,
release-ref and signing-environment checks. It also requires automatic main
validation and an explicitly dispatched successful native Windows/Mint upgrade
run on that exact main SHA. Skipped native steps or a green packaging-only run
are not proof. The evidence checker fails closed on missing or truncated job data.

`probe-native-upgrade.yml` is dispatch-only because it executes archived installers.
The frozen Linux 1.0.1 fallback remains a separate manual-only legacy publication
workflow; its pinned historical source and behavior are unchanged.

Automatic runs cancel superseded PR validation only. Manual packaging/native/
publication runs are not cancelled by a new PR or push. No branch protection or
GitHub environment settings were changed; maintainers should include the new
Windows/Linux desktop validation checks when updating required-check policy.

## Local verification and implementation history

Workflow changes pass actionlint 1.7.7 (including shellcheck), seven classifier
checks, seven boundary checks (including event/input truth tables), and four
native-evidence checks. No package workflow was dispatched as validation.

The implementation PR is assembled from reviewed Phase 1/2 commits on
`feat/issue72-app-only-core`, with no production-source changes during extraction.
Research stays on the published prototype/history branches; the approved decision
links to pinned historical protocol/ledger files. Existing JSON evidence source
SHAs refer to the original reviewed commits, not the cherry-picked PR SHAs.

The feature remains unwired/disabled. Native package-hook, compatibility migration,
privilege/request lifetime and recovery gates remain open. Desktop UAT belongs to
the owner on owned Mint and Windows 11 PCs after an authorized test build.

### PR review correction: package-changing desktop tests

The first workflow split moved `cargo test` into automatic desktop validation but
missed two existing Windows tests enabled solely by GITHUB_ACTIONS: a real Node
migration and a Chocolatey fixture installation. Automatic runs reached that test
step on disposable runners; package operations may have occurred. A cancellation
attempt found the run already completed. This is not described as prevented or
as a native-package dispatch authorized by the owner. No student PC was targeted.

Both tests are now explicitly ignored by default, assert a disposable runner AND
SDE_RUN_NATIVE_PACKAGES=1 before any action, and are selected with --ignored only
by a separately gated manual native-package step. The Node migration script also
requires the opt-in. Automatic compilation still checks those test bodies, while
automatic test execution excludes them. Regression checks enforce both layers.
