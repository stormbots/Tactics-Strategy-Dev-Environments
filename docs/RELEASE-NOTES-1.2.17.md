# SDE 1.2.17 — save the student update preference

Fixes the native permission declaration for **Schedule → SDE application updates
→ Automatic SDE updates**. In v1.2.16, switching off could report an unavailable
setting and return to Enabled on Refresh or reopening because the save command
was not granted to the main window. The fixed command can save the ordinary
student's pause preference without an administrator prompt.

The preference persists through Refresh and reopening. Current policy remains
separate from earlier attempt history. Saving starts no maintenance, downloads,
elevation or installer. Every application installation/upgrade still intentionally
enables updates; students can pause again afterward. Existing administrator CLI
controls remain available.

The applied tool baseline, projects/settings and existing schedule/enabled/custom
timing remain separate and preserved. App-only installation creates no tool
schedule. Only the fixed-schema preference data is student-editable; all existing
code, receipt, trust, eligibility and package protections remain in force.

v1.2.15 Windows/Mint owner acceptance and unaffected v1.2.16 Windows observations
are retained within scope. This fresh candidate requires its own checks, human
signing, independent authentication, focused Windows/Mint owner UAT and separate
stable approval. It is ineligible for automatic stable installation while marked
prerelease. Publication does not authorize a device pilot or fleet expansion.
