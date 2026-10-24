# SDE 1.2.16 — automatic updates and student controls

Every Windows or Linux Mint application installation or upgrade now enables
automatic SDE updates, including installations paused under the earlier UAT
policy. Existing enabled settings stay enabled. Students can use the new
**Schedule → SDE application updates → Automatic SDE updates** toggle to pause
or resume without an administrator prompt. Changes save automatically.

Enabling updates does not start maintenance or an immediate installer. The
existing schedule and enabled/disabled task or timer state remain in control.
Application identity is separate from the applied development-tool baseline;
baseline bytes/version, student projects/preferences, log permissions and custom
schedule settings are preserved. App-only installations still create no tool
schedule. An installer already running is allowed to finish.

The current setting remains separate from the last completed update attempt.
Changing it does not erase a failure, rewrite history or create a success receipt.
Saving/error/unavailable states are explicit. Every subsequent application
installation enables updates again; reapply an intended operational pause after
installation when needed. Administrator pause/resume commands remain available.

Only the fixed-schema pause preference's data is student-editable. Its parent,
trusted engines, signed installers, status/recovery receipts and maintenance
controls remain protected. Release signatures, stable eligibility, active-session
deferral and package-health checks still apply. Beta-channel behavior remains
deferred under #101; this release uses verified stable releases.

v1.2.15's complete authenticated distribution and Windows/Mint owner UAT are
retained unchanged. #59 is closed with the owner's explicit acceptance of the
historical affected Windows 11 v1.2.6 pass plus native fixtures; additional
affected-PC/private-ACL inventories remain an accepted evidence limit.

This candidate requires its own passing checks, protected human signing,
independent authentication, focused desktop UAT and exact stable-promotion
approval. It remains ineligible for automatic stable installation while marked
prerelease. #43's automatic-update pilot and #99's retained v1.2.14 live discovery
remain separate; publication does not authorize fleet expansion.
