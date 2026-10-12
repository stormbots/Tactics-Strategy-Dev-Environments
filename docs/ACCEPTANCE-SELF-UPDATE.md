# Self-update acceptance record (#43)

**Owner UAT: Pending. Stable promotion: Not authorized. Classroom resume: Not authorized.**

On 2026-10-12 the owner confirmed the encrypted release key and Bitwarden
passphrase are backed up separately. No secret values or backup paths are recorded
here. USB storage is not required. A later key rotation requires a new recovery
check and owner confirmation.

Signing infrastructure was inspected on 2026-10-12: environment
`sde-release-signing` has reviewer `rdpollard`, administrator bypass disabled, and
both signing secret names configured. Following human environment approval, the
protected candidate workflow successfully signed both distributions, verified them
with the pinned release key, and downloaded and authenticated the published
assets. No signing secrets were exported.

| Evidence | Record |
| --- | --- |
| Native integration before #43 | [PR #51](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/51), exact head c7892980d3e9db0eb5f97be12a04336a938e3666; [successful run](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38254978692) |
| Candidate source commit / protected workflow run | `c186e75925e40101e7e36c3d7dfb845e562a017d` ([PR #52](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/52)); [successful protected candidate run](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38266099258); [successful full main CI](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38265778561) |
| Published signed v1.2.2 / v1.2.3 URLs and manifest hashes | [v1.2.2](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/v1.2.2) and [v1.2.3](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/v1.2.3); both unaccepted prereleases, hashes below |
| Candidate Windows SYSTEM / actual Mint root pair CI | Passed on the candidate source above in run `38266099258`; both Windows installer exits 0; actual `SDE_UAT_PAIR_WINDOWS_OK` and `SDE_UAT_PAIR_MINT_OK` markers recorded. Versions, paused policy/engine, preserved sample files/settings and legacy baseline checked |
| Windows 11 owner tests and school network | Pending |
| Booted Mint owner tests and school network | Pending |
| Findings and retests | Pending |
| Owner acceptance wording / date / exact target | Pending |
| Explicit stable-promotion authorization / date | Pending |
| Representative pilot results / per-laptop resume | Pending |

Use the [UAT checklist](SELF-UPDATE-UAT.md). Record pass/fail/not-applicable and
reason for each row on each OS, identifying the exact assets tested. Codex may
record the owner's supplied results but must not infer or manufacture acceptance.
Existing acceptance of archived 1.2.1 applies only to that historical release.

## Published candidate verification (2026-10-12)

Both tags point to the exact source commit above. Each release contains exactly
the five canonical assets. After publication, Codex independently downloaded
both complete asset sets, rebuilt the verifier from that reviewed source, and
verified both metadata signatures and both platform installer hashes per release.
SHA256SUMS.txt also passed. A modified metadata copy was rejected for each
version. These checks authenticate the distributions; they do not establish
owner laptop acceptance. Latest stable remains historical v1.2.1.

| Version | Asset | SHA-256 |
| --- | --- | --- |
| 1.2.2 | sde-update.json | `8e76f362b250d954ef502255596f0faa9f70b6da05331a80a63e011b1a4a1e0b` |
| 1.2.2 | Skyview-Dev-Setup-Windows-x64.exe | `c6e64e6042a02572f68e6bc86f151db6955a02fa65b56ae68ff1f98fef09de96` |
| 1.2.2 | Skyview-Dev-Setup-LinuxMint-amd64.deb | `a253724ea358675ab7701d9c2a142f341891e5437b8b5e24de63e610eb5ef1d6` |
| 1.2.3 | sde-update.json | `2272e0dbca6f2354d4aab6a25c47ef709dc46869a8d88787cd34eeb32e8483d1` |
| 1.2.3 | Skyview-Dev-Setup-Windows-x64.exe | `8e86072ad942e320fc9ee180109446003e9724a1749a38334c2df8e939e455a3` |
| 1.2.3 | Skyview-Dev-Setup-LinuxMint-amd64.deb | `303f820d79da391eac7fc9e72d0a9c26319e50339e98acb2bb44dd5fb7f78716` |
