# Installed Mint spare: physical-console disabled-entry gate

**Reviewed proposal; not authorization to execute.** The owner explicitly requires
a reviewed plan and specific authorization before repeating the stopped attempt.
Use only after that approval. The historical clean-host bootstrap packet is not
appropriate for this installed host.

The latest owner-supplied session is UID 1000, seat0, lightdm, X11, display :0,
active, Remote=no. The preceding c11 session was XRDP with no seat. In polkit
124, locality requires a seat; Active=yes/Remote=no alone do not select the
action's active authorization rule. The XRDP report predicts denial under
implicit-any=no. The original attempt's session was not captured, so its cause
remains unproven. Cinnamon implements its own agent; do not launch another agent
or repair the root accessibility-bus warning.

Source references: [polkit session locality](https://github.com/polkit-org/polkit/blob/124/src/polkitbackend/polkitbackendsessionmonitor-systemd.c),
[authorization selection](https://github.com/polkit-org/polkit/blob/124/src/polkitbackend/polkitbackendinteractiveauthority.c),
[Cinnamon agent](https://github.com/linuxmint/cinnamon/blob/6.6.0/js/ui/polkitAuthenticationAgent.js).
These explain the targeted diagnosis; they do not attest the registered agent's
actual object owner or prove native authentication safety.

## Scope for specific approval

On `ryan-ThinkCentre-M910q` only, from ryan's physical Cinnamon console:

1. Read-only preflight verifies the reported session, Mint 22.3, installed SDE
   1.2.9, no app-only request namespace/recovery barriers, and absent fixed files
   and action. Existing helper, tool, service/timer, pause, updater and recovery
   file identities are recorded. Unknown ownership, links or existing targets stop.
2. One sudo preparation creates a new root-private 0700 journal under
   `/var/tmp/sde-mint-disabled-broker-<UUID>` and **only these two installed files**:

   | File | Owner/mode | SHA-256 |
   | --- | --- | --- |
   | `/usr/local/libexec/skyview-app-update-request` | root:root 0755 | `122bef3156eb03e258c1693af3eb177e082a0c84db9fe2d927ed8b039d581b10` |
   | `/usr/share/polkit-1/actions/org.skyviewrobotics.sde.app-update.policy` | root:root 0644 | `50900fa7d3f8f92c8646c8ae821b6ed6ac9356639abed17c9091b7ee17b25187` |

   The broker remains source-disabled. The installed policy's product-facing
   dialog text says “Prepare the latest eligible SDE update and install after all
   SDE windows close, including unexpected closure. No immediate cancellation.
   Tools and maintenance settings remain unchanged.” In this diagnostic the
   reviewed broker exits before any update request or installation.
3. As ryan, invoke the fixed pkexec command once and visibly cancel its GUI prompt.
   Expected exit 126. Then, only if that observation passed, invoke it once more
   and approve the GUI prompt. Expected exit 78, empty stdout, stderr JSON
   `{"schemaVersion":1,"status":"disabled","uid":1000}`. Exit codes alone
   never establish that a GUI prompt appeared. Never put a password in a terminal
   command or output supplied to Codex.
4. One sudo cleanup checks both recorded files' owners, modes, links, device,
   inode, timestamps and hashes before removing either. It removes policy then
   broker, verifies action removal and protected-state preservation, and retains
   the private journal and unelevated source/evidence directory. No recursive
   deletion, removal of older evidence, or adoption of unknown bytes.

No bootstrap, agent launch, settings change, package operation, external V2 helper
migration, worker, capability, feature enablement or release. This proves only
the disabled OS-authorized entry boundary. ACL/full-worker/package/protected-close
gates remain open even on success.

Bounds: one deployment, at most two prompts, one removal, 15 minutes from prepare,
120 seconds per prompt, 16 KiB per observation and 1 MiB total evidence. Stop at
the first unexpected result; do not retry, repair, change hashes, or kill uncertain
pkexec/broker processes. If a call has not returned after 120 seconds, leave it
alone and report it from a separate terminal. Do not clean up while that call is
pending. If a returned call failed, skip the next authorization and perform only
the checked cleanup below. Partial preparation/cleanup, unknown files or baseline
drift require review; never force cleanup. The root journal path prints before
installed-file mutation to permit diagnosis of partial failure.

## Operator commands, after approval only

Run in Bash as ryan, without sudo for the surrounding shell. Keep this terminal
open. These commands deliberately retain the new source/evidence directory.
Preparation/cleanup require sudo; the two GUI requests do not.

```bash
umask 077
sde_gate_dir=$(mktemp -d /tmp/sde-mint-console.XXXXXXXX)
sde_gate_ref=bca5aa473496fc97baf153477b5adfb721fa971e
sde_gate_base="https://raw.githubusercontent.com/stormbots/Tactics-Strategy-Dev-Environments/$sde_gate_ref"
curl -fsSL --max-time 30 "$sde_gate_base/tests/mint_disabled_broker_gate.py" -o "$sde_gate_dir/gate.py" &&
curl -fsSL --max-time 30 "$sde_gate_base/linux/self-update/app_request.py" -o "$sde_gate_dir/app_request.py" &&
curl -fsSL --max-time 30 "$sde_gate_base/linux/polkit/org.skyviewrobotics.sde.app-update.policy" -o "$sde_gate_dir/app-update.policy" &&
printf '%s  %s\n' \
  c40c3d0b77402fc527e6bad9f1bb38948b02a7e77eaec5bf925e531aa2030f0a "$sde_gate_dir/gate.py" \
  122bef3156eb03e258c1693af3eb177e082a0c84db9fe2d927ed8b039d581b10 "$sde_gate_dir/app_request.py" \
  50900fa7d3f8f92c8646c8ae821b6ed6ac9356639abed17c9091b7ee17b25187 "$sde_gate_dir/app-update.policy" | sha256sum --check
```

All three must report OK; otherwise stop. Define this root loader once. It hashes
the bounded, unlinked helper **again as root**, then compiles exactly those bytes;
it never checks one user-writable file and subsequently executes a different read.
For cleanup it requires the known root-private journal namespace and owner.

```bash
sde_gate_root() {
  sudo /usr/bin/python3 -I - "$@" <<'PY'
import hashlib, os, re, stat, sys
from pathlib import Path
mode = sys.argv[1]
if mode not in ('prepare', 'cleanup') or len(sys.argv) != (4 if mode == 'prepare' else 3):
    raise SystemExit('STOP: unexpected operation')
directory = Path(sys.argv[2])
owner = 1000 if mode == 'prepare' else 0
if mode == 'cleanup' and not re.fullmatch(r'/var/tmp/sde-mint-disabled-broker-[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}', str(directory)):
    raise SystemExit('STOP: unexpected journal namespace')
m = directory.lstat()
if not stat.S_ISDIR(m.st_mode) or m.st_uid != owner or stat.S_IMODE(m.st_mode) != 0o700:
    raise SystemExit('STOP: unexpected directory identity')
fd = os.open(directory / 'gate.py', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
with os.fdopen(fd, 'rb') as stream:
    m = os.fstat(stream.fileno())
    if not stat.S_ISREG(m.st_mode) or m.st_uid != owner or m.st_mode & 0o022 or m.st_nlink != 1 or m.st_size > 65536:
        raise SystemExit('STOP: unexpected helper identity')
    data = stream.read(65537)
if hashlib.sha256(data).hexdigest() != 'c40c3d0b77402fc527e6bad9f1bb38948b02a7e77eaec5bf925e531aa2030f0a':
    raise SystemExit('STOP: helper hash mismatch')
sys.argv = ['gate.py', *sys.argv[1:]]
exec(compile(data, '<reviewed disabled broker gate>', 'exec'),
     {'__name__': '__main__', '_VERIFIED_SOURCE': data})
PY
}
sde_gate_root prepare "$sde_gate_dir" "$XDG_SESSION_ID" > "$sde_gate_dir/prepared.json"
```

Preparation must return successfully. If it reports STOP or fails, stop here and
paste its output plus the printed journal path; do not run pkexec or force cleanup.
On success, display and retain its exact returned journal path:

```bash
cat "$sde_gate_dir/prepared.json"
sde_gate_journal=$(/usr/bin/python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["journal"])' "$sde_gate_dir/prepared.json")
```

Run this **once** and click Cancel in the GUI dialog. Do not enter credentials:

```bash
/usr/bin/pkexec --disable-internal-agent /usr/local/libexec/skyview-app-update-request \
  > "$sde_gate_dir/cancel.stdout" 2> "$sde_gate_dir/cancel.stderr"
sde_gate_cancel_rc=$?
printf 'cancel exit=%s\n' "$sde_gate_cancel_rc"
```

Only if a GUI dialog appeared, you cancelled it, and exit was 126, run the next
command **once**, approving that GUI dialog. Otherwise skip to checked cleanup
after the first call has returned:

```bash
/usr/bin/pkexec --disable-internal-agent /usr/local/libexec/skyview-app-update-request \
  > "$sde_gate_dir/approve.stdout" 2> "$sde_gate_dir/approve.stderr"
sde_gate_approve_rc=$?
printf 'approved exit=%s\n' "$sde_gate_approve_rc"
/usr/bin/python3 -I - "$sde_gate_dir" "$sde_gate_approve_rc" <<'PY'
import json, sys
from pathlib import Path
d = Path(sys.argv[1])
if any(p.stat().st_size > 16384 for p in d.glob('*.std*')):
    raise SystemExit('STOP: observation bound exceeded')
if sys.argv[2] != '78' or (d/'approve.stdout').read_bytes():
    raise SystemExit('STOP: unexpected approved result')
value = json.loads((d/'approve.stderr').read_text())
if value != {'schemaVersion': 1, 'status': 'disabled', 'uid': 1000}:
    raise SystemExit('STOP: unexpected disabled response')
print(json.dumps(value))
PY
```

After both calls have returned (or after the first returned failure), perform
checked cleanup once:

```bash
sde_gate_root cleanup "$sde_gate_journal"
```

Expected JSON: status cleaned, installedFilesRemoved 2, preservationUnchanged
true, journalRetained set. A refusal means retain/report evidence, not manual rm.
Paste prepare JSON, cancellation/approval exit statuses, the validated disabled
JSON (if reached), cleanup JSON/errors, and whether each GUI prompt appeared.
Do not paste credentials or unrelated system logs. Diagnostic completion, cleanup
correctness and the remaining authentication-safety limits are reported separately.

## Focused QA and next engineering step

13 temporary-filesystem tests exercise success, target collision, source drift,
symlinks, byte/inode changes, partial journals, untrusted paths, preserved-state
drift, forbidden commands and XRDP refusal. They never run sudo/polkit/native SDE.
Workflow boundaries, CI scope and fixture-artifact checks remain passing. Existing
application evidence is reused; adding this packet does not justify a replacement
installer build. New helper commands are fixed read-only probes; actual pkexec is
kept as two visible manual operations in this packet.

After this gate, review the installed old helper bytes and preservation-only V2
migration alongside private recovery state, then authorize the minimum 1.2.9 to
1.2.10 fixture operation. Complete full-worker/capability and close/recovery gates
before producing an enabled Linux UAT build. Windows packaging, optional hosts,
VMs, media and releases remain paused until needed. Success at this gate is not
Mint UAT completion or permission to publish stable.
