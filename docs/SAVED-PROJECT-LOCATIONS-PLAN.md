# Saved workspace and project locations: implementation contract

Part of [#161](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161).
The owner approved this workflow. Implementation is authorized; this contract
requires no new design-approval pause. Source reviewed: main
`4f3aa40d22fec43a2a88059417c18c8ee29d524d`, whose
[full exact-main CI passed](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/45709011070).
This reference adds no application action, saved preference or native permission.

## The problem to solve together

Current [validation](../linux/Validate-SkyviewStudentDev.sh),
[Open workspace](../installer/src-tauri/src/main.rs), and
[profile setup](../linux/Configure-SkyviewUser.sh) use independent default paths.
Windows [repository setup](../windows/chocolatey/tools/Setup-SkyviewRepositories.ps1)
also defaults to `C:\Development`. A Save button alone would leave some consumers
using the old location and could permit a second clone there.

The [working-folder verification](PROJECT-LOCATIONS.md) now recognizes real Git
repositories and linked worktrees. That establishes folder structure, not course-
project identity, persistence, or a shared location used by all operations.

The completed flow must let the student review an existing folder, explicitly
save its reference, automatically check the result, and keep the finding in place
until the relevant evidence resolves it. Save changes only the reference.

## One reference, several consumers

Use one bounded, versioned, per-user location record. All consumers must resolve
it through the same contract; avoid independent preferences in the browser,
validation scripts and native Open handler.

The record distinguishes a workspace container from individual project bindings.
An existing workspace need not itself be a Git repository. A project binding
identifies one configured project and one explicitly selected working folder.
It must not merge different clones or infer a binding from a familiar name.

Persist only schema version, revision, explicit paths/binding IDs and the bounded
identity information needed to recognize changed selections. Do not store
credentials, commands, scripts or a package-maintenance grant. Define the concrete
format and storage path once and test agreement between Windows/Mint/native
consumers before exposing Save. Bound record size, binding count and path lengths;
reject malformed UTF-8, duplicate/unknown fields and unsupported schema versions.

| Reference state | Required behavior |
| --- | --- |
| No saved record | Use the current platform default as the proposed workspace; inspect it before claiming it is available. |
| Saved record and current folder verified | Use that explicit reference in validation and Open; later approved setup must use its reviewed snapshot. |
| Saved folder unavailable or drive disconnected | Keep the saved reference visible and offer access review/reselection. Do not fall back to the old default. |
| Record unreadable, malformed or unsupported | Report an unavailable reference. Do not replace the record, clear the finding or clone at a default. |
| Selected folder or record changed since review | Require a fresh review before Save or a modifying operation uses the changed context. |
| Another clone or fork found | Keep it distinct and show its evidence. Never rewrite remotes or silently replace a saved binding. |

A location record supplies data only. It cannot certify required tools, retire an
incident, acknowledge an interruption, enable maintenance or authorize package
changes. Invalid or missing identity evidence is uncertainty, not permission.

## Review, Save and follow-up

1. **Choose an existing folder.** Accept a literal folder path using a bounded,
   ordinary-user inspector. Do not create the folder, search drives or run code
   from it. Reuse the fixed Git working-folder query where a project is expected.
2. **Show the result.** Distinguish an available workspace container, a verified
   working folder, uncertain project identity, unavailable access and unsupported
   layout. Show which configured project would use the selected folder.
3. **Save explicitly.** Recheck the folder and reference revision. Save only when
   the reviewed selection is still current. Write only the private user record;
   no move, clone, fetch, pull, branch switch, remote rewrite or trust change.
4. **Recheck automatically.** Resolve the saved reference and run the applicable
   permitted project checks. Update the existing finding and summary in place.
   A successful preference write alone cannot become a readiness pass.
5. **Keep failures in the flow.** A failed Save preserves the previous record.
   A failed follow-up retains the saved choice but keeps its unresolved finding
   visible, with retry, access review or support-report actions as appropriate.

Cancel and review-only navigation preserve the previous reference and project
bytes. Prevent duplicate submissions and reject late results after navigation or
a newer selection. Keep keyboard focus at the current result, with no return-and-
scroll cycle. A changed folder needs fresh review rather than automatic retry.

Native Save must validate its arguments and current context independently of the
page. Use an atomic private-file replacement with compare-and-swap revision
semantics, appropriate user ownership/permissions, and checks against links or
foreign replacement. Define recovery for an interrupted write. Keep the old
record on refusal or failure; a malformed existing record is not an empty record.
Cross-process changes and stale UI tickets must be covered explicitly.

## Version 1 format foundation

The native [format module](../coordination/src/project_references.rs) defines the
bounded data format below. It is a parser only. It reads no files, writes no
preferences and adds no application command or completed Save flow. Connecting
the user-owned file reader, every consumer and the reviewed operation snapshot
remains required before Save becomes available.

```json
{
  "schema": 1,
  "platform": "linux",
  "revision": 1,
  "workspace": "/home/student/Development",
  "projects": [
    {
      "projectId": "robot-code",
      "path": "/media/student/School/robot"
    }
  ]
}
```

Every field is required. The platform is `linux` or `windows` and must match the
consumer. The revision is an integer from 1 through 9007199254740991, so readers
using JavaScript numbers can represent it exactly. Later persistence must compare
the expected revision and handle exhaustion without wrapping or silently resetting.
The complete UTF-8 JSON record is at most 16384 bytes. Unknown fields, duplicate
keys, unsupported schemas, invalid UTF-8 and trailing JSON are errors.

`projects` holds at most 64 bindings; an empty list is valid. Each `projectId` is
unique and case-sensitive, with 1–128 ASCII letters, digits, underscores, hyphens
or dots. Its first character cannot be a dot. A binding uses an explicit path;
it need not live inside the workspace. Names, nearby folders and common Git
metadata do not imply that two bindings or clones are interchangeable.

Paths contain at most 4096 UTF-8 bytes and use an explicit absolute spelling.
Linux uses `/`; Windows uses a local drive and backslashes, such as
`C:\Development`. Reject relative paths, empty or dot segments, trailing
separators except filesystem roots, controls, bidirectional override/isolate
characters and `|`. Windows also rejects UNC/device forms, forward slashes,
alternate-stream colons, wildcard characters, ordinary DOS device names and
trailing dots/spaces. Supported Unicode and spaces remain literal data. There
is no shell expansion, home expansion, path normalization or filesystem lookup.

A decoded record is only syntactically acceptable data. It is not proof of
existence, access, ownership, current folder identity, Git trust, project identity
or readiness. In particular, an unmounted drive can have a valid saved path.
Keep that reference visible after an access failure; never decode failure into an
empty/default record. Secure file ownership, link defenses, atomic persistence,
fresh inspection and shared-consumer integration are separate implementation
requirements. The public decoded types expose read-only accessors, and callers
cannot deserialize directly into them to skip validation.

## Read-only file observation foundation

The [file observer](../coordination/src/project_references/store.rs) reads only
`references.json` inside an existing directory supplied by trusted native code.
The caller must choose its fixed per-account application storage directory;
never accept this directory from IPC, project content or a saved preference.
This foundation is not yet connected to application commands or script consumers.
It adds no Save, provisioning, repair or default-location behavior.

The public observer requires an ordinary account. It distinguishes:

| Observation | Meaning |
| --- | --- |
| Absent | The fixed record was not found inside a checked, existing private directory. |
| Saved | Bounded bytes decoded and the private file/directory identities remained consistent during observation. |
| Unavailable | Storage, ownership, permissions, links, file identity or record contents could not be accepted. |

An absent storage directory is **Unavailable** in this low-level API. It is not
proof of an absent record. The future fixed-path resolver must handle a genuine
first-use directory separately, without treating denied access or malformed state
as permission to use an old default. Observing creates no directory, marker or
lock file, changes no ACL or mode, and never repairs a rejected record.

Linux requires ordinary effective/real user identity, account-owned private
storage and a singly linked regular record. Ancestors must be plain directories
owned by this account or root; other writable ancestors are refused except
root-owned sticky directories. The file is opened without following its final
link and in nonblocking mode, so a FIFO cannot stall the reader. Windows requires
a non-administrator token, current-account ownership, a checked DACL, ordinary
directories without reparse points and a singly linked record. Its handles deny
concurrent write/delete sharing. Trusted system/administrator access is retained;
foreign read/write grants on private storage are refused. Ancestor checks retain
the system servicing identity without granting it ownership of a user's record.

Reads stop at the record byte bound. Invalid, oversized, linked or unavailable
records remain unresolved and unchanged. File and directory object identities
are checked again before Saved is returned. A local SHA-256 fingerprint includes
those identities and the exact record bytes; replacing a record with identical
bytes/revision must produce different comparison evidence. This is observation
data, not a Save ticket, project inspection or operation permit. Future consumers
must read again, check folder identity and retain their own fresh native gates.
These checks do not provide an atomic filesystem snapshot or an execution lock.

Tests exercise absent versus unavailable storage, preserved disconnected paths,
malformed/oversized bytes, private permissions, hard links, replacement records
and directories, Linux links/FIFOs and root-only foreign ownership, and Windows
junction/ACL handling. The production ordinary-account guard is tested separately
from low-level file fixtures on privileged CI hosts. Actual Windows execution
and supported Mint ownership remain required native evidence. A managed local
workspace with foreign-owned namespace ancestors is intentionally refused; do
not relax the production owner checks to make such a fixture pass. Secure writes,
shared consumers and the connected UI remain open implementation work.

## Identity and requirement policy

Extend read-only observations only as needed to show bounded repository/worktree
identity and remote evidence. Keep fork remotes, credentials and configuration
bytes intact. A common Git directory can identify related worktrees; it does not
make independent clones interchangeable. An unfamiliar origin alone is not
permission to change it or evidence that the folder is the wrong project.

Do not infer requiredness from a saved location. Keep existing configured-project
requirements until their explicit optional/required classification is implemented
and tested. Missing optional projects must become information; an explicit course
requirement still needs its own truthful finding. Project availability must not
be presented as broken Python, Node or editor functionality.

A required project that is confirmed absent needs a separate, fully scoped
clone/setup review. Selecting or saving a location does not approve that work.

## Native boundaries and operation snapshots

Add only narrow, main-window commands for inspection and explicit user-reference
Save. Register and test their arguments/permissions and use the existing
[read sequence](../installer/src/nativeReadQueue.ts) for serialized observations.
A queue ticket, saved revision or inspection fingerprint is never a native
execution permit. Read/Save must use the ordinary account, without elevation.

Open workspace must resolve the current reference and open a freshly verified
folder with the existing fixed operating-system handler. Paths remain literal
data, with no shell evaluation or project-supplied executable. Keep editor
selection and project-location identities separate.

Before operation approval, include the reviewed workspace/project reference in
its context. Invalidate an old review when a selection changes. Native execution
must freeze and recheck that context at the appropriate boundary, including
before the profile phase writes or clones. A changed record or replaced directory
must stop the affected work safely; do not read a new path silently after approval.
Retain normal journals, permission prompts and fresh native safety checks.

Keep selected paths out of privileged command/script sources. Machine package
work must not obtain authority over a user-selected project folder. The profile
phase remains ordinary-user work. Legacy setup must either honor the same safe
reference contract or refuse the affected project step with useful guidance;
it cannot ignore a saved choice and clone at the old default. Audit every entry
point rather than updating only the GUI.

Provisioning must preserve existing work, Git metadata, branches and settings.
Check each intended destination immediately before a separately approved clone;
an existing or changed destination is not permission to overwrite it. Scheduled
machine maintenance gains no user-project or location-selection authority.

## Implementation order and completion evidence

1. **Reference contract and readers.** Implement bounded state parsing,
   unavailable/default distinctions and shared consumers. Add no Save UI while
   another consumer can still silently use the old default.
2. **Inspection and explicit Save.** Connect normal-user review, native argument
   checks, atomic persistence, revision conflicts, cancellation and in-place
   permitted follow-up. Preserve unavailable evidence after failed collection.
3. **Open and operation integration.** Bind Open and reviewed normal-user profile
   work to the same reference. Verify changed-selection and destination races;
   remove default-clone fallbacks. Keep unsupported legacy actions unavailable.
4. **Project identity and requirement findings.** Cover forks, multiple clones,
   worktrees, explicit course requirements and optional projects without changing
   tool readiness from unrelated project availability.

These are verifiable engineering increments, not permission to publish an
incomplete workflow as finished. Keep #161 open until all accepted criteria and
exact-candidate owner UAT are satisfied.

Required tests include absent/default/saved/malformed records; missing and denied
access; disconnected drives; changed records and folder identity; spaces and
supported Unicode paths; worktrees, forks and multiple clones; no project byte or
remote changes on review/Save/Cancel; failed write and failed follow-up; concurrent
Save and stale results; native argument/window restrictions; and actual Windows/
Mint standard-user validation, Open and approved setup using the saved location.
Show no duplicate clone or overwrite at the previous default.

Implementation retains full Windows/Mint, trust, integrity, acceptance and exact-
main gates. Human signing, authenticated exact-candidate owner UAT and separately
authorized promotion remain required. The Windows filename-extension exception
in the [preservation audit](MAINTENANCE-RESTORATION-SCOPE.md#windows-file-name-visibility-exception)
also remains in force. This reference itself needs only lightweight documentation
checks; it starts no new native or release validation.
