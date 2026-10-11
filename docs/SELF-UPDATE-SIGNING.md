# SDE release signing and recovery

Issue #36 implements the trust format in `SELF-UPDATE-ARCHITECTURE.md`.
The `updater` Rust crate uses maintained Minisign 0.10 with hashed Ed25519
signatures. It is a shared library plus a release verifier CLI for Windows and
Linux. Packaging it into the privileged host belongs to #39/#40; discovery and
protected downloads belong to #37. It does not install anything or promote releases.

## Release contract

Each candidate contains the existing two native installer filenames and
`SHA256SUMS.txt`, plus `sde-update.json` and `sde-update.json.minisig`.
Metadata schema 1 binds the official repository, canonical stable semantic
version/tag, stable intent, minimum engine/schema 1, and exactly these platforms:

| Platform | Installer |
| --- | --- |
| `windows-x86_64` | `Skyview-Dev-Setup-Windows-x64.exe` |
| `linux-amd64` | `Skyview-Dev-Setup-LinuxMint-amd64.deb` |

Each entry binds filename, byte length, and lowercase SHA-256. Metadata is limited
to 64 KiB; signature to 8 KiB; each installer to 512 MiB. Unknown fields, schemas,
platforms, incomplete metadata, legacy signatures, identity mismatches, missing
files, and invalid hashes fail closed. Signature verification happens on the exact
bytes before interpreting JSON. Only authentication creates an
`AuthenticatedManifest`, which is required for installer verification.

The public key is compiled from `updater/keys/release.pub`. There is no runtime
key, environment, or download override. Test keys are ephemeral and confined to
unit tests; they cannot be selected by a production verifier. A verifier without a
valid pinned key refuses authentication and signing.

The verifier assumes its caller provides an administrator-protected directory and
holds it protected until installation. It does not establish ownership/ACLs,
resolve network redirects, acquire installation locks, or inspect the package
version itself; those are #37/#38/#39/#40 responsibilities. The release pipeline
checks the tag against all application build versions, checks Windows installer
version on Windows, and checks DEB package name/version/architecture before signing.

CLI from repository root:

```
cargo run --locked --manifest-path updater/Cargo.toml -- create dist v1.2.2
cargo run --locked --manifest-path updater/Cargo.toml -- sign dist v1.2.2
cargo run --locked --manifest-path updater/Cargo.toml -- verify dist v1.2.2
```

`create` hashes release build inputs; it provides no authentication. `sign` needs
`SDE_UPDATE_SIGNING_KEY` (complete encrypted Minisign key file) and
`SDE_UPDATE_SIGNING_PASSWORD`. It emits only the detached signature, verifies it
against the pinned key, and suppresses secret-bearing diagnostics. `verify`
authenticates metadata and checks both installers. The library exposes equivalent
platform-specific verification for downstream native engines.

## Protected signing and candidate acceptance

The existing release job now needs successful repository, native installer, and
Windows/Linux trust checks. It uses the `sde-release-signing` GitHub environment.
As configured for this repository, that environment:

- Requires approval from `rdpollard` before secrets become available.
- Disallows administrator bypass of that approval.
- Allows only tags `v1.1.*`/`v1.2.*` and branches
  `release/v1.1.*`/`release/v1.2.*`.
- Holds `SDE_UPDATE_SIGNING_KEY` and `SDE_UPDATE_SIGNING_PASSWORD` as environment
  secrets, never repository source or downloadable artifacts.

Self-review is allowed so the sole owner can approve their own release run.
Approval is a human action: inspect the workflow source, commit, artifact inputs,
and requested version before approving. Environment configuration is repository
administration state, not something YAML creates or protects automatically.
Keep its reviewer and ref restrictions in place when extending version families.

Secrets are scoped to the signing step, which does not write key files. Signing
or verification failure stops before GitHub release creation. The publication step
always uses `--prerelease` and publishes the signature with the installers.
It does not replace assets in an existing release. Never patch or re-sign assets
of an accepted stable release; publish a new version instead.

