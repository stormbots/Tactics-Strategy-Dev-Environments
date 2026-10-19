# Mint native validation: prerequisites and conditional execution scope

Prepared 2026-10-17. PR #73 stays draft and unmerged. This document is a review
packet, not permission to run guest tests or package/build/release workflows.

## Observed evidence

The original head 50f81a0 had passing application checks, Linux/Windows desktop
compilation and trust checks, host inventory, mocked checks, workflow checks and
Windows fixtures. Its Mint fixture job was still running when inspected.

Artifact 12114900317 (`mint-host-preflight`, 601 bytes) exists and was unexpired.
Its download returned HTTP 403 from the storage endpoint, so its bytes were not
inspected. Do not describe that original artifact as reviewed.

Commit 2027415 exposes the same bounded report as a Checks notice, alongside the
artifact. The subsequent read-only probe passed and its actual notice was read
through the GitHub API (check run 117504629655, Actions run 39069720810).
That report is retained in `evidence/ISSUE72-MINT-HOST-OBSERVED.json`.
The report's sourceCommit is the PR **merge** SHA, not the feature-head SHA.
The workflow/code is associated with feature head 2027415; the merge SHA is
06bdcebab4278353b6089641b62291571bbdcbd0.

Observed: Ubuntu 24.04 x86_64; 4 CPUs; 15,264,927,744 bytes available RAM;
92,107,538,432 bytes free disk. Capacity passes. KVM API was unavailable (`null`)
and the required protected QEMU/SSH/GPG tool set failed its combined check. The
report does not distinguish missing KVM hardware/device from device permissions,
or identify individual missing tools; do not invent that diagnosis. Console and
no-host-mount declarations are false. Media, provisioning and guest authorization
remain blocked. A green observation job is not a green VM-readiness gate.

This managed workspace has no /dev/kvm or QEMU executable, no attached host
capability, VPN, configured outbound cloud identity or private TCP destinations.
Downloading official metadata from
https://mirrors.kernel.org/linuxmint/stable/22.3/sha256sum.txt returned HTTP 403.
No alternate route, unsigned checksum, Xfce media, container or TCG substitute was
used. The repository self-hosted-runner inventory API also returned 403 (Resource not
accessible by integration); that prevents discovering an alternate registered
host, not proof that none exists. No guest, credentials, paid host or media image
was created.

## Host preparation decision and stop gate

The ordinary hosted runner is **not yet an established VM host**. Do not merge
#73, change production schedules, chmod a shared KVM device, install a service,
or dispatch the native-package workflow to obtain one.

The next host-only preparation must either diagnose the existing ephemeral
runner's KVM open/ioctl failure and fixed tool paths read-only, or use a separately
configured disposable Ubuntu 24.04 x86_64 KVM host. An alternate host needs access
configured through secure environment settings; no host/account is currently
configured. No paid resource may be assumed provisioned.

Development-tool installation is already authorized in principle, but a concrete
host must exist before selecting/installing its QEMU development components.
Do not treat installation alone as remediation for unavailable hardware/KVM.
Re-run the existing preflight on that host; require API 12 and resource/tool gates.
Keep the host alive through media preparation, guest testing and cleanup: the
short-lived PR inventory runner is not a persistent console endpoint.

## Authenticated media preparation (not completed)

Use exactly linuxmint-22.3-cinnamon-64bit.iso. Retrieve the official signed
sha256sum.txt and sha256sum.txt.gpg plus ISO into a fresh private directory.
Use the repository key tests/fixtures/linuxmint-iso-signing.asc with primary
fingerprint 27DEB15644C6B3CF3BD7D291300F846BA25BAE09. GPG verification must succeed
in a fresh private keyring with automatic retrieval disabled. Require exactly
one Cinnamon entry; freeze its authenticated SHA-256, then stream-hash the full
ISO and require equality before any boot. Do not reuse the existing Xfce pin.

The existing host_preflight.verify_media implements signature, edition, digest
and size checks against supplied files. A checksum authenticated in signed
metadata can supply the explicit pin; an unsigned website checksum cannot.
Freeze the signature/checksum/ISO/key hashes and verification result as evidence.
Recheck immutable ISO bytes at boot. Downloads and private staging are host-side
preparation, not native SDE package tests; none were completed in this step.
Network configuration must permit the official mirror before acquisition here;
there is no supported configuration-change tool available in this session.

