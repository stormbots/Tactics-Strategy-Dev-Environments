# Temporary spare-Mint runner: prepared, not activated

This packet does not register/start a runner, change GitHub settings, run guest
validation or authorize host modifications. PR #73 remains draft/unmerged.
The template is deliberately outside .github/workflows: it cannot run as-is.

## Verified facts and remaining administration gate

Repository API reports stormbots/Tactics-Strategy-Dev-Environments is **public**,
organization-owned, default branch main. The integration has repository admin
access but org runner-group and repository runner inventory APIs both return
403 Resource not accessible by integration. Repository administration does not
establish permission to manage organization runners. The organization's current
plan, group settings, environment protections and branch rules are **unverified**.

GitHub documents group-level selected repositories and, where available, selected
workflows. The enterprise-cloud documentation describes the workflow restriction;
its availability must be confirmed in this organization, not inferred from labels
or a plan name. If Selected workflows cannot be configured and verified, STOP.
Do not register a repository runner, use Default group, allow all workflows,
upgrade the plan, or treat labels/environment approval as equivalent isolation.
A separately reviewed private control repository is an alternative, not enabled
by this packet. Public-repository runner exposure deserves explicit owner review.

The host's Mint 22.3, 4 CPUs, ~15 GiB RAM, ~199 GiB free disk, KVM API 12 and
QEMU 8.2.2 are user-reported evidence, not a remote observation by Codex.
Mint is not explicitly listed in GitHub's supported host OS list; its Ubuntu
base does not itself establish support. Native runner dependency/connectivity
checks remain necessary before claiming compatibility.

## Organization administrator: exact settings to review/apply later

Visit https://github.com/organizations/stormbots/settings/actions/runner-groups
(or organization Settings > Actions > Runner groups). Requires an organization
owner or delegated runner-management permission. No settings were changed here.

1. Create **sde-mint-isolated**, not Default. Repository access: **Selected
   repositories**, only **Tactics-Strategy-Dev-Environments**. This public repo
   requires the explicit allow-public-repositories setting; do not enable access
   for any other repository.
2. Workflow access: **Selected workflows**, exactly:

   stormbots/Tactics-Strategy-Dev-Environments/.github/workflows/mint-host-inventory.yml@refs/heads/main

   GitHub requires non-reusable workflows to be pinned to a branch, not an
   invented SHA allowlist entry. The workflow itself gates its run SHA against
   MINT_RUNNER_APPROVED_SHA, in addition to the group restriction.
3. Protect main against direct/force pushes/deletion and require reviewed PRs
   and code-owner review for this workflow; include administrators/no routine
   bypass. A trusted admin can still change policy: this is an explicit trust
   boundary, not protection against organization-owner compromise.
4. In repository Settings > Environments, create **mint-host-access**. Required
   reviewers: the owner/mentor approving host access. Enable **Prevent
   self-review**, restrict deployments to **Selected branches: main**, and disable
   administrator bypass where available. No secrets. If these protections cannot
   be enforced, STOP. An independent authorized actor must dispatch; a sole
   reviewer cannot approve their own dispatch when self-review is prevented.
5. Review/install mint-host-inventory.yml.template as
   .github/workflows/mint-host-inventory.yml through a **separate infrastructure
   PR**. Do not merge #73 for runner access. Registering a workflow on default
   main is required for manual dispatch; a feature-branch template is not ready
   for dispatch. No infrastructure PR was created/merged in this preparation.
6. After that reviewed commit is on main, set repository Actions variable
   **MINT_RUNNER_APPROVED_SHA** to its full 40-character commit SHA. Changing main
   disables inventory until that new SHA is reviewed and reapproved. No arbitrary
   ref, input, command or code checkout is allowed by this first workflow.
7. Verify there are no queued/running jobs for this group and check runner
   membership/settings again before registration. Do not attach the host to a
   preexisting unknown group or queue.

