# Architecture and security

## Shared application

`installer/src` contains the shared React UI, typed event parser, operation reducer, and native bridge. `installer/src-tauri` contains the Rust process manager and platform-specific elevation bridge. Browser development previews are explicitly marked as simulated; installed Tauri apps use real system inspection and provisioning.

The GUI exposes three registered commands: inspect the system, run an enumerated operation, and open an enumerated destination. There is no arbitrary shell, argument, executable, URL, or privileged path API. Tauri's application manifest includes these commands so capabilities restrict them to the local main window. No shell/filesystem plugin or remote capability is granted. A CSP restricts remote content.

The backend remains one provisioning implementation per platform. Linux splits existing profile work into `Configure-SkyviewUser.sh`; Windows uses `Configure-SkyviewUser.ps1`. Command-line setup still uses the same scripts. The GUI calls the system phase, then the unelevated user phase, then validation. Repair repeats the same idempotent path (Windows forces the Skyview configuration package to rerun). Update calls the existing managed-package updater and refreshes user configuration/extensions before validation.

## Elevation

**Windows:** NSIS installs the application and resources per-machine under Program Files. A hidden, fixed PowerShell launcher calls `Start-Process -Verb RunAs` on this same installed executable with `--privileged`, a fixed operation, and a UUID. UAC provides the administrative prompt. The helper validates the operation and UUID, rejects development builds and executables outside Program Files, resolves backend resources relative to itself, and invokes only the known system script. It never accepts a frontend script path or student home directory. Its sanitized output is written to a newly created UUID log in the administrator-protected installation directory; the GUI reads that log while the helper runs. The UUID controls only the log filename. Profile work runs afterward in the original, unelevated account, including when another administrator supplies UAC credentials. Execution policy bypass is limited to individual child processes; no machine/user policy is changed. The Windows backend continues to target `C:\Development` as in v1.0.1; newly created workspaces grant local Users Modify rights.

**Linux:** the app invokes `/usr/bin/pkexec` on its own executable with the same narrow helper arguments. The desktop PolicyKit agent provides the graphical authentication dialog. The helper requires root, validates the packaged executable/resources are root-owned and not group/world-writable or symbolic links, clears the inherited environment, and uses a system-only PATH. It runs the same Bash installer with `--system-only` or the managed updater. No student home/user arguments are accepted by the privileged interface. The original GUI account then runs profile configuration and validation with its normal HOME. The entire webview remains unelevated. Mint's existing PolicyKit agent is required; no custom permissive policy is installed.

Both privileged platforms clear inherited user environment variables and use system-only executable/module search paths. Windows system provisioning uses a neutral system profile for installer caches, while the original GUI account owns subsequent profile work. Native byte output is decoded safely and protected-log polling waits for complete lines, including UTF-8 split across writes.

The app prevents normal window closure while a process is active. There is no mid-package cancellation button because forcibly terminating a package transaction can damage the package database. If the process or machine crashes, preserve the logs and use Repair; package-manager recovery may require mentor help.

## Protocol, logs, and failures

Events are UTF-8, one line each: `SKYVIEW_EVENT|type|key|description`. Supported types are `progress`, `phase`, `status`, `validation`, `warning`, `error`, `summary`, and `update`. The description can contain additional pipe characters. Percentages must be 0–100. Validation keys are PASS/WARNING/FAIL/INFO, and the summary key is the failure count. Human-readable native output is shown as logs but never interpreted as installation state.

Both the Rust and TypeScript parsers validate the protocol. Successful completion requires process exit zero, at least one graphical check, an explicit zero-failure validator summary, and no FAIL result. A failed system or profile process stops before later phases. Retry repeats the chosen operation; existing repositories and editor settings are preserved. Authentication rejection is distinguished from package/validation failure. Child errors include stage and exit code, and original diagnostics remain in Show details.

Rust sanitizes credential-bearing HTTP URLs, GitHub token patterns, and common token/password/API-key assignments before emitting or persisting GUI logs. The log includes raw native output after this sanitization. No authentication token or actual Git identity is printed by the validators. Redaction is best-effort for unforeseen vendor formats; mentors should review logs before sharing them.

GUI logs use Tauri's per-user log directory, displayed verbatim in Show details. Windows elevated helper logs live under `<Program Files application directory>\operation-logs`. Existing platform logs remain under `C:\ProgramData\SkyviewRobotics\Logs`, the Chocolatey log directory, and `/var/log/skyview-robotics/student-dev`. Mentors can remove old logs after diagnostics; the installer does not delete student data.

## Validation and maintenance

The Windows `Test-SkyviewStudentDev.ps1` entry point calls the canonical `Validate-SkyviewEnvironment.ps1`, which now emits explicit results and a meaningful exit code. It checks runtime families, applications, extension IDs from the existing list, workspace, Git defaults, registry configuration and scheduled maintenance. Linux's existing validator now emits the same protocol and uses the invoking user's home rather than another account's stored metadata. Both treat Git identity/authentication as information. Version strings are included where CLI or executable metadata supports them.

Windows maintenance uses the same `Update-SkyviewTools.ps1` path as GUI Update, including the existing `Update-Node24.ps1` implementation and `python314` package. Chrome continues using Google's native updater as in v1.0.1. Linux installs only the named managed package set, selects Node 24 explicitly, and updates JetBrains PyCharm with SHA-256 verification; it never invokes a full distribution upgrade. Weekly maintenance is system-only. Editor extension refresh occurs in the user's GUI Update/Repair operation, avoiding unattended launches of user-configured editors by a privileged service.

Strict-JSON Linux settings merge defaults before existing values; JSONC is preserved. Windows existing settings are preserved. Optional repository folder names are restricted to single safe directory components, existing non-repository folders are skipped, and clones run in user context with terminal prompting disabled. No identity or GitHub authentication is provisioned.

## Accessibility

The supplied Skyview logo is used unchanged; installer icons are resized derivatives. Navy/silver colors follow the logo. Text and status controls have AA contrast checked with axe in Chromium. Status always includes words and icons. Semantic headings, labeled navigation, result tables, native details/checkbox/progress elements, focus indicators, a skip link, progress announcements, completion focus, reduced-motion support, responsive layout, and keyboard interaction are included. Automated axe checks run for desktop/mobile overview, completion, and validation. Manual screen-reader, keyboard, scaling and native webview checks remain in the acceptance test.
