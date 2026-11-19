# Mint CI repository transport

The exact-main Build for `dc64c1615b9444b8ef36297524bf9c732d2a53b4`
failed twice while the disposable Mint 22.3 container ran its first
`apt-get update`. APT rejected the HTTP Zena `InRelease` response with
`NOSPLIT`. The signed-upgrade test had not started. Windows, common checks
and both update-trust jobs passed; these remain useful historical evidence.

- [Failed Build, attempt 2](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/44456584124/attempts/2)
- [Mint's official repository mirror list](https://linuxmint.com/mirrors.php)
- [Mint's upstream Zena source configuration](https://github.com/linuxmint/mintsources/blob/1bc8878ed6a2cc8186d829a2773614af6bc759df/usr/share/mintsources/zena/mintsources.conf)

Both disposable native fixtures now select `https://fastly.linuxmint.io`,
listed by Mint as its own HTTPS repository mirror. The fixed-path helper
changes only the expected default Zena repository URI. It preserves suites,
components, comments, Ubuntu repositories, file ownership and permissions. Unexpected source
formats fail before any write. A second invocation makes no further change.
The command requires root, GitHub Actions and an actual Mint 22.3 userland.
It has no caller-selected path or endpoint.

The ISO's pinned checksum, ISO signature, archive keyring and ordinary APT
signature verification remain required. No keys are added, no repository is
disabled, and no unsigned fallback is allowed. Production workstation setup
and application behavior are unchanged. Release, acceptance, signing and owner
UAT requirements are unchanged.

The official HTTPS endpoint returned Zena `Release` and `Release.gpg` with
HTTP 200 during investigation. Its `InRelease` returned 404, allowing APT's
normal detached-signature path. Retrieval alone does not authenticate those
bytes. This workspace cannot reach the feed directly, so actual APT
verification and installed upgrade behavior must pass on the native CI runner.
Local tests prove the bounded source transformation and refusal cases only.

This is an executable CI change and requires full PR validation, followed by
full exact-main evidence after protected merge. Earlier successful feature PR
and Windows checks cannot replace that evidence. Do not retry the unchanged
failed main run again.
