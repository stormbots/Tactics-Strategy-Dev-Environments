# Development Environment Maintenance

This document describes maintenance procedures shared across the Windows and
Linux student development environments.

## Goals

- Keep development laptops reasonably consistent.
- Minimize configuration drift between machines.
- Keep security-sensitive applications current.
- Avoid unnecessary upgrades to runtime-sensitive tools.
- Make rebuilds and replacement laptops straightforward.

## Update Strategy

### Viewing the installed schedule

In GUI version 1.2.0, choose **Schedule** to inspect maintenance as a normal user. Refresh reads the actual task/timer and service history; it does not run or modify maintenance. Times are displayed in the machine's local time. Missing schedules, access errors, and unavailable execution history are shown explicitly. **Open maintenance log folder** opens the system maintenance logs, separately from the GUI's per-operation logs.

Windows uses `\Skyview Robotics - Dev Tool Updates` as SYSTEM, normally Sunday at 03:00 with missed-run catch-up. Linux uses `skyview-student-dev-update.timer` and `skyview-student-dev-update.service`, normally Sunday at 03:00 with up to one hour of randomized delay and persistent catch-up. The page reads actual settings, so changes made outside the GUI are reflected there. Neither schedule upgrades the setup app itself. User editor extensions are refreshed by GUI Install, Repair, and Update in the student's profile, rather than by the system maintenance account.

Overview counts tool updates separately from failed validation checks. Installed/available versions are retained as structured records. **Ready** means validation passed; unavailable or skipped package checks are identified rather than interpreted as proof of no updates. Linux availability uses existing APT metadata (the GUI does not refresh it during validation) and the JetBrains stable PyCharm API. Windows uses Chocolatey metadata and resolves pinned Node 24 releases independently. Chrome uses native Google Update on Windows and managed APT updates on Linux.

### Automatically updated

The following should generally remain current through their normal update
mechanisms:

- Windows Update
- Google Chrome
- Mozilla Firefox
- Other security-sensitive desktop applications

### Managed through provisioning scripts

The platform-specific provisioning and maintenance scripts are responsible for
keeping the standard development toolset consistent.

Examples include:

- Git
- GitHub CLI
- Python 3.14.x and pip
- VSCodium
- DBeaver
- PowerShell or shell utilities
- Editor extensions

### Runtime version policy

Runtime-sensitive development tools should not automatically move to a new
major or minor runtime family without mentor review.

Current standards:

- **Node.js:** constrained to 24.x. GUI and weekly managed updates include safe
  patch releases in that family; major-version changes require mentor review.
- **Python:** standardized on Python 3.14. Patch/security releases within the
  Python 3.14 family may update normally, but moving to Python 3.15 or later
  requires an explicit baseline change.

Runtime-family changes should be tested against current team projects before
being added to the standard environment.

Python projects should use project-local virtual environments (`.venv`) rather
than global project dependencies. Skyview AWS Lambda Python projects should
normally target the `python3.14` Lambda runtime unless the project explicitly
requires another version.

## Repository Policy

The Git repository contains:

- Provisioning scripts
- Configuration files
- Validation scripts
- Maintenance scripts
- Documentation

Generated installation archives and binary packages should be published as
GitHub Release assets rather than committed to the repository.

## Platform Releases

The shared graphical app publishes both native installers in each shared release.
Version 1.2.1 is stable following the project owner's acceptance on 2026-10-08. It includes the UI features above and fixes the Linux Node version selector. Earlier releases remain available as fallbacks.

Examples:

- `v1.1.5` (previous shared stable release)
- `v1.2.0` (shared GUI with Schedule/About, mentor testing)
- `v1.2.1` (current stable; Schedule/About and Linux broken-pipe correction)
- `windows-v1.0.1` (stable fallback)
- `linux-v1.0.1` (stable fallback)

## Rebuilding a Laptop

A replacement or freshly installed laptop should be brought to the standard
state by:

1. Installing the supported operating system.
2. Applying operating-system updates.
3. Opening the graphical installer and clicking Install.
4. Reviewing its automatic validation results.
5. Using optional configured repositories as needed.
6. Verifying browser, Git, editor, Node.js, Python, and database-client operation.

Platform-specific instructions are maintained in:

- `windows/README.md`
- `linux/README.md`
