# SDE 1.2.6 — inherited Logs permission migration UAT candidate

This candidate adds the narrow Windows installer migration reviewed in PR #60
at `72813311d62615f3870d40e758824808f214dce7`. An elevated installation can
correct the recognized inherited container-only Users Write grant on the fixed
Logs directory without manual ACL repair, provided every existing log already
passes the original owner/write trust checks. Writable files, links, unexpected
entries/owners/grants and busy writers remain rejected. Existing logs remain
diagnostic evidence, never authenticated status.

Application and maintenance-engine identity is 1.2.6; the development-tool
baseline remains v1.2.1. The installation preserves existing protected log bytes
and private ACLs, baseline, schedule settings and application-update policy.
An eligible existing schedule action moves to the protected maintenance host;
installation does not provision tools or start maintenance.

Build using **Prepare signed self-update UAT pair**, `logs_migration=true`, on
`release/v1.2.uat` at the reviewed merged main commit. Earlier versions built by
this recipe are unpublished upgrade fixtures, not replacements for old assets.
The production pinned-key Minisign manifest authenticates both native installers;
this is separate from Windows Authenticode signing. The protected environment
requires human approval. Publish only the new immutable v1.2.6 prerelease with
`latest=false`; existing releases/tags/assets remain unchanged.

Affected-PC Windows 11 acceptance is **pending**. Use the commit-bound checklist
in [SELF-UPDATE-UAT-1.2.5.md](SELF-UPDATE-UAT-1.2.5.md#affected-pc-windows-11-checklist-for-reviewed-commit-7281331)
and record the actual candidate source/build run and installer SHA-256 before
testing. Require first-attempt installation without manual remediation and
separate preservation, application, scheduled-maintenance and paused-policy
results. Keep broader rollout and application updates paused. Candidate signing
or publication does not approve stable promotion, fleet deployment, automatic
updates or closure of outstanding acceptance conditions.
