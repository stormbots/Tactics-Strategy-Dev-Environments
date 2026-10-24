# v1.2.16 execution ledger — October 24, 2026

The owner explicitly selected a fresh v1.2.16 with #102 and the student-accessible
Inline setting toggle. v1.2.15 remains an immutable prerelease with both desktop
UAT passes [recorded](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/100#issuecomment-6390739972).
Stable remains v1.2.14. The target tag was unused when engineering began;
publication must recheck this.

## Completed acceptance reused

- #59 [owner-approved closeout](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/59#issuecomment-6390763131):
  historical affected Windows 11 v1.2.6 clean pass plus current native fixtures;
  additional affected-PC/private-ACL inventories unreported and explicitly
  accepted as a limit. Issue closed October 24. Fresh Windows v1.2.15 UAT is not
  relabeled as legacy migration evidence.
- v1.2.15's [full/native/authentication receipt](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/100#issuecomment-6320616136)
  and owner Windows/Mint desktop passes remain valid within their actual scope.
- Prior accepted five-zoom/sidebar/readiness/discovery UAT remains reused; focused
  regressions cover changed Schedule UI and policy behavior.

## New engineering and verification scope

- Windows/Mint installers enable updates after fresh install and any upgrade,
  including paused policy. No maintenance, task enablement or provisioning starts.
- The Schedule Inline toggle passes one boolean to a fixed native operation,
  with current policy distinct from historical results. No administrator prompt.
- Only the root/admin-owned fixed-schema pause file permits student data writes.
  Root/private stores retain their guards. Bounds, schema/type/unknown/duplicate
  checks, regular-file/single-link checks and trusted owners/parents fail closed.
  Concurrent/interrupted preference saves may be unreadable; the UI reports an
  unconfirmed setting and requires refresh instead of promising the old value.
- Administrator CLI pause/resume remains; separate ordinary-user fixed verbs
  exercise the GUI's same operation in native tests. New installs reset pauses.
- Required tests include native fresh/default and paused/enabled upgrade paths,
  real standard-user toggle/protected-state denial, strict preference decoding,
  unit saving/error/history tests, Chromium/WebKit keyboard/accessibility/compact
  UI plus existing native trust, package failure, migration and sidebar checks.
- Candidate recipe builds unpublished same-source 1.2.15/1.2.16 fixtures; the
  rebuilt starting installer is not the accepted published v1.2.15 bytes. Only
  v1.2.16 may be signed/published by the protected candidate job.

## Gates still to execute

PR review and required full/native checks; merged exact-main checks; exact input
receipt and human signing approval; five-asset publication/authentication;
focused v1.2.16 Windows/Mint owner UAT; explicit stable approval and public-link
verification. Do not transfer v1.2.15 signing/UAT approval to changed bytes.

#43 and milestone 2 remain open for a named-device/action/policy/window pilot or
explicit owner-approved scope disposition. Retained actual v1.2.14 Windows/Mint
devices remain reserved for live #99 after an accepted newer stable exists.
No Codex device policy/installation/maintenance operations or fleet changes have
been performed. #101 and shelved #72/#73 remain outside this release.
