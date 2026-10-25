# Skyview Robotics Student Development Environment

Graphical setup and workstation management for the **Bureau of Tactics & Strategy**.
Use the [current stable release](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/latest) for Windows 11 x64 and Linux Mint Cinnamon 22.x amd64. Its release notes describe the accepted changes and supported installers.

The SDE application and the applied development-tool baseline have separate versions. Application upgrades preserve the existing baseline, student settings and maintenance schedule. Starting with v1.2.16, every application installation or upgrade enables automatic SDE updates, including previously paused installations. Students can pause or resume them under **Schedule → SDE application updates → Automatic SDE updates**. Saving this setting does not start maintenance or an installer. Fleet rollout remains a separate owner decision.

## Install with the app

[Download your installer from the current stable release](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/latest). Download **Skyview-Dev-Setup-Windows-x64.exe** for Windows or **Skyview-Dev-Setup-LinuxMint-amd64.deb** for Linux Mint; authenticate the complete five-file release folder using the mentor procedure before installation.

**Windows:** open `Skyview-Dev-Setup-Windows-x64.exe`, approve installation, then launch **Skyview Dev Setup**.

**Linux Mint:** open `Skyview-Dev-Setup-LinuxMint-amd64.deb`, install it using Software Installer, then launch **Skyview Development Environment Setup** from the menu.

In the app, click **Install Development Environment**, approve the system's administrator prompt, and keep the window open until validation finishes. No terminal commands, folder preparation, or manual validation are required.

For an existing managed workstation, follow the [mentor migration and pinned-verification procedure](docs/SELF-UPDATE-ROLLOUT.md) before installing the new app; application installation preserves the applied tool baseline and does not perform tool Repair. From v1.2.16 it intentionally enables app updates; it does not create or enable a tool schedule. Authenticate the complete release asset folder with the installed pinned verifier. Minisign release authentication is separate from Windows Authenticode; Windows installers remain unsigned by project decision. Keep operating-system protections enabled.

The earlier **1.2.1** [both-platform acceptance](docs/ACCEPTANCE-1.2.1.md), including Mint 22.3 validation, remains historical evidence for that version. Published tags/assets are retained unchanged.

## Manage a workstation

| Operation | What it does |
|---|---|
| Install | Installs the managed tools, configures your workspace and editor, enables weekly maintenance, then validates. |
| Repair | Safely reruns provisioning and configuration, restores missing components, then validates. |
| Validate | Checks tools, runtime versions, extensions, configuration, and weekly maintenance without installing packages. |
| Update | Updates managed development tools within the Node 24.x and Python 3.14.x families, then validates. |

The app checks local workstation readiness when it opens, then checks managed-tool updates separately. SDE application releases have their own launch/About check. Unavailable update checks do not invalidate successful local validation. Validation uses explicit **PASS**, **WARNING**, **FAIL**, and **INFORMATION** labels. Git identity and GitHub authentication are optional information; neither is set automatically. A spinner indicates startup validation is working. Operations show **Live details** automatically below progress; **Show details** remains available for initial validation output. **Advanced** can include another update check during validation; Linux uses the latest available local APT metadata.

Tools include Git, GitHub CLI, Node/npm, Python, VSCodium and the repository's standard extension set, PyCharm, DBeaver, Chrome, Firefox, PowerShell 7, OpenSSH, and 7-Zip utilities. Linux's system Python remains untouched and Snap stays disabled. Student repositories and existing editor settings are preserved. Existing strict-JSON Linux settings receive missing defaults; user values win. Windows and JSONC settings remain intact with a warning where defaults cannot safely be merged.

## Stable fallback and advanced manual installation

The original packages remain available:

- [Windows v1.0.1](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/windows-v1.0.1)
- [Linux Mint v1.0.1](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/linux-v1.0.1)

For mentor-led command-line setup, see [Windows manual instructions](windows/README.md) and [Linux manual instructions](linux/README.md). They remain supported. Optional repositories use the existing platform `repositories.csv`; the GUI does not hardcode repository URLs.

## Engineering

One Tauri 2 / React / Vite app orchestrates the existing PowerShell/Chocolatey and Bash/APT backends. See [architecture and security](docs/ARCHITECTURE.md), [build instructions](docs/BUILD.md), [maintenance](docs/maintenance.md), and [acceptance tests](docs/ACCEPTANCE-TEST.md).

GitHub Actions tests the app and backends, builds native NSIS and DEB installers on their respective runners, verifies checksums, and initially publishes a prerelease only when both packages succeed. After manual acceptance and merge review, the tested release is promoted to stable without replacing its tag or assets. Existing platform tags and published fallback assets are preserved.

For administrator pause/resume controls and recovery, see the
[mentor self-update guide](docs/SELF-UPDATE-MENTOR.md). v1.2.16 enables app updates
on installation/upgrade; earlier releases retain their historical pause defaults.
Existing development-tool maintenance remains independent.

Self-update verification evidence and remaining school-laptop UAT: [SELF-UPDATE-EVIDENCE.md](docs/SELF-UPDATE-EVIDENCE.md).

Owner UAT, signed candidate preparation and one-time migration: [SELF-UPDATE-UAT.md](docs/SELF-UPDATE-UAT.md), [SELF-UPDATE-ROLLOUT.md](docs/SELF-UPDATE-ROLLOUT.md), and [release/acceptance status](docs/ACCEPTANCE-SELF-UPDATE.md).
