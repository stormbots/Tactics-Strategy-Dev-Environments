# Skyview Robotics Student Development Environment

Graphical setup and workstation management for the **Bureau of Tactics & Strategy**.
Version **1.1.3** targets Windows 11 x64 and Linux Mint Cinnamon 22.x amd64.

## Install with the app

Download your installer from the [1.1.3 release](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/v1.1.3).

**Windows:** open `Skyview-Dev-Setup-Windows-x64.exe`, approve installation, then launch **Skyview Dev Setup**.

**Linux Mint:** open `Skyview-Dev-Setup-LinuxMint-amd64.deb`, install it using Software Installer, then launch **Skyview Development Environment Setup** from the menu.

In the app, click **Install Development Environment**, approve the system's administrator prompt, and keep the window open until validation finishes. No terminal commands, folder preparation, or manual validation are required.

The first 1.1.3 release is a **mentor-testing prerelease**. Complete the [laptop acceptance test](docs/ACCEPTANCE-TEST.md) before deploying to the fleet. The application installers are currently unsigned; mentor testing should include Windows publisher/SmartScreen behavior. Signing is a release-operations follow-up, not a reason to disable operating-system protection.

## Manage a workstation

| Operation | What it does |
|---|---|
| Install | Installs the managed tools, configures your workspace and editor, enables weekly maintenance, then validates. |
| Repair | Safely reruns provisioning and configuration, restores missing components, then validates. |
| Validate | Checks tools, runtime versions, extensions, configuration, and weekly maintenance without installing packages. |
| Update | Updates managed development tools within the Node 24.x and Python 3.14.x families, then validates. |

The app checks your workstation and available managed updates when it opens. Validation uses explicit **PASS**, **WARNING**, **FAIL**, and **INFORMATION** labels. Git identity and GitHub authentication are optional information; neither is set automatically. **Show details** displays native output and the saved log location. **Advanced** can include another update check during validation; Linux uses the latest available local APT metadata.

Tools include Git, GitHub CLI, Node/npm, Python, VSCodium and the repository's standard extension set, PyCharm, DBeaver, Chrome, Firefox, PowerShell 7, OpenSSH, and 7-Zip utilities. Linux's system Python remains untouched and Snap stays disabled. Student repositories and existing editor settings are preserved. Existing strict-JSON Linux settings receive missing defaults; user values win. Windows and JSONC settings remain intact with a warning where defaults cannot safely be merged.

## Stable fallback and advanced manual installation

The original packages remain available:

- [Windows v1.0.1](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/windows-v1.0.1)
- [Linux Mint v1.0.1](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/linux-v1.0.1)

For mentor-led command-line setup, see [Windows manual instructions](windows/README.md) and [Linux manual instructions](linux/README.md). They remain supported. Optional repositories use the existing platform `repositories.csv`; the GUI does not hardcode repository URLs.

## Engineering

One Tauri 2 / React / Vite app orchestrates the existing PowerShell/Chocolatey and Bash/APT backends. See [architecture and security](docs/ARCHITECTURE.md), [build instructions](docs/BUILD.md), [maintenance](docs/maintenance.md), and [acceptance tests](docs/ACCEPTANCE-TEST.md).

GitHub Actions tests the app and backends, builds native NSIS and DEB installers on their respective runners, verifies checksums, and publishes a single `v1.1.3` prerelease only when both packages succeed. Existing platform tags and published fallback assets are preserved.
