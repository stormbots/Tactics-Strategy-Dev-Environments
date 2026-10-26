## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues for `stormbots/Tactics-Strategy-Dev-Environments`. Before reading or publishing tickets, read `docs/agents/issue-tracker.md`.

### Triage labels

Use the five default triage labels. Before applying triage labels, read `docs/agents/triage-labels.md`.

### Domain docs

Use a single-context layout: root `GLOSSARY.md` and `docs/adr/`. Before exploring the codebase, read `docs/agents/domain.md`.

## Execution efficiency

### Task boundaries

- Work toward the requested acceptance criteria. Avoid expanding scope into unrelated improvements or hardening unless required for correctness, security, or completion.
- Break substantial work into independently verifiable phases.
- Do not continue into another major phase without an explicit request or established acceptance criteria.

### Context and tool usage

- Prefer targeted file searches and reads over repeatedly inspecting entire files or directories.
- Avoid repeating commands that produce no new actionable information.
- Batch related inspections where practical.
- Prefer concise command output and failure-specific logs over complete successful test logs.

### Testing and CI

- Run targeted tests during implementation and broader validation when changes are ready.
- Do not rerun successful tests unless subsequent changes could invalidate their results.
- Use existing GitHub Actions workflows for authoritative cross-platform builds, installation tests, regression testing, and release gates.
- After triggering CI, inspect the initial run status and capture the run URL and commit SHA.
- Do not continuously poll CI or occupy an agent session waiting for long-running jobs.
- If CI is still running and no other actionable work remains, report the outstanding checks and end the turn.
- When CI results become available, investigate failures and review final evidence rather than repeatedly collecting unchanged results.
- Never bypass required validation or report pending checks as passing.

### Session handoff

When work is complete or blocked by an external process, provide a concise handoff containing:

- Completed work and relevant files.
- Commit SHA and branch, when applicable.
- Tests and validation already completed.
- Pending CI checks, with links when available.
- Outstanding risks, blockers, and acceptance criteria.
- The specific next action required.

Record durable project decisions in the repository rather than relying exclusively on conversation history.
