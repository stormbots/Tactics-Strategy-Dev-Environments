# Read-only retained incident observations

Branch: `codex/recovery-incident-history`. Bounded T7/T8 increment accepted at
`9f0fd91256af72538f98a1aca1708130fb25ad36` in
[Build 41240901801](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41240901801).
All 165 frontend/97 browser tests, Windows trust 128/128, root Linux 142/142,
native Tauri Windows 99/99 and Linux 96/96 passed. Actual standard-user archive
enumeration/private read denial and both signed-upgrade paths passed. This accepts
read-only discovery; subsequent view deletion has its own separate contract.
Base #135: `c069922659eac695f33ff4eff6682d4cf506832a`, accepted in
[Build 41234049333](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41234049333).

## Acceptance criteria

- Add report-independent observations under the existing Recovery destination,
  separate from optional saved report copies and current Recovery findings.
  Paginate machine/account sources independently with canonical incident UUIDs,
  bounded 25-entry UI requests and explicit refresh. No polling or automatic replay.
- Account history reads only existing private evidence/decision directories. It
  works after report save failure/deletion or replacement/removal of the current
  GUI journal. Missing storage stays absent; unsafe/unreadable state is not empty.
- Validate the one retained generation's receipt, preserved bytes/hash, context,
  incident identity, report reference and timestamps. Never expose native generation,
  raw evidence/hash, log paths or restart keys over IPC. A missing receipt is unknown;
  corruption is unavailable; multiple generations sharing one UUID are explicitly
  ambiguous, not merged or selected by directory order/newest timestamp.
- Machine history validates existing protected archive directories under the
  operation gate and enumerates only canonical IDs from known archive filenames.
  It does not open private journals or receipts or publish new protected metadata.
  Even an apparently committed filename yields **acknowledgment unknown**: filenames
  can arise from partial publication and cannot establish private evidence validity.
- Histories report continuation/completion as not recorded. An observation, report
  reference or acknowledgment record is never an execution permit. Each source
  can be unavailable without hiding the other source's successful observations.
- All history operations in this increment are read-only. Do not remove views,
  evidence, receipts, minimum decisions or journals; do not loosen ACLs or change
  mutation/restart gates. Explicit view-deletion semantics remain a later increment.

## Source boundaries

`recovery::history` only acquires the existing gate, validates the archive and
enumerates sanitized filenames. Directory-entry metadata avoids opening private
Windows receipt files merely to get attributes. Existing public-directory access
is sufficient in principle; the required real standard-account CI probe must prove
this on both platforms. Private file contents remain unreadable. Partial archive
publication, a directory where a regular entry is expected, or an active gate is
never silently certified acknowledged, healthy or complete.

`recovery_user::history` reads minimum state separate from `recovery-reports`.
Ordinary UUID paging has no retention cap or purge. Within a single incident,
generation inspection remains bounded at 128 entries; excess becomes unavailable,
not silently truncated or declared unacknowledged. Multiple generations are shown
as ambiguous even if one context/receipt looks familiar. Unexpected root entries
produce an explicit coverage warning without exposing filenames or deleting them.
This is observation of retained records, not proof that all historical work was
recorded by older SDE versions, nor certification of same-account tamper resistance.

The fixed `list_recovery_incidents` command accepts only typed source, cursor and
bounded limit. No input path, HTML, token or mutation argument is accepted. Report
availability is not consulted. The UI offers refresh/load-more only, and explicitly
separates opaque machine candidates, observed account decisions and unknown/
ambiguous/unavailable findings. Current incidents remain in the findings above.

Exit 75's existing native message now says that current safety checks deferred
setup, rather than asserting another operation is definitely running. The exit
code and all guard behavior are unchanged; unknown activity is not labeled active.

## Validation and required CI

Local: 165 frontend tests and production TypeScript/Vite build passed, including
separate-source errors, unknown machine versus observed account status, ambiguous
generation display, paging and no startup replay. Five new account-history tests
actually executed: read-only absence, survival without a report/current journal,
missing report references, corruption/duplicate generations, partial publication
and paging/coverage warnings. Linux and Windows-GNU coordinator clippy with
warnings denied, 32 backend contracts, four permission checks and whitespace pass.

Two new protected archive tests require native root/administrator context: partial
publication never implies acknowledgment, gates stay held/blocking, canonical
paging deduplicates filenames without reading private contents or purging them,
and wrong entry types fail closed. The unprivileged local fixture returns early;
its harness counts are not native proof. Existing standard-user production-storage
CI now prepares an **earlier synthetic** archive and a distinct current private
journal generation. The actual unprivileged account must enumerate the older ID,
be denied both private journal/receipt reads, submit only current intent and obtain
stable restart provenance. Only disposable fixture files are recreated/renamed.
Do not waive this native boundary if a platform rejects directory enumeration.

Browsers are known absent locally. Existing CI installs Chromium/WebKit and must
run the full suite plus four synthetic light/dark 640/1140px incident-history
read-only/axe/reflow cases. All inherited Windows/Linux native/trust, feasibility,
installed/manual/read-only, scheduled/application and signed SYSTEM/actual Mint
22.3 gates remain required. Real reboot/dialog behavior remains owner UAT later.

## Remaining work

Next: explicit history-view deletion that preserves minimum operational authority,
malformed/unavailable-source self-service completeness, and final end-to-end
execution/UX audit before consolidation and focused UAT preparation. Account
generation-overflow lookup and privately verifiable historical machine disposition
are not solved by this read-only list; do not misrepresent unknown as verified.
No new permission prompt, mentor service requirement, automatic native repair,
protected archive deletion or evidence-clearing bypass is introduced here.

Owner Windows interruption evidence and Mint v1.2.18 Install/Validate 35/0/0 are
preserved. No partial-stack merge, signing, release/publication, automation or UAT.
