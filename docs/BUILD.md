# Build and release

## Development

Use Node 24, a current stable Rust toolchain, and Tauri 2 platform prerequisites. Windows native builds need Visual Studio C++ build tools/Windows SDK. Linux native builds need GTK 3, WebKitGTK 4.1, librsvg, the Ayatana appindicator development package and patchelf. The Windows and Ubuntu CI jobs install/provide these prerequisites.

From `installer`: `npm ci`, `npm test`, `npm run build`. For the explicitly simulated browser design preview, use `npm run dev`. Native development uses `npm run tauri dev`; validation reads the source backend, but privileged setup is intentionally rejected in debug builds. Provision using an installed release package.

For browser verification, install Playwright Chromium with `npx playwright install chromium`, then `npm run test:browser`. Rust tests run from `installer/src-tauri` using `cargo test --locked`. Python backend checks use `python tests/backend_contracts.py`. Windows read-only parser/validator checks use `tests/Test-BackendContracts.ps1`. ShellCheck runs on `linux/*.sh` and `linux/lib/*.sh`; actionlint verifies workflows.

Before a Windows release build, run `choco pack windows/chocolatey/skyview-student-dev.nuspec --outputdirectory windows` from the repository root. This packages the existing backend and dependencies, not a separate JavaScript installer. Build from `installer` with `npm run tauri build -- --bundles nsis` on Windows, or `--bundles deb` on Linux. Tauri's bundle resource mapping places each existing backend under `backend/windows` and `backend/linux` in the protected installed application resource directory.

## Automated packaging

`build-dev-setup.yml` runs for PRs, main, implementation branches and `v1.1.*` tags. Frontend type/build/tests, axe/browser tests, npm audit, Bash analysis, PowerShell parsing/analysis, backend safety contracts, Actions validation and native Rust tests gate builds. A matrix builds Windows NSIS and Linux DEB; each artifact is nonempty, uniquely identified and SHA-256 checked. Linux additionally inspects DEB metadata and expected executable/backend paths.

Each successful run exposes `Skyview-Dev-Setup-Windows-x64.exe` and `Skyview-Dev-Setup-LinuxMint-amd64.deb` as workflow artifacts, each with its checksum. UI screenshots are uploaded separately. Dependency lockfiles are checked in. Rebuilding a commit reproduces dependency selection; third-party vendor package availability and byte-for-byte NSIS reproducibility are not guaranteed.

Only a tag triggers release publication. The release job requires both native matrix jobs and all checks, downloads both outputs, checks each recorded hash, combines `SHA256SUMS.txt`, and verifies it again before calling `gh release create --verify-tag --prerelease`. It never overwrites an existing release. A single `v1.1.0` release supersedes independent tags for the shared app; the old `windows-v1.0.1` and `linux-v1.0.1` releases remain immutable fallbacks. The legacy Linux workflow checks out its original immutable tag and exits without modifying an existing release.

The first release is for mentor testing. Complete `ACCEPTANCE-TEST.md` before marking it stable. Code-signing/notarization credentials are not added to the repository; Windows code signing should be configured through protected CI secrets when available.
