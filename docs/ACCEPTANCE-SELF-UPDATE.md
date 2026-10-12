# Self-update acceptance record (#43)

**Owner UAT: Pending. Stable promotion: Not authorized. Classroom resume: Not authorized.**

On 2026-10-12 the owner confirmed the encrypted release key and Bitwarden
passphrase are backed up separately. No secret values or backup paths are recorded
here. USB storage is not required. A later key rotation requires a new recovery
check and owner confirmation.

Signing infrastructure was inspected on 2026-10-12: environment
`sde-release-signing` has reviewer `rdpollard`, administrator bypass disabled, and
both signing secret names configured. Secret presence is not evidence of valid
contents: successful candidate signing and pinned-key verification are still
required. The reviewed pipeline supplies that check without exporting secrets.

| Evidence | Record |
| --- | --- |
| Native integration before #43 | [PR #51](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/51), exact head c7892980d3e9db0eb5f97be12a04336a938e3666; [successful run](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38254978692) |
| Candidate source commit / protected workflow run | Pending |
| Published signed v1.2.2 / v1.2.3 URLs and manifest hashes | Pending |
| Candidate Windows SYSTEM / actual Mint root pair CI | Pending; record exact tested source/run |
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
