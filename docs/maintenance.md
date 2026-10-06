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

- **Node.js:** pinned and mentor-controlled. Major-version changes are deliberate.
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

Windows and Linux environments are versioned independently.

Examples:

- `windows-v1.0.0`
- `windows-v1.1.0`
- `linux-v1.0.0`

## Rebuilding a Laptop

A replacement or freshly installed laptop should be brought to the standard
state by:

1. Installing the supported operating system.
2. Applying operating-system updates.
3. Running the current platform provisioning package.
4. Running the platform validation script.
5. Provisioning current team repositories as needed.
6. Verifying browser, Git, editor, Node.js, Python, and database-client operation.

Platform-specific instructions are maintained in:

- `windows/README.md`
- `linux/README.md`
