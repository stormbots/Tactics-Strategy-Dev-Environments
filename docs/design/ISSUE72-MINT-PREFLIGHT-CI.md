# Mint preflight CI boundary

The separate `mint-validation-preflight.yml` workflow runs on PR events without
merging #73. It runs the 28 mocked driver checks in one job and a read-only host
inventory in another. Neither job depends on packaging or release jobs. A future
manual dispatch becomes available only after the workflow is registered on the
default branch; no registration or merge is required for PR-event validation.

Host inventory reads OS/resource/tool facts and queries KVM_GET_API_VERSION only.
It never creates a VM, installs tools, downloads media, elevates, changes device
permissions, runs the guest driver, or authenticates a desktop session. Missing
KVM/tools/resources are reported as blockers, with no fallback or remediation.
An inventory job passing means successful observation, not a usable guest host.
The report always says ready=false: media authentication, provisioning, console
isolation and guest-execution authorization remain separate gates. The ephemeral
GitHub runner declaration is not a guest isolation attestation.

The workflow uses contents:read, no secrets, credential-free checkout, five-minute
job bounds and seven-day JSON artifact retention. PR source runs with the normal
unprivileged pull_request event, never pull_request_target. No arbitrary ref,
command, URL or guest-execution input is accepted.

Local review: 28 mocked checks and 10 static workflow-boundary checks pass.
The embedded inventory program was syntax-checked without running its probes.
Existing application/native-package/release dispatch boundaries are unchanged.
The runbook and historical local evidence remain records of their original checks;
this document records the subsequent CI integration separately.

After publication, inspect automatic checks and the host-preflight artifact.
Stop on probe errors or absent prerequisites; do not install QEMU, alter KVM
access, provision guests or dispatch package/application/release workflows as an
implicit fix. Privileged guest testing still requires specific authorization.
Diagnostic observation, cleanup correctness and authentication safety remain
separate; this workflow proves neither of the latter two.