## Console and VM preparation contract (not executed)

Use one run-owned private directory (0700), a 30-GiB ext4 guest disk, 2 vCPUs and
4 GiB RAM, QEMU/KVM only, standard QEMU DMI identity and a unique UUID bound to
the approval. Boot authenticated Cinnamon media, then verify Mint 22.3/systemd
in the installed guest. Require a real local Cinnamon login and its real polkit
agent. Do not simulate the session through SSH/Xvfb/environment variables.

Prefer a private Unix-domain graphical console socket in that directory; an SSH
control port, if used, must bind 127.0.0.1 only, with run-owned keys and pinned
host key. No public VNC/SSH, shared clipboard, drag/drop, host directory/9p/virtiofs
mount or reusable personal credentials. Do not assert console/no-mount checks
until inspecting actual QEMU argv, listeners, guest mounts and console login.
A secure controller capable of entering mentor consent without recording the
password must be established before testing. There is no working controller or
VM provisioner yet; this contract is not a claim that one was implemented.

## Exact conditional guest operations to authorize

Only after the host, authenticated media, console and immutable artifact hashes
pass the above gates, authorize the following in fresh disposable guests:

1. Install/configure the guest OS/test development components and create
   sde-student, sde-other and sde-mentor; only mentor has sudo membership.
   Privately generate credentials. No installed SDE, personal data or preexisting
   fixture may be present. This is OS/test provisioning, not an SDE update.
2. Stage the five exact runbook artifacts in root-owned
   /run/sde-mint-validation-<runId> (0700), with approval.json (0600) binding
   run/VM/boot, three actual UIDs, media hash, artifact hashes and bounded expiry.
   Build only the pinned verifier development tool, not an application installer.
3. Run only this named ACL probe on a run-owned guest file:

   cargo test --locked --manifest-path updater/Cargo.toml --lib linux_request::tests::named_reader_acl_roundtrips_on_an_unprivileged_owned_file -- --ignored --exact

4. Use the reviewed driver `prepare --execute --approval <approval> --kind
   production` for the negative production-worker cases; sentinel only for its
   lifecycle cases. Temporarily create exactly:
   /usr/local/libexec/skyview-app-update-request,
   /usr/share/polkit-1/actions/org.skyviewrobotics.sde.app-update.policy,
   /opt/sde-phase3-validation and owned receipts/snapshots under
   /var/lib/skyview-robotics/self-update. Capabilities must remain {}.
   Never provision a valid enablement receipt or a coordination tree.
5. Exercise approved, denied, bad-args, inactive, normal and abrupt cases on fresh
   fixtures through the real desktop polkit boundary. Use `arm-desktop` and
   `capture` exactly as the existing runbook specifies. Inspect ownership,
   reader-vs-other ACL access, protected deferral, replay/claim results and bounded
   attributed audit facts. Do not replace failed session/audit attribution with
   a mock or label it a product-security failure without evidence.
6. Allow the abrupt case to signal only its enrolled GUI surrogate through a
   retained pidfd. Allow termination only of owned bounded read-only probes.
   Never kill a production worker/installer to force progress or cleanup.
7. Export sanitized evidence; invoke `cleanup` only for sealed manifest-owned
   objects after complete identity/child-set checks. On uncertainty stop, preserve
   evidence and discard the VM. Then destroy owned guest disks, keys/accounts,
   staging and host artifacts with separate disposal evidence.

The five approval actions remain root-fixtures, temporary-polkit,
desktop-authorization, owned-sentinel-signals and owned-cleanup. This scope does
not authorize installed app updates, SDE native package operations, task/service
registration, broad ignored tests, W2/W3 experiments, application builds,
package workflows, signing, releases or promotion. Real package-child handling,
positive installation, actual Tauri cgroup teardown and Windows remain later gates.

## Outcome distinctions

Read-only diagnostic completion: Pass on the hosted inventory. VM readiness:
Blocked. Media authentication, guest authentication and native cleanup: NotRun /
unproven. Production readiness: false. Preserve the historical W2h counterexample,
W2i-W2l limited results, W2m immediate cleanup Fail, W2n N1/N2 NotRun and managed
filesystem ACL EOPNOTSUPP. None is repaired by this host inventory.
