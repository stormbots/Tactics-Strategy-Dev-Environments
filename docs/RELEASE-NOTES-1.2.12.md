# SDE 1.2.12 — Windows launcher and taskbar icon candidate

Testing prerelease for Windows 11 x64 and Linux Mint Cinnamon amd64.

Windows now installs a versioned copy of the reviewed rounded ICO and updates
owned Start-menu and existing desktop shortcuts to reference it, including
silent upgrades. The running window also sets its large taskbar icon directly
from its embedded resource. This addresses the old square icon retained by the
Windows Shell after an executable replacement at the same path.

The supplied SVG, generated artwork and Linux icon assets remain unchanged.
The owner accepted the Mint Cinnamon icon on v1.2.11; only the Windows icon
finding remains for focused desktop UAT. Earlier accepted theme, zoom,
accessibility and validation checks do not require a full repeat.

The application/activated maintenance engine is 1.2.12; the development-tool
baseline remains 1.2.1. Existing update pause policy, schedule and preferences
are retained. Published v1.2.11 and earlier assets remain immutable. Automated
1.2.11 -> 1.2.12 upgrade checks use unpublished same-source fixtures; they do
not replace testing an upgrade from the actual installed published version.

Download all five assets together and authenticate with the trusted installed
pinned verifier before installation. Follow the
[Windows installation and focused UAT sheet](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/main/docs/UI-UAT-1.2.12.md).
Candidate publication is separate from stable promotion and fleet rollout.
