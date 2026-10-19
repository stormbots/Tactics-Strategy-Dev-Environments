# SDE 1.2.11 — rounded-square icon UAT candidate

Testing prerelease for Windows 11 x64 and Linux Mint Cinnamon amd64.

Uses the owner's supplied `skyview_logo_rounded_square.svg` for packaged
application icons: a rounded white tile with transparent corners that follows
the desktop background. Preserves the supplied artwork and the existing in-app
logo. This resolves the icon-shape finding from v1.2.10 owner UAT.

The owner reported all v1.2.10 UAT rows Pass on both desktops, then explicitly
requested this icon revision. Themes, zoom and validation guidance are accepted;
#63 and milestone closeout await focused acceptance of the revised icon.

The application/activated maintenance engine is 1.2.11; the development-tool
baseline remains 1.2.1. Installation retains the existing update pause policy,
schedule and user preferences. No theme, zoom or guidance behavior changes.

The native 1.2.10 -> 1.2.11 probe uses unpublished same-source fixtures. Published
v1.2.10 and earlier assets remain unchanged. Owner UAT checks the actual installed
workstation upgrade and native taskbar/dock appearance.

Download all five assets together and authenticate with the trusted installed
pinned verifier before installation. Follow the
[installation and focused icon UAT sheet](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/main/docs/UI-UAT-1.2.11.md).
Candidate publication is separate from stable promotion and fleet rollout.
