# SDE 1.2.6 — Windows legacy Logs migration

SDE 1.2.6 is the current stable/latest release for Windows 11 x64 and Linux Mint
Cinnamon 22.x amd64. The owner declared testing complete and authorized promotion
of the existing signed candidate. Its tag and five release assets are unchanged;
no rebuild or re-signing was performed for stable promotion.

The Windows installer now corrects the recognized inherited container-only Users
Write grant on the fixed Logs directory without a separate manual ACL repair.
Every existing log must already pass the original owner/write trust checks.
Writable files, links, unexpected entries/owners/grants and busy writers remain
rejected. Existing logs remain diagnostic evidence, never authenticated status.

Application and maintenance-engine identity is **1.2.6**; the development-tool
baseline remains **1.2.1**. The migration preserves protected log bytes/private
ACLs, baseline, existing schedule settings and application-update policy. An
eligible existing task action moves to the protected maintenance host.
Application installation does not provision tools or start maintenance.

The owner confirmed first-attempt installation without ACL remediation on an
affected Windows 11 laptop. GUI Update/Validate passed, and a controlled SYSTEM
maintenance invocation reported app/engine 1.2.6, baseline 1.2.1, tool exit 0 and
paused application installation. Native Windows/Mint checks and protected signing
and published-asset authentication also passed. Detailed results and evidence
limitations remain in the [acceptance record](ACCEPTANCE-SELF-UPDATE.md).

Download [the existing v1.2.6 assets](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/v1.2.6)
and authenticate the complete folder with the installed pinned verifier before
mentor-led installation. Minisign authentication is separate from Windows
Authenticode signing. Windows installer SHA-256:

```text
15b29e9a3f50787ed05734faf0b480b48825bd88fff349ad944bab72bf2fa690
```

Source/tag: `741f681c0444a8d44d9430a107c80f2fed95b68e`; protected
[candidate build/signing run](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38608215787).
The fixed `logs_migration=true` recipe built application identities in disposable
checkouts; older versions were unpublished fixtures. Do not rebuild or replace
these published assets from the unchanged development build identity.

Stable promotion does not resume any laptop policy. Keep application updates
paused until a separately approved automatic-update/recovery pilot and rollout.
Manual installation does not synthesize automatic-update history or signed
recovery; the existing maintenance task records fresh results when invoked.
Follow the [mentor controls and recovery guide](SELF-UPDATE-MENTOR.md).
