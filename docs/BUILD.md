# Build and release

## Development

Use Node 24, a current stable Rust toolchain, and Tauri 2 platform prerequisites. Windows native builds need Visual Studio C++ build tools/Windows SDK. Linux native builds need GTK 3, WebKitGTK 4.1, librsvg, the Ayatana appindicator development package and patchelf. The Windows and Ubuntu CI jobs install/provide these prerequisites.

From `installer`: `npm ci`, `npm test`, `npm run build`. For the explicitly simulated browser design preview, use `npm run dev`. Native development uses `npm run tauri dev`; validation reads the source backend, but privileged setup is intentionally rejected in debug builds. Provision using an installed release package.

For browser verification, install Playwright Chromium with `npx playwright install chromium`, then `npm run test:browser`. Rust tests run from `installer/src-tauri` using `cargo test --locked`. Python backend checks use `python tests/backend_contracts.py`. Windows read-only parser/validator checks use `tests/Test-BackendContracts.ps1`. ShellCheck runs on `linux/*.sh` and `linux/lib/*.sh`; actionlint verifies workflows.

Before a Windows release build, run `choco pack windows/chocolatey/skyview-student-dev.nuspec --outputdirectory windows` from the repository root. This packages the existing backend and dependencies, not a separate JavaScript installer. Build from `installer` with `npm run tauri build -- --bundles nsis` on Windows, or `--bundles deb` on Linux. Tauri's bundle resource mapping places each existing backend under `backend/windows` and `backend/linux` in the protected installed application resource directory.

## Automated packaging

`build-dev-setup.yml` runs for PRs, main and `v1.1.*` tags. Frontend type/build/tests, axe/browser tests, npm audit, Bash analysis, PowerShell parsing/analysis, backend safety contracts, Actions validation and native Rust tests gate release publication. A matrix builds Windows NSIS and Linux DEB in parallel with the other checks; each artifact is nonempty, uniquely identified and SHA-256 checked. Linux additionally inspects DEB metadata and expected executable/backend paths.

Each successful run exposes `Skyview-Dev-Setup-Windows-x64.exe` and `Skyview-Dev-Setup-LinuxMint-amd64.deb` as workflow artifacts, each with its checksum. UI screenshots are uploaded separately. Dependency lockfiles are checked in. Rebuilding a commit reproduces dependency selection; third-party vendor package availability and byte-for-byte NSIS reproducibility are not guaranteed.

A `v1.1.*` or `v1.2.*` tag, or the corresponding `release/v1.1.*` / `release/v1.2.*` branch, triggers release publication. Only after both packages and all checks pass, the branch pipeline creates the version tag at its exact commit (or verifies an existing tag matches). The release job downloads both outputs, checks each recorded hash, combines `SHA256SUMS.txt`, and verifies it again before calling `gh release create --verify-tag --prerelease`. It never overwrites an existing release. Shared releases contain both native installers; the old `windows-v1.0.1` and `linux-v1.0.1` releases remain immutable fallbacks. The legacy Linux workflow checks out its original immutable tag and exits without modifying an existing release.

Patch releases use the same gate on `release/v1.1.*` branches: the tag comes from the branch suffix and notes from `docs/RELEASE-NOTES-<version>.md`. For example, `release/v1.1.1` creates a new immutable `v1.1.1` release after both native builds and all checks pass. Existing tags/assets are never replaced.

New releases are initially published for mentor testing. Complete `ACCEPTANCE-TEST.md` and merge the reviewed implementation before marking a tested release stable. Promote the existing GitHub release by clearing its prerelease status and marking it latest, then update its notes with acceptance evidence. Preserve the existing tag, installers and checksum asset so users receive the exact binaries that passed acceptance; do not rerun release publication or replace assets for promotion. Version 1.2.1 was accepted for stable publication by the project owner on 2026-10-08; see `ACCEPTANCE-1.2.1.md`. Version 1.1.5's earlier fresh-machine acceptance remains historical evidence in `ACCEPTANCE-TEST.md`.

Windows releases ship unsigned by project decision, confirmed on 2026-10-07. Windows code signing is excluded from release requirements and follow-up work.
