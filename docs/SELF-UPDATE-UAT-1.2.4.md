# SDE 1.2.4 correction candidate

This is an unaccepted prerelease for the Linux schedule-history finding from
owner UAT of 1.2.3. Existing 1.2.2/1.2.3 releases remain immutable, and stable
1.2.1 remains unchanged. Application and maintenance engine identify as 1.2.4;
the applied development-tool baseline remains 1.2.1. Production discovery ignores
prereleases. Keep application installation paused during manual testing.

On October 12, both owner PCs completed protected tool maintenance successfully
with SDE installation paused. Windows' Schedule page reported that success.
Mint's app receipt correctly reported the completed attempt, but the schedule
summary showed an older timer trigger and an unavailable result because systemd
no longer supplied service execution timestamps. The journal independently
confirmed the successful Mint attempt. These results do not accept automatic
installation, signed recovery, or classroom rollout.

## Correction

Two root-only systemd hooks persist the latest service start and completion in a
bounded, non-secret, student-readable maintenance-history receipt. Starting an
attempt replaces old success with an incomplete result. The completion hook also
records launcher/startup failures; it does not rely on an older tool receipt.
The read-only Schedule inspector uses this protected record when appropriate,
rejects linked/writable/invalid history, and defers to evidence of a newer service
invocation or timer trigger. Missing history never means success. Unavailable
history no longer claims that the computer restarted.

An application upgrade installs the hooks for an existing coordinated baseline
without changing timer enablement, frequency, random delay, pause policy, or the
existing schema-1 launcher. App-only and legacy uncoordinated installations do
not acquire a weekly task. Historical attempts are not fabricated: run the
existing maintenance service once after upgrading to establish new history.

## Focused owner retest

1. Download the complete five-file 1.2.4 prerelease asset set into its own folder.
   Verify it with the installed pinned worker before launching an installer.
2. Close SDE and wait for native package work to finish. Manually upgrade each
   existing 1.2.3 test PC using the owner UAT procedure, with app updates paused.
   Another baseline Repair is unnecessary on these already migrated test PCs.
3. Confirm About 1.2.4, unchanged project/editor settings, preserved schedule and
   paused policy. Run existing protected maintenance with SDE closed; inspect
   independent tool success and paused app outcome.
4. On Mint, disable/stop and restore the existing timer after maintenance, as in
   the reported reproduction, then reopen SDE and refresh Schedule. The latest
   run and successful result must remain visible even if systemd drops its live
   timestamps. Reboot and refresh to check durability. Restore the timer to its
   originally enabled state and confirm its next run.
5. On Windows, confirm the Schedule page still shows the successful tool result,
   paused app outcome and preserved weekly task. Report any Windows download
   warning separately; Minisign is not Windows Authenticode signing.

CI covers absent timestamps, interrupted/newer attempts, protected-file rejection
and real systemd success followed by failure without running development tools.
Candidate CI tests native Windows and actual Mint userland upgrades through
1.2.4. Booted-laptop UAT remains required. Publish only through the protected
reviewed-main workflow with its `correction` option; it signs and publishes only
new 1.2.4 assets, using earlier versions solely as unpublished CI fixtures.
Signing requires the existing human environment approval. Stable promotion and
application-policy resume require separate explicit owner instructions.