**Signing approval is not stable-promotion approval.** Candidates carry signed
stable-intent metadata but remain GitHub prereleases. #37 must exclude drafts,
prereleases, noncanonical tags, and versions not newer than the installed app.
A signed manifest alone does not grant automatic eligibility. The owner must
explicitly accept and promote the candidate after UAT. No release is created or
promoted as part of this implementation.

Minisign update authentication is separate from Windows Authenticode executable
signing. This work adds no Windows code-signing certificate or SmartScreen claim.

## Owner recovery backup and initial provisioning

A dedicated encrypted key was generated for this project on 2026-10-11.
The recovery copy is on the owner's persistent computer, outside Git and the
Codex temporary/project workspace:

`/home/ryan/.local/share/skyview-robotics/release-signing-backup/`

The directory is owner-only (0700); `release.key`, `release.passphrase`, public
key, and recovery instructions are owner-only (0600). The saved encrypted key was
restored and used to sign and verify a disposable message before GitHub secrets
were provisioned. Only the public key enters the repository. GitHub does not
provide a readable recovery copy of Actions secrets.

**Owner follow-up:** copy `release.key` and `release.pub` to offline encrypted
storage under your control, and place the passphrase in your password manager
separately. The local recovery copy is durable across Codex sessions but cannot
survive loss of this computer by itself. Do not paste either secret into chat or
upload the backup to an issue/PR. Keep the protected local copy until you have
verified the off-device backup. Use the included `BACKUP-README.txt`.

For a future replacement key, use official Minisign `minisign -G` on a trusted
owner computer, or the `owner_key_setup` example with an existing owner-only
password file and a fresh protected directory (set restrictive permissions first).
The utility refuses to overwrite key files and recovery-tests the encrypted copy.
Do not generate production keys on public CI runners. Upload encrypted key and
password through the environment Secrets UI or `gh secret set` reading directly
from protected files; do not put secret values on command lines or print them.

## Rotation, loss, or compromise

Normal rollover needs a release authenticated by the old key that installs a
verifier trusting the new key. Current schema/implementation trusts one key;
coordinated rollover needs a reviewed transitional dual-key implementation before
changing signing secrets. Do not change the pinned key and secret independently:
old installations will reject new signatures. Retain encrypted historical key
backups until the fleet has migrated and recovery retention has ended.

If the signing secret is lost but an owner backup remains, recover into the same
protected environment, restore both secrets, and verify a candidate against the
existing public key before publishing. Do not rotate solely because Actions
cannot display its stored secret.

If all private copies are lost, an already installed single-key verifier cannot
trust a replacement signer automatically. Ship a new bootstrap installer through
the normal administrator-approved installation path. Document the migration;
never disable signature validation to bypass the loss.

If compromise is suspected, pause automatic installation, disable the signing
environment, and remove its secrets while preserving incident evidence. Review
published releases and protected workflow changes. Old trust must be considered
unsafe; use an administrator-approved bootstrap with new trust, then explicitly
accept new candidates. Revoking a GitHub secret alone does not revoke signatures
already made with the compromised key. Emergency migration and fleet pause/status
integration belong to #41/#43.

## Verification

`cargo test --locked --manifest-path updater/Cargo.toml` runs on Windows and Linux.
It covers exact-byte modification, altered trusted comments, wrong keys, missing
signatures, altered/truncated/missing/renamed installers, candidate tag mismatch,
unsupported platform/schema/engine, incomplete fields, invalid identities, limits,
and rejection of ephemeral fixture keys by the production key.
Linux also tests both directions against the official Minisign CLI, including
rejection of valid legacy-format signatures. Real signing environment approvals
and stable promotions remain human-controlled operations, not CI test shortcuts.

References: [Minisign format and owner commands](https://jedisct1.github.io/minisign/),
[maintained Rust implementation](https://github.com/jedisct1/rust-minisign),
[GitHub environment protections](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).
