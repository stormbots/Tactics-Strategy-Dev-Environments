# #72 Linux testing build and next native gate

Active continuation, 2026-10-18 (owner timezone). Verified starting PR HEAD:
`f4b7d255f544bbabcd18c67348e310dad426eeba`; its sole change after application
snapshot `8350cba954882366288976b92228241264524884` is the handoff document.
The owner now authorizes moving Update Now/protected close forward, including
native execution, installer builds and eventual releases/rollout. That supersedes
the handoff's blanket deferrals. It does **not** repeat the stopped spare-Mint
attempt: that still needs a reviewed exact plan and specific authorization.
Additional concrete privileged/package operations are presented when needed.

## Shortest remaining route

1. Produce Linux artifacts and the pinned shared-core driver below. Leave Windows
   packaging and optional runner/VM/media work paused. Automatic cross-platform
   development checks remain useful and unchanged.
2. Obtain the read-only existing-desktop diagnosis. Establish the packaged agent,
   effective autostart entry, original UID and active session before proposing
   any agent launch or repeating polkit. Do not infer agent registration from a
   process name, and do not call exit 127/no prompt cancellation.
3. Review exact installed baseline, external V2 helper migration, current recovery
   state, artifact hashes and bounded root operations together. Do not downgrade
   an installed newer release to fit synthetic fixture versions.
4. One bounded native session: authorization denial/approved disabled entry,
   kernel ACL/user separation, worker/admission/close/recovery checks, and the
   controlled package upgrade. Stop at the first unexpected result; fix and rerun
   the affected case only. Existing shared-core/crypto/UI tests remain evidence.
5. Finish the isolated full-worker signed-discovery fixture and evidence-backed
   capability provisioning/renewal. Build the enabled Linux UAT artifact only
   after these safety gates pass. Owner Mint Cinnamon UAT, then necessary Windows
   implementation/native UAT, then merge/release/stable promotion. No automatic
   test or mocked marker satisfies a native gate.

This continuation prepares a **disabled Linux engineering build**, not an
enabled Update Now UAT build. No stable version is allocated or published to
manufacture a compatible candidate. Latest public stable observed: `v1.2.9`;
its hooks must not be assumed compatible with this PR.

## Build inputs and artifacts

