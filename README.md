# Skyview Robotics Student Development Environment

Graphical setup and workstation management for the **Bureau of Tactics & Strategy**.
Version **1.2.1** targets Windows 11 x64 and Linux Mint Cinnamon 22.x amd64.

Stable version **1.2.1** adds version-aware updates, a read-only **Schedule** page, and **About**, and corrects a Linux installation/update failure. The project owner accepted all release checklist items on **2026-10-08**. See the [acceptance record](docs/ACCEPTANCE-1.2.1.md) and [release notes](docs/RELEASE-NOTES-1.2.1.md).

## Install with the app

[Download your installer from the 1.2.1 release](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/v1.2.1).

**Windows:** open `Skyview-Dev-Setup-Windows-x64.exe`, approve installation, then launch **Skyview Dev Setup**.

**Linux Mint:** open `Skyview-Dev-Setup-LinuxMint-amd64.deb`, install it using Software Installer, then launch **Skyview Development Environment Setup** from the menu.

In the app, click **Install Development Environment**, approve the system's administrator prompt, and keep the window open until validation finishes. No terminal commands, folder preparation, or manual validation are required.

Version **1.2.1** is [accepted on both platforms](docs/ACCEPTANCE-1.2.1.md) by the project owner's sign-off. The supplied Mint 22.3 logs confirm 35 passed checks after installation and in a separate validation run; automated checks and both native builds also passed. Stable promotion retains the tested installers and their checksums. Windows installers ship unsigned by project decision. Keep operating-system protections enabled.

## Manage a workstation

| Operation | What it does |
|---|---|
| Install | Installs the managed tools, configures your workspace and editor, enables weekly maintenance, then validates. |
| Repair | Safely reruns provisioning and configuration, restores missing components, then validates. |
| Validate | Checks tools, runtime versions, extensions, configuration, and weekly maintenance without installing packages. |
| Update | Updates managed development tools within the Node 24.x and Python 3.14.x families, then validates. |

The app checks your workstation and available managed updates when it opens. Validation uses explicit **PASS**, **WARNING**, **FAIL**, and **INFORMATION** labels. Git identity and GitHub authentication are optional information; neither is set automatically. A spinner indicates startup validation is working. Operations show **Live details** automatically below progress; **Show details** remains available for initial validation output. **Advanced** can include another update check during validation; Linux uses the latest available local APT metadata.

Tools include Git, GitHub CLI, Node/npm, Python, VSCodium and the repository's standard extension set, PyCharm, DBeaver, Chrome, Firefox, PowerShell 7, OpenSSH, and 7-Zip utilities. Linux's system Python remains untouched and Snap stays disabled. Student repositories and existing editor settings are preserved. Existing strict-JSON Linux settings receive missing defaults; user values win. Windows and JSONC settings remain intact with a warning where defaults cannot safely be merged.

## Stable fallback and advanced manual installation

The original packages remain available:

- [Windows v1.0.1](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/windows-v1.0.1)
- [Linux Mint v1.0.1](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/linux-v1.0.1)

For mentor-led command-line setup, see [Windows manual instructions](windows/README.md) and [Linux manual instructions](linux/README.md). They remain supported. Optional repositories use the existing platform `repositories.csv`; the GUI does not hardcode repository URLs.

## Engineering

One Tauri 2 / React / Vite app orchestrates the existing PowerShell/Chocolatey and Bash/APT backends. See [architecture and security](docs/ARCHITECTURE.md), [build instructions](docs/BUILD.md), [maintenance](docs/maintenance.md), and [acceptance tests](docs/ACCEPTANCE-TEST.md).

GitHub Actions tests the app and backends, builds native NSIS and DEB installers on their respective runners, verifies checksums, and initially publishes a prerelease only when both packages succeed. After manual acceptance and merge review, the tested release is promoted to stable without replacing its tag or assets. Existing platform tags and published fallback assets are preserved.