Administrator read-only evidence export (replace numeric GROUP_ID and the
approved 40-character SHA; run on the administrator's own authenticated machine):

```bash
umask 077
gh api orgs/stormbots/actions/runner-groups/GROUP_ID > mint-group.json
gh api orgs/stormbots/actions/runner-groups/GROUP_ID/repositories > mint-repositories.json
python3 tests/runner_setup/group_policy.py mint-group.json mint-repositories.json APPROVED_40_CHARACTER_SHA
```

The local validator verifies snapshot contents only, not their freshness or API
origin. Recheck live settings as admin; include separate screenshots/read-only API
evidence of environment rules, main protection and approved SHA. Do not paste
registration tokens, PATs or .credentials files into chat or artifact uploads.
A snapshot pass alone never authorizes registration.

## Future host setup: copy/paste only after explicit approval

These steps are prepared instructions; **do not run them during this review**.
One-time changes require sudo on the spare host only. Use a dedicated unprivileged
account, not ryan (which has sudo and personal session access). No service,
passwordless sudo, Docker/libvirt group, router port forwarding or public SSH/VNC.
KVM membership is still significant host access, not a sandbox/security guarantee.
No host directories may be shared into future test guests.

```bash
sudo adduser --disabled-password --gecos '' sde-runner
sudo usermod -aG kvm sde-runner
sudo -iu sde-runner
```

If the account already exists, stop and inspect; do not reuse unknown state. In
that dedicated-account shell, download but do not run the reviewed runner:

```bash
umask 077
mkdir "$HOME/mint-runner-session"
cd "$HOME/mint-runner-session"
curl --fail --location --proto '=https' --proto-redir '=https' \
  --connect-timeout 20 --max-time 300 \
  -o actions-runner-linux-x64-2.338.0.tar.gz \
  https://github.com/actions/runner/releases/download/v2.338.0/actions-runner-linux-x64-2.338.0.tar.gz
printf '%s  %s\n' \
  af4b794c1bc41d73d40535e3fe092a39f9679cd8d965954c2aca25a05ca41d32 \
  actions-runner-linux-x64-2.338.0.tar.gz | sha256sum --check || exit 1
tar -xzf actions-runner-linux-x64-2.338.0.tar.gz
```

Version/digest came from the official actions/runner release API during this
review; the archive was not downloaded/executed. Reconfirm the current release
and security advisories before activation; do not silently substitute a new
version/hash or disable automatic security updates. Review missing dependencies
before installing anything. Do not blindly execute installdependencies.sh as root.

## Future registration and start: separate authorization gates

After admin settings are verified, obtain a short-lived **organization** runner
registration token from organization Settings > Actions > Runners > New
self-hosted runner. Select Linux/x64. Do not register through repository Settings.
The administrator must deliver the token directly to the operator privately.

The following config command prompts for the token interactively, avoiding
shell history/argv exposure. Do not add --token, --unattended or --replace:

```bash
./config.sh \
  --url https://github.com/stormbots \
  --runnergroup sde-mint-isolated \
  --name sde-mint-spare-once \
  --labels sde-mint-inventory \
  --no-default-labels \
  --work _work \
  --ephemeral
```

STOP after registration. Admin must confirm the runner is in the intended group,
no unexpected members exist, and workflow/repo restrictions still match. If
registration fails or the group is unavailable, never fall back to Default.

Only after a separately approved inventory dispatch is queued and settings
rechecked, run in the foreground (not root, not a service):

```bash
./run.sh
```

Ephemeral means one assigned job, not automatic disk cleanup or proof of which
job was assigned. Group policy is the scheduling boundary; labels only route.
The first job is read-only host inventory, not an interactive remote shell. The
runner is not yet a console controller or VM provisioner. A later approved
workflow revision is needed for media/console preparation, and a separate
explicit approval is needed for guest tests. Keep the terminal attended; the
five-minute job limit is not a hard cleanup or process-lifetime guarantee.

## Stop and teardown

No untrusted PR/event may use the group. Unexpected job, policy drift, failed
isolation or runner compatibility error: stop the runner, preserve sanitized
logs and keep it offline. Do not start guest work to troubleshoot registration.

After its one job, verify runner deregistration through the organization API/UI.
If interrupted before a job completes, an admin must remove the registration;
do not assume --ephemeral already removed an idle runner. If needed config.sh
remove uses its interactive removal-token prompt; never publish credentials.
Close the dedicated-user shell. Later authorized cleanup must remove only the
positively identified runner session/account, its credentials/workspace and any
owned VM artifacts. No recursive-delete/account-delete command is authorized by
this packet. Remove/revoke runner membership before deleting files. Consider
host reprovisioning if unexpected code executed; one-job registration does not
make the host disposable or clean.

## Review and source references

Local checks cover exact group/repository/ref policy rejection and static
workflow boundaries, including parsing the inline inventory program. No runner
binary, actual scheduling restriction, approval enforcement, host startup,
network connection, guest or cleanup was validated here. Production code and
existing workflows are unchanged. Labels, environment approval and job-level if
are defense in depth; they cannot replace scheduler-side group workflow policy.

- https://docs.github.com/en/enterprise-cloud@latest/actions/how-tos/manage-runners/self-hosted-runners/manage-access
- https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/manage-access
- https://docs.github.com/en/rest/actions/self-hosted-runner-groups
- https://docs.github.com/en/actions/reference/runners/self-hosted-runners
- https://github.com/actions/runner/releases/tag/v2.338.0