The existing `build-dev-setup.yml` now accepts a Linux-only installer matrix.
Reviewed dispatch (already authorized by the owner's current request):

```text
gh workflow run build-dev-setup.yml --ref feat/issue72-app-only-pr \
  -f build_installers=true -f installer_platform=linux \
  -f build_linux_fixture_pair=true -f run_native_packages=false \
  -f publish_prerelease=false
```

Record the returned run's exact `headSha` before consuming artifacts. No native
package execution, signing, release upload or Windows packaging is selected.
GitHub-hosted build dependencies are installed by the existing Linux build job.

Artifacts:

* `Skyview-Dev-Setup-LinuxMint-amd64.deb`: current-source disabled application,
  version 1.2.1, plus checksum. Do not install it over a newer deployed version.
* `linux-app-only-unpublished-fixtures`: the same baseline, synthetic 1.2.2
  candidate, updater library `native-tests` binary and `pins.json`. These reuse
  the existing native fixture version pair; neither is a proposed release.
* `pins.json` binds source commit, both DEBs, compiled test driver, exact baseline
  installed-file bytes and the DEB postinst/prerm hashes. Preparation streams the
  archives without extracting or executing hooks. The fixture's Windows-named
  file is an explicit inert placeholder required by the test manifest schema;
  it is not a Windows build or native Windows evidence.

The package pair is a shared-core test input, never an eligible public stable
candidate. The production key rejects its ephemeral signatures. No runtime
key/feed override is added to product code. Full public stable discovery and a
real detached product worker still need their separate evidence.

## Targeted Mint diagnosis — read-only and unelevated

Run `tests/mint_authorization_diagnosis.py` with `/usr/bin/python3 -I` in the
existing Cinnamon desktop terminal as `ryan`, without sudo. The script refuses
root and non-Mint hosts. Review/download it at an exact PR commit and verify its
SHA-256 before execution; retain its JSON output.

It reads only: selected session variables and `loginctl` properties, daemon state,
the fixed `pkaction`, package inventory/file lists, relevant system/user autostart
keys (including Hidden overrides), visible polkit process executable/UIDs, SDE
version, V2 markers and presence/permissions of the cleaned files/recovery barriers.
It never invokes pkexec, starts an agent, changes a setting, reads credentials,
prints process arguments or writes installed state. Missing access is Unknown.
The fixed action is expected to be absent after the reported cleanup.

Interpret the facts together: active original-user session, existing packaged
agent executable, effective autostart override and actual visible agent process.
An absent process alone cannot prove the cause. If a packaged agent needs launch,
name its observed exact path, user/session, how its PID is retained and how only
that new owned process is stopped. Present that operation and any two-file
registration/retry packet for specific authorization; no sudo fallback or guessed
agent package/service repair.

## V2 maintenance prerequisite

The bundled Python adapter now performs I/A/I/S/I for new sessions, releases A
and retains S, refuses orphaned scope intent, and lets an already inherited S
continue without entering A again. O contention remains nonblocking. The V2
markers now describe actual implementation; V1 markers remain for compatibility.
The nested `check` path retains its existing journal/descriptor behavior because
the supervised system operation owns that journal.

This is source support, **not an external-file migration**. Installing the app
does not overwrite the tool baseline. Unknown external helpers still stop. Before
touching installed maintenance, compare exact old bytes and review a preservation-
only migration of the existing entry/helper; do not invoke Install/Repair/tools,
change the maintenance schedule or relabel old code with a marker.

## Native driver contract and exact selection

`linux_install::app_only_native::pinned_app_only_upgrade` is compiled only into
tests and ignored by default. It also requires all three explicit environment
values below, UID 0, a root-trusted canonical UUID directory, exact reviewed
pin-file/artifact digests, its own pinned executable path, actual Mint installed
identity, exact baseline installed bytes, observable timer state, unpaused policy,
no existing recovery receipt and successful V2 preparation. Missing prerequisites
stop without installing or repairing a baseline.

After a separately reviewed root deployment under
`/var/lib/sde-app-only-validation/<UUID>` and after all actual pins are filled,
the exact test selection is:

```text
sudo /usr/bin/env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/root LC_ALL=C \
  SDE_RUN_APP_ONLY_NATIVE=unpublished-linux-app-only-core-fixture \
  SDE_APP_ONLY_FIXTURE_DIR=/var/lib/sde-app-only-validation/<UUID> \
  SDE_APP_ONLY_PINS_SHA256=<reviewed-pins.json-sha256> \
  /var/lib/sde-app-only-validation/<UUID>/native-tests \
  --exact linux_install::app_only_native::pinned_app_only_upgrade \
  --ignored --nocapture --test-threads=1
```

This is a command template, not a filled spare-host execution packet. It does
not deploy polkit or touch authentication. Review baseline-install effects,
any preservation-only V2 migration, unpause/restoration, ownership/inode/hash
journal, evidence bounds and removal plan before requesting their execution.
If the existing spare has newer SDE or meaningful recovery state, stop and adapt
the artifact/fixture plan; do not uninstall/downgrade/delete evidence to pass.

The driver uses existing test-only authenticated discovery/staging, proves the
production key rejects that fixture, and then invokes the actual native backend
through the shared app-only core under caller-retained O/A/S. S blocks install;
A blocks new admission; no lease is dropped/reacquired around the core. The real
suspend-aware boot clock limits precommit to 15 minutes/2 minutes. Real APT is
never timed out/killed. Postchecks verify installed/activated engine identity;
other package versions, tool-baseline files, pause bytes, service/timer bytes and
timer activation must remain unchanged. No development-tool callback runs.

It preserves staged fixture/recovery and any uncertainty rather than cleaning
real intent. After success, production recovery verification will reject that
test-key receipt. A reviewed closeout is therefore required before using the host
as a production updater again. It creates **no native capability receipt**.
GUI-crash independence, cross-user ACLs, full-worker supervision, unknown package
descendants, restricted-startup dialogs and actual GUI exit remain separate
native/desktop obligations; this shared-core fixture cannot certify them.

## Evidence and finite stopping rule

Focused local QA: 65 ordinary updater tests passed; two native tests ignored
(ACL and the new package driver). All-target updater Clippy/Rustfmt passed.
Four archive/diagnostic tests, 11 workflow boundaries, nine CI-scope tests,
ten broker mocks and twelve package-hook mocks passed. Three pure Python
admission-ordering checks passed; nine protected Python checks require the
existing disposable root CI job and were skipped locally. DEB tests construct
tiny temporary archives only; they never install them. Earlier UI/desktop/browser
evidence is reused because those sources are unchanged.

Do not claim a stable release until native proof and owner UAT pass. Conversely,
after relevant checks pass, do not reopen unrelated protocol research, optional
infrastructure or whole-suite repetition without a concrete failure. Each native
failure gets one diagnosis/fix and an affected-case rerun; uncertainty preserves
the barrier and requires review rather than repeated installation attempts.
